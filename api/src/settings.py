from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load provider configuration from environment variables and dotenv."""

    model_config = SettingsConfigDict(env_file=".env")

    INFOMANIAK_API_KEY: SecretStr = SecretStr("")
    INFOMANIAK_PRODUCT_ID: str = Field(default="112804", pattern=r"^\d+$")
    INFOMANIAK_MODEL: str = "swiss-ai/Apertus-v1.5-70B"


settings = Settings()
