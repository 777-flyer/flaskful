"""Tests for the Django/NestJS-style resource scaffolding CLI engine."""

from pathlib import Path

from app.core.scaffold import parse_resource_name, scaffold_resource


def test_parse_resource_name_variants():
    """Resource name parser should handle CamelCase, snake_case, and pluralization."""
    project = parse_resource_name("Project")
    assert project.singular_snake == "project"
    assert project.plural_snake == "projects"
    assert project.pascal_case == "Project"
    assert project.url_slug == "projects"

    category = parse_resource_name("BlogCategory")
    assert category.singular_snake == "blog_category"
    assert category.plural_snake == "blog_categories"
    assert category.pascal_case == "BlogCategory"
    assert category.plural_pascal == "BlogCategories"
    assert category.url_slug == "blog-categories"


def test_scaffold_resource_creates_all_layers_and_registers_inits(tmp_path: Path):
    """scaffold_resource should create model, schema, service, blueprint, and test files."""
    # Seed minimal __init__.py files in tmp_path
    models_init = tmp_path / "app" / "models" / "__init__.py"
    models_init.parent.mkdir(parents=True, exist_ok=True)
    models_init.write_text(
        'from app.models.user import User\n\n__all__ = [\n    "User",\n]\n',
        encoding="utf-8",
    )

    api_v1_init = tmp_path / "app" / "api" / "v1" / "__init__.py"
    api_v1_init.parent.mkdir(parents=True, exist_ok=True)
    api_v1_init.write_text(
        'from app.api.v1.health import blp as health_blp\n\nV1_BLUEPRINTS = (\n    health_blp,\n)\n',
        encoding="utf-8",
    )

    created = scaffold_resource("project", base_dir=tmp_path, include_tests=True)
    assert len(created) == 5

    assert (tmp_path / "app" / "models" / "project.py").exists()
    assert (tmp_path / "app" / "schemas" / "project.py").exists()
    assert (tmp_path / "app" / "services" / "project_service.py").exists()
    assert (tmp_path / "app" / "api" / "v1" / "projects.py").exists()
    assert (tmp_path / "tests" / "test_projects.py").exists()

    # Verify auto-registration in __init__.py files
    assert "from app.models.project import Project" in models_init.read_text(
        encoding="utf-8"
    )
    assert "projects_blp" in api_v1_init.read_text(encoding="utf-8")

    # Running a second time without force=True should skip existing files safely
    skipped = scaffold_resource("project", base_dir=tmp_path, include_tests=True)
    assert len(skipped) == 0
