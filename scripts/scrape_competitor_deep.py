import asyncio
import logging
import argparse
from typing import List, Set
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession as CurlSession

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import async_session_factory
from core.models import Competitor, Product, ProductVariant
from core.config import settings
from workers.web_monitor.platform_detector import PlatformDetector
from workers.web_monitor.extractor_factory import ExtractorFactory
from workers.web_monitor.models import ProductData

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s")
logger = logging.getLogger("deep_scraper")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
}

async def fetch_urls_from_sitemap(sitemap_url: str, limit: int = 50) -> List[str]:
    """Recursively fetches URLs from sitemaps, looking for product-like URLs."""
    urls_found = set()
    sitemaps_to_visit = [sitemap_url]
    visited_sitemaps = set()
    
    async with CurlSession(impersonate="chrome120", timeout=30.0) as client:
        while sitemaps_to_visit and (limit <= 0 or len(urls_found) < limit):
            current_sitemap = sitemaps_to_visit.pop(0)
            if current_sitemap in visited_sitemaps:
                continue
                
            visited_sitemaps.add(current_sitemap)
            logger.info("Fetching sitemap: %s", current_sitemap)
            
            try:
                response = await client.get(current_sitemap, headers=DEFAULT_HEADERS)
                
                # Save sitemap to local storage
                import os
                from urllib.parse import urlparse
                from pathlib import Path
                
                parsed_url = urlparse(current_sitemap)
                file_name = os.path.basename(parsed_url.path) or "sitemap.xml"
                domain = parsed_url.netloc.replace("www.", "")
                
                save_dir = Path("storage/sitemaps") / domain
                save_dir.mkdir(parents=True, exist_ok=True)
                
                save_path = save_dir / file_name
                save_path.write_text(response.text, encoding="utf-8")
                logger.info("Saved sitemap to %s", save_path)
                
                soup = BeautifulSoup(response.text, "xml")
                
                # If it's a sitemap index, queue sub-sitemaps
                sitemap_tags = soup.find_all("sitemap")
                for s in sitemap_tags:
                    loc = s.find("loc")
                    if loc and loc.text:
                        # Prioritize product sitemaps
                        if "product" in loc.text.lower():
                            sitemaps_to_visit.insert(0, loc.text) # Push to front
                        else:
                            sitemaps_to_visit.append(loc.text)
                
                # If it contains URLs, add them
                url_tags = soup.find_all("url")
                for u in url_tags:
                    loc = u.find("loc")
                    if loc and loc.text:
                        url_str = loc.text.strip()
                        urls_found.add(url_str)
                        if limit > 0 and len(urls_found) >= limit:
                            break
                            
            except Exception as e:
                logger.error("Failed fetching sitemap %s: %s", current_sitemap, e)
                
    # Basic heuristic to filter out general pages/categories if possible
    # We'll just return all for now, limiting to `limit` if it's > 0
    urls_list = list(urls_found)
    return urls_list[:limit] if limit > 0 else urls_list

async def fetch_page_html(url: str) -> tuple[str, dict]:
    async with CurlSession(impersonate="chrome120", timeout=15.0) as client:
        response = await client.get(url, headers=DEFAULT_HEADERS)
        return response.text, dict(response.headers)

async def _upload_file_to_directus(file_path_or_url: str, is_url: bool = True, title: str = "") -> str | None:
    if not settings.directus_key:
        return None
        
    url_upload = f"{settings.directus_url}/files"
    headers = {"Authorization": f"Bearer {settings.directus_key}"}
    import httpx
    import os
    
    try:
        if is_url:
            async with httpx.AsyncClient() as client:
                resp = await client.get(file_path_or_url)
                if resp.status_code == 200:
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                        tmp.write(resp.content)
                        tmp_path = tmp.name
                        
                    with open(tmp_path, "rb") as fp:
                        files = {"file": (os.path.basename(file_path_or_url) or "image.jpg", fp, "image/jpeg")}
                        data = {"title": title}
                        upload_resp = await client.post(url_upload, headers=headers, files=files, data=data)
                        
                    os.unlink(tmp_path)
                    
                    if upload_resp.status_code == 200:
                        return upload_resp.json().get("data", {}).get("id")
        else:
            with open(file_path_or_url, "rb") as fp:
                files = {"file": (os.path.basename(file_path_or_url), fp, "application/xml")}
                data = {"title": title}
                async with httpx.AsyncClient() as client:
                    upload_resp = await client.post(url_upload, headers=headers, files=files, data=data)
                    if upload_resp.status_code == 200:
                        return upload_resp.json().get("data", {}).get("id")
                        
    except Exception as e:
        logger.error("Failed to upload to Directus: %s", e)
    return None

