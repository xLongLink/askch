import io
import csv
import math
import httpx2
import asyncio
import unicodedata
from typing import Literal, Annotated
from datetime import UTC, datetime, timedelta
from pydantic import Field
from src.utils import website
from mcp.server.mcpserver.exceptions import ToolError

COLLECTION = "https://data.geo.admin.ch/api/stac/v1/collections/ch.meteoschweiz.ogd-local-forecasting"
DATA = "https://data.geo.admin.ch/ch.meteoschweiz.ogd-local-forecasting/"
PARAMETERS = {"temperature": ("tre200h0", "°C"), "precipitation": ("rre150h0", "mm"), "wind": ("fu3010h0", "km/h")}


def _normalize(value: str) -> str:
    """Match location names without requiring accents or a particular case."""
    return "".join(character for character in unicodedata.normalize("NFKD", value).casefold() if not unicodedata.combining(character))


async def meteo(
    location: Annotated[str, Field(min_length=1, max_length=100, description="Swiss postcode, place name, or station abbreviation.")],
    parameter: Literal["temperature", "precipitation", "wind", "all"] = "temperature",
    hours: Annotated[int, Field(ge=1, le=192)] = 24,
    include_hourly: Annotated[
        bool, Field(description="Set false for summary-only answers; keep true for charts or hourly forecasts.")
    ] = True,
) -> dict:
    """Get hourly MeteoSwiss forecasts for a Swiss postcode, place name, or station.

    Times are UTC. Temperature is in °C, precipitation in mm, and wind speed in km/h.
    For example, location="6900" or location="Lugano".
    If several locations match, ask the user to choose a returned station abbreviation.
    Use parameter="all" for a temperature, rain, and wind overview in one call.
    Use the supplied summaries instead of calculating ranges or totals yourself.
    Summaries flag missing hours; precipitation totals are null when incomplete.
    Set include_hourly=false when only a summary is needed; hourly rows are included by default.
    Attribute forecast data to MeteoSwiss (CC-BY).
    """

    # Reject blank locations before requesting the forecast catalog.
    query = _normalize(location.strip())
    if not query:
        raise ToolError("Enter a Swiss postcode, place name, or station abbreviation.")

    # Bound the complete lookup as well as individual network requests.
    async with asyncio.timeout(60):
        response = await website.fetch(f"{DATA}ogd-local-forecasting_meta_point.csv")
        points = list(csv.DictReader(io.StringIO(response.content.decode("cp1252")), delimiter=";"))

        # Prefer exact names, postcodes, and station codes over partial names.
        names = [_normalize(point["point_name"]) for point in points]
        matches = [
            point
            for point, name in zip(points, names, strict=True)
            if query in {name, point["postal_code"].casefold(), point["station_abbr"].casefold()}
        ]
        if not matches:
            matches = [point for point, name in zip(points, names, strict=True) if query in name]
        if not matches:
            raise ToolError("No forecast location found. Try a Swiss postcode, place name, or station abbreviation.")
        if len(matches) > 1:
            return {"locations": [{key: point[key] for key in ("point_name", "postal_code", "station_abbr")} for point in matches[:20]]}
        point = matches[0]

        # Skip empty future-day items and select the newest available forecast run.
        response = await website.fetch(f"{COLLECTION}/items", params={"limit": 5, "sortby": "-id"})
        features = response.json()["features"]
        now = datetime.now(UTC)
        end = now + timedelta(hours=hours)
        expected_times = {now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=offset) for offset in range(hours + 1)}
        expected_times = {timestamp.isoformat() for timestamp in expected_times if now <= timestamp <= end}
        measurements = {}
        async with httpx2.AsyncClient(timeout=30, trust_env=False) as client:
            for measurement in PARAMETERS if parameter == "all" else (parameter,):
                # Select and validate each measurement's newest download URL.
                code, unit = PARAMETERS[measurement]
                assets = [asset for item in features for name, asset in item["assets"].items() if name.endswith(f".{code}.csv")]
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
                forecast = []
                size = 0
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
                            value = float(row[3]) if row[3] else None
                            if value is not None and not math.isfinite(value):
                                value = None
                            forecast.append({"time": timestamp.isoformat(), "value": value})
                if not forecast:
                    raise ToolError("No upcoming forecast values are currently available for this location.")

                # Calculate summaries in code, marking null and absent hourly values as missing.
                available = {row["time"]: row["value"] for row in forecast if row["value"] is not None}
                values = list(available.values())
                missing_hours = len(expected_times - available.keys())
                summary = {
                    "start": now.isoformat(),
                    "end": end.isoformat(),
                    "available_hours": len(available),
                    "missing_hours": missing_hours,
                    "complete": missing_hours == 0,
                }
                if measurement == "temperature":
                    summary.update(minimum=min(values) if values else None, maximum=max(values) if values else None)
                elif measurement == "precipitation":
                    summary["total"] = round(sum(values), 6) if not missing_hours else None
                else:
                    summary["maximum"] = max(values) if values else None
                measurements[measurement] = {"parameter": measurement, "unit": unit, "summary": summary, "source": str(url)}
                if include_hourly:
                    measurements[measurement]["forecast"] = sorted(forecast, key=lambda value: str(value["time"]))

        # Preserve single-measurement responses and group combined forecasts under measurements.
        result = {"location": point["point_name"], "postal_code": point["postal_code"], "attribution": "MeteoSwiss (CC-BY)"}
        if parameter == "all":
            return {**result, "measurements": measurements}
        return {**result, **measurements[parameter]}
