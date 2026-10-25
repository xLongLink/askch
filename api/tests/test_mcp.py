from src.settings import Settings
from fastapi.testclient import TestClient


def test_mounted_mcp(load_app):
    """Expose weather forecasts through MCP without allowing arbitrary website fetching."""
    app = load_app(Settings(_env_file=None, INFOMANIAK_API_KEY=""))
    with TestClient(app, base_url="http://localhost:8000") as client:
        headers = {"Accept": "application/json, text/event-stream"}
        response = client.post(
            "/api/mcp/",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}},
            },
        )
        assert response.status_code == 200
        result = response.json()["result"]
        assert result["serverInfo"]["name"] == "Swiss"
        headers["Mcp-Protocol-Version"] = result["protocolVersion"]
        response = client.post("/api/mcp/", headers=headers, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools = response.json()["result"]["tools"]
        assert [tool["name"] for tool in tools] == ["meteo", "government_announcements"]
        assert tools[0]["inputSchema"]["required"] == ["location"]
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
        assert result["isError"] is True
        assert "Unknown tool" in result["content"][0]["text"]


def test_mcp_tool_errors(monkeypatch, load_app):
    """Report forecast lookup failures as MCP tool errors."""

    async def fetch(url, **kwargs):
        raise ValueError("Forecast unavailable.")

    monkeypatch.setattr("src.utils.website.fetch", fetch)
    app = load_app(Settings(_env_file=None, INFOMANIAK_API_KEY=""))
    with TestClient(app, base_url="http://localhost:8000") as client:
        response = client.post(
            "/api/mcp/",
            headers={"Accept": "application/json, text/event-stream", "Mcp-Protocol-Version": "2025-11-25"},
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "meteo", "arguments": {"location": "3011"}}},
        )
        result = response.json()["result"]
        assert result["isError"] is True
        assert "The data source returned an invalid response." in result["content"][0]["text"]
