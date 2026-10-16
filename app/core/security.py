"""HTTP security headers, request tracing, proxy hardening, and RBAC decorators."""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from functools import wraps

from flask import Flask, Response, current_app, g, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from werkzeug.middleware.proxy_fix import ProxyFix

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.extensions import db

SAFE_REQUEST_ID_PATTERN = re.compile(r"^[a-zA-Z0-9\-_]{1,64}$")


def register_security_middleware(app: Flask) -> None:
    """Configure reverse proxy trust, request ID tracing, and OWASP security headers."""
    trusted_proxies = int(app.config.get("TRUSTED_PROXY_COUNT", 0))
    if trusted_proxies > 0:
        app.wsgi_app = ProxyFix(  # type: ignore[method-assign]
            app.wsgi_app,
            x_for=trusted_proxies,
            x_proto=trusted_proxies,
            x_host=trusted_proxies,
            x_Prefix=trusted_proxies,
        )

    @app.before_request
    def attach_request_id() -> None:
        """Assign or sanitize X-Request-ID for end-to-end audit correlation."""
        incoming_id = request.headers.get("X-Request-ID", "").strip()
        if incoming_id and SAFE_REQUEST_ID_PATTERN.match(incoming_id):
            g.request_id = incoming_id
        else:
            g.request_id = str(uuid.uuid4())

    @app.after_request
    def set_security_headers(response: Response) -> Response:
        """Apply OWASP-recommended HTTP security headers to all responses."""
        # Request correlation header
        request_id = getattr(g, "request_id", None)
        if request_id:
            response.headers["X-Request-ID"] = request_id

        # Prevent MIME-sniffing and clickjacking
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
        )

        # Strict CSP and cache prevention for API endpoints
        if request.path.startswith("/api/"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'"
            )
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, max-age=0"
            )
            response.headers["Pragma"] = "no-cache"

        # Enforce HSTS in production or over HTTPS connections
        if not current_app.config.get("DEBUG") or request.is_secure:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )

        return response


def roles_required(*allowed_roles: str) -> Callable:
    """Decorator enforcing Role-Based Access Control (RBAC) on JWT-protected endpoints."""

    def wrapper(fn: Callable) -> Callable:
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            from app.models.user import User

            user_id = int(get_jwt_identity())
            user = db.session.get(User, user_id)
            if user is None or not user.is_active:
                raise UnauthorizedError("User account is inactive or does not exist.")
            if user.role not in allowed_roles:
                raise ForbiddenError(
                    f"Access denied. Required role(s): {', '.join(allowed_roles)}."
                )
            return fn(*args, **kwargs)

        return decorator

    return wrapper
