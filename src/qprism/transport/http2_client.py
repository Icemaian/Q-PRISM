import httpx
import asyncio

async def fetch_tile_h2(tile_url: str) -> bytes:
    async with httpx.AsyncClient(http2=True) as client:
        response = await client.get(tile_url)
        response.raise_for_status()
        return response.content

