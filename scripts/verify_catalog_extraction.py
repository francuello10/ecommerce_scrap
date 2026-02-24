"""
verify_catalog_extraction.py
============================
Manual verification of the Catalog Extraction logic.
"""

import asyncio
from workers.web_monitor.extractors.vtex import VtexExtractor
from workers.web_monitor.extractors.shopify import ShopifyExtractor
from workers.web_monitor.models import EcommercePlatform

# Mock HTML for VTEX (truncated __STATE__)
VTEX_HTML = """
<html>
<body>
    <script>
        window.__STATE__ = {
            "Product:123": {
                "__typename": "Product",
                "productId": "SKU-999",
                "productName": "Zapatillas Nike Air Max",
                "brand": "Nike",
                "priceRange": {
                    "sellingPrice": {"lowPrice": 150000},
                    "listPrice": {"highPrice": 180000}
                },
                "items": [{"sellers": [{"commertialOffer": {"AvailableQuantity": 10}}]}]
            }
        };
    </script>
</body>
</html>
"""

# Mock HTML for Shopify (truncated meta)
SHOPIFY_HTML = """
<html>
<body>
    <script>
        window.meta = {
            "product": {
                "id": 456,
                "type": "Remera Adidas",
                "vendor": "Adidas",
                "variants": [
                    {"id": 789, "sku": "AD-101", "price": 4500000, "public_title": "Default Title"}
                ]
            }
        };
    </script>
</body>
</html>
"""

async def test():
    print("Testing VTEX extraction...")
    vtex = VtexExtractor(VTEX_HTML, {})
    v_data = await vtex.extract_product()
    print(f"VTEX extracted: {v_data}")

    print("\nTesting Shopify extraction...")
    shopify = ShopifyExtractor(SHOPIFY_HTML, {})
    s_data = await shopify.extract_product()
    print(f"Shopify extracted: {s_data}")

if __name__ == "__main__":
    asyncio.run(test())
