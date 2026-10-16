"""Django/NestJS-style resource scaffolding engine for FlaskFul CLI."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class ResourceNames:
    """Normalized naming variants for a scaffolded resource."""

    singular_snake: str  # e.g., "blog_post"
    plural_snake: str  # e.g., "blog_posts"
    pascal_case: str  # e.g., "BlogPost"
    plural_pascal: str  # e.g., "BlogPosts"
    url_slug: str  # e.g., "blog-posts"
    human_singular: str  # e.g., "blog post"


def parse_resource_name(raw_name: str) -> ResourceNames:
    """Convert any resource name (e.g., 'Project', 'blog-post', 'category') into naming variants."""
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", raw_name.strip())
    # Convert CamelCase to snake_case
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", cleaned)
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower().strip("_")
    snake = re.sub(r"_+", "_", snake)

    if not snake or not re.match(r"^[a-z][a-z0-9_]*$", snake):
        raise ValueError(
            f"Invalid resource name {raw_name!r}. Use letters, digits, or underscores (e.g., 'project' or 'blog_post')."
        )

    # Naive pluralization rules covering common English nouns
    if snake.endswith("y") and len(snake) > 1 and snake[-2] not in "aeiou":
        plural_snake = f"{snake[:-1]}ies"
    elif snake.endswith(("s", "x", "z", "ch", "sh")):
        plural_snake = f"{snake}es"
    else:
        plural_snake = f"{snake}s"

    pascal = "".join(part.capitalize() for part in snake.split("_"))
    plural_pascal = "".join(part.capitalize() for part in plural_snake.split("_"))
    url_slug = plural_snake.replace("_", "-")
    human_singular = snake.replace("_", " ")

    return ResourceNames(
        singular_snake=snake,
        plural_snake=plural_snake,
        pascal_case=pascal,
        plural_pascal=plural_pascal,
        url_slug=url_slug,
        human_singular=human_singular,
    )


def render_model_template(names: ResourceNames) -> str:
    """Render SQLAlchemy 2.0 model file content."""
    return f'''"""{names.pascal_case} database model with public UUID, soft deletion, and user ownership."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.base import CRUDMixin, SoftDeleteMixin, TimestampMixin, UUIDMixin


class {names.pascal_case}(CRUDMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin, db.Model):
    """{names.pascal_case} resource model."""

    __tablename__ = "{names.plural_snake}"

    name: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default="active", index=True, nullable=False
    )
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<{names.pascal_case} id={{self.id}} uuid={{self.uuid!r}} name={{self.name!r}}>"
'''


def render_schema_template(names: ResourceNames) -> str:
    """Render Marshmallow validation & serialization schema file content."""
    upper_prefix = names.singular_snake.upper()
    return f'''"""Marshmallow schemas for {names.pascal_case} CRUD operations, sorting, and filtering."""

from marshmallow import fields, validate

from app.schemas.common import BaseSchema, PaginationMetaSchema, PaginationQuerySchema

{upper_prefix}_STATUSES = ("draft", "active", "archived")
{upper_prefix}_SORT_FIELDS = ("created_at", "updated_at", "name", "status")
SORT_ORDERS = ("asc", "desc")


class {names.pascal_case}Schema(BaseSchema):
    """Serialized {names.pascal_case} response schema."""

    id = fields.Integer(dump_only=True)
    uuid = fields.String(dump_only=True)
    name = fields.String(required=True)
    description = fields.String(allow_none=True)
    status = fields.String(required=True)
    owner_id = fields.Integer(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    deleted_at = fields.DateTime(dump_only=True, allow_none=True)


class {names.pascal_case}CreateSchema(BaseSchema):
    """Payload schema for creating a new {names.pascal_case}."""

    name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=150),
        metadata={{"example": "Sample {names.pascal_case}"}},
    )
    description = fields.String(
        load_default=None,
        allow_none=True,
        validate=validate.Length(max=2000),
        metadata={{"example": "Description for {names.human_singular}."}},
    )
    status = fields.String(
        load_default="active",
        validate=validate.OneOf({upper_prefix}_STATUSES),
        metadata={{"example": "active"}},
    )


