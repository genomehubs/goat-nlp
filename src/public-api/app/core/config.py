"""Configuration and settings"""

from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        # Don't try to parse complex types as JSON from env
        env_parse_enums=True,
    )

    # API Keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    admin_api_key: str = ""

    # Security
    secret_key: str = "dev-secret-key-change-in-production"

    # Rate Limiting
    redis_url: str = "redis://localhost:6379"
    free_tier_rate_limit: str = "100/day"

    # Database
    database_url: str = "sqlite+aiosqlite:///./usage.db"

    # CORS (accepts comma-separated string or list via validator)
    # Default allows all for local development
    allowed_origins: List[str] = ["*"]

    # Environment
    environment: str = "development"
    debug: bool = True

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_cors(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            return [origin.strip() for origin in v.split(",")]
        return v

    # Model Configuration
    default_free_model: str = "gpt-4o-mini"
    free_tier_models: List[str] = ["gpt-4o-mini", "claude-haiku-3.5-20241022"]
    premium_models: List[str] = [
        "claude-sonnet-4-5-20241022",
        "claude-sonnet-3-5-20241022",
        "gpt-4o",
        "gpt-4-turbo",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-2.0-flash-exp",
    ]

    # MCP Server
    mcp_server_url: str = "http://host.docker.internal:8008/mcp"


settings = Settings()
