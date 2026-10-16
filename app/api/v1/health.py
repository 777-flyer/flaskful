"""Health check and system status endpoints."""

from flask import current_app
from flask.views import MethodView
from flask_smorest import Blueprint
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.schemas.common import HealthResponseSchema

blp = Blueprint(
    "Health",
    __name__,
    url_prefix="/api/v1/health",
    description="System health and readiness checks.",
)


@blp.route("")
class HealthCheckResource(MethodView):
    """Health check endpoint for monitoring and frontend connectivity verification."""

    @blp.response(200, HealthResponseSchema)
    def get(self):
        """Check API and database connectivity status."""
        db_status = "connected"
        try:
            db.session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            db_status = "disconnected"

        return {
            "status": "healthy" if db_status == "connected" else "degraded",
            "environment": "testing"
            if current_app.config.get("TESTING")
            else ("development" if current_app.config.get("DEBUG") else "production"),
            "database": db_status,
            "version": current_app.config.get("API_VERSION", "v1"),
        }

