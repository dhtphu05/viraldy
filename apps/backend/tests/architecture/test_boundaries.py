from __future__ import annotations

import ast
from pathlib import Path

SRC = Path("src/viraldy")
LEGACY_LAYER_DIRS = {"application", "domain", "infrastructure", "presentation"}
ALLOWED_CROSS_MODULE_PUBLIC_IMPORTS = {"public"}


def imports_for(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def test_modules_do_not_use_legacy_deep_layer_dirs() -> None:
    offenders: list[str] = []
    for path in (SRC / "modules").glob("*/*"):
        if path.is_dir() and path.name in LEGACY_LAYER_DIRS:
            offenders.append(str(path))
    assert offenders == []


def test_modules_have_flat_feature_files_only() -> None:
    offenders: list[str] = []
    for path in (SRC / "modules").glob("*/*.py"):
        if path.name == "__init__.py":
            continue
        if path.parent == SRC / "modules":
            offenders.append(str(path))
    assert offenders == []


def test_cross_module_imports_go_through_public_contracts() -> None:
    offenders: list[str] = []
    for path in (SRC / "modules").glob("*/*.py"):
        module_name = path.relative_to(SRC / "modules").parts[0]
        for imported in imports_for(path):
            marker = "viraldy.modules."
            if not imported.startswith(marker):
                continue
            parts = imported.removeprefix(marker).split(".")
            if (
                len(parts) >= 2
                and parts[0] != module_name
                and parts[1] not in ALLOWED_CROSS_MODULE_PUBLIC_IMPORTS
            ):
                offenders.append(f"{path}: {imported}")
    assert offenders == []
