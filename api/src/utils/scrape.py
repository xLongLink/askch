import math
import httpx2
import socket
import asyncio
import logging
import sqlite3
import ipaddress
import trafilatura
from urllib import robotparser
from pathlib import Path
from contextlib import closing
from collections import deque

logger = logging.getLogger(__name__)
USER_AGENT = "AskCHBot"
MAX_BYTES = 5_000_000


def _url(value: str, base: httpx2.URL | None = None) -> httpx2.URL:
    """Normalize public HTTP URLs and keep discovered links on the original host."""
    url = base.join(value) if base else httpx2.URL(value if "://" in value else f"https://{value}")
    if url.scheme not in {"http", "https"} or not url.host or url.username or url.password:
        raise ValueError("Expected an HTTP(S) URL without credentials.")
    if url.port not in {None, 80 if url.scheme == "http" else 443}:
        raise ValueError("Only standard HTTP(S) ports are supported.")
    if base and url.host != base.host:
        raise ValueError("Links must stay on the original hostname.")
    return url.copy_with(fragment=None)


def _public(host: str) -> None:
    """Reject hosts that resolve to private or otherwise non-public addresses."""
    addresses = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(address[4][0]).is_global for address in addresses):
        raise ValueError("Only public websites can be indexed.")


async def _fetch(
    client: httpx2.AsyncClient, url: httpx2.URL, delay: float, rules: robotparser.RobotFileParser | None = None
) -> httpx2.Response:
    """Fetch bounded responses while checking each redirect before following it."""
    for _ in range(6):
        # Check robots and public addressing before every request, including redirects.
        if rules is not None and not rules.can_fetch(USER_AGENT, str(url)):
            raise ValueError("robots.txt disallows crawling this URL.")
        await asyncio.to_thread(_public, url.host)
        await asyncio.sleep(delay)

        # Stream responses to bound decompressed content and never follow external redirects.
        async with asyncio.timeout(30), client.stream("GET", url) as response:
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location")
                if not location:
                    raise ValueError("Redirect has no location.")
                url = _url(location, base=url)
                continue
            content = bytearray()
            async for chunk in response.aiter_bytes(chunk_size=65_536):
                content.extend(chunk)
                if len(content) > MAX_BYTES:
                    raise ValueError("Response exceeds the 5 MB limit.")
            headers = dict(response.headers)
            headers.pop("content-encoding", None)
            headers.pop("content-length", None)
            return httpx2.Response(response.status_code, headers=headers, content=bytes(content), request=response.request)
    raise ValueError("Too many redirects.")


def _store(database: Path, site: str, url: str = "", html: bytes | None = None) -> list[str]:
    """Extract HTML and update its full-text entry outside the async event loop."""
    database.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database, timeout=30)) as connection, connection:
        connection.execute("CREATE VIRTUAL TABLE IF NOT EXISTS pages USING fts5(site UNINDEXED, url UNINDEXED, title, text)")
        if html is None:
            return []

        # Discover links even when the page has no extractable main content.
        tree = trafilatura.load_html(html)
        if tree is None:
            return []
        links = tree.xpath("//a[@href]/@href")
        base_links = tree.xpath("//base[@href]/@href")
        link_base = httpx2.URL(url).join(base_links[0]) if base_links else httpx2.URL(url)
        document = trafilatura.bare_extraction(tree, url=url, include_comments=False, with_metadata=True)
        if document is not None and document.text:
            connection.execute("DELETE FROM pages WHERE site = ? AND url = ?", (site, url))
            connection.execute(
                "INSERT INTO pages (site, url, title, text) VALUES (?, ?, ?, ?)", (site, url, document.title or url, document.text)
            )
        resolved = []
        for link in links:
            try:
                resolved.append(str(link_base.join(link)))
            except (httpx2.InvalidURL, ValueError):
                continue
        return resolved


async def index(url: str, *, database: Path = Path(".indexes/websites.sqlite3"), max_pages: int = 100, delay: float = 1.0) -> Path:
    """Index linked HTML pages on an exact hostname and return the SQLite FTS5 database path.

    Bare domains use HTTPS. Crawl at most max_pages URLs, honoring robots.txt,
    crawl delays and request rates. Existing entries are updated, not globally
    replaced: bounded or interrupted crawls do not remove unvisited pages.
    PDFs, JavaScript rendering and subdomains are not supported. This is a trusted
    backend utility, not a public URL-fetch endpoint; enforce network-level egress
    restrictions if exposed to untrusted callers to prevent DNS rebinding.
    """
    # Validate crawl limits before touching the network or creating the index.
    if isinstance(max_pages, bool) or not isinstance(max_pages, int) or max_pages < 1:
        raise ValueError("max_pages must be a positive integer.")
    if not math.isfinite(delay) or delay < 0:
        raise ValueError("delay must be finite and non-negative.")
    base = _url(url.strip())
    await asyncio.to_thread(_public, base.host)
    await asyncio.to_thread(_store, database, base.host)

    # Load robots separately; missing rules allow crawling, but other failures stop it.
    async with httpx2.AsyncClient(timeout=30, trust_env=False, follow_redirects=False, headers={"User-Agent": USER_AGENT}) as client:
        robots_url = base.copy_with(path="/robots.txt", query=None)
        response = await _fetch(client, robots_url, delay)
        rules = robotparser.RobotFileParser(str(robots_url))
        if response.status_code in {401, 403}:
            raise ValueError("The website does not permit crawling its robots.txt.")
        if response.status_code not in {404, 410}:
            response.raise_for_status()
            rules.parse(response.text.splitlines())
        else:
            rules.parse([])
        delay = max(delay, rules.crawl_delay(USER_AGENT) or 0)
        rate = rules.request_rate(USER_AGENT)
        if rate and rate.requests > 0:
            delay = max(delay, rate.seconds / rate.requests)
        if not rules.can_fetch(USER_AGENT, str(base)):
            raise ValueError("robots.txt disallows crawling the starting URL.")

        # Bound both page attempts and the discovered frontier to avoid crawl traps.
        pending = deque([base])
        discovered = {str(base)}
        visited: set[str] = set()
        while pending and len(visited) < max_pages:
            current = pending.popleft()
            if str(current) in visited:
                continue
            visited.add(str(current))
            try:
                response = await _fetch(client, current, delay, rules)
                response.raise_for_status()
                if response.headers.get("content-type", "").split(";")[0].strip().lower() not in {"text/html", "application/xhtml+xml"}:
                    continue
                final_url = str(response.url)
                visited.add(final_url)
                links = await asyncio.to_thread(_store, database, base.host, final_url, response.content)
            except (httpx2.HTTPError, httpx2.InvalidURL, TimeoutError, ValueError, socket.gaierror):
                if current == base:
                    raise
                logger.warning("Could not index %s", current, exc_info=True)
                continue

            # Ignore unsupported links without dropping other links from the same page.
            for link in links:
                if len(discovered) >= max_pages * 10:
                    break
                try:
                    candidate = _url(link, base=base)
                except (httpx2.InvalidURL, ValueError):
                    continue
                if str(candidate) not in discovered and rules.can_fetch(USER_AGENT, str(candidate)):
                    discovered.add(str(candidate))
                    pending.append(candidate)
    return database
