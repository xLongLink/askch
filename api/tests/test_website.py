import httpx2
import pytest
from src.utils import website


@pytest.fixture
def anyio_backend():
    """Run asynchronous website checks with the asyncio backend."""
    return "asyncio"


@pytest.fixture
def mock_fetch(monkeypatch):
    """Intercept website requests with an HTTP transport."""
    original_client = httpx2.AsyncClient

    def configure(handler):
        monkeypatch.setattr(
            website.httpx2, "AsyncClient", lambda **kwargs: original_client(transport=httpx2.MockTransport(handler), **kwargs)
        )

    return configure


@pytest.mark.anyio
async def test_fetches_text(mock_fetch):
    """Fetch the supplied URL and extract its readable text."""

    def upstream(request):
        assert str(request.url) == "https://example.com/page?lang=en"
        assert request.headers["Host"] == "example.com"
        return httpx2.Response(
            200,
            headers={"Content-Type": "text/html"},
            text=(
                "<html><head><title>Title</title></head><body>"
                "<script>secret script</script><style>css</style>"
                "<h1>Hello</h1><p>Website text</p></body></html>"
            ),
        )

    mock_fetch(upstream)
    assert await website.fetch("https://example.com/page?lang=en") == "Hello\nWebsite text"


@pytest.mark.anyio
async def test_rejects_redirect_without_following(mock_fetch):
    """Reject redirects without requesting their destinations."""
    requests = []

    def upstream(request):
        requests.append(request)
        return httpx2.Response(302, headers={"Location": "http://localhost"})

    mock_fetch(upstream)
    with pytest.raises(ValueError, match="could not be fetched"):
        await website.fetch("https://example.com")
    assert len(requests) == 1


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("response", "error"),
    [
        (httpx2.Response(200, headers={"Content-Type": "application/pdf"}, content=b"pdf"), "HTML or plain text"),
        (httpx2.Response(200, headers={"Content-Type": "text/plain"}, text="x" * 2_000_001), "2 MB limit"),
        (httpx2.Response(404), "could not be fetched"),
        (httpx2.Response(302, headers={"Location": "/loop"}), "could not be fetched"),
    ],
)
async def test_fetch_failures(mock_fetch, response, error):
    """Reject unsupported content, excessive bodies, redirects, and HTTP errors."""
    mock_fetch(lambda request: response)
    with pytest.raises(ValueError, match=error):
        await website.fetch("https://example.com")


@pytest.mark.anyio
async def test_timeout(mock_fetch):
    """Convert provider timeouts into a readable website error."""

    def upstream(request):
        raise httpx2.ReadTimeout("timeout", request=request)

    mock_fetch(upstream)
    with pytest.raises(ValueError, match="too long"):
        await website.fetch("https://example.com")


def test_text_truncation():
    """Bound extracted text and indicate truncation."""
    text = website.readable_text(b"x" * 50_001, "utf-8", "text/plain")
    assert text == "x" * 50_000 + "\n[Text truncated]"
