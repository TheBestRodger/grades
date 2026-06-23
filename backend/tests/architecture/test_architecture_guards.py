from __future__ import annotations

import ast
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[2] / "app"
FEATURES_DIR = APP_DIR / "features"


def test_feature_business_modules_do_not_import_fastapi() -> None:
    offenders: list[str] = []
    allowed_names = {"router.py", "demo_router.py", "audit_router.py"}

    for path in FEATURES_DIR.rglob("*.py"):
        if path.name in allowed_names or path.name == "__init__.py":
            continue
        for node in _imports(path):
            if _module_name(node) == "fastapi" or _module_name(node).startswith("fastapi."):
                offenders.append(str(path.relative_to(APP_DIR)))

    assert offenders == []


def test_repositories_do_not_import_services() -> None:
    offenders: list[str] = []

    for path in FEATURES_DIR.rglob("repository.py"):
        for node in _imports(path):
            module = _module_name(node)
            if module.endswith(".service") or ".service." in module:
                offenders.append(str(path.relative_to(APP_DIR)))

    assert offenders == []


def test_rules_modules_do_not_import_db_or_session() -> None:
    offenders: list[str] = []

    for path in FEATURES_DIR.rglob("rules.py"):
        source = path.read_text(encoding="utf-8")
        for node in _imports(path):
            module = _module_name(node)
            imported_names = {alias.name for alias in getattr(node, "names", [])}
            if module.startswith("sqlalchemy") or "Session" in imported_names or "Session" in source:
                offenders.append(str(path.relative_to(APP_DIR)))

    assert offenders == []


def test_sqlalchemy_engine_factory_is_centralized_in_core_db() -> None:
    offenders: list[str] = []
    allowed = {Path("core/db.py")}

    for path in APP_DIR.rglob("*.py"):
        relative = path.relative_to(APP_DIR)
        if relative in allowed:
            continue
        source = path.read_text(encoding="utf-8")
        if "create_engine" in source or "sessionmaker" in source:
            offenders.append(str(relative))

    assert offenders == []


def test_features_do_not_import_private_names_from_other_features() -> None:
    offenders: list[str] = []

    for path in FEATURES_DIR.rglob("*.py"):
        own_feature = path.relative_to(FEATURES_DIR).parts[0]
        for node in _imports(path):
            if not isinstance(node, ast.ImportFrom):
                continue
            target_feature = _target_feature(path, node)
            if target_feature is None or target_feature == own_feature:
                continue
            private_names = [alias.name for alias in node.names if alias.name.startswith("_")]
            if private_names:
                offenders.append(
                    f"{path.relative_to(APP_DIR)} imports {', '.join(private_names)} from {target_feature}"
                )

    assert offenders == []


def _imports(path: Path) -> list[ast.Import | ast.ImportFrom]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node for node in ast.walk(tree) if isinstance(node, ast.Import | ast.ImportFrom)]


def _module_name(node: ast.Import | ast.ImportFrom) -> str:
    if isinstance(node, ast.Import):
        return node.names[0].name
    return node.module or ""


def _target_feature(path: Path, node: ast.ImportFrom) -> str | None:
    if node.level == 0:
        module = node.module or ""
        prefix = "app.features."
        return module.removeprefix(prefix).split(".", 1)[0] if module.startswith(prefix) else None

    current_parts = path.relative_to(FEATURES_DIR).parts[:-1]
    base_parts = current_parts[: max(len(current_parts) - node.level + 1, 0)]
    module_parts = tuple((node.module or "").split(".")) if node.module else ()
    target_parts = (*base_parts, *module_parts)
    return target_parts[0] if target_parts else None
