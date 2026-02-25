"""
Directus UX Setup Script — Automates the configuration of the Directus UI.
This script sets up folders, field interfaces, and displays for an optimal experience.
"""

import httpx
import asyncio
import sys

DIRECTUS_URL = "http://localhost:8055"
ADMIN_EMAIL = "francuello.1999@gmail.com"
ADMIN_PASSWORD = "monaco99" 

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

        # 1b. Unhide collections so they appear in Directus sidebar
        tables_to_manage = [
            "daily_brief", "weekly_brief", "newsletter_message", 
            "page_snapshot", "change_event", "product", 
            "product_variant", "subscription_tier", "client", 
            "job_execution_log", "competitor_tech_profile",
            "tech_profile_change", "monitored_page", "newsletter_account"
        ]
        
        for table in tables_to_manage:
            try:
                # Directus automatically identifies DB tables, we just need to ensure they have an unhidden meta
                await client.post(
                    f"{DIRECTUS_URL}/collections", 
                    json={"collection": table}, 
                    headers=headers
                )
            except:
                pass # Already managed
                
            try:
                print(f"�️ Ensuring collection is visible: {table}...")
                await client.patch(
                    f"{DIRECTUS_URL}/collections/{table}", 
                    json={"meta": {"hidden": False}}, 
                    headers=headers
                )
            except Exception as e:
                print(f"⚠️ Error unhiding {table}: {e}")

        # 2. Configure Field Displays & Interfaces
        # Note: Directus stores these in system tables. We update them via the /fields endpoint.
        
        fields_to_update = [
            # Screenshots
            {"collection": "page_snapshot", "field": "screenshot_url", "meta": {
                "interface": "input",
                "display": "image",
                "display_options": {"circle": False, "size": "large"}
            }},
            # Signals (One-To-Many relational view)
            {"collection": "page_snapshot", "field": "signals", "meta": {
                "interface": "list-o2m",
                "display": "related-values",
                "display_options": {"template": "{{raw_text_found}} ({{confidence_score}})"}
            }},
            # Mails (Displaying HTML visually)
            {"collection": "newsletter_message", "field": "body_html", "meta": {
                "interface": "input-rich-text-html",
                "display": "formatted-text"
            }},
            {"collection": "newsletter_message", "field": "body_preview", "meta": {
                "interface": "textarea",
                "display": "raw"
            }},
            # AI Briefs (Rendering Markdown)
            {"collection": "daily_brief", "field": "content_markdown", "meta": {
                "interface": "input-rich-text-md",
                "display": "formatted-text"
            }},
            {"collection": "weekly_brief", "field": "content_markdown", "meta": {
                "interface": "input-rich-text-md",
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
            {"collection": "product", "field": "current_price", "meta": {
                "interface": "input",
                "display": "currency",
                "display_options": {"symbol": "$", "suffix": True}
            }},
            # Premium Fields
            {"collection": "product", "field": "description", "meta": {
                "interface": "markdown",
                "display": "formatted-text"
            }},
            
            # Images & Files (Mapped Native Directus UUIDs)
            {"collection": "product", "field": "directus_image_id", "meta": {
                "interface": "file-image",
                "display": "image"
            }},
            {"collection": "competitor", "field": "sitemap_file_id", "meta": {
                "interface": "file",
                "display": "file"
            }},
            {"collection": "page_snapshot", "field": "screenshot_url", "meta": {
                "interface": "file-image",
                "display": "image"
            }},
            {"collection": "product", "field": "images", "meta": {
                "interface": "list",
                "display": "raw"
            }},
            {"collection": "product", "field": "category_tree", "meta": {
                "interface": "list",
                "display": "raw"
            }},
            # Relational Displays
            {"collection": "competitor_tech_profile", "field": "competitor_id", "meta": {
                "interface": "select-dropdown-m2o",
                "display": "related-values",
                "display_options": {"template": "{{name}}"}
            }},
            {"collection": "page_snapshot", "field": "monitored_page_id", "meta": {
                "interface": "select-dropdown-m2o",
                "display": "related-values",
                "display_options": {"template": "{{url}}"}
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
