from typing import Optional
import httpx

async def fetch_tile_h2(base_url: str, tile_path: str, *, client: Optional[httpx.AsyncClient] = None) -> bytes:
    close_client = False
    if client is None:
        client = httpx.AsyncClient(http2=True, timeout=30.0)
        close_client = True

    try:
        url = base_url.rstrip("/") + "/" + tile_path.lstrip("/")
        r = await client.get(url)
        r.raise_for_status()
        return r.content
    finally:
        if close_client:
            await client.aclose()
