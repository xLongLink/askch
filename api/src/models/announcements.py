from typing import Literal
from datetime import datetime
from pydantic import Field, BaseModel, ConfigDict, computed_field
from urllib.parse import quote


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
