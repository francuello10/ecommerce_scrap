"""
Newsletter Monitor — IMAP Reader.

Connects to the monitoring inbox, fetches new emails, matches them
to known competitor domains, and saves raw messages for parsing.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from email.utils import parseaddr

from imap_tools import AND, MailBox, MailMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import Competitor, NewsletterAccount, NewsletterMessage

logger = logging.getLogger(__name__)


class ImapReader:
    """Reads competitor newsletters from a monitoring inbox."""

    def __init__(self, account: NewsletterAccount) -> None:
        self.account = account

    async def fetch_new_messages(
        self,
        session: AsyncSession,
        since_hours: int = 24,
    ) -> list[NewsletterMessage]:
        """
        Fetch new emails and match them to competitors by domain.

        Returns list of created NewsletterMessage records.
        """
        since_date = datetime.utcnow() - timedelta(hours=since_hours)

        # Get all known competitor domains
        result = await session.execute(select(Competitor.domain, Competitor.id))
        domain_map: dict[str, int] = {
            row.domain.lower(): row.id for row in result.all()
        }

        created_messages: list[NewsletterMessage] = []

        try:
            with MailBox(self.account.imap_host, self.account.imap_port).login(
                self.account.email_address,
                self._get_password(),
            ) as mailbox:
                for msg in mailbox.fetch(
                    AND(date_gte=since_date.date()),
                    reverse=True,
                    limit=200,
                ):
                    competitor_id = self._match_competitor(msg, domain_map)
                    if not competitor_id:
                        continue

                    newsletter_msg = await self._save_message(
                        session, msg, competitor_id
                    )
                    if newsletter_msg:
                        created_messages.append(newsletter_msg)

            await session.commit()
            logger.info(
                "Fetched %d new newsletter messages from %s",
                len(created_messages),
                self.account.email_address,
            )

        except Exception as e:
            logger.error("IMAP fetch failed for %s: %s", self.account.email_address, e)
            raise

        return created_messages

    def _match_competitor(
        self, msg: MailMessage, domain_map: dict[str, int]
    ) -> int | None:
        """Match email sender to a known competitor domain."""
        _, sender_email = parseaddr(msg.from_)
        if not sender_email:
            return None

        sender_domain = sender_email.split("@")[-1].lower()

        # Direct domain match
        for comp_domain, comp_id in domain_map.items():
            # Match newsletter@newsport.com.ar → newsport.com.ar
            if sender_domain == comp_domain or sender_domain.endswith(f".{comp_domain}"):
                return comp_id

        return None

    async def _save_message(
        self,
        session: AsyncSession,
        msg: MailMessage,
        competitor_id: int,
    ) -> NewsletterMessage | None:
        """Save a newsletter message to the database."""
        # Check for duplicates by subject + date
        existing = await session.execute(
            select(NewsletterMessage).where(
                NewsletterMessage.competitor_id == competitor_id,
                NewsletterMessage.subject == msg.subject,
                NewsletterMessage.received_at == msg.date,
            )
        )
        if existing.scalar_one_or_none():
            return None

        is_optin = self._is_optin_email(msg)

        newsletter_msg = NewsletterMessage(
            competitor_id=competitor_id,
            newsletter_account_id=self.account.id,
            sender_email=msg.from_,
            subject=msg.subject,
            received_at=msg.date,
            is_optin_confirmation=is_optin,
            status="RECEIVED",
        )
        session.add(newsletter_msg)
        return newsletter_msg

    def _is_optin_email(self, msg: MailMessage) -> bool:
        """Detect double opt-in confirmation emails."""
        subject_lower = (msg.subject or "").lower()
        optin_keywords = [
            "confirma",
            "confirm",
            "verificar",
            "verify",
            "suscripción",
            "subscription",
            "opt-in",
            "activar",
        ]
        return any(kw in subject_lower for kw in optin_keywords)

    def _get_password(self) -> str:
        """Get IMAP password from env config."""
        from core.config import settings
        return settings.email_server_password
