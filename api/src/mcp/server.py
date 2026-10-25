import io
import csv
import httpx2
import asyncio
from typing import Literal, Annotated
from datetime import UTC, datetime, timedelta
from pydantic import Field
from src.utils import website
from mcp.server import MCPServer
from src.mcp.government import announcement
from src.models.postcodes import Postcodes
from mcp.server.mcpserver.exceptions import ToolError

# Configure the internal MCP server and its official Swiss data tools.
server = MCPServer("Swiss", instructions="Fetch local MeteoSwiss weather forecasts and official Swiss federal announcements.")
COLLECTION = "https://data.geo.admin.ch/api/stac/v1/collections/ch.meteoschweiz.ogd-local-forecasting"
DATA = "https://data.geo.admin.ch/ch.meteoschweiz.ogd-local-forecasting/"
PARAMETERS = {"temperature": ("tre200h0", "°C"), "precipitation": ("rre150h0", "mm"), "wind": ("fu3010h0", "km/h")}


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

    # Validate the forecast range before contacting MeteoSwiss.
    if parameter not in PARAMETERS or not 1 <= hours <= 192:
        raise ToolError("Choose temperature, precipitation, or wind and between 1 and 192 hours.")

    # Bound the complete lookup as well as individual network requests.
    try:
        async with asyncio.timeout(60):
            response = await website.fetch(f"{DATA}ogd-local-forecasting_meta_point.csv")
            points = list(csv.DictReader(io.StringIO(response.content.decode("cp1252")), delimiter=";"))

            # Prefer exact names, postcodes, and station codes over partial names.
            query = location.value.casefold()
            matches = [
                point
                for point in points
                if query in {point["point_name"].casefold(), point["postal_code"].casefold(), point["station_abbr"].casefold()}
            ]
            if not matches:
                matches = [point for point in points if query in point["point_name"].casefold()]
            if not matches:
                raise ToolError("No forecast location found. Try a Swiss postcode or station abbreviation.")
            if len(matches) > 1:
                return {"locations": [{key: point[key] for key in ("point_name", "postal_code", "station_abbr")} for point in matches[:20]]}
            point = matches[0]

            # Skip empty future-day items and select the newest available forecast run.
            response = await website.fetch(f"{COLLECTION}/items", params={"limit": 5, "sortby": "-id"})
            code, unit = PARAMETERS[parameter]
            assets = [
                asset for item in response.json()["features"] for name, asset in item["assets"].items() if name.endswith(f".{code}.csv")
            ]
            if not assets:
                raise ToolError("No forecast file is currently available for this parameter.")
            asset = max(assets, key=lambda asset: asset["href"])
            url = httpx2.URL(asset["href"])
            if (
                url.scheme != "https"
                or url.host != "data.geo.admin.ch"
                or not url.path.startswith("/ch.meteoschweiz.ogd-local-forecasting/")
                or url.userinfo
                or url.port not in {None, 443}
            ):
                raise ToolError("The forecast service returned an unsupported download URL.")

            # Stream only this location's future values without retaining the full CSV.
            now = datetime.now(UTC)
            end = now + timedelta(hours=hours)
            forecast = []
            size = 0
            async with httpx2.AsyncClient(timeout=30, trust_env=False) as client:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        size += len(line)
                        if size > 64_000_000:
                            raise ToolError("Forecast file exceeds the download limit.")
                        row = next(csv.reader([line], delimiter=";"))
                        if len(row) != 4 or row[0] != point["point_id"] or row[1] != point["point_type_id"]:
                            continue
                        timestamp = datetime.strptime(row[2], "%Y%m%d%H%M").replace(tzinfo=UTC)
                        if now <= timestamp <= end:
                            forecast.append({"time": timestamp.isoformat(), "value": float(row[3]) if row[3] else None})
            if not forecast:
                raise ToolError("No upcoming forecast values are currently available for this location.")
            return {
                "location": point["point_name"],
                "postal_code": point["postal_code"],
                "parameter": parameter,
                "unit": unit,
                "forecast": sorted(forecast, key=lambda value: str(value["time"])),
                "source": str(url),
                "attribution": "MeteoSwiss (CC-BY)",
            }
    except (TimeoutError, httpx2.TimeoutException):
        raise ToolError("MeteoSwiss forecast lookup timed out.")
    except httpx2.HTTPError:
        raise ToolError("MeteoSwiss forecast data could not be fetched.")
    except ValueError as error:
        raise ToolError(str(error)) from error


server.tool()(announcement.government_announcements)
