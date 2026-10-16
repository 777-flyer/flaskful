"""Authentication, token rotation, revocation, and account security service layer."""

from __future__ import annotations

from typing import Any

from flask import current_app
from flask_jwt_extended import create_access_token, create_refresh_token
from sqlalchemy import or_, select

from app.core.exceptions import (
    AccountLockedError,
     APIError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
)
from app.extensions import db
from app.models.token_blocklist import TokenBlocklist
from app.models.user import User


class AuthService:
    """Encapsulates user registration, hardened login, token rotation, and revocation."""

    @staticmethod
    def register_user(data: dict[str, Any]) -> dict[str, Any]:
        """Register a new user and return user + JWT tokens."""
        username = data["username"].strip()
        email = data["email"].strip().lower()

        existing_user = db.session.scalar(
            select(User).where(or_(User.email == email, User.username == username))
        )
        if existing_user is not None:
            if existing_user.email == email:
                raise ConflictError("A user with this email address already exists.")
            raise ConflictError("A user with this username already exists.")

        user = User(username=username, email=email)
        user.set_password(data["password"])
        user.save()

        return AuthService.build_auth_payload(user)

    @staticmethod
    def authenticate_user(data: dict[str, Any]) -> dict[str, Any]:
        """Verify user credentials with timing-attack mitigation and brute-force lockout."""
        email = data["email"].strip().lower()
        raw_password = data["password"]
        user = db.session.scalar(select(User).where(User.email == email))

        if user is None:
            # Constant-time dummy check prevents timing-based email enumeration
            User.verify_dummy_password(raw_password)
            raise UnauthorizedError("Invalid email or password.")

        if not user.is_active:
            raise UnauthorizedError("This user account has been deactivated.")

        if user.is_locked():
            raise AccountLockedError(
                "Account is temporarily locked due to multiple failed login attempts. Please try again later."
            )

        if not user.check_password(raw_password):
            max_attempts = int(current_app.config.get("MAX_FAILED_LOGIN_ATTEMPTS", 5))
            lockout_mins = int(current_app.config.get("ACCOUNT_LOCKOUT_MINUTES", 15))
            user.record_failed_login(
                max_attempts=max_attempts, lockout_minutes=lockout_mins
            )
            if user.is_locked():
                raise AccountLockedError(
                    "Account has been temporarily locked due to multiple failed login attempts."
                )
            raise UnauthorizedError("Invalid email or password.")

        user.reset_failed_logins()
        return AuthService.build_auth_payload(user)

    @staticmethod
    def rotate_refresh_token(jwt_payload: dict[str, Any]) -> dict[str, str]:
        """Revoke the used refresh token JTI and issue a new access + refresh token pair."""
        jti = jwt_payload["jti"]
        identity = str(jwt_payload["sub"])
        user = AuthService.get_user_by_id(identity)

        # Single-use refresh token rotation: block the old refresh token immediately
        TokenBlocklist.revoke_token(jti=jti, token_type="refresh", user_id=user.id)

        return {
            "access_token": create_access_token(
                identity=identity, additional_claims={"role": user.role}
            ),
            "refresh_token": create_refresh_token(identity=identity),
            "token_type": "Bearer",
        }

    @staticmethod
    def revoke_token_payload(jwt_payload: dict[str, Any]) -> None:
        """Add the given token's JTI to the persistent blocklist."""
        jti = jwt_payload["jti"]
        token_type = jwt_payload.get("type", "access")
        sub = jwt_payload.get("sub")
        user_id = int(sub) if sub is not None else None
        TokenBlocklist.revoke_token(jti=jti, token_type=token_type, user_id=user_id)

    @staticmethod
    def change_password(
        user_id: int,
        current_password: str,
        new_password: str,
        current_jti: str | None = None,
    ) -> None:
        """Verify current password, set new password, and revoke the current access token."""
        user = AuthService.get_user_by_id(user_id)
        if not user.check_password(current_password):
            raise UnauthorizedError("Current password is incorrect.")
        if current_password == new_password:
            raise APIError(
                "New password must be different from the current password.",
                status_code=400,
                error_code="INVALID_PASSWORD_CHANGE",
            )
        user.set_password(new_password)
        user.save()
        if current_jti:
            TokenBlocklist.revoke_token(
                jti=current_jti, token_type="access", user_id=user.id
            )

    @staticmethod
    def get_user_by_id(user_id: int | str) -> User:
        """Retrieve an active user by ID or raise NotFoundError."""
        user = db.session.get(User, int(user_id))
        if user is None or not user.is_active:
            raise NotFoundError("User account not found.")
        return user

    @staticmethod
    def build_auth_payload(user: User) -> dict[str, Any]:
        """Generate access and refresh JWT tokens for a given User."""
        identity = str(user.id)
        access_token = create_access_token(
            identity=identity, additional_claims={"role": user.role}
        )
        refresh_token = create_refresh_token(identity=identity)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "user": user,
        }
