import re
import html
from typing import Literal, Annotated
from pydantic import Field, AliasPath, BaseModel, ConfigDict, field_validator
from src.utils import website
from mcp.server.mcpserver.exceptions import ToolError

SEARCH = "https://api3.geo.admin.ch/rest/services/api/SearchServer"


class City(BaseModel):
    """An official geographic search match for a municipality or postcode."""

    model_config = ConfigDict(json_schema_mode_override="serialization")

    # Original search identifiers, text, and WGS84 coordinates.
    id: str = Field(validation_alias=AliasPath("attrs", "featureId"))
    name: str = Field(validation_alias=AliasPath("attrs", "label"))
    origin: Literal["gg25", "zipcode"] = Field(validation_alias=AliasPath("attrs", "origin"))
    latitude: float = Field(ge=-90, le=90, validation_alias=AliasPath("attrs", "lat"))
    longitude: float = Field(ge=-180, le=180, validation_alias=AliasPath("attrs", "lon"))

    @field_validator("name")
    @classmethod
    def plain_name(cls, value: str) -> str:
        """Remove search highlighting while preserving official spelling."""
        return html.unescape(re.sub(r"<[^>]*>", "", value))


class CityResults(BaseModel):
    """A bounded set of official geographic matches with provenance."""

    model_config = ConfigDict(json_schema_mode_override="serialization")

    # Search matches and their official source.
    items: list[City] = Field(validation_alias="results")
    source: str = SEARCH


async def cities(
    query: Annotated[str, Field(min_length=2, max_length=100, description="Swiss city, municipality, or postcode, e.g. Zürich or 8001.")],
    limit: Annotated[int, Field(ge=1, le=50)] = 10,
) -> CityResults:
    """Search Swiss cities, municipalities, and postcodes using swisstopo.

    Returns geographic names (including canton abbreviations where provided) and
    WGS84 coordinates. Municipalities have origin gg25; postcode areas have origin
    zipcode. Different language variants may refer to the same feature ID within
    an origin. Results are limited, not a complete list of Swiss municipalities.
    This is a geographic lookup, not population data or a legal city classification.
    Cite the source and attribute geographic data to swisstopo.
    """

    # Reject blank searches before querying the official geographic service.
    query = query.strip()
    if len(query) < 2:
        raise ToolError("Enter at least two characters of a Swiss place name or postcode.")

    # Restrict matches to municipalities and postcode areas, excluding street addresses.
    response = await website.fetch(SEARCH, params={"searchText": query, "type": "locations", "origins": "gg25,zipcode", "limit": limit})
    return CityResults.model_validate(response.json())
