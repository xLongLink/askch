import httpx
import pytest
from fastapi.testclient import TestClient

from src.main import create_app
from src.models.settings import Settings


@pytest.fixture
def frontend_dir(tmp_path):
    (tmp_path / "index.html").write_text("<html>Swiss Chat</html>")
    (tmp_path / "_app").mkdir()
    (tmp_path / "_app" / "app.js").write_text("console.log('Swiss Chat')")
    (tmp_path / "about").mkdir()
    (tmp_path / "about" / "index.html").write_text("<html>About</html>")
    return tmp_path


@pytest.fixture
def client(frontend_dir):
    settings = Settings(_env_file=None, infomaniak_api_key="", frontend_dir=frontend_dir)
    with TestClient(create_app(settings), base_url="http://localhost:8000") as client:
        yield client


def test_frontend_files(client):
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
    response = client.request(method, "/client/nested.route", headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


@pytest.mark.parametrize("path", ["/_app/missing.js", "/missing.css", "/client/route"])
def test_non_navigation_misses(client, path):
    assert client.get(path).status_code == 404


@pytest.mark.parametrize("path", ["/api", "/api/missing", "/api/missing/deep"])
def test_api_misses_never_serve_frontend(client, path):
    response = client.get(path, headers={"Accept": "text/html"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_api_routes_with_frontend(client):
    assert client.get("/api/health", headers={"Accept": "text/html"}).json() == {"status": "ok"}
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert "/api/chat" in schema["paths"]
    assert client.post("/api/health").status_code == 405
    assert client.post("/api/chat", json={}).status_code == 422
    response = client.post(
        "/api/mcp/",
        headers={"Accept": "application/json, text/event-stream"},
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
    )
    assert response.status_code == 200
    assert response.json()["result"]["tools"][0]["name"] == "search"


def test_chat_stream_with_frontend(frontend_dir):
    def upstream(request):
        return httpx.Response(
            200,
            text='data: {"choices":[{"delta":{"content":"Hello"}}]}\n\ndata: [DONE]\n\n',
            headers={"Content-Type": "text/event-stream"},
        )

    settings = Settings(_env_file=None, infomaniak_api_key="test", frontend_dir=frontend_dir)
    with TestClient(create_app(settings, httpx.MockTransport(upstream))) as client:
        response = client.post(
            "/api/chat",
            json={
                "messages": [{"id": "1", "role": "user", "parts": [{"type": "text", "text": "Hi"}]}]
            },
        )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"delta": "Hello"' in response.text
    assert response.text.endswith("data: [DONE]\n\n")


def test_frontend_is_optional():
    with TestClient(create_app(Settings(_env_file=None, frontend_dir=None))) as client:
        assert client.get("/", headers={"Accept": "text/html"}).status_code == 404
        assert client.get("/api/health").status_code == 200


def test_configured_missing_build_fails(tmp_path):
    with pytest.raises(RuntimeError, match="does not exist"):
        create_app(Settings(_env_file=None, frontend_dir=tmp_path / "missing"))


def test_configured_missing_index_fails(tmp_path):
    with pytest.raises(RuntimeError, match="fallback file"):
        create_app(Settings(_env_file=None, frontend_dir=tmp_path))


def test_no_files_outside_frontend(client, frontend_dir):
    secret = frontend_dir.parent / "private.txt"
    secret.write_text("private")
    response = client.get("/%2e%2e/private.txt")
    assert response.status_code == 404
    assert "private" not in response.text
