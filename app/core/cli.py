"""Custom Flask CLI commands for database initialization, seeding, and Django-style resource scaffolding."""

import click
from flask import Flask
from sqlalchemy import select

from app.core.scaffold import (
    BASE_DIR,
     _register_in_api_v1_init,
    _register_in_models_init,
    parse_resource_name,
    render_blueprint_template,
    render_model_template,
    render_schema_template,
    render_service_template,
    scaffold_resource,
    write_scaffold_file,
)
from app.extensions import db
from app.models.item import Item
from app.models.user import User


def register_cli_commands(app: Flask) -> None:
    """Register custom management and scaffolding commands with the Flask CLI."""

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

    @app.cli.command("make-resource")
    @click.argument("name")
    @click.option("--no-tests", is_flag=True, help="Skip generating pytest file.")
    @click.option("--force", is_flag=True, help="Overwrite existing files.")
    def make_resource_command(name: str, no_tests: bool, force: bool) -> None:
        """Generate a complete resource (Model, Schema, Service, Blueprint, and Tests) like Django startapp."""
        try:
            names = parse_resource_name(name)
            created = scaffold_resource(
                name,
                base_dir=BASE_DIR,
                include_tests=not no_tests,
                force=force,
            )
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc

        if not created:
            click.echo(
                f"Resource '{names.singular_snake}' files already exist. Use --force to overwrite."
            )
            return

        click.echo(f"Scaffolded '{names.pascal_case}' resource (/api/v1/{names.url_slug}):")
        for path in created:
            click.echo(f"  + {path.relative_to(BASE_DIR)}")
        click.echo("Run `flask init-db` (or `flask db migrate -m 'Add table'`) to create the table.")

    @app.cli.command("make-model")
    @click.argument("name")
    @click.option("--force", is_flag=True, help="Overwrite existing file.")
    def make_model_command(name: str, force: bool) -> None:
        """Generate a standalone SQLAlchemy 2.0 model in app/models/."""
        names = parse_resource_name(name)
        target = BASE_DIR / "app" / "models" / f"{names.singular_snake}.py"
        if write_scaffold_file(target, render_model_template(names), force=force):
            _register_in_models_init(BASE_DIR, names)
            click.echo(f"Created model: {target.relative_to(BASE_DIR)}")
        else:
            click.echo(f"Model {target.relative_to(BASE_DIR)} already exists.")

    @app.cli.command("make-schema")
    @click.argument("name")
    @click.option("--force", is_flag=True, help="Overwrite existing file.")
    def make_schema_command(name: str, force: bool) -> None:
        """Generate Marshmallow CRUD schemas in app/schemas/."""
        names = parse_resource_name(name)
        target = BASE_DIR / "app" / "schemas" / f"{names.singular_snake}.py"
        if write_scaffold_file(target, render_schema_template(names), force=force):
            click.echo(f"Created schema: {target.relative_to(BASE_DIR)}")
        else:
            click.echo(f"Schema {target.relative_to(BASE_DIR)} already exists.")

    @app.cli.command("make-service")
    @click.argument("name")
    @click.option("--force", is_flag=True, help="Overwrite existing file.")
    def make_service_command(name: str, force: bool) -> None:
        """Generate a business logic service class in app/services/."""
        names = parse_resource_name(name)
        target = BASE_DIR / "app" / "services" / f"{names.singular_snake}_service.py"
        if write_scaffold_file(target, render_service_template(names), force=force):
            click.echo(f"Created service: {target.relative_to(BASE_DIR)}")
        else:
            click.echo(f"Service {target.relative_to(BASE_DIR)} already exists.")

    @app.cli.command("make-blueprint")
    @click.argument("name")
    @click.option("--force", is_flag=True, help="Overwrite existing file.")
    def make_blueprint_command(name: str, force: bool) -> None:
        """Generate a versioned REST API blueprint in app/api/v1/."""
        names = parse_resource_name(name)
        target = BASE_DIR / "app" / "api" / "v1" / f"{names.plural_snake}.py"
        if write_scaffold_file(target, render_blueprint_template(names), force=force):
            _register_in_api_v1_init(BASE_DIR, names)
            click.echo(f"Created blueprint: {target.relative_to(BASE_DIR)}")
        else:
            click.echo(f"Blueprint {target.relative_to(BASE_DIR)} already exists.")
