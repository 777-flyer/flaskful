"""Centralized blueprint registration for the REST API."""

from flask_smorest import Api

from app.api.v1 import V1_BLUEPRINTS


def register_blueprints(api_ext: Api) -> None:
    """Register all versioned API blueprints with Flask-Smorest."""
    for blueprint in V1_BLUEPRINTS:
        api_ext.register_blueprint(blueprint)

