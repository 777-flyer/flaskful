"""API v1 blueprints export."""

from app.api.v1.admin import blp as admin_blp
from app.api.v1.auth import blp as auth_blp
from app.api.v1.health import blp as health_blp
from app.api.v1.items import blp as items_blp

V1_BLUEPRINTS = (
    health_blp,
    auth_blp,
    items_blp,
    admin_blp,
)

__all__ = ["V1_BLUEPRINTS"]