class {names.pascal_case}UpdateSchema(BaseSchema):
    """Payload schema for updating an existing {names.pascal_case}."""

    name = fields.String(
        validate=validate.Length(min=1, max=150),
        metadata={{"example": "Updated {names.pascal_case}"}},
    )
    description = fields.String(
        allow_none=True,
        validate=validate.Length(max=2000),
    )
    status = fields.String(
        validate=validate.OneOf({upper_prefix}_STATUSES),
    )


class {names.pascal_case}QuerySchema(PaginationQuerySchema):
    """Query parameters for filtering, sorting, and paginating {names.plural_pascal}."""

    status = fields.String(validate=validate.OneOf({upper_prefix}_STATUSES))
    search = fields.String(validate=validate.Length(min=1, max=100))
    sort_by = fields.String(
        load_default="created_at",
        validate=validate.OneOf({upper_prefix}_SORT_FIELDS),
    )
    sort_order = fields.String(
        load_default="desc",
        validate=validate.OneOf(SORT_ORDERS),
    )
    include_deleted = fields.Boolean(load_default=False)


class Paginated{names.pascal_case}ResponseSchema(BaseSchema):
    """Paginated response wrapper for {names.plural_pascal}."""

    items = fields.List(fields.Nested({names.pascal_case}Schema), required=True)
    meta = fields.Nested(PaginationMetaSchema, required=True)
