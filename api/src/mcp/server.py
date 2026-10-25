from src.mcp import errors
from mcp.server import MCPServer
from src.mcp.core import cities, cantons
from src.mcp.data import meteo
from src.mcp.jobs import ictjobs
from src.mcp.government import announcement

# Configure the internal MCP server and its Swiss data tools.
server = MCPServer("Swiss", instructions="Access Swiss data and information, including official sources and ICT job listings.")

server.tool()(errors.boundary(meteo.meteo))
server.tool()(errors.boundary(announcement.government_announcements))
server.tool()(errors.boundary(cantons.cantons))
server.tool()(errors.boundary(cities.cities))
server.tool()(errors.boundary(ictjobs.ictjobs))
