"""VTEX IO / VTEX Legacy extractor.

Strategy: Extract from __STATE__ JSON pre-rendered in HTML.
Fallback: Generic HTML regex extraction (inherited from GenericHtmlExtractor).
"""

from __future__ import annotations

import json
import logging
import re

from workers.web_monitor.extractors.generic_html import GenericHtmlExtractor
from workers.web_monitor.models import ExtractionResult, EcommercePlatform, PromoSignal, ProductData, VariantData

from scrapling import Selector

logger = logging.getLogger(__name__)

# VTEX stores page state in a window.__STATE__ JSON object
_STATE_PATTERN = re.compile(r"window\.__STATE__\s*=\s*(\{.*?\})\s*(?:;|</script>)", re.DOTALL)
_DATA_PATTERN = re.compile(r"vtex-data\s*=\s*(\{.*?\})\s*(?:;|</script>)", re.DOTALL)


class VtexExtractor(GenericHtmlExtractor):
    """VTEX-specific extractor. Reads window.__STATE__ for pre-rendered data."""

    def __init__(self, html: str, headers: dict[str, str], url: str | None = None) -> None:
        super().__init__(html, headers, url)
        self._platform = EcommercePlatform.VTEX

    async def extract_all(self) -> ExtractionResult:
        result = await super().extract_all()
        result.platform_detected = EcommercePlatform.VTEX

        # Try to enhance with __STATE__ data
        state = self._parse_state()
        if state:
            logger.debug("VTEX __STATE__ found (%d keys)", len(state))
            # Enhance signals if needed...
        else:
            logger.debug("VTEX __STATE__ not found, using generic extraction only")

        return result

    async def extract_product(self) -> ProductData | None:
        """
        Extract VTEX product data from __STATE__.
        """
        products = await self.extract_products()
        return products[0] if products else await super().extract_product()

    async def extract_products(self) -> list[ProductData]:
        """
        Extract ALL products and their variants from VTEX STATE using a relational map.
        This follows the Apollo/GQL normalized state structure.
        """
        state = self._parse_state()
        if not state:
            return await self._extract_products_internal()

        # 1. Build a local relational map
        objects_by_type = {} # typename -> {id -> data}
        for key, val in state.items():
            if not isinstance(val, dict): continue
            tname = val.get("__typename")
            if tname:
                if tname not in objects_by_type: objects_by_type[tname] = {}
                objects_by_type[tname][key] = val

        # 2. Extract Offers (Pricing)
        offers = {} # key -> price_info
        for key, val in objects_by_type.get("CommertialOffer", {}).items():
            offers[key] = {
                "sale_price": val.get("Price") or val.get("price") or val.get("spotPrice"),
                "list_price": val.get("ListPrice") or val.get("listPrice"),
                "available": val.get("AvailableQuantity", 0) > 0
            }

        # 3. Extract SKUs (Variants)
        skus = {} # key -> VariantData
        for key, val in objects_by_type.get("SKU", {}).items():
            sku_id = val.get("itemId") or val.get("id")
            
            # Follow pointers to find associated offer
            best_offer = {"sale_price": None, "list_price": None, "available": False}
            
            # SKUs usually have sellers, and each seller has a commertialOffer
            sellers = val.get("sellers", [])
            for s_ref in sellers:
                seller_obj = self._resolve_vtex_pointer(s_ref, state)
                offer_ref = seller_obj.get("commertialOffer")
                if offer_ref:
                    offer_obj = self._resolve_vtex_pointer(offer_ref, state)
                    # Use typename for safety or just check keys
                    if offer_obj.get("__typename") == "CommertialOffer" or "Price" in offer_obj:
                         best_offer = {
                            "sale_price": offer_obj.get("Price") or offer_obj.get("price") or offer_obj.get("spotPrice"),
                            "list_price": offer_obj.get("ListPrice") or offer_obj.get("listPrice"),
                            "available": offer_obj.get("AvailableQuantity", 0) > 0
                         }
                         if best_offer["sale_price"]: break

            skus[key] = VariantData(
                sku=sku_id,
                title=val.get("name") or val.get("nameComplete"),
                is_in_stock=best_offer["available"],
                list_price=best_offer["list_price"],
                sale_price=best_offer["sale_price"],
                raw_metadata={"vtex_key": key}
            )

        # 4. Extract Products
        extracted_products = []
        for key, val in objects_by_type.get("Product", {}).items():
            prod_id = val.get("productId")
            product_variants = []
            
            # Premium Data Extraction
            description = val.get("description")
            all_images = []
            
            # Follow item pointers
            items = val.get("items", [])
            for item_ref in items:
                item_obj = self._resolve_vtex_pointer(item_ref, state)
                i_key = item_ref.get("id") if isinstance(item_ref, dict) else item_ref
                
                # Extract images from item/SKU
                sku_images = item_obj.get("images", [])
                for img_ref in sku_images:
                    img_obj = self._resolve_vtex_pointer(img_ref, state)
                    img_url = img_obj.get("imageUrl")
                    if img_url and img_url not in all_images:
                        all_images.append(img_url)

                if i_key in skus:
                    product_variants.append(skus[i_key])
                else:
                    item_id_in_map = item_obj.get("id") or item_obj.get("itemId")
                    if item_id_in_map in skus:
                        product_variants.append(skus[item_id_in_map])

            # Building ProductData with resolved priceRange
            price_info = self._get_vtex_price_range(val, product_variants, state)
            
            # Extract category path and tree safely
            cats = val.get("categories")
            cat_path = None
            cat_tree = []
            if isinstance(cats, list) and cats:
                cat_path = cats[0] # e.g. "/Accesorios/Gorras/"
                cat_tree = [c for c in cat_path.split("/") if c]
            elif isinstance(cats, dict):
                cat_path = cats.get("0") or cats.get("id")

            # Extract installments (cuotas) from state if available
            installments = None
            if items:
                # Try to find financing info in the first SKU's teasers or sellers
                item_obj = self._resolve_vtex_pointer(items[0], state)
                sellers = item_obj.get("sellers", [])
                for seller_ref in sellers:
                    seller_obj = self._resolve_vtex_pointer(seller_ref, state)
                    comm_offers = seller_obj.get("commertialOffer", {})
                    # CommertialOffer can have Installments list
                    inst_refs = comm_offers.get("Installments", [])
                    if inst_refs:
                        # Find the one with highest count or 'sin interés'
                        best_inst = sorted(inst_refs, key=lambda x: x.get("NumberOfInstallments", 0), reverse=True)[0]
                        count = best_inst.get("NumberOfInstallments")
                        value = best_inst.get("Value")
                        if count:
                            installments = f"{count} cuotas de ${value}"

            # Social Proof & Badges (CRO)
            badges = []
            # VTEX clusters often contain marketing labels
            clusters = val.get("clusterHighlights", [])
            for c_ref in clusters:
                c_obj = self._resolve_vtex_pointer(c_ref, state)
                if c_obj and c_obj.get("name"):
                    badges.append(c_obj["name"])
            
            # Legacy VTEX badges
            if not badges:
                badges = self._extract_generic_badges()

            # Ratings
            rating_refs = val.get("reviews", []) or val.get("aggregateRating")
            rating_val = None
            review_count = 0
            if rating_refs:
                r_obj = self._resolve_vtex_pointer(rating_refs, state) if isinstance(rating_refs, (dict, str)) else None
                if r_obj:
                    rating_val = r_obj.get("ratingValue")
                    review_count = r_obj.get("reviewCount") or 0

            pdata = ProductData(
                sku=prod_id or val.get("productReference"),
                title=val.get("productName") or val.get("productTitle") or val.get("linkText"),
                brand=val.get("brand"),
                category_path=cat_path,
                category_tree=cat_tree,
                description=description,
                images=all_images,
                image_url=all_images[0] if all_images else None,
                list_price=price_info.get("list_price"),
                sale_price=price_info.get("sale_price"),
                is_in_stock=any(v.is_in_stock for v in product_variants) if product_variants else True,
                variants=product_variants,
                installments=installments,
                rating=float(rating_val) if rating_val else None,
                review_count=int(review_count),
                badges=badges,
                source_url=self.url,
                raw_metadata={"vtex_key": key}
            )
            extracted_products.append(pdata)

        # 5. Final fallback for PDP if no products extracted via typename
        if not extracted_products:
            extracted_products = await self._extract_products_internal()

        return extracted_products

    def _resolve_vtex_pointer(self, ref: str | dict, state: dict) -> dict:
        """Link Apollo pointers safely."""
        if not ref: return {}
        p_id = ref.get("id") if isinstance(ref, dict) else ref
        if p_id: return state.get(p_id, ref if isinstance(ref, dict) else {})
        return ref if isinstance(ref, dict) else {}

    def _get_vtex_price_range(self, product_val: dict, variants: list[VariantData], state: dict) -> dict:
        """Calculate best prices for the product based on its variants or metadata."""
        if variants:
            valid_sales = [v.sale_price for v in variants if v.sale_price is not None]
            valid_lists = [v.list_price for v in variants if v.list_price is not None]
            if valid_sales:
                return {
                    "sale_price": min(valid_sales),
                    "list_price": max(valid_lists) if valid_lists else min(valid_sales)
                }
        
        # Fallback to priceRange (often a pointer in Listings)
        pr_ref = product_val.get("priceRange")
        pr = self._resolve_vtex_pointer(pr_ref, state) if pr_ref else {}
        
        selling = self._resolve_vtex_pointer(pr.get("sellingPrice"), state) if pr.get("sellingPrice") else {}
        list_p = self._resolve_vtex_pointer(pr.get("listPrice"), state) if pr.get("listPrice") else {}
        
        return {
            "sale_price": selling.get("lowPrice") or selling.get("Price"),
            "list_price": list_p.get("highPrice") or list_p.get("ListPrice")
        }

    def _find_sku_pricing(self, sku_id: str, state: dict) -> dict:
        """Deep dive into state to find the commertialOffer for a SKU."""
        res = {"available": True, "list_price": None, "sale_price": None}
        
        # Search for any key that contains SKU:{id} and commertialOffer
        # VTEX IO keys can be: SKU:123... or $Product:XYZ.items.0.sellers.0.commertialOffer
        target_token = f"SKU:{sku_id}"
        
        for key, val in state.items():
            # Match if it has SKU:ID or if it's a pointer to an offer related to this SKU
            # We also look for specific fields in the value
            if (target_token in key or sku_id in key) and "commertialOffer" in key:
                res["list_price"] = val.get("ListPrice") or val.get("listPrice")
                res["sale_price"] = val.get("Price") or val.get("price")
                res["available"] = val.get("AvailableQuantity", 0) > 0
                if res["sale_price"] is not None:
                    return res
        
        return res

    async def _extract_aggressive_prices(self) -> dict:
        """Fallback: Aggressively search HTML for anything that looks like price JSON."""
        # Find all script tags
        for script in self.soup.find_all("script"):
            content = script.string
            if not content: continue
            if '"Price":' in content or '"Price":' in content:
                # Try to extract the closest number
                # This is a last resort to fulfill "TODO TODO"
                match_sale = re.search(r'"Price":\s*([\d.]+)', content)
                match_list = re.search(r'"ListPrice":\s*([\d.]+)', content)
                if match_sale:
                    return {
                        "sale_price": float(match_sale.group(1)),
                        "list_price": float(match_list.group(1)) if match_list else None
                    }
        return {}

    def _parse_state(self) -> dict | None:
        """Robustly extract VTEX state from HTML."""
        # 1. Look for script tags containing __STATE__ or vtex-data
        for script in self.soup.find_all("script"):
            content = script.string
            if not content: continue
            
            # Find the JSON start
            start_index = -1
            if "__STATE__ =" in content:
                start_index = content.find("__STATE__ =") + 11
            elif "vtex-data =" in content:
                start_index = content.find("vtex-data =") + 11
            
            if start_index != -1:
                # Find matching brace for valid JSON
                # We search for the first '{' then match until the script ends or semicolon
                json_start = content.find("{", start_index)
                if json_start != -1:
                    # Often the JSON ends at the last '}' before the end of the script
                    json_end = content.rfind("}")
                    if json_end != -1 and json_end > json_start:
                        try:
                            json_str = content[json_start:json_end+1]
                            return json.loads(json_str)
                        except json.JSONDecodeError:
                            continue
        
        # 2. Try regex as fallback for inline or complex patterns
        for pattern in [_STATE_PATTERN, _DATA_PATTERN]:
            match = pattern.search(self.html)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass

        return None
