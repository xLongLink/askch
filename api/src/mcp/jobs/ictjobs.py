import html
from typing import Annotated
from datetime import datetime
from pydantic import Field, AliasPath, BaseModel, ConfigDict, TypeAdapter, field_validator
from src.utils import website


class Jobs(BaseModel):
    """A published ICT job listing with its original source link."""

    model_config = ConfigDict(json_schema_mode_override="serialization")

    # Listing identity and publication details.
    id: int
    title: str = Field(validation_alias=AliasPath("title", "rendered"))
    source: str = Field(validation_alias="link")
    published_at: datetime = Field(validation_alias="date")

    @field_validator("title")
    @classmethod
    def decode_title(cls, value: str) -> str:
        """Decode HTML entities in WordPress titles."""
        return html.unescape(value)


class JobResults(BaseModel):
    """A page of job listings from ictjobs.ch."""

    model_config = ConfigDict(json_schema_mode_override="serialization")

    # Results and pagination.
    page: int
    items: list[Jobs]
    total: int
    total_pages: int


async def ictjobs(
    search: Annotated[str, Field(max_length=200, description="Keywords to search for, such as Python or Zürich.")] = "",
    limit: Annotated[int, Field(ge=1, le=20)] = 5,
    page: Annotated[int, Field(ge=1)] = 1,
) -> JobResults:
    """Search IT job listings in Switzerland on ictjobs.ch, newest first.

    Leave search empty for the latest listings. Returns titles, publication dates
    in the site's local time, and source links, not full descriptions or application
    details. Cite source links; do not infer missing job requirements or salaries.
    Increase page to retrieve more results only when page is below total_pages.
    An empty items list means no matches, not a service failure. Search is a keyword
    search, not a dedicated geographic filter. By default, show a short Markdown list
    with each job's exact title, publication date, and source link. Use a card grid
    only if the user requests one. Include other details only if returned by a tool.
    """

    # Fetch only the public listing fields needed for search results.
    response = await website.fetch(
        "https://ictjobs.ch/wp-json/wp/v2/posts",
        params={"search": search, "per_page": limit, "page": page, "_fields": "id,title,link,date"},
    )
    listings = TypeAdapter(list[Jobs])
    items = listings.validate_python(response.json())
    return JobResults(
        page=page, items=items, total=int(response.headers["X-WP-Total"]), total_pages=int(response.headers["X-WP-TotalPages"])
    )
