"""Authentication, token rotation, logout, and password management endpoints."""

from flask import current_app
from flask.views import MethodView
from flask_jwt_extended import (
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from flask_smorest import Blueprint

from app.extensions import limiter
from app.schemas.auth import (
    AuthTokenResponseSchema,
    PasswordChangeSchema,
    TokenRotationResponseSchema,
    UserLoginSchema,
    UserRegisterSchema,
    UserSchema,
)
from app.schemas.common import MessageSchema
from app.services.auth_service import AuthService

blp = Blueprint(
    "Auth",
    __name__,
    url_prefix="/api/v1/auth",
    description="User registration, JWT authentication, token rotation, logout, and profile endpoints.",
)


def _auth_rate_limit() -> str:
    return current_app.config.get("RATELIMIT_AUTH_LIMIT", "5 per minute")


@blp.route("/register")
class AuthRegisterResource(MethodView):
    """User registration endpoint."""

    decorators = [limiter.limit(_auth_rate_limit)]

    @blp.arguments(UserRegisterSchema)
    @blp.response(201, AuthTokenResponseSchema)
    def post(self, user_data: dict):
        """Register a new user account and return JWT tokens."""
        return AuthService.register_user(user_data)


@blp.route("/login")
class AuthLoginResource(MethodView):
    """User login endpoint protected by rate limiting and account lockout."""

    decorators = [limiter.limit(_auth_rate_limit)]

    @blp.arguments(UserLoginSchema)
    @blp.response(200, AuthTokenResponseSchema)
    def post(self, credentials: dict):
        """Authenticate with email and password to receive JWT tokens."""
        return AuthService.authenticate_user(credentials)


@blp.route("/refresh")
class AuthRefreshResource(MethodView):
    """Single-use JWT refresh token rotation endpoint."""

    decorators = [limiter.limit(_auth_rate_limit)]

    @jwt_required(refresh=True)
    @blp.doc(security=[{"BearerAuth": []}])
    @blp.response(200, TokenRotationResponseSchema)
    def post(self):
        """Exchange a valid refresh token for a new access and refresh token pair (rotates token)."""
        jwt_payload = get_jwt()
        return AuthService.rotate_refresh_token(jwt_payload)


@blp.route("/logout")
class AuthLogoutResource(MethodView):
    """Token revocation (logout) endpoint."""

    @jwt_required(verify_type=False)
    @blp.doc(security=[{"BearerAuth": []}])
    @blp.response(200, MessageSchema)
    def post(self):
        """Revoke the current access or refresh token so it can no longer be used."""
        jwt_payload = get_jwt()
        AuthService.revoke_token_payload(jwt_payload)
        return {"status": "success", "message": "Token has been revoked successfully."}


@blp.route("/change-password")
class AuthChangePasswordResource(MethodView):
    """Authenticated password update endpoint."""

    decorators = [limiter.limit(_auth_rate_limit)]

    @jwt_required()
    @blp.doc(security=[{"BearerAuth": []}])
    @blp.arguments(PasswordChangeSchema)
    @blp.response(200, MessageSchema)
    def post(self, password_data: dict):
        """Update the authenticated user's password and revoke the current token."""
        user_id = int(get_jwt_identity())
        current_jti = get_jwt().get("jti")
        AuthService.change_password(
            user_id=user_id,
            current_password=password_data["current_password"],
            new_password=password_data["new_password"],
            current_jti=current_jti,
        )
        return {
            "status": "success",
            "message": "Password updated successfully. Please log in again.",
        }


@blp.route("/me")
class AuthMeResource(MethodView):
    """Current authenticated user profile endpoint."""

    @jwt_required()
    @blp.doc(security=[{"BearerAuth": []}])
    @blp.response(200, UserSchema)
    def get(self):
        """Get the currently authenticated user's profile."""
        user_id = int(get_jwt_identity())
        return AuthService.get_user_by_id(user_id)
