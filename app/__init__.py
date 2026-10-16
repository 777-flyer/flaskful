"""Flask Application Factory with enterprise security & database hardening."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify

from app.api import register_blueprints
from app.config import CONFIG_BY_NAME
from app.core.cli import register_cli_commands
from app.core.error_handlers import register_error_handlers
from app.core.security import register_security_middleware
from app.extensions import api, cors, db, jwt, limiter, migrate


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application instance."""
    app = Flask(__name__, instance_relative_config=True)

    # Ensure instance folder exists for local SQLite databases
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    env_name = (config_name or os.getenv("FLASK_ENV", "development")).lower()
    config_cls = CONFIG_BY_NAME.get(env_name, CONFIG_BY_NAME["default"])
    config_cls.validate()
    app.config.from_object(config_cls)

    # Import models so SQLAlchemy and Flask-Migrate register metadata
    from app import models as _models  # noqa: F401

    # Initialize Flask extensions
    db.init_app(app)
    migrate.init_app(app, db)
    api.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}},
        supports_credentials=True,
        expose_headers=["X-Request-ID", "Retry-After", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
    )

    # Register HTTP security headers, request ID tracing, and ProxyFix middleware
    register_security_middleware(app)

    # Register versioned REST API blueprints
    register_blueprints(api)

    # Register global JSON error handlers, DB rollback safety, and JWT revocation callbacks
    register_error_handlers(app, jwt)

    # Register custom CLI commands (flask init-db, flask seed-db)
    register_cli_commands(app)

    # Root discovery endpoint
    @app.get("/")
    def index():
        return jsonify(
            {
                "name": app.config.get("API_TITLE", "FlaskFul API"),
                "version": app.config.get("API_VERSION", "v1"),
                "docs_url": app.config.get("OPENAPI_SWAGGER_UI_PATH", "/docs"),
                "redoc_url": app.config.get("OPENAPI_REDOC_PATH", "/redoc"),
                "health_url": "/api/v1/health",
            }
        )

    return app
