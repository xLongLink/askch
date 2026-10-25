from pydantic import BaseModel, ConfigDict
from src.models.languages import Languages


class ChatContext(BaseModel):
    """Keep validated conversation preferences isolated to each agent run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Default API clients without a UI language to English.
    language: Languages = Languages.ENGLISH
