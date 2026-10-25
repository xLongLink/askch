import json
import httpx2
import pytest
from src.settings import Settings
from fastapi.testclient import TestClient


@pytest.fixture
def frontend_dir(tmp_path):
    """Create static frontend files beside the isolated entry point."""
    directory = tmp_path / "web"
    directory.mkdir()
    (directory / "index.html").write_text("<html>Swiss Chat</html>")
    (directory / "_app").mkdir()
    (directory / "_app" / "app.js").write_text("console.log('Swiss Chat')")
    (directory / "about").mkdir()
    (directory / "about" / "index.html").write_text("<html>About</html>")
    return directory


@pytest.fixture
def client(frontend_dir, load_app):
    """Start the application with a bundled frontend and no provider key."""
    settings = Settings(_env_file=None, INFOMANIAK_API_KEY="")
    app = load_app(settings)
    with TestClient(app, base_url="http://localhost:8000") as client:
        yield client


def test_frontend_files(client):
    """Serve frontend HTML, JavaScript, directory indexes, and HEAD requests."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.text == "<html>Swiss Chat</html>"
    response = client.get("/_app/app.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert response.text == "console.log('Swiss Chat')"
    assert client.get("/about/").text == "<html>About</html>"
    assert client.head("/").status_code == 200
    assert client.head("/").content == b""


@pytest.mark.parametrize("method", ["GET", "HEAD"])
def test_browser_navigation_fallback(client, method):
    """Serve the frontend entry point for HTML navigation requests."""
    response = client.request(method, "/client/nested.route", headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


@pytest.mark.parametrize("path", ["/_app/missing.js", "/missing.css", "/client/route"])
def test_non_navigation_misses(client, path):
    """Return not found for missing non-navigation resources."""
    assert client.get(path).status_code == 404


@pytest.mark.parametrize("path", ["/api", "/api/missing", "/api/missing/deep"])
def test_api_misses_never_serve_frontend(client, path):
    """Keep unknown API paths out of the HTML fallback."""
    response = client.get(path, headers={"Accept": "text/html"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_api_routes_with_frontend(client):
    """Preserve API, documentation, validation, and MCP routes with a frontend."""
    assert client.get("/api/health", headers={"Accept": "text/html"}).json() == {"status": "ok"}
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert "/api/chat" in schema["paths"]
    assert client.post("/api/health").status_code == 405
    assert client.post("/api/chat", json={}).status_code == 422
    response = client.post(
        "/api/mcp/", headers={"Accept": "application/json, text/event-stream"}, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    )
    assert response.status_code == 200
    assert [tool["name"] for tool in response.json()["result"]["tools"]] == ["meteo", "government_announcements"]


def test_chat_stream_with_frontend(frontend_dir, load_app):
    """Stream chat responses while frontend serving is enabled."""

    def upstream(request):
        return httpx2.Response(
            200,
            text=(
                'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'
                'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n'
                "data: [DONE]\n\n"
            ),
            headers={"Content-Type": "text/event-stream"},
        )

    settings = Settings(_env_file=None, INFOMANIAK_API_KEY="test")
    app = load_app(settings, httpx2.MockTransport(upstream))
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"messages": [{"id": "1", "role": "user", "parts": [{"type": "text", "text": "Hi"}]}]})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    chunks = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ") and line != "data: [DONE]"]
    assert any(chunk.get("delta") == "Hello" for chunk in chunks)
    assert response.text.endswith("data: [DONE]\n\n")


def test_frontend_is_optional(load_app):
    """Keep the API available when no frontend build is bundled."""
    app = load_app(Settings(_env_file=None))
    with TestClient(app) as client:
        assert client.get("/", headers={"Accept": "text/html"}).status_code == 404
        assert client.get("/api/health").status_code == 200


def test_missing_index_fails(tmp_path, load_app):
    """Reject a bundled frontend without its entry point."""
    (tmp_path / "web").mkdir()
    with pytest.raises(RuntimeError, match="fallback file"):
        load_app(Settings(_env_file=None))


def test_no_files_outside_frontend(client, frontend_dir):
    """Prevent static requests from escaping the frontend directory."""
    secret = frontend_dir.parent / "private.txt"
    secret.write_text("private")
    response = client.get("/%2e%2e/private.txt")
    assert response.status_code == 404
    assert "private" not in response.text
