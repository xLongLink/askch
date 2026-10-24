from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load provider configuration from environment variables and dotenv."""

    model_config = SettingsConfigDict(env_file=".env")

    # Store chat traces locally until a remote storage backend is configured.
    CHATS_DIR: Path = Path(".chats")

    # Load the default system instructions from the packaged prompt file.
    SYSTEM_PROMPT: str = Path(__file__).with_name("SYSTEM.md").read_text(encoding="utf-8").strip()

    # Configure the Infomaniak model and credentials.
    INFOMANIAK_MODEL: str = "swiss-ai/Apertus-v1.5-70B"
    INFOMANIAK_API_KEY: SecretStr = SecretStr("")
    INFOMANIAK_PRODUCT_ID: str = Field(default="112804", pattern=r"^\d+$")


settings = Settings()
