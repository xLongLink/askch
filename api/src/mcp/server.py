from mcp.server import MCPServer
from src.mcp.website import fetch_website
from mcp.server.mcpserver.exceptions import ToolError

# Configure the internal MCP server and its website tool.
server = MCPServer("Swiss", instructions="Fetch readable text from public websites.")


@server.tool()
async def search(website: str) -> str:
    """Fetch a website URL and return its readable text. This is not a search engine."""

    # Report rejected URLs as MCP tool errors.
    try:
        return await fetch_website(website)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
