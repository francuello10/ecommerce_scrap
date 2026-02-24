"""Verification script: Test API endpoints directly using httpx."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from httpx import ASGITransport, AsyncClient
from api.main import app

async def main():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test Health
        print("🔍 Testing /health...")
        resp = await client.get("/health")
        print(f"   Status: {resp.status_code}")
        print(f"   Body: {resp.json()}")

        # 2. Test Suggestions Industries
        print("\n🔍 Testing /api/suggestions/industries...")
        resp = await client.get("/api/suggestions/industries")
        print(f"   Status: {resp.status_code}")
        industries = resp.json()
        print(f"   Count: {len(industries)}")
        if industries:
            print(f"   First: {industries[0]['name']} ({industries[0]['slug']})")

        # 3. Test Suggestions for 'deportes'
        print("\n🔍 Testing /api/suggestions/deportes...")
        resp = await client.get("/api/suggestions/deportes")
        print(f"   Status: {resp.status_code}")
        data = resp.json()
        print(f"   Industry: {data['name']}")
        for group in data['groups']:
            print(f"   - {group['label']}: {len(group['competitors'])} competitors")

        # 4. Test Onboarding Identify
        print("\n🔍 Testing /api/onboarding/identify...")
        payload = {
            "client_name": "Test Client",
            "client_email": "test@example.com",
            "client_slug": "test-client",
            "company_name": "My Shop",
            "company_domain": "myshop.com.ar",
            "industry_slug": "deportes"
        }
        resp = await client.post("/api/onboarding/identify", json=payload)
        print(f"   Status: {resp.status_code}")
        print(f"   Body: {resp.json()}")

if __name__ == "__main__":
    asyncio.run(main())
