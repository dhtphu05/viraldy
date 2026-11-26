from __future__ import annotations

import json
import runpy
import socket
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "check-smart-remake-readiness.py"


@pytest.fixture
def readiness():
    return runpy.run_path(str(SCRIPT))


@pytest.fixture
def configured_env():
    values = {
        "AI_MODE": "live",
        "SMART_REMAKE_ENABLED": "true",
        "DATABASE_URL": "postgresql+asyncpg://redaction-marker@private/db",
        "DATABASE_SYNC_URL": "postgresql+psycopg://redaction-marker@private/db",
        "GEMINI_API_KEY": "redaction-marker-gemini",
        "OPENAI_API_KEY": "redaction-marker-openai",
        "KIE_API_KEY": "redaction-marker-kie",
        "S3_BUCKET": "redaction-marker-bucket",
        "S3_REGION": "redaction-marker-region",
        "S3_ACCESS_KEY_ID": "redaction-marker-id",
        "S3_SECRET_ACCESS_KEY": "redaction-marker-secret",
        "REDIS_URL": "redaction-marker-redis",
        "CELERY_BROKER_URL": "redaction-marker-broker",
        "CELERY_RESULT_BACKEND": "redaction-marker-result",
        "SMART_REMAKE_FFMPEG_PATH": "/private/redaction-marker-ffmpeg",
        "SMART_REMAKE_FFPROBE_PATH": "/private/redaction-marker-ffprobe",
    }
    for stage in ("ANALYSIS", "IMAGE", "VIDEO", "INSPECTION"):
        values[f"SMART_REMAKE_P0_MAX_{stage}_USD"] = "1.25"
    return values


def test_configuration_is_offline_redacted_and_not_runtime_or_rights_verification(
    readiness, configured_env, monkeypatch
):
    monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: pytest.fail("no network"))
    result = readiness["check_configuration"](configured_env)
    assert result["status"] == "configuration_ready"
    assert result["runtimeVerification"] == "not_performed"
    assert result["pilotAuthorization"] == "not_verified"
    assert "redaction-marker" not in json.dumps(result)


@pytest.mark.parametrize("value", ["", "0", "-1", "NaN", "Infinity", "bad", "0.000000001"])
def test_bound_missing_invalid_or_zero_is_paid_blocked(readiness, configured_env, value):
    configured_env["SMART_REMAKE_P0_MAX_VIDEO_USD"] = value
    result = readiness["check_configuration"](configured_env)
    assert result["status"] == "configuration_blocked"
    assert result["paidExecution"] == "blocked"
    assert any(
        c["name"] == "SMART_REMAKE_P0_MAX_VIDEO_USD" and c["status"] == "blocked"
        for c in result["checks"]
    )


def test_fixture_media_can_prepare_without_paid_configuration(readiness, configured_env, tmp_path):
    case = tmp_path / "private-case.json"
    case.write_text(json.dumps({"source": "self-authored", "rights": {"declared": True}}))
    configured_env["AI_MODE"] = "fixture"
    configured_env.pop("SMART_REMAKE_P0_MAX_IMAGE_USD")
    result = readiness["check_configuration"](configured_env, pilot_case=case)
    assert result["status"] == "configuration_blocked"
    assert result["pilotAuthorization"] == "not_verified"
    assert any(c["name"] == "PILOT_CASE_FILE" and c["status"] == "passed" for c in result["checks"])
    assert any(
        c["name"] == "PILOT_BUDGET_CAP" and c["status"] == "pending" for c in result["checks"]
    )


def test_claims_of_authorization_and_declared_case_do_not_verify_rights(
    readiness, configured_env, tmp_path
):
    case = tmp_path / "redaction-marker-case.json"
    case.write_text('{"rights": "redaction-marker-cleared"}')
    result = readiness["check_configuration"](
        configured_env, pilot_case=case, cap_usd="2.5", operator_authorized=True
    )
    assert result["pilotAuthorization"] == "not_verified"
    assert "redaction-marker" not in json.dumps(result)
    bad = readiness["check_configuration"](
        configured_env, pilot_case=tmp_path / "missing", cap_usd="NaN"
    )
    assert any(c["code"] == "CASE_JSON_UNAVAILABLE" for c in bad["checks"])
    assert any(c["name"] == "PILOT_BUDGET_CAP" and c["status"] == "blocked" for c in bad["checks"])


def test_changed_profiles_missing_provider_and_wrong_database_block(readiness, configured_env):
    configured_env.update(
        SMART_REMAKE_GEMINI_MODEL="different",
        SMART_REMAKE_OPENAI_IMAGE_QUALITY="low",
        DATABASE_URL="sqlite://fixture",
        OPENAI_API_KEY="",
    )
    result = readiness["check_configuration"](configured_env)
    blocked = {c["name"] for c in result["checks"] if c["status"] == "blocked"}
    assert {
        "SMART_REMAKE_GEMINI_MODEL",
        "SMART_REMAKE_OPENAI_IMAGE_QUALITY",
        "DATABASE_URL",
        "OPENAI_API_KEY",
    } <= blocked


def test_json_cli_has_only_redacted_names_and_codes(configured_env):
    result = subprocess.run(  # noqa: S603 - fixed local checker argv, no shell or network
        [sys.executable, str(SCRIPT), "--json"],
        env=configured_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["status"] == "configuration_ready"
    assert "redaction-marker" not in result.stdout + result.stderr


def test_cli_redacts_invalid_arguments_and_never_treats_operator_flag_as_permission(
    readiness, configured_env, monkeypatch, capsys
):
    monkeypatch.setattr(readiness["os"], "environ", configured_env)
    main = readiness["main"]
    assert main(["--json"]) == 0
    assert json.loads(capsys.readouterr().out)["pilotAuthorization"] == "not_verified"
    assert main([]) == 0
    assert "redaction-marker" not in capsys.readouterr().out
    assert main(["--unknown", "redaction-marker?Signature=private"]) == 2
    error = capsys.readouterr()
    assert json.loads(error.out)["code"] == "ARGUMENT_INVALID"
    assert "redaction-marker" not in error.out + error.err
    assert (
        main(
            [
                "--json",
                "--pilot-case",
                "/redaction-marker-missing",
                "--cap-usd",
                "NaN",
                "--authorized",
            ]
        )
        == 1
    )
    result = json.loads(capsys.readouterr().out)
    assert result["pilotAuthorization"] == "not_verified"


def test_missing_source_profiles_cannot_certify_configuration(readiness, configured_env, tmp_path):
    result = readiness["check_configuration"](configured_env, repo_root=tmp_path)
    assert result["status"] == "configuration_blocked"
    assert any(
        c["name"] == "CODEBASE_MODEL_PROFILES" and c["status"] == "blocked"
        for c in result["checks"]
    )
