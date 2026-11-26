"""Read configuration and source profiles only; never call a provider or service."""

from __future__ import annotations

import argparse
import ast
import json
import os
import shutil
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Never

ROOT = Path(__file__).resolve().parents[1]
STAGES = ("ANALYSIS", "IMAGE", "VIDEO", "INSPECTION")
PRESENCE = (
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "KIE_API_KEY",
    "S3_BUCKET",
    "S3_REGION",
    "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY",
    "REDIS_URL",
    "CELERY_BROKER_URL",
    "CELERY_RESULT_BACKEND",
)


def positive_usd(raw: str | None) -> bool:
    try:
        amount = Decimal(raw or "0")
        return (
            amount.is_finite()
            and 0 < amount < Decimal("10000000000")
            and amount == amount.quantize(Decimal("0.00000001"))
        )
    except (InvalidOperation, ValueError):
        return False


def _constant(tree: ast.Module, name: str) -> Any:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    return None


def _image_defaults(tree: ast.Module) -> dict[str, Any]:
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "edit":
            return {
                arg.arg: ast.literal_eval(value)
                for arg, value in zip(node.args.kwonlyargs, node.args.kw_defaults, strict=True)
                if isinstance(value, ast.Constant)
            }
    return {}


def source_profiles(root: Path) -> list[tuple[str, bool]]:
    engine = root / "apps/backend/src/viraldy/modules/smart_remake/engine"
    try:
        images = ast.parse((engine / "openai_images.py").read_text())
        video = ast.parse((engine / "kie_adapter.py").read_text())
        defaults = _image_defaults(images)
        variants = [
            ast.literal_eval(value)
            for node in ast.walk(video)
            if isinstance(node, ast.Dict)
            for key, value in zip(node.keys, node.values, strict=True)
            if isinstance(key, ast.Constant)
            and key.value == "model"
            and isinstance(value, ast.Constant)
        ]
        return [
            (
                "CODEBASE_OPENAI_IMAGE_PROFILE",
                _constant(images, "IMAGE_MODEL") == "gpt-image-2.6-sunburst"
                and _constant(images, "IMAGE_SIZE") == "720x1280"
                and defaults.get("quality") == "max"
                and defaults.get("complexity") == "high",
            ),
            (
                "CODEBASE_KIE_VIDEO_PROFILE",
                _constant(video, "KIE_MODEL") == "veo-3-1"
                and bool(variants)
                and set(variants) == {"veo3_lite"},
            ),
        ]
    except (OSError, SyntaxError, ValueError, TypeError):
        return [("CODEBASE_MODEL_PROFILES", False)]


