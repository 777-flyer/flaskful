"""Custom Flask CLI commands for database initialization and seeding."""

import click
from flask import Flask
from sqlalchemy import select

from app.extensions import db
from app.models.item import Item
from app.models.user import User


def register_cli_commands(app: Flask) -> None:
    """Register custom management commands with the Flask CLI."""

    @app.cli.command("init-db")
    def init_db_command() -> None:
        """Create all database tables directly from SQLAlchemy models."""
        db.create_all()
        click.echo("Initialized the database tables.")

    @app.cli.command("seed-db")
    def seed_db_command() -> None:
        """Seed the database with a demo user, an admin user, and sample items."""
        db.create_all()

        # 1. Seed standard demo user
        demo_email = "demo@example.com"
        user = db.session.scalar(select(User).where(User.email == demo_email))
        if user is None:
            user = User(username="demouser", email=demo_email, role="user")
            user.set_password("DemoPass123!")
            user.save()
            click.echo(f"Created demo user: {demo_email} (password: DemoPass123!)")
        else:
            click.echo(f"Demo user {demo_email} already exists.")

        # 2. Seed admin user for RBAC /api/v1/admin/* endpoints
        admin_email = "admin@example.com"
        admin = db.session.scalar(select(User).where(User.email == admin_email))
        if admin is None:
            admin = User(username="adminuser", email=admin_email, role="admin")
            admin.set_password("AdminPass123!")
            admin.save()
            click.echo(f"Created admin user: {admin_email} (password: AdminPass123!)")
        else:
            click.echo(f"Admin user {admin_email} already exists.")

        # 3. Seed sample items
        existing_items = db.session.scalars(
            select(Item).where(Item.owner_id == user.id)
        ).all()
        if not existing_items:
            sample_items = [
                Item(
                    title="Set up FlaskFul REST API boilerplate",
                    description="Configure Flask-Smorest, SQLAlchemy 2.0, Caching, and JWT auth.",
                    status="active",
                    owner_id=user.id,
                ),
                Item(
                    title="Connect frontend client application",
                    description="Point React/Vue/Next.js API client to http://localhost:5000/api/v1.",
                    status="draft",
                    owner_id=user.id,
                ),
            ]
            db.session.add_all(sample_items)
            db.session.commit()
            click.echo(f"Seeded {len(sample_items)} sample items.")
        else:
            click.echo("Sample items already exist.")
