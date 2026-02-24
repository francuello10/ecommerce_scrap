"""
Directus UX Setup Script — Automates the configuration of the Directus UI.
This script sets up folders, field interfaces, and displays for an optimal experience.
"""

import httpx
import asyncio
import sys

DIRECTUS_URL = "http://localhost:8055"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "password" # User should ensure this matches

async def setup_ux():
    print(f"🚀 Starting Directus UX Automation at {DIRECTUS_URL}...")
    
    async with httpx.AsyncClient() as client:
        # 1. Login to get token
        try:
            resp = await client.post(f"{DIRECTUS_URL}/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            })
            resp.raise_for_status()
            token = resp.json()["data"]["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
        except Exception as e:
            print(f"❌ Error logging into Directus: {e}")
            print("⚠️ Make sure Directus is running and credentials are correct in the script.")
            return

        # 2. Configure Field Displays & Interfaces
        # Note: Directus stores these in system tables. We update them via the /fields endpoint.
        
        fields_to_update = [
            # Screenshots
            {"collection": "page_snapshot", "field": "screenshot_url", "meta": {
                "interface": "image",
                "display": "image",
                "display_options": {"circle": False, "size": "medium"}
            }},
            # Mails
            {"collection": "newsletter_message", "field": "body_html", "meta": {
                "interface": "input-code",
                "options": {"language": "html"},
                "display": "raw"
            }},
            {"collection": "newsletter_message", "field": "body_preview", "meta": {
                "interface": "textarea",
                "display": "raw"
            }},
            # AI Briefs
            {"collection": "daily_brief", "field": "content_markdown", "meta": {
                "interface": "markdown",
                "display": "formatted-text"
            }},
            # Signal Severity
            {"collection": "change_event", "field": "severity", "meta": {
                "interface": "select-dropdown",
                "options": {
                    "choices": [
                        {"text": "Critical", "value": "CRITICAL"},
                        {"text": "High", "value": "HIGH"},
                        {"text": "Medium", "value": "MEDIUM"},
                        {"text": "Low", "value": "LOW"}
                    ]
                },
                "display": "labels",
                "display_options": {
                    "showAsDot": True,
                    "choices": [
                        {"background": "#dc3545", "text": "white", "value": "CRITICAL"},
                        {"background": "#fd7e14", "text": "white", "value": "HIGH"},
                        {"background": "#ffc107", "text": "white", "value": "MEDIUM"},
                        {"background": "#0d6efd", "text": "white", "value": "LOW"}
                    ]
                }
            }},
            # Catalog — Product
            {"collection": "product", "field": "variants", "meta": {
                "interface": "list-m2m", # Directus uses this for O2M as well in many cases
                "display": "related-values"
            }},
            # Catalog — Variants
            {"collection": "product_variant", "field": "is_in_stock", "meta": {
                "interface": "boolean",
                "display": "boolean"
            }},
            {"collection": "product_variant", "field": "sale_price", "meta": {
                "interface": "input",
                "display": "currency",
                "display_options": {"symbol": "$", "suffix": True}
            }},
            # Premium Fields
            {"collection": "product", "field": "description", "meta": {
                "interface": "markdown",
                "display": "formatted-text"
            }},
            {"collection": "product", "field": "images", "meta": {
                "interface": "list",
                "display": "raw"
            }},
            {"collection": "product", "field": "category_tree", "meta": {
                "interface": "list",
                "display": "raw"
            }}
        ]

        for item in fields_to_update:
            try:
                # Directus uses PATCH /fields/{collection}/{field}
                print(f"🔧 Configuring {item['collection']}.{item['field']}...")
                await client.patch(
                    f"{DIRECTUS_URL}/fields/{item['collection']}/{item['field']}",
                    json={"meta": item["meta"]},
                    headers=headers
                )
            except Exception as e:
                print(f"⚠️ Could not update field {item['field']}: {e}")

        print("✅ Directus UX Configuration Complete!")

if __name__ == "__main__":
    asyncio.run(setup_ux())
