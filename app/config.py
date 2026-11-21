from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/nomerok"
    bot_token: str = Field(
        default="",
        validation_alias=AliasChoices("BOT_TOKEN", "TELEGRAM_BOT_TOKEN"),
    )
    admin_id: int = Field(
        default=0,
        validation_alias=AliasChoices("ADMIN_ID", "TELEGRAM_ADMIN_ID"),
    )
    webhook_secret: str = Field(
        default="",
        validation_alias=AliasChoices("WEBHOOK_SECRET", "TELEGRAM_WEBHOOK_SECRET"),
    )
    public_url: str = Field(default="http://localhost:8000", validation_alias="PUBLIC_URL")
    dev_mode: bool = Field(default=True, validation_alias="DEV_MODE")

    free_spin_hours: int = 3
    spin_cost: int = 50
    daily_base: int = 150
    start_balance: int = 1500


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
