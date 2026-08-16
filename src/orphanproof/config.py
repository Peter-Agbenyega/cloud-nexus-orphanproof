"""Runtime configuration for the OrphanProof API."""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CORS_ORIGIN = "http://localhost:5173"
DEFAULT_AWS_REGION = "us-east-1"
DEFAULT_EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
DEFAULT_REASONING_MODEL = "amazon.nova-lite-v1:0"
DEFAULT_MCP_URL = "https://cockroachlabs.cloud/mcp"
PUBLIC_DEMO_RESOURCE_KEYS = frozenset(
    {
        "demo-rds-dr-standby-001",
        "demo-ebs-abandoned-001",
    }
)


class Settings(BaseSettings):
    """Application settings loaded from process environment."""

    model_config = SettingsConfigDict(extra="ignore")

    database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
        repr=False,
    )
    database_url_parameter_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "ORPHANPROOF_DATABASE_URL_PARAMETER_NAME",
            "database_url_parameter_name",
        ),
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
    public_demo_only: bool = Field(
        default=False,
        validation_alias=AliasChoices("ORPHANPROOF_PUBLIC_DEMO_ONLY", "public_demo_only"),
    )
    aws_region: str = Field(
        default=DEFAULT_AWS_REGION,
        validation_alias=AliasChoices("ORPHANPROOF_AWS_REGION", "aws_region"),
    )
    bedrock_embedding_model: str = Field(
        default=DEFAULT_EMBEDDING_MODEL,
        validation_alias=AliasChoices(
            "ORPHANPROOF_BEDROCK_EMBEDDING_MODEL",
            "bedrock_embedding_model",
        ),
    )
    bedrock_reasoning_model: str = Field(
        default=DEFAULT_REASONING_MODEL,
        validation_alias=AliasChoices(
            "ORPHANPROOF_BEDROCK_REASONING_MODEL",
            "bedrock_reasoning_model",
        ),
    )
    mcp_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("ORPHANPROOF_MCP_ENABLED", "mcp_enabled"),
    )
    mcp_url: str = Field(
        default=DEFAULT_MCP_URL,
        validation_alias=AliasChoices("ORPHANPROOF_MCP_URL", "mcp_url"),
    )
    mcp_cluster_id: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("ORPHANPROOF_MCP_CLUSTER_ID", "mcp_cluster_id"),
        repr=False,
    )
    mcp_bearer_token: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("ORPHANPROOF_MCP_BEARER_TOKEN", "mcp_bearer_token"),
        repr=False,
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
            if self.database_url_parameter_name:
                return self._load_database_url_from_ssm()
            raise RuntimeError("DATABASE_URL is required for the live repository")
        return self.database_url

    def _load_database_url_from_ssm(self) -> str:
        if not self.database_url_parameter_name:
            raise RuntimeError("database URL parameter name is required")
        try:
            import boto3

            client = boto3.client("ssm", region_name=self.aws_region)
            response = client.get_parameter(
                Name=self.database_url_parameter_name,
                WithDecryption=True,
            )
            value = response["Parameter"]["Value"]
        except Exception as exc:  # pragma: no cover - AWS-provider specific
            raise RuntimeError("database URL secret could not be loaded") from exc
        if not isinstance(value, str) or not value:
            raise RuntimeError("database URL secret is empty")
        return value

    def mcp_is_configured(self) -> bool:
        return bool(self.mcp_enabled and self.mcp_cluster_id and self.mcp_bearer_token)

    def __repr__(self) -> str:
        fields = self.model_dump(
            exclude={
                "database_url",
                "database_url_parameter_name",
                "mcp_cluster_id",
                "mcp_bearer_token",
            }
        )
        return (
            "Settings(database_url='***REDACTED***', "
            "database_url_parameter_name='***REDACTED***', "
            "mcp_cluster_id='***REDACTED***', "
            f"mcp_bearer_token='***REDACTED***', {fields!r})"
        )

    def __str__(self) -> str:
        return self.__repr__()


def get_settings() -> Settings:
    """Load settings at call time so tests can inject configuration safely."""

    return Settings()
