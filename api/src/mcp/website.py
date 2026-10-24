import httpx
import socket
import asyncio
import ipaddress
from bs4 import BeautifulSoup

MAX_BYTES = 2_000_000
MAX_TEXT = 50_000
MAX_REDIRECTS = 5


async def public_address(host: str, port: int) -> str:
    """Resolve a hostname only when every returned address is public."""
    try:
        addresses = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("Website hostname could not be resolved.") from exc
    if not addresses:
        raise ValueError("Website hostname could not be resolved.")
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global or ip.is_multicast:
            raise ValueError("Only public websites are allowed.")
    return addresses[0][4][0]


def website_url(website: str) -> httpx.URL:
    """Normalize a website URL and reject unsupported connection targets."""
    website = website.strip()
    if "://" not in website:
        website = f"https://{website}"
    try:
        url = httpx.URL(website)
        if url.scheme not in {"http", "https"} or not url.host or url.userinfo or url.port not in {None, 80, 443}:
            raise ValueError("Provide a public HTTP or HTTPS website on port 80 or 443.")
        return url.copy_with(fragment=None)
    except httpx.InvalidURL as exc:
        raise ValueError("Invalid website URL.") from exc


def readable_text(content: bytes, encoding: str, content_type: str) -> str:
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
    if len(text) > MAX_TEXT:
        return text[:MAX_TEXT] + "\n[Text truncated]"
    return text


async def fetch_website(website: str) -> str:
    """Fetch readable website text with validated DNS, redirects, and limits."""
    try:
        async with asyncio.timeout(30):
            url = website_url(website)
            async with httpx.AsyncClient(
                timeout=10,
                follow_redirects=False,
                trust_env=False,
                limits=httpx.Limits(max_keepalive_connections=0),
                headers={"User-Agent": "SwissMCP/0.1", "Accept-Encoding": "identity"},
            ) as client:
                for redirect in range(MAX_REDIRECTS + 1):
                    address = await public_address(url.raw_host.decode("ascii"), url.port or (443 if url.scheme == "https" else 80))
                    # Pin DNS to the checked address, preserving TLS verification and Host.
                    async with client.stream(
                        "GET",
                        url.copy_with(host=address),
                        headers={"Host": url.netloc.decode("ascii")},
                        extensions={"sni_hostname": url.raw_host.decode("ascii")},
                    ) as response:
                        if response.is_redirect:
                            if redirect == MAX_REDIRECTS or "location" not in response.headers:
                                raise ValueError("Website redirected too many times or without a URL.")
                            url = website_url(str(url.join(response.headers["location"])))
                            continue
                        response.raise_for_status()
                        content_type = response.headers.get("content-type", "").split(";")[0].strip()
                        if content_type not in {"text/html", "application/xhtml+xml", "text/plain"}:
                            raise ValueError("Website must return HTML or plain text.")
                        content = bytearray()
                        async for chunk in response.aiter_bytes(chunk_size=65_536):
                            content.extend(chunk)
                            if len(content) > MAX_BYTES:
                                raise ValueError("Website response exceeds the 2 MB limit.")
                        return readable_text(bytes(content), response.encoding or "utf-8", content_type)
    except (TimeoutError, httpx.TimeoutException) as exc:
        raise ValueError("Website took too long to respond.") from exc
    except httpx.HTTPError as exc:
        raise ValueError("Website could not be fetched.") from exc
