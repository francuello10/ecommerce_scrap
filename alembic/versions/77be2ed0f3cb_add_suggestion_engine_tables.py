"""add_suggestion_engine_tables

Revision ID: 77be2ed0f3cb
Revises: 95cff26e2644
Create Date: 2026-02-24 02:41:35.299847

Adds:
- industry table (business verticals)
- competitor_industry junction table (N:N with CompetitorLevel)
- client.industry_id FK
- subscription_tier.enable_competitor_suggestions flag
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "77be2ed0f3cb"
down_revision: Union[str, Sequence[str], None] = "95cff26e2644"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- Industry table --
    op.create_table(
        "industry",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon_emoji", sa.String(length=10), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )

    # -- Competitor ↔ Industry junction --
    op.create_table(
        "competitor_industry",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("competitor_id", sa.BigInteger(), nullable=False),
        sa.Column("industry_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "level",
            sa.Enum("GLOBAL_BENCHMARK", "REGIONAL_RIVAL", "DIRECT_RIVAL", name="competitorlevel"),
            nullable=False,
        ),
        sa.Column("is_suggested", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["competitor_id"], ["competitor.id"]),
        sa.ForeignKeyConstraint(["industry_id"], ["industry.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("competitor_id", "industry_id", name="uq_competitor_industry"),
    )

    # -- Client.industry_id FK --
    op.add_column("client", sa.Column("industry_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key("fk_client_industry", "client", "industry", ["industry_id"], ["id"])

    # -- Feature flag on subscription_tier --
    op.add_column(
        "subscription_tier",
        sa.Column("enable_competitor_suggestions", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_column("subscription_tier", "enable_competitor_suggestions")
    op.drop_constraint("fk_client_industry", "client", type_="foreignkey")
    op.drop_column("client", "industry_id")
    op.drop_table("competitor_industry")
    op.execute("DROP TYPE IF EXISTS competitorlevel")
    op.drop_table("industry")
