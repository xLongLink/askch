from typing import Literal, Annotated
from pydantic import Field
from mcp.server import MCPServer
from src.utils.meteo import fetch_meteo
from src.models.postcodes import Postcodes
from mcp.server.mcpserver.exceptions import ToolError

# Configure the internal MCP server and its weather tool.
server = MCPServer("Swiss", instructions="Fetch local MeteoSwiss weather forecasts.")


@server.tool()
async def meteo(
    location: Annotated[Postcodes, Field(description="A four-digit postcode supported by MeteoSwiss, such as 8001 for Zürich.")],
    parameter: Literal["temperature", "precipitation", "wind"] = "temperature",
    hours: Annotated[int, Field(ge=1, le=192)] = 24,
) -> dict:
    """Get hourly MeteoSwiss forecasts for a supported four-digit postcode.

    Times are UTC. Temperature is in °C, precipitation in mm, and wind speed in km/h.
    Send location as a quoted postcode string, for example "6900" for Lugano.
    Attribute forecast data to MeteoSwiss (CC-BY).
    """

    # Report forecast lookup failures as MCP tool errors.
    try:
        return await fetch_meteo(location.value, parameter, hours)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
