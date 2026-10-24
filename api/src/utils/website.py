import httpx2
import asyncio
from bs4 import BeautifulSoup


def readable_text(content: bytes | bytearray, encoding: str, content_type: str) -> str:
    """Extract bounded readable text from HTML or plain text."""
    decoded = content.decode(encoding, errors="replace")
    if content_type == "text/plain":
        text = decoded.strip()
    else:
        soup = BeautifulSoup(decoded, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "template", "head"]):
            tag.decompose()
        text = (soup.body or soup).get_text(separator="\n", strip=True)
    if not text:
        raise ValueError("Website did not contain readable text.")
    if len(text) > 50_000:
        return text[:50_000] + "\n[Text truncated]"
    return text


async def fetch(url: str) -> str:
    """Fetch bounded readable text from a trusted developer-provided URL without redirects."""
    try:
        async with asyncio.timeout(30):
            async with httpx2.AsyncClient(
                timeout=10, trust_env=False, headers={"User-Agent": "SwissMCP/0.1", "Accept-Encoding": "identity"}
            ) as client:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").split(";")[0].strip()
                    if content_type not in {"text/html", "application/xhtml+xml", "text/plain"}:
                        raise ValueError("Website must return HTML or plain text.")
                    content = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=65_536):
                        content.extend(chunk)
                        if len(content) > 2_000_000:
                            raise ValueError("Website response exceeds the 2 MB limit.")
                    return readable_text(content, response.encoding or "utf-8", content_type)
    except (TimeoutError, httpx2.TimeoutException):
        raise ValueError("Website took too long to respond.")
    except httpx2.HTTPError:
        raise ValueError("Website could not be fetched.")
