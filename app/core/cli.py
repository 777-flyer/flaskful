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
        """Seed the database with a demo user and sample items."""
        db.create_all()

        demo_email = "demo@example.com"
        user = db.session.scalar(select(User).where(User.email == demo_email))
        if user is None:
            user = User(username="demouser", email=demo_email)
            user.set_password("DemoPass123!")
            user.save()
            click.echo(f"Created demo user: {demo_email} (password: DemoPass123!)")
        else:
            click.echo(f"Demo user {demo_email} already exists.")

        existing_items = db.session.scalars(
            select(Item).where(Item.owner_id == user.id)
        ).all()
        if not existing_items:
            sample_items = [
                Item(
                    title="Set up Flask REST API boilerplate",
                    description="Configure Flask-Smorest, SQLAlchemy 2.0, and JWT auth.",
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

