"""Application configuration settings across environments with enterprise security defaults."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from typing import Any, ClassVar

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

INSECURE_DEFAULT_SECRETS = {
    "dev-fallback-secret-key",
    "dev-fallback-jwt-secret-key",
    "change-this-secret-key-in-production",
    "change-this-secret-key-in-production-min-32-chars",
    "change-this-jwt-secret-key-in-production",
    "change-this-jwt-secret-key-in-production-min-32-chars",
}


def _parse_cors_origins(raw_origins: str) -> str | list[str]:
    """Parse comma-separated CORS origins from environment variable."""
    cleaned = raw_origins.strip()
    if not cleaned or cleaned == "*":
        return "*"
    return [origin.strip() for origin in cleaned.split(",") if origin.strip()]


def _build_engine_options(database_uri: str) -> dict[str, Any]:
    """Build hardened SQLAlchemy engine and connection pool options."""
    options: dict[str, Any] = {
        "pool_pre_ping": True,
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),
    }
    if not database_uri.startswith("sqlite"):
        options.update(
            {
                "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
                "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
                "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
            }
        )
    return options


class BaseConfig:
    """Base configuration shared across all environments."""

    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-fallback-secret-key")
    DEBUG: bool = False
    TESTING: bool = False

    # Request & Payload Hardening
    # Restrict maximum request payload size (default 1 MB) to prevent DoS / memory exhaustion
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_CONTENT_LENGTH_BYTES", str(1024 * 1024)))
    TRUSTED_PROXY_COUNT: int = int(os.getenv("TRUSTED_PROXY_COUNT", "0"))

    # Cookie & Session Hardening
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"

    # SQLAlchemy settings
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ECHO: bool = False

    # Flask-Smorest & OpenAPI settings
    API_TITLE: str = os.getenv("API_TITLE", "FlaskFul API")
    API_VERSION: str = os.getenv("API_VERSION", "v1")
    OPENAPI_VERSION: str = os.getenv("OPENAPI_VERSION", "3.0.3")
    OPENAPI_URL_PREFIX: str = os.getenv("OPENAPI_URL_PREFIX", "/")
    OPENAPI_SWAGGER_UI_PATH: str = os.getenv("OPENAPI_SWAGGER_UI_PATH", "/docs")
    OPENAPI_SWAGGER_UI_URL: str = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
    OPENAPI_REDOC_PATH: str = os.getenv("OPENAPI_REDOC_PATH", "/redoc")
    OPENAPI_REDOC_URL: str = (
        "https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"
    )

    # Register JWT Bearer Auth in OpenAPI / Swagger UI
    API_SPEC_OPTIONS: ClassVar[dict[str, Any]] = {
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "Enter your JWT access token in the format: **<token>**",
                }
            }
        }
    }

    # JWT & Authentication Security Configuration
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-fallback-jwt-secret-key")
    JWT_ALGORITHM: str = "HS256"
    JWT_TOKEN_LOCATION: ClassVar[list[str]] = ["headers"]
    JWT_HEADER_NAME: str = "Authorization"
    JWT_HEADER_TYPE: str = "Bearer"
    JWT_ACCESS_TOKEN_EXPIRES: timedelta = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "15"))
    )
    JWT_REFRESH_TOKEN_EXPIRES: timedelta = timedelta(
        days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_DAYS", "7"))
    )
    JWT_ERROR_MESSAGE_KEY: str = "message"

    # Brute-force Account Lockout Policy
    MAX_FAILED_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_FAILED_LOGIN_ATTEMPTS", "5"))
    ACCOUNT_LOCKOUT_MINUTES: int = int(os.getenv("ACCOUNT_LOCKOUT_MINUTES", "15"))

    # Rate Limiting (Flask-Limiter)
    RATELIMIT_ENABLED: bool = True
    RATELIMIT_STORAGE_URI: str = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_DEFAULT: str = os.getenv("RATELIMIT_DEFAULT", "200 per day;60 per minute")
    RATELIMIT_AUTH_LIMIT: str = os.getenv("RATELIMIT_AUTH_LIMIT", "5 per minute")
    RATELIMIT_HEADERS_ENABLED: bool = True

    # CORS Configuration (for separate frontend applications)
    CORS_ORIGINS: ClassVar[str | list[str]] = _parse_cors_origins(
        os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
    )

    @classmethod
    def validate(cls) -> None:
        """Hook to validate environment security invariants at startup."""


class DevelopmentConfig(BaseConfig):
    """Development environment configuration."""

    DEBUG: bool = True
    SESSION_COOKIE_SECURE: bool = False
    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'app.db'}"
    )
    SQLALCHEMY_ENGINE_OPTIONS: ClassVar[dict[str, Any]] = _build_engine_options(
        SQLALCHEMY_DATABASE_URI
    )


class TestingConfig(BaseConfig):
    """Testing environment configuration."""

    TESTING: bool = True
    DEBUG: bool = True
    SESSION_COOKIE_SECURE: bool = False
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS: ClassVar[dict[str, Any]] = _build_engine_options(
        SQLALCHEMY_DATABASE_URI
    )
    JWT_ACCESS_TOKEN_EXPIRES: timedelta = timedelta(minutes=5)
    RATELIMIT_ENABLED: bool = True
    RATELIMIT_DEFAULT: str = "1000 per minute"
    RATELIMIT_AUTH_LIMIT: str = "5 per minute"


class ProductionConfig(BaseConfig):
    """Production environment configuration with strict security enforcement."""

    DEBUG: bool = False
    TESTING: bool = False
    SESSION_COOKIE_SECURE: bool = True
    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'prod.db'}"
    )
    SQLALCHEMY_ENGINE_OPTIONS: ClassVar[dict[str, Any]] = _build_engine_options(
        SQLALCHEMY_DATABASE_URI
    )

    @classmethod
    def validate(cls) -> None:
        """Fail fast if production security requirements are violated."""
        if (
            not cls.SECRET_KEY
            or cls.SECRET_KEY in INSECURE_DEFAULT_SECRETS
            or len(cls.SECRET_KEY) < 32
        ):
            raise RuntimeError(
                "SECURITY ERROR: Production SECRET_KEY must be set to a strong "
                "random value of at least 32 characters."
            )
        if (
            not cls.JWT_SECRET_KEY
            or cls.JWT_SECRET_KEY in INSECURE_DEFAULT_SECRETS
            or len(cls.JWT_SECRET_KEY) < 32
        ):
            raise RuntimeError(
                "SECURITY ERROR: Production JWT_SECRET_KEY must be set to a strong "
                "random value of at least 32 characters."
            )
        if cls.SECRET_KEY == cls.JWT_SECRET_KEY:
            raise RuntimeError(
                "SECURITY ERROR: Production SECRET_KEY and JWT_SECRET_KEY must be distinct."
            )
        if cls.CORS_ORIGINS == "*":
            raise RuntimeError(
                "SECURITY ERROR: Wildcard CORS_ORIGINS='*' is forbidden in production. "
                "Specify explicit frontend origins."
            )


CONFIG_BY_NAME: dict[str, type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