'''


def render_service_template(names: ResourceNames) -> str:
    """Render Service layer file content with caching, BOLA, soft-delete, and AuditLog."""
    s = names.singular_snake
    p = names.plural_snake
    cls = names.pascal_case
    upper = s.upper()
    return f'''"""{cls} CRUD, caching, soft-delete, dynamic sorting, and query service layer."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.core.exceptions import ForbiddenError, NotFoundError
from app.extensions import cache, db
from app.models.{s} import {cls}
from app.models.audit_log import AuditLog

SORTABLE_COLUMNS = {{
    "created_at": {cls}.created_at,
    "updated_at": {cls}.updated_at,
    "name": {cls}.name,
    "status": {cls}.status,
}}


def _escape_like_wildcards(term: str) -> str:
    """Escape SQL LIKE/ILIKE wildcard characters (%, _, \\\\) in user search input."""
    return term.replace("\\\\", "\\\\\\\\").replace("%", "\\\\%").replace("_", "\\\\_")


class {cls}Service:
    """Encapsulates business logic, caching, soft-delete, and queries for {cls}."""

    @staticmethod
    def _get_cache_version(owner_id: int) -> int:
        ver = cache.get(f"user_{p}_ver:{{owner_id}}")
        if ver is None:
            cache.set(f"user_{p}_ver:{{owner_id}}", 1, timeout=3600)
            return 1
        return int(ver)

    @staticmethod
    def invalidate_user_cache(owner_id: int) -> None:
        ver = {cls}Service._get_cache_version(owner_id)
        cache.set(f"user_{p}_ver:{{owner_id}}", ver + 1, timeout=3600)

    @staticmethod
    def list_{p}(
        *,
        owner_id: int,
        page: int = 1,
        per_page: int = 20,
        status: str | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        include_deleted: bool = False,
    ) -> dict[str, Any]:
        """Return a paginated, dynamically sorted, and cached list of {p}."""
        ver = {cls}Service._get_cache_version(owner_id)
        cache_key = (
            f"{p}:{{owner_id}}:v{{ver}}:p{{page}}:pp{{per_page}}:"
            f"st{{status}}:q{{search}}:sb{{sort_by}}:so{{sort_order}}:del{{include_deleted}}"
        )
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        stmt = select({cls}).where({cls}.owner_id == owner_id)

        if not include_deleted:
            stmt = stmt.where({cls}.deleted_at.is_(None))
        if status:
            stmt = stmt.where({cls}.status == status)
        if search:
            escaped = _escape_like_wildcards(search.strip())
            stmt = stmt.where({cls}.name.ilike(f"%{{escaped}}%", escape="\\\\"))

        sort_col = SORTABLE_COLUMNS.get(sort_by, {cls}.created_at)
        if sort_order.lower() == "asc":
            stmt = stmt.order_by(sort_col.asc(), {cls}.id.asc())
        else:
            stmt = stmt.order_by(sort_col.desc(), {cls}.id.desc())

        pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
        result = {{
            "items": pagination.items,
            "meta": {{
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total_items": pagination.total,
                "total_pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            }},
        }}
        cache.set(cache_key, result)
        return result

    @staticmethod
    def get_{s}_for_owner(
        record_id: int, owner_id: int, *, include_deleted: bool = False
    ) -> {cls}:
        """Fetch a {cls} by ID and enforce strict object-level ownership (BOLA)."""
        record = db.session.get({cls}, record_id)
        if record is None or (record.is_deleted and not include_deleted):
            raise NotFoundError(f"{cls} with id {{record_id}} was not found.")
        if record.owner_id != owner_id:
            raise ForbiddenError("You do not have permission to access this {names.human_singular}.")
        return record

    @staticmethod
    def create_{s}(data: dict[str, Any], owner_id: int) -> {cls}:
        """Create a new {cls}, invalidate cache, and record an audit log."""
        record = {cls}(
            name=data["name"].strip(),
            description=data.get("description"),
            status=data.get("status", "active"),
            owner_id=owner_id,
        )
        record.save()
        {cls}Service.invalidate_user_cache(owner_id)
        AuditLog.record(
            "{upper}_CREATE",
            user_id=owner_id,
            resource_type="{s}",
            resource_id=record.id,
        )
        return record

    @staticmethod
    def update_{s}(record_id: int, data: dict[str, Any], owner_id: int) -> {cls}:
        """Update an existing {cls}, invalidate cache, and record an audit log."""
        record = {cls}Service.get_{s}_for_owner(record_id, owner_id)
        if "name" in data:
            record.name = data["name"].strip()
        if "description" in data:
            record.description = data["description"]
        if "status" in data:
            record.status = data["status"]

        record.save()
        {cls}Service.invalidate_user_cache(owner_id)
        AuditLog.record(
            "{upper}_UPDATE",
            user_id=owner_id,
            resource_type="{s}",
            resource_id=record.id,
        )
        return record

    @staticmethod
    def delete_{s}(record_id: int, owner_id: int) -> None:
        """Soft-delete a {cls}, invalidate cache, and record an audit log."""
        record = {cls}Service.get_{s}_for_owner(record_id, owner_id)
        record.soft_delete()
        {cls}Service.invalidate_user_cache(owner_id)
        AuditLog.record(
            "{upper}_SOFT_DELETE",
            user_id=owner_id,
            resource_type="{s}",
            resource_id=record.id,
        )

    @staticmethod
    def restore_{s}(record_id: int, owner_id: int) -> {cls}:
        """Restore a soft-deleted {cls} and invalidate cache."""
        record = {cls}Service.get_{s}_for_owner(record_id, owner_id, include_deleted=True)
        record.restore()
        {cls}Service.invalidate_user_cache(owner_id)
        AuditLog.record(
            "{upper}_RESTORE",
            user_id=owner_id,
            resource_type="{s}",
            resource_id=record.id,
        )
        return record
'''


def render_blueprint_template(names: ResourceNames) -> str:
    """Render Flask-Smorest Blueprint file content."""
    s = names.singular_snake
    p = names.plural_snake
    cls = names.pascal_case
    return f'''"""REST API endpoints for {cls} resources."""

from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint

from app.schemas.{s} import (
    {cls}CreateSchema,
    {cls}QuerySchema,
    {cls}Schema,
    {cls}UpdateSchema,
    Paginated{cls}ResponseSchema,
)
from app.schemas.common import MessageSchema
from app.services.{s}_service import {cls}Service

blp = Blueprint(
    "{names.plural_pascal}",
    __name__,
    url_prefix="/api/v1/{names.url_slug}",
    description="CRUD, dynamic sorting, caching, and soft-delete operations for {cls} resources.",
)


@blp.route("")
class {cls}ListResource(MethodView):
    """Collection endpoint for listing and creating {names.plural_pascal}."""

    @jwt_required()
    @blp.doc(security=[{{"BearerAuth": []}}])
    @blp.arguments({cls}QuerySchema, location="query")
    @blp.response(200, Paginated{cls}ResponseSchema)
    def get(self, query_args: dict):
        """List paginated {p} belonging to the authenticated user."""
        owner_id = int(get_jwt_identity())
        return {cls}Service.list_{p}(
            owner_id=owner_id,
            page=query_args["page"],
            per_page=query_args["per_page"],
            status=query_args.get("status"),
            search=query_args.get("search"),
            sort_by=query_args.get("sort_by", "created_at"),
            sort_order=query_args.get("sort_order", "desc"),
            include_deleted=query_args.get("include_deleted", False),
        )

    @jwt_required()
    @blp.doc(security=[{{"BearerAuth": []}}])
    @blp.arguments({cls}CreateSchema)
    @blp.response(201, {cls}Schema)
    def post(self, payload: dict):
        """Create a new {names.human_singular}."""
        owner_id = int(get_jwt_identity())
        return {cls}Service.create_{s}(payload, owner_id=owner_id)


@blp.route("/<int:record_id>")
class {cls}DetailResource(MethodView):
    """Single resource endpoint for retrieving, updating, and soft-deleting a {cls}."""

    @jwt_required()
    @blp.doc(security=[{{"BearerAuth": []}}])
    @blp.response(200, {cls}Schema)
    def get(self, record_id: int):
        """Retrieve a specific {names.human_singular} by ID."""
        owner_id = int(get_jwt_identity())
        return {cls}Service.get_{s}_for_owner(record_id, owner_id=owner_id)

    @jwt_required()
    @blp.doc(security=[{{"BearerAuth": []}}])
    @blp.arguments({cls}UpdateSchema)
    @blp.response(200, {cls}Schema)
    def patch(self, update_data: dict, record_id: int):
        """Partially update an existing {names.human_singular} by ID."""
        owner_id = int(get_jwt_identity())
        return {cls}Service.update_{s}(record_id, update_data, owner_id=owner_id)

    @jwt_required()
    @blp.doc(security=[{{"BearerAuth": []}}])
    @blp.response(200, MessageSchema)
    def delete(self, record_id: int):
        """Soft-delete a {names.human_singular} by ID."""
        owner_id = int(get_jwt_identity())
        {cls}Service.delete_{s}(record_id, owner_id=owner_id)
        return {{"status": "success", "message": f"{cls} {{record_id}} deleted successfully."}}


@blp.route("/<int:record_id>/restore")
class {cls}RestoreResource(MethodView):
    """Endpoint to restore a previously soft-deleted {cls}."""

    @jwt_required()
    @blp.doc(security=[{{"BearerAuth": []}}])
    @blp.response(200, {cls}Schema)
    def post(self, record_id: int):
        """Restore a soft-deleted {names.human_singular} by ID."""
        owner_id = int(get_jwt_identity())
        return {cls}Service.restore_{s}(record_id, owner_id=owner_id)
'''


def render_test_template(names: ResourceNames) -> str:
    """Render Pytest CRUD & soft-delete test file for the new resource."""
    p = names.plural_snake
    slug = names.url_slug
    cls = names.pascal_case
    return f'''"""Automated CRUD, UUID, and soft-delete tests for {cls} endpoints."""


def test_{p}_crud_and_restore_lifecycle(client, auth_headers):
    """Authenticated user can create, list, update, soft-delete, and restore {p}."""
    create_res = client.post(
        "/api/v1/{slug}",
        headers=auth_headers,
        json={{"name": "Initial {cls}", "description": "Generated test", "status": "active"}},
    )
    assert create_res.status_code == 201
    record = create_res.get_json()
    record_id = record["id"]
    assert len(record["uuid"]) == 36

    list_res = client.get("/api/v1/{slug}", headers=auth_headers)
    assert list_res.status_code == 200
    assert list_res.get_json()["meta"]["total_items"] == 1

    patch_res = client.patch(
        f"/api/v1/{slug}/{{record_id}}",
        headers=auth_headers,
        json={{"name": "Updated {cls}", "status": "archived"}},
    )
    assert patch_res.status_code == 200
    assert patch_res.get_json()["name"] == "Updated {cls}"

    del_res = client.delete(f"/api/v1/{slug}/{{record_id}}", headers=auth_headers)
    assert del_res.status_code == 200

    assert client.get(f"/api/v1/{slug}/{{record_id}}", headers=auth_headers).status_code == 404

    restore_res = client.post(
        f"/api/v1/{slug}/{{record_id}}/restore", headers=auth_headers
    )
    assert restore_res.status_code == 200
    assert restore_res.get_json()["deleted_at"] is None
'''


def _register_in_models_init(base_dir: Path, names: ResourceNames) -> None:
    """Auto-register the generated model in app/models/__init__.py."""
    init_file = base_dir / "app" / "models" / "__init__.py"
    if not init_file.exists():
        return
    content = init_file.read_text(encoding="utf-8")
    import_line = f"from app.models.{names.singular_snake} import {names.pascal_case}"
    if import_line in content:
        return

    lines = content.splitlines()
    import_idx = 0
    for idx, line in enumerate(lines):
        if line.startswith("from app.models."):
            import_idx = idx + 1
    lines.insert(import_idx, import_line)

    updated = "\n".join(lines) + "\n"
    all_match = re.search(r"__all__\s*=\s*\[(.*?)\]", updated, flags=re.DOTALL)
    if all_match:
        existing_items = re.findall(r'"([^"]+)"', all_match.group(1))
        if names.pascal_case not in existing_items:
            existing_items.append(names.pascal_case)
            existing_items.sort()
            formatted_items = ",\n".join(f'    "{item}"' for item in existing_items)
            new_all = f"__all__ = [\n{formatted_items},\n]"
            updated = updated[: all_match.start()] + new_all + updated[all_match.end() :]

    init_file.write_text(updated, encoding="utf-8")


def _register_in_api_v1_init(base_dir: Path, names: ResourceNames) -> None:
    """Auto-register the generated blueprint in app/api/v1/__init__.py."""
    init_file = base_dir / "app" / "api" / "v1" / "__init__.py"
    if not init_file.exists():
        return
    content = init_file.read_text(encoding="utf-8")
    blp_alias = f"{names.plural_snake}_blp"
    import_line = f"from app.api.v1.{names.plural_snake} import blp as {blp_alias}"
    if import_line in content:
        return

    lines = content.splitlines()
    import_idx = 0
    for idx, line in enumerate(lines):
        if line.startswith("from app.api.v1."):
            import_idx = idx + 1
    lines.insert(import_idx, import_line)

    updated = "\n".join(lines) + "\n"
    tuple_match = re.search(r"V1_BLUEPRINTS\s*=\s*\((.*?)\)", updated, flags=re.DOTALL)
    if tuple_match:
        inner = tuple_match.group(1).strip()
        entries = [e.strip() for e in inner.split(",") if e.strip()]
        if blp_alias not in entries:
            entries.append(blp_alias)
            formatted = ",\n".join(f"    {e}" for e in entries)
            new_tuple = f"V1_BLUEPRINTS = (\n{formatted},\n)"
            updated = (
                updated[: tuple_match.start()] + new_tuple + updated[tuple_match.end() :]
            )

    init_file.write_text(updated, encoding="utf-8")


def write_scaffold_file(target: Path, content: str, *, force: bool = False) -> bool:
    """Write a generated file safely, returning True if written or False if skipped."""
    if target.exists() and not force:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return True


def scaffold_resource(
    raw_name: str,
    *,
    base_dir: Path = BASE_DIR,
    include_tests: bool = True,
    force: bool = False,
) -> list[Path]:
    """Generate Model, Schema, Service, Blueprint, and Test files for a new resource."""
    names = parse_resource_name(raw_name)
    created_files: list[Path] = []

    model_path = base_dir / "app" / "models" / f"{names.singular_snake}.py"
    schema_path = base_dir / "app" / "schemas" / f"{names.singular_snake}.py"
    service_path = base_dir / "app" / "services" / f"{names.singular_snake}_service.py"
    blueprint_path = base_dir / "app" / "api" / "v1" / f"{names.plural_snake}.py"

    if write_scaffold_file(model_path, render_model_template(names), force=force):
        created_files.append(model_path)
        _register_in_models_init(base_dir, names)

    if write_scaffold_file(schema_path, render_schema_template(names), force=force):
        created_files.append(schema_path)

    if write_scaffold_file(service_path, render_service_template(names), force=force):
        created_files.append(service_path)

    if write_scaffold_file(
        blueprint_path, render_blueprint_template(names), force=force
    ):
        created_files.append(blueprint_path)
        _register_in_api_v1_init(base_dir, names)

    if include_tests:
        test_path = base_dir / "tests" / f"test_{names.plural_snake}.py"
        if write_scaffold_file(test_path, render_test_template(names), force=force):
            created_files.append(test_path)

    return created_files
