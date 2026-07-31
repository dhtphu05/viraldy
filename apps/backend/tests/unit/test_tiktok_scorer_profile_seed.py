from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from viraldy.modules.tiktok_scorer.profiles import profile_seed_payloads

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _seed_migration() -> ModuleType:
    migration_path = BACKEND_DIR / "alembic" / "versions" / "0016_seed_tiktok_score_profiles.py"
    spec = importlib.util.spec_from_file_location("seed_tiktok_profiles", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_seeded_profile_configuration_matches_runtime_profiles() -> None:
    migration = _seed_migration()

    for payload in profile_seed_payloads():
        code = payload["code"]
        assert migration._weights(code) == payload["weights_json"]
        assert migration._thresholds(code) == payload["thresholds_json"]
        assert migration._configuration(code) == payload["configuration_json"]
