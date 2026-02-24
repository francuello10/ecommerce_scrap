import asyncio
import logging
from workers.web_monitor.extractor_factory import ExtractorFactory
from workers.web_monitor.models import EcommercePlatform

logging.basicConfig(level=logging.INFO)

MOCK_HTML_SFCC = """
<body>
<div class="product-detail" data-pid="SFCC-PROD-123">
    <h1 class="pdp-title">Zapatillas Nike Air Max</h1>
    <div class="price"><span class="value">$ 150.999,00</span></div>
</div>
</body>
"""

MOCK_HTML_MAGENTO = """
<body>
<div class="price-box" data-product-id="MAG-456">
    <span class="price">$ 99.000,00</span>
</div>
<div class="installment-block">6 cuotas sin interés</div>
</body>
"""

MOCK_HTML_VTEX_IO = """
<script>window.__STATE__ = {"Product:123": {"__typename": "Product", "productId": "VTEX-IO-789", "productName": "Nike Sport" }};</script>
"""

async def run_test():
    headers = {"user-agent": "test"}
    
    # Test Salesforce
    print("\n--- Testing Salesforce (Dexter/Puma/Adidas) ---")
    sf_ext = ExtractorFactory.create(EcommercePlatform.SALESFORCE, MOCK_HTML_SFCC, headers)
    sf_prod = await sf_ext.extract_product()
    print(f"SKU: {sf_prod.sku if sf_prod else 'NOT FOUND'}")
    print(f"Price: {sf_prod.list_price if sf_prod else 'NOT FOUND'}")

    # Test Magento
    print("\n--- Testing Magento (Solo Deportes) ---")
    mg_ext = ExtractorFactory.create(EcommercePlatform.MAGENTO, MOCK_HTML_MAGENTO, headers)
    mg_res = await mg_ext.extract_all()
    print(f"Metadata: {mg_res.raw_metadata}")

    # Test VTEX IO
    print("\n--- Testing VTEX IO (Nike/Sporting) ---")
    vt_ext = ExtractorFactory.create(EcommercePlatform.VTEX, MOCK_HTML_VTEX_IO, headers)
    vt_prod = await vt_ext.extract_product()
    print(f"SKU: {vt_prod.sku if vt_prod else 'NOT FOUND'}")
    print(f"Name: {vt_prod.title if vt_prod else 'NOT FOUND'}")

if __name__ == "__main__":
    asyncio.run(run_test())
