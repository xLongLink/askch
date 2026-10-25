from src.mcp import meteo, errors
from mcp.server import MCPServer
from src.mcp.government import announcement

# Configure the internal MCP server and its official Swiss data tools.
server = MCPServer("Swiss", instructions="Access official Swiss data and information.")

server.tool()(errors.boundary(meteo.meteo))
server.tool()(errors.boundary(announcement.government_announcements))
