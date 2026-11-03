from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ShopEase Product Service"
    app_version: str = "1.0.0"
    sql_host: str | None = Field(default=None, validation_alias="SQL_HOST")
    sql_database: str | None = Field(default=None, validation_alias="SQL_DATABASE")
    sql_authentication: str = Field(
        default="SqlPassword",
        validation_alias="SQL_AUTHENTICATION",
    )
    sql_user: str | None = Field(default=None, validation_alias="SQL_USER")
    sql_password: str | None = Field(default=None, validation_alias="SQL_PASSWORD")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
