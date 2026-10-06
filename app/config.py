"""
Configuration: loads and manages application settings from environment variables.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings loaded from environment.

    Attributes:
        ENVIRONMENT: Runtime environment mode (e.g. 'development', 'production').
        HOST: Server bind host address.
        PORT: Server bind port.
        LOG_LEVEL: Logging level (e.g. 'info', 'debug').
        BACKEND_URL: Base URL of Elysia backend service.
        BACKEND_TIMEOUT_SECONDS: Timeout for HTTP requests to Elysia backend.
        BACKEND_MATCHING_POOL_PATH: Path for matching pool endpoint on backend.
        BACKEND_CANDIDATES_PATH: Path for candidate pool endpoint on backend.
        WEIGHT_AGE: Scoring weight for age compatibility.
        WEIGHT_DISTANCE: Scoring weight for distance compatibility.
        DEFAULT_AGE_SIGMA: Fallback sigma for zero-width age preferences.
        SCORE_DECIMALS: Number of decimal places to round match score.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "info"

    BACKEND_URL: str = Field(
        default="http://api:3000",
        description="Base URL of the Elysia backend service",
    )
    BACKEND_TIMEOUT_SECONDS: float = Field(
        default=10.0,
        description="HTTP request timeout in seconds when calling the backend",
    )
    BACKEND_MATCHING_POOL_PATH: str = Field(
        default="/internal/v1/matching-pool",
        description="Path for fetching user profile and candidates pool",
    )
    BACKEND_CANDIDATES_PATH: str = Field(
        default="/internal/v1/candidates",
        description="Path for fetching candidate pool for search",
    )

    WEIGHT_AGE: float = Field(
        default=0.7,
        description="Weight w_age for age compatibility",
    )
    WEIGHT_DISTANCE: float = Field(
        default=0.3,
        description="Weight w_distance for distance compatibility",
    )
    DEFAULT_AGE_SIGMA: float = Field(
        default=2.0,
        description="Fallback sigma value for age scoring if range width is zero",
    )
    SCORE_DECIMALS: int = Field(
        default=1,
        description="Decimal places for rounding match scores (e.g. 96.4)",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton.

    Returns:
        The cached Settings instance.
    """
    return Settings()
