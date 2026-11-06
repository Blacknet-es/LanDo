import ast
from pathlib import Path

API_ROOT = Path(__file__).parents[2] / "src"
FORBIDDEN_DOMAIN_IMPORTS = {
    "fastapi",
    "langchain",
    "langgraph",
    "sqlalchemy",
    "sqlmodel",
    "src.infrastructure",
    "src.routers",
}
FORBIDDEN_APPLICATION_IMPORTS = FORBIDDEN_DOMAIN_IMPORTS


def _imported_modules(source: Path) -> list[tuple[int, str]]:
    tree = ast.parse(source.read_text(), filename=str(source))
    imports: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append((node.lineno, node.module))
    return imports


def test_domain_has_no_framework_or_infrastructure_imports() -> None:
    violations = []
    for source in (API_ROOT / "domain").rglob("*.py"):
        for line, module in _imported_modules(source):
            if any(
                module == forbidden or module.startswith(f"{forbidden}.")
                for forbidden in FORBIDDEN_DOMAIN_IMPORTS
            ):
                violations.append(f"{source.relative_to(API_ROOT)}:{line}: {module}")
    assert not violations, "\n".join(violations)


def test_application_depends_only_on_inner_layers() -> None:
    violations = []
    for source in (API_ROOT / "application").rglob("*.py"):
        for line, module in _imported_modules(source):
            if any(
                module == forbidden or module.startswith(f"{forbidden}.")
                for forbidden in FORBIDDEN_APPLICATION_IMPORTS
            ):
                violations.append(f"{source.relative_to(API_ROOT)}:{line}: {module}")
    assert not violations, "\n".join(violations)


def test_http_routers_do_not_construct_infrastructure_adapters() -> None:
    forbidden_imports = {"src.infrastructure", "sqlalchemy", "sqlmodel"}
    violations = []
    for source in (API_ROOT / "routers").rglob("*.py"):
        for line, module in _imported_modules(source):
            if any(
                module == forbidden or module.startswith(f"{forbidden}.")
                for forbidden in forbidden_imports
            ):
                violations.append(f"{source.relative_to(API_ROOT)}:{line}: {module}")
    assert not violations, "\n".join(violations)
