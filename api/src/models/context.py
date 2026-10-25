from typing import Literal
from pydantic import BaseModel, ConfigDict


class ChatContext(BaseModel):
    """Keep validated conversation preferences isolated to each agent run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Default API clients without a UI language to English.
    language: Literal["de", "fr", "it", "rm", "en"] = "en"
