import asyncio
from typing import Literal, Annotated
from datetime import date, datetime
from pydantic import Field, AliasPath, BaseModel, ConfigDict, AliasChoices, computed_field
from zoneinfo import ZoneInfo
from src.utils import website
from urllib.parse import quote
from mcp.server.mcpserver.exceptions import ToolError

DEPARTMENTS = {
    "D-ARCH": "02100wd",
    "D-BAUG": "02115wd",
    "D-BSSE": "02060wd",
    "D-INFK": "02150wd",
    "D-ITET": "02140wd",
    "D-MATL": "02160wd",
    "D-MAVT": "02130wd",
    "D-BIOL": "02030wd",
    "D-CHAB": "02020wd",
    "D-MATH": "02000wd",
    "D-PHYS": "02010wd",
    "D-EAPS": "02330wd",
    "D-HEST": "02070wd",
    "D-USYS": "02350wd",
    "D-MTEC": "02120wd",
    "D-GESS": "02045wd",
}

ACCESSIBILITY = {"motor disabilities": "1", "visual impairments": "2", "hearing impairments": "3", "sign language": "4"}


class FilterOptions(BaseModel):
    """A public calendar filter value and its display label."""

    model_config = ConfigDict(json_schema_mode_override="serialization")

    # Upstream filter identifiers and descriptions.
    code: str = Field(validation_alias=AliasChoices("code", "id"), coerce_numbers_to_str=True)
    label: str = Field(validation_alias=AliasChoices("label", "desc"))


class EventFilters(BaseModel):
    """Available filters matching the ETH Zurich event search interface."""

    # Filter categories.
    types: list[str]
    locations: list[str]
    departments: list[str]
    accessibility: list[str]


class Events(BaseModel):
    """An ETH Zurich calendar entry with its original schedule and location."""

    model_config = ConfigDict(json_schema_mode_override="serialization")

    # Event identity and published content.
    id: int
    title: str = Field(validation_alias=AliasPath("content", "title"))
    event_type: str = Field(validation_alias=AliasPath("classification", "entry-type-desc"))
    description: str | None = Field(default=None, validation_alias=AliasPath("content", "description"))
    registration_required: bool | None = Field(default=None, validation_alias=AliasPath("classification", "registration-required"))

    # Preserve recurring dates, opening hours, and location details without inventing missing values.
    location: dict[str, object] | None = None
    schedule: dict[str, object] = Field(validation_alias="date-time-indication")
    organizers: dict[str, object] | None = None
    accessibility: list[dict[str, str | int]] = Field(
        default_factory=list, validation_alias=AliasPath("classification", "accessibility-array")
    )

    @computed_field
    @property
    def source(self) -> str:
        """Link to the event on the official ETH Zurich calendar."""
        return f"https://ethz.ch/en/news-and-events/events/details.{quote(self.title, safe='')}.{self.id}.html"


class EventResults(BaseModel):
    """A page of ETH Zurich calendar entries."""

    model_config = ConfigDict(json_schema_mode_override="serialization")

    # Results and pagination.
    items: list[Events] = Field(validation_alias="entry-array")
    limit: int
    offset: int


async def _catalog(category: Literal["types", "locations"], *, needed: bool) -> list[FilterOptions]:
    """Load an event filter catalog only when the caller needs it."""

    # Skip unused catalogs so unrelated services cannot fail the requested lookup.
    if not needed:
        return []

    # Fetch and validate the requested catalog from its public endpoint.
    if category == "types":
        response = await website.fetch(
            "https://idapps.ethz.ch/pcm-pub-services/v2/entry-types", params={"lang": "en", "client-id": "wcms", "cal": 1}
        )
        options = response.json()["entry-type-array"]
    else:
        response = await website.fetch(
            "https://idapps.ethz.ch/domains-services/v1/locations/areas", params={"lang": "en", "client-id": "wcms"}
        )
        options = response.json()["area-array"]
    return [FilterOptions.model_validate(option) for option in options]


async def ethz_event_filters(
    category: Annotated[
        Literal["all", "types", "locations", "departments", "accessibility"],
        Field(description="Filter category to list. Use all to discover every available filter."),
    ] = "all",
) -> EventFilters:
    """List readable filter names accepted by ethz_events; no numeric IDs or codes are needed.

    Defaults to all filters; select a category only to narrow the response.
    Unrequested categories are empty. Pass names directly in the corresponding filter lists. Names are
    case-insensitive, such as types=["Exhibition"] or departments=["D-INFK"].
    """

    # Return accepted names rather than exposing the upstream identifiers.
    types, locations = await asyncio.gather(
        _catalog("types", needed=category in ("all", "types")), _catalog("locations", needed=category in ("all", "locations"))
    )
    return EventFilters(
        types=[option.label for option in types] if category in ("all", "types") else [],
        locations=[option.label for option in locations] if category in ("all", "locations") else [],
        departments=list(DEPARTMENTS) if category in ("all", "departments") else [],
        accessibility=list(ACCESSIBILITY) if category in ("all", "accessibility") else [],
    )


