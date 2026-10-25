import httpx2
from collections.abc import Mapping


async def fetch(url: str | httpx2.URL, *, params: Mapping[str, str | int] | None = None) -> httpx2.Response:
    """Fetch a URL with a bounded request timeout and reject unsuccessful responses."""

    # Close the client after the response body has been read.
    async with httpx2.AsyncClient(timeout=30, trust_env=False) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response
