from typing import Literal, Annotated
from src.mcp import context
from datetime import UTC, date, time, datetime, timedelta
from pydantic import Field, BaseModel, ConfigDict, computed_field
from src.utils import website
from urllib.parse import quote
from mcp.server.mcpserver.exceptions import ToolError


class Announcements(BaseModel):
    """An official federal announcement in its published language."""

    model_config = ConfigDict(json_schema_mode_override="serialization")

    # Published content and source identifiers.
    id: str
    title: str
    language: Literal["de", "fr", "it", "en"] = Field(validation_alias="lang")
    text_html: list[str] = Field(validation_alias="text")
    description: str
    published_at: datetime = Field(validation_alias="publishDate")
    publisher_ids: list[str] = Field(validation_alias="publishers")
    language_group_id: str = Field(validation_alias="langGroupId")

    @computed_field
    @property
    def source(self) -> str:
        """Link to the announcement on the official federal portal."""
        return f"https://www.admin.ch/{self.language}/newnsb/{quote(self.language_group_id, safe='')}"


class AnnouncementResults(BaseModel):
    """A page of announcements returned by News Service Bund."""

    model_config = ConfigDict(json_schema_mode_override="serialization")

    # Pagination and original announcements.
    items: list[Announcements]
    limit: int
    total: int = Field(validation_alias="pageResults")
    offset: int


async def government_announcements(
    start_date: Annotated[date | None, Field(description="First publication date (inclusive), YYYY-MM-DD.")] = None,
    end_date: Annotated[date | None, Field(description="Last publication date (inclusive), YYYY-MM-DD. Defaults to today in UTC.")] = None,
    limit: Annotated[int, Field(ge=1, le=20)] = 5,
    offset: Annotated[int, Field(ge=0)] = 0,
) -> AnnouncementResults:
    """Get official Swiss federal press releases directly from News Service Bund.

    Defaults to the last 30 days, newest first. Use offset to fetch more results.
    Returns original full text as HTML paragraphs, publication dates, publisher IDs,
    and official source links. Cite those links and distinguish quotations from summaries.
    Uses the conversation language automatically, with English sources for Romansh.
    Only announcements published in that source language are returned; an empty page
    does not imply there are no announcements in other languages. Does not cover cantonal
    or municipal announcements.
    """

    # Use inclusive calendar dates and default to the past 30 days in UTC.
    end_date = end_date or datetime.now(UTC).date()
    start_date = start_date or end_date - timedelta(days=min(29, (end_date - date.min).days))
    if start_date > end_date:
        raise ToolError("The start date must not be after the end date.")

    # News Service Bund does not publish a Romansh feed.
    language = context.current.get().language
    if language == "rm":
        language = "en"

    # Fetch press releases only, without accepting arbitrary upstream URLs.
    params = {
        "languages": language,
        "start_date": datetime.combine(start_date, time.min, UTC).isoformat(),
        "end_date": datetime.combine(end_date, time.max, UTC).isoformat(),
        "newsCategoryIDs": "medienmitteilung",
        "limit": limit,
        "offset": offset,
    }
    response = await website.fetch("https://www.newsd.admin.ch/v1/search", params=params)
    return AnnouncementResults.model_validate(response.json())
