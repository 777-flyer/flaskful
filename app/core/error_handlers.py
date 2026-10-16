"""Global JSON error handlers, database rollback protection, and JWT security callbacks."""

from __future__ import annotations

from flask import Flask, g, jsonify
from flask_jwt_extended import JWTManager
from flask_limiter.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.exceptions import HTTPException

from app.core.exceptions import APIError
from app.extensions import db


def _get_request_id() -> str | None:
    return getattr(g, "request_id", None)


def register_error_handlers(app: Flask, jwt_manager: JWTManager) -> None:
    """Attach global error handlers, DB rollback safety, and JWT callbacks to the app."""

    @app.errorhandler(APIError)
    def handle_api_error(error: APIError):
        return jsonify(error.to_dict(request_id=_get_request_id())), error.status_code

    @app.errorhandler(RateLimitExceeded)
    def handle_rate_limit_exceeded(error: RateLimitExceeded):
        payload = {
            "status": "error",
            "code": 429,
            "error": "TOO_MANY_REQUESTS",
            "message": f"Rate limit exceeded: {error.description}",
            "request_id": _get_request_id(),
        }
        return jsonify(payload), 429

    @app.errorhandler(IntegrityError)
    def handle_db_integrity_error(error: IntegrityError):
        # Always rollback session and never leak raw SQL/table details to the client
        db.session.rollback()
        app.logger.warning("Database integrity violation: %s", error)
        return (
            jsonify(
                {
                    "status": "error",
                    "code": 409,
                    "error": "DATABASE_INTEGRITY_ERROR",
                    "message": "The operation violated a database uniqueness or foreign-key constraint.",
                    "request_id": _get_request_id(),
                }
            ),
            409,
        )

    @app.errorhandler(SQLAlchemyError)
    def handle_sqlalchemy_error(error: SQLAlchemyError):
        # Rollback poisoned session and mask internal DB details
        db.session.rollback()
        app.logger.error("Database error: %s", error)
        return (
            jsonify(
                {
                    "status": "error",
                    "code": 500,
                    "error": "DATABASE_ERROR",
                    "message": "A database error occurred while processing the request.",
                    "request_id": _get_request_id(),
                }
            ),
            500,
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        data = getattr(error, "data", None)
        payload = {
            "status": "error",
            "code": error.code or 500,
            "error": error.name.upper().replace(" ", "_"),
            "message": error.description,
            "request_id": _get_request_id(),
        }
        if isinstance(data, dict):
            if "messages" in data:
                payload["message"] = "Validation failed."
                payload["details"] = data["messages"]
            elif "message" in data:
                payload["message"] = data["message"]
        return jsonify(payload), error.code or 500

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error: Exception):
        db.session.rollback()
        app.logger.exception("Unhandled exception: %s", error)
        return (
            jsonify(
                {
                    "status": "error",
                    "code": 500,
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected internal server error occurred.",
                    "request_id": _get_request_id(),
                }
            ),
            500,
        )

    # JWT Revocation (Blocklist) & Active User Verification Callbacks
    @jwt_manager.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header: dict, jwt_payload: dict) -> bool:
        from app.models.token_blocklist import TokenBlocklist

        jti = jwt_payload.get("jti")
        if not jti:
            return True
        if TokenBlocklist.is_jti_blocked(jti):
            return True

        # Also verify the user account still exists and is active
        from app.models.user import User

        identity = jwt_payload.get("sub")
        if identity is not None:
            user = db.session.get(User, int(identity))
            if user is None or not user.is_active:
                return True
        return False

    @jwt_manager.expired_token_loader
    def expired_token_callback(jwt_header: dict, jwt_payload: dict):
        return (
            jsonify(
                {
                    "status": "error",
                    "code": 401,
                    "error": "TOKEN_EXPIRED",
                    "message": "The authentication token has expired.",
                    "request_id": _get_request_id(),
                }
            ),
            401,
        )

    @jwt_manager.invalid_token_loader
    def invalid_token_callback(error_string: str):
        return (
            jsonify(
                {
                    "status": "error",
                    "code": 401,
                    "error": "INVALID_TOKEN",
                    "message": "Invalid authentication token.",
                    "request_id": _get_request_id(),
                }
            ),
            401,
        )

    @jwt_manager.unauthorized_loader
    def missing_token_callback(error_string: str):
        return (
            jsonify(
                {
                    "status": "error",
                    "code": 401,
                    "error": "AUTHORIZATION_REQUIRED",
                    "message": "Authorization header with Bearer token is required.",
                    "request_id": _get_request_id(),
                }
            ),
            401,
        )

    @jwt_manager.revoked_token_loader
    def revoked_token_callback(jwt_header: dict, jwt_payload: dict):
        return (
            jsonify(
                {
                    "status": "error",
                    "code": 401,
                    "error": "TOKEN_REVOKED",
                    "message": "The authentication token has been revoked or the account is inactive.",
                    "request_id": _get_request_id(),
                }
            ),
            401,
        )
