from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    infomaniak_api_key: SecretStr = SecretStr("")
    infomaniak_product_id: str = Field(default="112804", pattern=r"^\d+$")
    infomaniak_model: str = "swiss-ai/Apertus-v1.5-70B"
    frontend_dir: Path | None = None