def check_configuration(
    environ: Mapping[str, str],
    *,
    pilot_case: Path | None = None,
    cap_usd: str | None = None,
    operator_authorized: bool = False,
    repo_root: Path = ROOT,
) -> dict[str, Any]:
    checks: list[dict[str, str]] = []

    def check(name: str, passed: bool, code: str = "CONFIGURED_NOT_VERIFIED") -> None:
        checks.append(
            {
                "name": name,
                "status": "passed" if passed else "blocked",
                "code": code if passed else "MISSING_OR_INVALID",
            }
        )

    check("AI_MODE", environ.get("AI_MODE", "").strip() == "live", "LIVE_MODE_CONFIGURED")
    check(
        "SMART_REMAKE_ENABLED",
        environ.get("SMART_REMAKE_ENABLED", "").strip() == "true",
    )
    for name in PRESENCE:
        check(name, bool(environ.get(name, "").strip()))
    for name, scheme in (
        ("DATABASE_URL", "postgresql+asyncpg://"),
        ("DATABASE_SYNC_URL", "postgresql+psycopg://"),
    ):
        check(name, environ.get(name, "").strip().startswith(scheme))
    for stage in STAGES:
        name = f"SMART_REMAKE_P0_MAX_{stage}_USD"
        check(name, positive_usd(environ.get(name)), "EXPLICIT_BOUND_CONFIGURED")
    check(
        "SMART_REMAKE_GEMINI_MODEL",
        environ.get("SMART_REMAKE_GEMINI_MODEL", "").strip() in {"", "gemini-2.5-flash"},
        "EXPECTED_PROFILE_CONFIGURED",
    )
    check(
        "SMART_REMAKE_OPENAI_IMAGE_QUALITY",
        environ.get("SMART_REMAKE_OPENAI_IMAGE_QUALITY", "max").strip().lower() == "max",
        "EXPECTED_PROFILE_CONFIGURED",
    )
    for name, valid in source_profiles(repo_root):
        check(name, valid, "EXPECTED_SOURCE_PROFILE")
    for binary in ("ffmpeg", "ffprobe"):
        configured = (
            environ.get(f"SMART_REMAKE_{binary.upper()}_PATH", "").strip()
            or environ.get(f"{binary.upper()}_PATH", "").strip()
            or shutil.which(binary)
        )
        check(binary.upper(), bool(configured), "CONFIGURED_OR_DISCOVERED_NOT_EXECUTED")
    checks.append(
        {
            "name": "S3_ENDPOINT_URL",
            "status": "passed",
            "code": "CONFIGURED_NOT_VERIFIED"
            if environ.get("S3_ENDPOINT_URL", "").strip()
            else "DEFAULT_ENDPOINT_NOT_VERIFIED",
        }
    )
    if pilot_case is None:
        checks.append({"name": "PILOT_CASE_FILE", "status": "pending", "code": "NOT_SUPPLIED"})
    else:
        try:
            valid_case = pilot_case.is_file() and pilot_case.stat().st_size <= 10 * 1024 * 1024
            if not valid_case or not isinstance(json.loads(pilot_case.read_text()), dict):
                raise ValueError
            checks.append(
                {
                    "name": "PILOT_CASE_FILE",
                    "status": "passed",
                    "code": "CASE_JSON_READABLE_NOT_RIGHTS_VERIFIED",
                }
            )
        except (OSError, ValueError, UnicodeError):
            checks.append(
                {
                    "name": "PILOT_CASE_FILE",
                    "status": "blocked",
                    "code": "CASE_JSON_UNAVAILABLE",
                }
            )
    if cap_usd is None:
        checks.append({"name": "PILOT_BUDGET_CAP", "status": "pending", "code": "NOT_SUPPLIED"})
    else:
        check(
            "PILOT_BUDGET_CAP",
            positive_usd(cap_usd),
            "CAP_DECLARED_NOT_AUTHORIZATION_VERIFIED",
        )
    checks.append(
        {
            "name": "OPERATOR_AUTHORIZATION",
            "status": "pending",
            "code": "OPERATOR_ASSERTION_RECORDED" if operator_authorized else "NOT_SUPPLIED",
        }
    )
    checks.append({"name": "RUNTIME_VERIFICATION", "status": "pending", "code": "NOT_PERFORMED"})
    blocked = any(item["status"] == "blocked" for item in checks)
    return {
        "schemaVersion": "smart_remake_p0_readiness_v1",
        "status": "configuration_blocked" if blocked else "configuration_ready",
        "paidExecution": "blocked" if blocked else "requires_explicit_authorization",
        "runtimeVerification": "not_performed",
        "pilotAuthorization": "not_verified",
        "checks": checks,
    }


class SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ValueError("ARGUMENT_INVALID")


def main(argv: Sequence[str] | None = None) -> int:
    parser = SafeParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pilot-case", type=Path)
    parser.add_argument("--cap-usd")
    parser.add_argument(
        "--authorized",
        action="store_true",
        help="Record an operator assertion; this does not verify user authorization.",
    )
    try:
        args = parser.parse_args(argv)
    except ValueError:
        print(json.dumps({"status": "configuration_blocked", "code": "ARGUMENT_INVALID"}))
        return 2
    result = check_configuration(
        os.environ,
        pilot_case=args.pilot_case,
        cap_usd=args.cap_usd,
        operator_authorized=args.authorized,
    )
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(result["status"])
        for item in result["checks"]:
            print(f"{item['status']} {item['name']} {item['code']}")
    return 1 if result["status"] == "configuration_blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