async def _save_deep_product(session: AsyncSession, comp_id: int, url: str, data: ProductData) -> None:
    # Uses similar logic to orchestrator.py, adapted for missing MonitoredPage
    if data.sku:
        stmt = select(Product).where(Product.competitor_id == comp_id, Product.sku == data.sku)
    else:
        stmt = select(Product).where(Product.competitor_id == comp_id, Product.url == url)
        
    res = await session.execute(stmt)
    product = res.scalar_one_or_none()
    
    # Upload image to Directus
    directus_image_id = None
    if getattr(product, 'directus_image_id', None) is None and getattr(data, 'images', []):
        try:
            image_url = data.images[0] if isinstance(data.images, list) else data.images
            directus_image_id = await _upload_file_to_directus(image_url, is_url=True, title=data.title[:100] if data.title else "Product Image")
        except:
            pass
            
    if not product:
        product = Product(
            competitor_id=comp_id,
            sku=data.sku,
            url=url if not data.url else data.url,
            brand=data.brand,
            title=data.title,
            category_path=data.category_path,
            category_tree=data.category_tree,
            description=data.description,
            images=data.images,
            current_price=data.sale_price or data.list_price,
            financing_options={"installments": data.installments} if data.installments else None,
            discovered_from="SIETEMAP_DEEP_CRAWL",
            rating_avg=data.rating,
            review_count=data.review_count,
            badges=data.badges,
            directus_image_id=directus_image_id,
        )
        session.add(product)
        await session.flush()
    else:
        product.current_price = data.sale_price or data.list_price
        product.images = data.images if data.images else product.images
        product.title = data.title if data.title else product.title
        if directus_image_id:
            product.directus_image_id = directus_image_id
        
    # Variables
    for vdata in data.variants:
        v_stmt = select(ProductVariant).where(
            ProductVariant.product_id == product.id,
            ProductVariant.sku == vdata.sku
        )
        vres = await session.execute(v_stmt)
        variant = vres.scalar_one_or_none()
        
        if not variant:
            variant = ProductVariant(
                product_id=product.id,
                sku=vdata.sku,
                title=vdata.title,
                is_in_stock=vdata.is_in_stock,
                list_price=vdata.list_price,
                sale_price=vdata.sale_price,
                raw_metadata=vdata.raw_metadata,
            )
            session.add(variant)
        else:
            variant.is_in_stock = vdata.is_in_stock
            variant.sale_price = vdata.sale_price
            variant.list_price = vdata.list_price

async def process_url(session: AsyncSession, comp_id: int, url: str):
    logger.info("Scraping %s", url)
    try:
        html, headers = await fetch_page_html(url)
        detector = PlatformDetector()
        platform = detector.detect(html, headers)
        
        extractor = ExtractorFactory.create(platform, html, headers, url)
        result = await extractor.extract_all()
        
        if result.products:
            logger.info("Found %d products on URL. Saving...", len(result.products))
            for pdata in result.products:
                await _save_deep_product(session, comp_id, url, pdata)
            await session.commit()
            return True
        else:
            logger.debug("No products found on %s", url)
            return False
    except Exception as e:
        logger.error("Error scraping %s: %s", url, e)
        return False

async def async_main(domain: str, limit: int):
    async with async_session_factory() as session:
        stmt = select(Competitor).where(Competitor.domain == domain)
        res = await session.execute(stmt)
        comp = res.scalar_one_or_none()
        
        if not comp:
            logger.error("Competitor %s not found in database.", domain)
            return
            
        logger.info("Target: %s (ID: %d)", comp.name, comp.id)
        
        # Determine sitemap URL
        scheme = "https"
        sitemap_url = f"{scheme}://www.{domain}/sitemap.xml"
        
        urls = await fetch_urls_from_sitemap(sitemap_url, limit=limit)
        logger.info("Found %d URLs to process.", len(urls))
        
        # Upload Sitemap to Directus
        sitemap_path = f"storage/sitemaps/{domain}/sitemap.xml"
        import os
        if os.path.exists(sitemap_path) and not getattr(comp, 'sitemap_file_id', None):
            logger.info("Uploading sitemap to Directus...")
            sitemap_id = await _upload_file_to_directus(sitemap_path, is_url=False, title=f"Sitemap {domain}")
            if sitemap_id:
                comp.sitemap_file_id = sitemap_id
                await session.commit()
                logger.info("Sitemap uploaded. UUID: %s", sitemap_id)
        
        success = 0
        for i, url in enumerate(urls, 1):
            logger.info("Progress: %d/%d", i, len(urls))
            res = await process_url(session, comp.id, url)
            if res:
                success += 1
                
        logger.info("Finished deep crawl. Successfully extracted product data from %d/%d URLs.", success, len(urls))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deep Competitor Scraper via Sitemap")
    parser.add_argument("--domain", type=str, required=True, help="Competitor domain (e.g. newsport.com.ar)")
    parser.add_argument("--limit", type=int, default=0, help="Max URLs to process (0 = all)")
    args = parser.parse_args()
    
    asyncio.run(async_main(args.domain, args.limit))
