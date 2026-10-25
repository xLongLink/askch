from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load provider configuration from environment variables and dotenv."""

    model_config = SettingsConfigDict(env_file=".env")

    # Store chat traces locally until a remote storage backend is configured.
    CHATS_DIR: Path = Path(".chats")

    # Load chat guidance and the generated component contract from packaged prompt files.
    SYSTEM_PROMPT: str = "\n\n".join(
        Path(__file__).with_name(name).read_text(encoding="utf-8").strip() for name in ("SYSTEM.md", "openui.txt")
    )

    # Configure the Infomaniak model and credentials.
    INFOMANIAK_MODEL: str = "swiss-ai/Apertus-v1.5-70B"
    INFOMANIAK_API_KEY: SecretStr = Field(min_length=1)
    INFOMANIAK_PRODUCT_ID: str = Field(default="112804", pattern=r"^\d+$")


settings = Settings()
