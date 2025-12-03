"""Test the API locally"""

import asyncio

import httpx

API_URL = "http://localhost:8000/api/v1"


async def test_health():
    """Test health endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/health")
        print("✓ Health check:", response.json())


async def test_models():
    """Test models endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/models")
        data = response.json()
        print(
            f"✓ Available models: {len(data['free_tier'])} free, {len(data['premium'])} premium"
        )


async def test_query():
    """Test query endpoint"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{API_URL}/query",
            json={"question": "How many species are in GoaT?", "model": "gpt-4o-mini"},
        )
        data = response.json()
        print(f"✓ Query successful:")
        print(f"  Answer: {data['answer'][:100]}...")
        print(f"  Tokens: {data['tokens_used']['total']}")
        print(f"  Cost: ${data['cost_usd']}")


async def main():
    print("Testing GoaT API...")
    print()

    try:
        await test_health()
        await test_models()
        await test_query()
        print()
        print("✅ All tests passed!")
    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(main())
