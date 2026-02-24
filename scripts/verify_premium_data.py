import asyncio
import logging
import json
from workers.web_monitor.extractor_factory import ExtractorFactory
from workers.web_monitor.models import EcommercePlatform

logging.basicConfig(level=logging.INFO)

TEST_URLS = [
    {
        "name": "Newsport (VTEX) - Gorra",
        "url": "https://www.newsport.com.ar/gorra-adidas-audi-one-team-nico-hulkenberg-ke9077/p",
        "platform": EcommercePlatform.VTEX
    },
    {
        "name": "Dexter (Salesforce) - Reebok",
        "url": "https://www.dexter.com.ar/mochila-reebok-19-pulgadas/RE60061N.html",
        "platform": EcommercePlatform.SALESFORCE
    }
]

async def test_premium_extraction():
    import httpx
    
    async with httpx.AsyncClient(timeout=30) as client:
        for test in TEST_URLS:
            print(f"\n🚀 Testing Premium Data: {test['name']}")
            print(f"🔗 URL: {test['url']}")
            
            try:
                resp = await client.get(test['url'])
                resp.raise_for_status()
                html = resp.text
                headers = dict(resp.headers)
                
                extractor = ExtractorFactory.create(test['platform'], html, headers, test['url'])
                products = await extractor.extract_products()
                
                print(f"📦 Products Found: {len(products)}")
                
                for i, p in enumerate(products[:1]):
                    print(f"\n--- Product {i+1}: {p.title} ---")
                    print(f"✅ SKU: {p.sku}")
                    print(f"✅ Desc: {p.description[:100]}..." if p.description else "❌ No Description")
                    print(f"✅ Images: {len(p.images)} found" if p.images else "❌ No Images")
                    if p.images:
                        print(f"   First Image: {p.images[0]}")
                    print(f"✅ Cat Tree: {' > '.join(p.category_tree)}" if p.category_tree else "❌ No Category Tree")
                    print(f"✅ Installments: {p.installments}" if p.installments else "❌ No Installments")
                    print(f"✅ Source: {p.source_url}")
                    print(f"✅ Metadata: {json.dumps(p.raw_metadata)}")
                    
            except Exception as e:
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_premium_extraction())
