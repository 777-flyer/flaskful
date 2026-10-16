"""Centralized Flask extensions initialization and database engine hardening."""

import sqlite3

from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_smorest import Api
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase

# Naming convention for SQLAlchemy constraints to ensure smooth Alembic migrations
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 Declarative Base with standard naming conventions."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


@event.listens_for(Engine, "connect")
def _set_sqlite_security_pragmas(dbapi_connection, connection_record) -> None:
    """Enforce foreign keys, WAL mode, secure_delete, and schema hardening on SQLite."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        # Enforce foreign key constraints (disabled by default in SQLite!)
        cursor.execute("PRAGMA foreign_keys=ON;")
        # Prevent untrusted SQL functions/triggers in schemas from executing arbitrary code
        cursor.execute("PRAGMA trusted_schema=OFF;")
        # Overwrite deleted records with zeroes on disk so sensitive data does not linger
        cursor.execute("PRAGMA secure_delete=ON;")
        # Busy timeout (5s) to prevent lock contention failures
        cursor.execute("PRAGMA busy_timeout=5000;")
        # Enable Write-Ahead Logging for concurrency & crash resilience
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.close()


db = SQLAlchemy(model_class=Base)
migrate = Migrate()
api = Api()
jwt = JWTManager()
cors = CORS()
limiter = Limiter(key_func=get_remote_address)
