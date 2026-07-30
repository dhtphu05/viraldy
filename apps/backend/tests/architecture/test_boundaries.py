from __future__ import annotations

import ast
from pathlib import Path

SRC = Path("src/viraldy")
LEGACY_LAYER_DIRS = {"application", "domain", "infrastructure", "presentation"}


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


def test_campaign_pack_compiler_does_not_depend_on_preflight_internals() -> None:
    offenders: list[str] = []
    for path in (SRC / "modules" / "campaign_packs").glob("*.py"):
        for imported in imports_for(path):
            if imported.startswith("viraldy.modules.preflight."):
                offenders.append(f"{path}: {imported}")
    assert offenders == []


def test_campaign_pack_requirement_compiler_is_publicly_exposed() -> None:
    public_imports = set(imports_for(SRC / "modules" / "campaign_packs" / "public.py"))

    assert "viraldy.modules.campaign_packs.requirements" in public_imports
