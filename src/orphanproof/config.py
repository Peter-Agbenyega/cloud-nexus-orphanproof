"""Runtime configuration for the OrphanProof API."""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CORS_ORIGIN = "http://localhost:5173"


class Settings(BaseSettings):
    """Application settings loaded from process environment."""

    model_config = SettingsConfigDict(extra="ignore")

    database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
        repr=False,
    )
    orphanproof_env: str = Field(
        default="development",
        validation_alias=AliasChoices("ORPHANPROOF_ENV", "orphanproof_env"),
    )
    cors_origins: list[str] = Field(
        default_factory=lambda: [DEFAULT_CORS_ORIGIN],
        validation_alias=AliasChoices("ORPHANPROOF_CORS_ORIGINS", "cors_origins"),
    )
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("ORPHANPROOF_LOG_LEVEL", "log_level"),
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if value is None or value == "":
            origins = [DEFAULT_CORS_ORIGIN]
        elif isinstance(value, str):
            origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        else:
            origins = list(value)

        if not origins:
            origins = [DEFAULT_CORS_ORIGIN]
        if "*" in origins:
            raise ValueError("wildcard CORS origins are not allowed")
        return origins

    def require_database_url(self) -> str:
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required for the live repository")
        return self.database_url

    def __repr__(self) -> str:
        fields = self.model_dump(exclude={"database_url"})
        return f"Settings(database_url='***REDACTED***', {fields!r})"

    def __str__(self) -> str:
        return self.__repr__()


def get_settings() -> Settings:
    """Load settings at call time so tests can inject configuration safely."""

    return Settings()