async def ethz_events(
    search: Annotated[str, Field(max_length=200, description="Keywords to search for in the event calendar.")] = "",
    departments: Annotated[
        list[Annotated[str, Field(min_length=1, max_length=100)]] | None,
        Field(max_length=16, description="Department names, such as D-INFK or D-PHYS. Case-insensitive."),
    ] = None,
    types: Annotated[
        list[Annotated[str, Field(min_length=1, max_length=100)]] | None,
        Field(max_length=50, description="Event type names, such as Exhibition, Workshop, Seminar, or Public lecture. Case-insensitive."),
    ] = None,
    start_date: Annotated[date | None, Field(description="Include events ending on or after this date, YYYY-MM-DD.")] = None,
    end_date: Annotated[date | None, Field(description="Include events starting on or before this date, YYYY-MM-DD.")] = None,
    locations: Annotated[
        list[Annotated[str, Field(min_length=1, max_length=100)]] | None,
        Field(max_length=30, description="Location names, such as Zürich Zentrum or Zürich Hönggerberg. Case-insensitive."),
    ] = None,
    accessibility: Annotated[
        list[Literal["motor disabilities", "visual impairments", "hearing impairments", "sign language"]] | None,
        Field(max_length=4, description="Accessibility needs as readable names, not numeric codes."),
    ] = None,
    limit: Annotated[int, Field(ge=1, le=20)] = 5,
    offset: Annotated[int, Field(ge=0)] = 0,
) -> EventResults:
    """Get ongoing and upcoming events from ETH Zurich's official event calendar.

    Uses the same public feed as https://ethz.ch/en/news-and-events/events.html.
    Use readable filter names, never numeric IDs or upstream codes. For example,
    types=["Workshop"], departments=["D-INFK"], locations=["Zürich Zentrum"],
    accessibility=["motor disabilities"]. Call ethz_event_filters for all names.
    Filters are applied upstream before pagination, using the same multi-select
    semantics as the UI.
    Dates select entries overlapping the inclusive date range, not individual
    occurrences. Without dates, returns ongoing and upcoming events within 30 days.
    Includes exhibitions and recurring events, in the calendar's original order.
    Some content is only available in German. Schedule dates and times are local
    to the event; recurring entries can also contain past dates. Respect opening
    hours and closure exceptions rather than treating exhibitions as always open.
    Cite the official event links. Increase offset by limit for another page;
    an empty items list means there are no more entries.
    """

    # Reject invalid date ranges before requesting events.
    if start_date and end_date and start_date > end_date:
        raise ToolError("The start date must not be after the end date.")

    # Match the UI's absolute date filters instead of combining them with its relative defaults.
    params: dict[str, str | int] = {"rs-size": limit, "rs-first": offset, "filters[0].cals": 1, "lang": "en", "client-id": "wcms"}
    if start_date or end_date:
        params["filters[0].ends-not-before"] = (start_date or datetime.now(ZoneInfo("Europe/Zurich")).date()).isoformat()
        if end_date:
            params["filters[0].starts-not-after"] = end_date.isoformat()
    else:
        params["filters[0].min-till-end"] = 0
        params["filters[0].max-till-start"] = 30

    # Load the current labels only when type or location translation is needed.
    type_options, location_options = await asyncio.gather(
        _catalog("types", needed=bool(types)), _catalog("locations", needed=bool(locations))
    )
    filters = (
        ("departments", "org-units", departments, DEPARTMENTS),
        ("types", "e-types", types, {option.label: option.code for option in type_options}),
        ("locations", "locs", locations, {option.label: option.code for option in location_options}),
        ("accessibility", "bf", accessibility, ACCESSIBILITY),
    )

    # Translate readable names to upstream codes immediately before fetching events.
    if search.strip():
        params["filters[0].search-term"] = search.strip()
    for category, name, values, options in filters:
        if values:
            codes = []
            normalized_options = {label.casefold(): code for label, code in options.items()}
            for value in values:
                code = normalized_options.get(value.strip().casefold())
                if code is None:
                    raise ToolError(f"Unknown {category} value '{value}'. Choose from: {', '.join(options)}.")
                codes.append(code)
            params[f"filters[0].{name}"] = ",".join(codes)

    # Fetch the public calendar without expanding recurring events into thousands of occurrences.
    response = await website.fetch("https://idapps.ethz.ch/pcm-pub-services/v2/entries", params=params)
    return EventResults.model_validate({**response.json(), "limit": limit, "offset": offset})
