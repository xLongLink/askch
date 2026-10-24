import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest

from src.mcp import website


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "address", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "224.0.0.1"]
)
async def test_blocks_non_public_addresses(monkeypatch, address):
    monkeypatch.setattr(
        asyncio.get_running_loop(),
        "getaddrinfo",
        AsyncMock(return_value=[(0, 0, 0, "", (address, 80))]),
    )
    with pytest.raises(ValueError, match="Only public websites"):
        await website.public_address("example.com", 80)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com",
        "http://a:b@example.com",
        "https://example.com:8000",
    ],
)
def test_invalid_urls(url):
    with pytest.raises(ValueError):
        website.website_url(url)


def test_schemeless_url():
    assert str(website.website_url("example.com")) == "https://example.com"


@pytest.fixture
def mock_fetch(monkeypatch):
    original_client = httpx.AsyncClient
    monkeypatch.setattr(website, "public_address", AsyncMock(return_value="93.184.216.34"))

    def configure(handler):
        monkeypatch.setattr(
            website.httpx,
            "AsyncClient",
            lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs),
        )

    return configure


@pytest.mark.anyio
async def test_fetches_text_and_pins_dns(mock_fetch):
    def upstream(request):
        assert request.url.host == "93.184.216.34"
        assert request.headers["Host"] == "example.com"
        assert request.extensions["sni_hostname"] == "example.com"
        return httpx.Response(
            200,
            headers={"Content-Type": "text/html"},
            text=(
                "<html><head><title>Title</title></head><body>"
                "<script>secret script</script><style>css</style>"
                "<h1>Hello</h1><p>Website text</p></body></html>"
            ),
        )

    mock_fetch(upstream)
    assert await website.fetch_website("https://example.com") == "Hello\nWebsite text"


@pytest.mark.anyio
async def test_redirect_rechecks_dns(mock_fetch):
    mock_fetch(lambda request: httpx.Response(302, headers={"Location": "http://localhost"}))

    async def resolve(host, port):
        if host == "localhost":
            raise ValueError("Only public websites are allowed.")
        return "93.184.216.34"

    website.public_address.side_effect = resolve
    with pytest.raises(ValueError, match="Only public websites"):
        await website.fetch_website("https://example.com")


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("response", "error"),
    [
        (
            httpx.Response(200, headers={"Content-Type": "application/pdf"}, content=b"pdf"),
            "HTML or plain text",
        ),
        (
            httpx.Response(
                200, headers={"Content-Type": "text/plain"}, text="x" * (website.MAX_BYTES + 1)
            ),
            "2 MB limit",
        ),
        (httpx.Response(404), "could not be fetched"),
        (httpx.Response(302, headers={"Location": "/loop"}), "redirected too many times"),
    ],
)
async def test_fetch_failures(mock_fetch, response, error):
    mock_fetch(lambda request: response)
    with pytest.raises(ValueError, match=error):
        await website.fetch_website("https://example.com")


@pytest.mark.anyio
async def test_timeout(mock_fetch):
    def upstream(request):
        raise httpx.ReadTimeout("timeout", request=request)

    mock_fetch(upstream)
    with pytest.raises(ValueError, match="too long"):
        await website.fetch_website("https://example.com")


def test_text_truncation():
    text = website.readable_text(b"x" * (website.MAX_TEXT + 1), "utf-8", "text/plain")
    assert text == "x" * website.MAX_TEXT + "\n[Text truncated]"
