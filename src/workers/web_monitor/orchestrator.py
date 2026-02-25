"""
Web Monitor Orchestrator — ARQ Job
====================================
Main ARQ job that:
1. Reads active monitored_pages from DB
2. Checks client's feature flags
3. Downloads HTML (HTTPX, Playwright fallback)
4. Routes to correct extractor via ExtractorFactory
5. Saves PageSnapshot + DetectedSignal to DB

This is the heart of the daily monitoring cron.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from playwright.async_api import async_playwright
import httpx

from curl_cffi.requests import AsyncSession as CurlSession, RequestsError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.models import (
    CompetitorStatus,
    MonitoredPage,
    PageSnapshot,
    SnapshotStatus,
    CrawlRun,
    JobStatus,
    DetectedSignal,
    SignalSource,
    SignalType,
    PageType,
    Product,
    ProductVariant,
    PriceHistory,
)
from workers.web_monitor.models import ProductData, VariantData
from workers.web_monitor.platform_detector import PlatformDetector
from workers.web_monitor.extractor_factory import ExtractorFactory
from workers.tech_fingerprint.fingerprinter import TechFingerprinter
from workers.diff_engine.analyzer import analyze_changes


logger = logging.getLogger(__name__)

# HTTP client config
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
}
REQUEST_TIMEOUT = 30.0


async def fetch_page_html(url: str) -> tuple[str, dict[str, str]]:
    """
    Fetch a URL and return (html_content, response_headers).
    Raises RequestsError on failure.
    """
    async with CurlSession(
        headers=DEFAULT_HEADERS,
        timeout=REQUEST_TIMEOUT,
        impersonate="chrome120",
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text, dict(response.headers)


async def _capture_homepage_screenshot(url: str, snapshot_id: int) -> str | None:
    """Capture a visual screenshot of a homepage using Playwright."""
    try:
        os.makedirs("public/snapshots", exist_ok=True)
        filepath = f"public/snapshots/snapshot_{snapshot_id}.jpg"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(
                user_agent=DEFAULT_HEADERS["User-Agent"]
            )
            await page.set_viewport_size({"width": 1280, "height": 800})
            
            # Fast navigation, wait for domcontentloaded to handle 403 pages smoothly
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(3000)
            except Exception as nav_e:
                logger.debug("Playwright navigation incomplete, but taking screenshot anyway: %s", nav_e)
            
            await page.screenshot(path=filepath, type="jpeg", quality=60, full_page=False)
            await browser.close()
            
            # Subir a Directus
            url_upload = f"{settings.directus_url}/files"
            headers = {"Authorization": f"Bearer {settings.directus_key}"} if settings.directus_key else {}
            
            try:
                with open(filepath, "rb") as fp:
                    files = {"file": (f"snapshot_{snapshot_id}.jpg", fp, "image/jpeg")}
                    data = {"title": f"Snapshot {snapshot_id} - {url}"}
                    
                    async with httpx.AsyncClient() as client:
                        resp = await client.post(url_upload, headers=headers, files=files, data=data)
                        if resp.status_code == 200:
                            file_id = resp.json().get("data", {}).get("id")
                            logger.info("Screenshot subido a Directus exitosamente: UUID %s", file_id)
                            return file_id
                        else:
                            logger.error("Error subiendo screenshot a Directus: %s", resp.text)
                            return f"/public/snapshots/snapshot_{snapshot_id}.jpg"
            except Exception as up_e:
                logger.error("Fallo la subida a Directus: %s", up_e)
                return f"/public/snapshots/snapshot_{snapshot_id}.jpg"
                
    except Exception as e:
        logger.warning("Failed to capture screenshot for %s: %s", url, e)
        return None


async def process_monitored_page(
    session: AsyncSession,
    page: MonitoredPage,
    run_id: int,
) -> bool:
    """
    Process a single monitored page:
    1. Fetch HTML
    2. Detect platform
    3. Extract signals
    4. Save snapshot + signals

    Returns True on success, False on failure.
    """
    logger.info("Processing page: %s", page.url)

    # 1. Fetch HTML
    try:
        html, headers = await fetch_page_html(page.url)
    except RequestsError as exc:
        logger.warning("Failed to fetch %s: %s", page.url, exc)
        # Save error snapshot
        snapshot = PageSnapshot(
            monitored_page_id=page.id,
            run_id=run_id,
            status=SnapshotStatus.ERROR,
        )
        session.add(snapshot)
        return False

    # 2. Save raw snapshot
    snapshot = PageSnapshot(
        monitored_page_id=page.id,
        run_id=run_id,
        status=SnapshotStatus.PENDING_EXTRACTION,
    )
    session.add(snapshot)
    await session.flush()  # get snapshot.id

    if page.page_type == PageType.HOMEPAGE:
        logger.info("  📸 Capturing visual screenshot for homepage...")
        screenshot_path = await _capture_homepage_screenshot(page.url, snapshot.id)
        if screenshot_path:
            # We save the absolute filesystem path so python/directus can eventually map it
            # For this MVP, we save it as a local URL reference
            snapshot.screenshot_url = f"file://{os.path.abspath(screenshot_path)}"

    # 3. Detect platform
    detector = PlatformDetector()
    platform = detector.detect(html, headers)
    logger.info("  Platform detected: %s", platform)

    # 4. Get extractor and extract signals
    extractor = ExtractorFactory.create(platform, html, headers, page.url)
    result = await extractor.extract_all()
    logger.info(
        "  Extracted: %d promos, %d financing, %d CTAs",
        len(result.promos),
        len(result.financing),
        len(result.ctas),
    )

    # 5. Save detected signals
    signals_saved = 0
    for promo in result.promos:
        signal = DetectedSignal(
            source_type=SignalSource.WEB,
            snapshot_id=snapshot.id,
            raw_text_found=promo.raw_text,
            confidence_score=promo.confidence,
        )
        session.add(signal)
        signals_saved += 1

    for fin in result.financing:
        signal = DetectedSignal(
            source_type=SignalSource.WEB,
            snapshot_id=snapshot.id,
            raw_text_found=fin.raw_text,
            confidence_score=fin.confidence,
        )
        session.add(signal)
        signals_saved += 1

    for cta in result.ctas:
        signal = DetectedSignal(
            source_type=SignalSource.WEB,
            snapshot_id=snapshot.id,
            raw_text_found=cta.text,
            confidence_score=0.9,
        )
        session.add(signal)
        signals_saved += 1

    # 6. Save Catalog Data (if extracted)
    if result.products:
        for product_data in result.products:
            await _save_product_data(session, page, snapshot.id, product_data)
        logger.info("  Catalog data saved for %d products", len(result.products))

    # 7. Mark snapshot as extracted
    snapshot.status = SnapshotStatus.EXTRACTED
    logger.info("  Saved %d signals for snapshot #%d", signals_saved, snapshot.id)

    # 7. Run Tech Fingerprinting (if homepage)
    if page.page_type == PageType.HOMEPAGE:
        fingerprinter = TechFingerprinter()
        await fingerprinter.fingerprint_competitor(session, page.competitor_id, page.url, html=html)
        logger.info("  Fingerprinted tech stack for competitor %d", page.competitor_id)

    # 8. Run Diff Engine to detect changes
    events = await analyze_changes(session, page)
    if events:
        logger.info("  Diff Engine detected %d changes", len(events))

    return True


async def _save_product_data(
    session: AsyncSession,
    page: MonitoredPage,
    snapshot_id: int,
    data: ProductData,
) -> None:
    """Save/Update product, its variants, and add price history entry."""
    # 1. Ensure Product exists
    # If we have a SKU, use SKU + competitor_id. Otherwise fallback to URL.
    if data.sku:
        stmt = select(Product).where(
            Product.competitor_id == page.competitor_id,
            Product.sku == data.sku
        )
    else:
        stmt = select(Product).where(
            Product.competitor_id == page.competitor_id,
            Product.url == page.url
        )
    
    res = await session.execute(stmt)
    product = res.scalar_one_or_none()
    
    if not product:
        product = Product(
            competitor_id=page.competitor_id,
            sku=data.sku,
            url=page.url if not data.url else data.url,
            brand=data.brand,
            title=data.title,
            category_path=data.category_path,
            category_tree=data.category_tree,
            description=data.description,
            images=data.images,
            current_price=data.sale_price or data.list_price,
            financing_options={"installments": data.installments} if data.installments else None,
            discovered_from=data.source_url or page.url,
            rating_avg=data.rating,
            review_count=data.review_count,
            badges=data.badges,
        )
        session.add(product)
        await session.flush()
    else:
        # Update metadata if changed
        product.title = data.title or product.title
        product.brand = data.brand or product.brand
        product.category_path = data.category_path or product.category_path
        product.category_tree = data.category_tree or product.category_tree
        product.description = data.description or product.description
        product.images = data.images or product.images
        product.current_price = data.sale_price or data.list_price or product.current_price
        product.financing_options = {"installments": data.installments} if data.installments else product.financing_options
        product.discovered_from = data.source_url or product.discovered_from or page.url
        product.rating_avg = data.rating or product.rating_avg
        product.review_count = data.review_count or product.review_count
        product.badges = data.badges or product.badges
        product.is_active = True

    # 2. Save Variants (if any)
    if data.variants:
        for v_data in data.variants:
            v_stmt = select(ProductVariant).where(
                ProductVariant.product_id == product.id,
                ProductVariant.sku == v_data.sku
            )
            v_res = await session.execute(v_stmt)
            variant = v_res.scalar_one_or_none()
            
            if not variant:
                variant = ProductVariant(
                    product_id=product.id,
                    sku=v_data.sku,
                    title=v_data.title,
                    is_in_stock=v_data.is_in_stock,
                    list_price=v_data.list_price,
                    sale_price=v_data.sale_price,
                    raw_metadata=v_data.raw_metadata
                )
                session.add(variant)
            else:
                variant.title = v_data.title or variant.title
                variant.is_in_stock = v_data.is_in_stock
                variant.list_price = v_data.list_price or variant.list_price
                variant.sale_price = v_data.sale_price or variant.sale_price

    # 3. Add Price History (Main Product)
    history = PriceHistory(
        product_id=product.id,
        snapshot_id=snapshot_id,
        list_price=data.list_price,
        sale_price=data.sale_price,
        currency=data.currency or "ARS",
        is_in_stock=data.is_in_stock,
    )
    session.add(history)


async def run_web_monitor(ctx: dict) -> dict:
    """
    ARQ job entry point.
    Fetches and processes all active monitored pages.
    """
    from core.database import async_session_factory
    
    async with async_session_factory() as session:
        # Create a CrawlRun to group this execution
        run = CrawlRun(started_at=datetime.now(timezone.utc))
        session.add(run)
        await session.flush()
        logger.info("🕷️  CrawlRun #%d started", run.id)

        # Fetch all active monitored pages for ACTIVE competitors
        result = await session.execute(
            select(MonitoredPage)
            .join(MonitoredPage.competitor)
            .where(
                MonitoredPage.is_active == True,
            )
            .order_by(MonitoredPage.competitor_id, MonitoredPage.id)
        )
        pages = result.scalars().all()
        logger.info("  Found %d active pages to monitor", len(pages))

        successes = 0
        failures = 0
        for page in pages:
            success = await process_monitored_page(session, page, run.id)
            if success:
                successes += 1
            else:
                failures += 1

        # Finalize run
        run.ended_at = datetime.now(timezone.utc)
        run.status = JobStatus.SUCCESS if failures == 0 else JobStatus.FAILED_PARTIAL
        await session.commit()

        logger.info(
            "🏁 CrawlRun #%d finished — %d success, %d failures",
            run.id, successes, failures,
        )
        return {"successes": successes, "failures": failures, "run_id": run.id}
