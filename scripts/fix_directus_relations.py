import asyncio
import httpx
from core.config import settings

DIRECTUS_URL = settings.directus_url
TOKEN = settings.directus_key
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

async def create_m2o_field(client: httpx.AsyncClient, collection: str, field: str, related_collection: str, interface: str):
    # 1. Create Field
    field_payload = {
        "field": field,
        "type": "uuid",
        "meta": {
            "interface": interface,
            "display": "image" if interface == "image" else "file",
            "hidden": False,
            "readonly": False
        }
    }
    r = await client.post(f"{DIRECTUS_URL}/fields/{collection}", json=field_payload)
    if r.status_code not in (200, 201):
        if "already exists" in r.text or "has already been taken" in r.text:
            print(f"[*] Field {collection}.{field} already exists, updating meta...")
            await client.patch(f"{DIRECTUS_URL}/fields/{collection}/{field}", json={"meta": field_payload["meta"]})
        else:
            print(f"[!] Error creating {collection}.{field}: {r.text}")
    else:
        print(f"[+] Created field {collection}.{field}")

    # 2. Create Relation
    relation_payload = {
        "collection": collection,
        "field": field,
        "related_collection": related_collection,
        "schema": {
            "on_update": "CASCADE",
            "on_delete": "SET NULL"
        }
    }
    r_rel = await client.post(f"{DIRECTUS_URL}/relations", json=relation_payload)
    if r_rel.status_code not in (200, 201):
        if "already exists" not in r_rel.text:
            print(f"[!] Error creating relation for {collection}.{field}: {r_rel.text}")
    else:
        print(f"[+] Created relation for {collection}.{field} -> {related_collection}")

async def main():
    if not TOKEN:
        print("[!] Directus Token not set in .env")
        return
        
    async with httpx.AsyncClient() as client:
        print("Configuring Snapshot screenshots...")
        # Actually page_snapshot already has screenshot_url. We want to be sure it has 'image' interface.
        # But wait! screenshot_url is text, not uuid currently in DB. 
        # So we create a new field named `screenshot_file_id` for the uuid? Or we update meta for `screenshot_url`. 
        # `competitor.sitemap_file_id`
        await create_m2o_field(client, "competitor", "sitemap_file_id", "directus_files", "file")
        
        # `product.directus_image_id`
        await create_m2o_field(client, "product", "directus_image_id", "directus_files", "image")

if __name__ == "__main__":
    asyncio.run(main())
