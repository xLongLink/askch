from fastapi.testclient import TestClient

from src.main import create_app
from src.models.settings import Settings


def test_mounted_mcp(monkeypatch):
    async def fetch(website):
        assert website == "https://example.com"
        return "Example website text"

    monkeypatch.setattr("src.mcp.server.fetch_website", fetch)
    app = create_app(Settings(_env_file=None, infomaniak_api_key=""))
    with TestClient(app, base_url="http://localhost:8000") as client:
        headers = {"Accept": "application/json, text/event-stream"}
        response = client.post(
            "/api/mcp/",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0"},
                },
            },
        )
        assert response.status_code == 200
        result = response.json()["result"]
        assert result["serverInfo"]["name"] == "Swiss"
        headers["Mcp-Protocol-Version"] = result["protocolVersion"]
        response = client.post(
            "/api/mcp/",
            headers=headers,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        )
        tools = response.json()["result"]["tools"]
        assert [tool["name"] for tool in tools] == ["search"]
        assert tools[0]["inputSchema"]["required"] == ["website"]
        response = client.post(
            "/api/mcp/",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "search", "arguments": {"website": "https://example.com"}},
            },
        )
        result = response.json()["result"]
        assert result["content"][0]["text"] == "Example website text"
        assert not result.get("isError", False)


def test_mcp_tool_errors(monkeypatch):
    async def fetch(website):
        raise ValueError("Only public websites are allowed.")

    monkeypatch.setattr("src.mcp.server.fetch_website", fetch)
    app = create_app(Settings(_env_file=None, infomaniak_api_key=""))
    with TestClient(app, base_url="http://localhost:8000") as client:
        response = client.post(
            "/api/mcp/",
            headers={
                "Accept": "application/json, text/event-stream",
                "Mcp-Protocol-Version": "2025-11-25",
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "search", "arguments": {"website": "http://localhost"}},
            },
        )
        result = response.json()["result"]
        assert result["isError"] is True
        assert "Only public websites are allowed." in result["content"][0]["text"]
