import ast
from pathlib import Path

import pytest

APP = Path(__file__).parents[2] / "app"

TECHNICAL = ("fastapi", "sqlalchemy", "pydantic", "starlette")
FORBIDDEN_IMPORTS = {
    "domain": (*TECHNICAL, "app.application", "app.adapters", "app.composition", "app.config"),
    "application": (*TECHNICAL, "app.adapters", "app.composition", "app.config"),
    "adapters/primary": ("sqlalchemy", "app.adapters.secondary"),
    "adapters/secondary": ("fastapi", "app.adapters.primary", "app.composition"),
}


def imported_modules(path: Path) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
            modules.update(f"{node.module}.{alias.name}" for alias in node.names)
    return modules


def is_under(module: str, package: str) -> bool:
    return module == package or module.startswith(f"{package}.")


@pytest.mark.parametrize("layer", FORBIDDEN_IMPORTS)
def test_layer_only_depends_on_what_it_is_allowed_to(layer):
    violations = [
        f"{path.relative_to(APP)} -> {module}"
        for path in (APP / layer).rglob("*.py")
        for module in imported_modules(path)
        if any(is_under(module, forbidden) for forbidden in FORBIDDEN_IMPORTS[layer])
    ]

    assert violations == []
