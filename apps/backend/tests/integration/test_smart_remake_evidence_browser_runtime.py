"""Cheap safety/media checks for the opt-in, isolated Smart Remake browser stack."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from tests.e2e.smart_remake_media import assert_export_pixels_and_audio, generate_media
from tests.e2e.smart_remake_providers import _record, local_address
from tests.e2e.smart_remake_runtime import child_environment
from viraldy.modules.smart_remake.engine.media_binaries import ffprobe_path


@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost"])
def test_browser_runtime_allows_only_loopback_infrastructure(host):
    assert local_address(host)


@pytest.mark.parametrize("host", ["api.openai.com", "8.8.8.8", "169.254.169.254"])
def test_browser_runtime_denies_provider_and_metadata_addresses(host):
    assert not local_address(host)


def test_browser_child_environment_does_not_inherit_provider_credentials(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-inherit")
    monkeypatch.setenv("KIE_API_KEY", "must-not-inherit")
    monkeypatch.setenv("DATABASE_URL", "seller-database-must-not-inherit")
    result = child_environment()
    assert "OPENAI_API_KEY" not in result
    assert "KIE_API_KEY" not in result
    assert "DATABASE_URL" not in result
    assert result["PATH"] == os.environ["PATH"]


def test_browser_network_guard_rejects_external_resolution_before_request():
    result = subprocess.run(  # noqa: S603 - fixed guard probe; no provider request body
        [
            sys.executable,
            "-c",
            """
import socket
from tests.e2e.smart_remake_providers import install_network_guard
install_network_guard()
try:
    socket.getaddrinfo('api.openai.com', 443)
except RuntimeError:
    print('external DNS blocked')
else:
    raise AssertionError('External provider resolution was permitted')
""",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.stdout.strip() == "external DNS blocked"


def test_browser_provider_log_rejects_reusing_one_paid_reservation(tmp_path, monkeypatch):
    path = tmp_path / "calls.jsonl"
    monkeypatch.setenv("P0_E2E_PROVIDER_LOG", str(path))
    _record("image", attemptId="attempt-1", requestHash="request-1")
    with pytest.raises(AssertionError, match="repeated provider submission"):
        _record("image", attemptId="attempt-1", requestHash="request-2")
    _record("image", attemptId="attempt-2", requestHash="request-2")
    assert len(path.read_text().splitlines()) == 2


def test_browser_fixture_media_is_self_owned_and_frame_accurate(tmp_path):
    result = generate_media(tmp_path)
    manifest = json.loads(result["manifest"].read_text())
    assert manifest["rights"]["basis"] == "owned"
    assert manifest["mode"] == "fixture"
    for role in ("source", "clip-0", "clip-1", "repair"):
        probe = subprocess.run(  # noqa: S603 - fixed argv and generated test media
            [
                ffprobe_path(),
                "-v",
                "error",
                "-count_frames",
                "-show_streams",
                "-of",
                "json",
                str(result[role]),
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
        streams = json.loads(probe.stdout)["streams"]
        video = next(item for item in streams if item["codec_type"] == "video")
        assert video["avg_frame_rate"] == "24/1"
        assert int(video["nb_read_frames"]) == (480 if role == "source" else 192)
        assert video["width"] * 16 == video["height"] * 9
        assert any(item["codec_type"] == "audio" for item in streams)
    assert result["clip-0"].read_bytes() != result["repair"].read_bytes()


def test_browser_export_oracle_rejects_unlabeled_bytes_and_checks_real_audio_trim(tmp_path):
    from viraldy.modules.smart_remake.export_media import export_labeled_media
    from viraldy.modules.smart_remake.timeline_media import _assemble

    paths = generate_media(tmp_path)
    raw = paths["clip-0"].read_bytes()
    assembled = _assemble(
        [raw, raw],
        [
            {"inFrame": 120, "outFrame": 168},
            {"inFrame": 24, "outFrame": 168},
        ],
    )
    preview = tmp_path / "preview.mp4"
    preview.write_bytes(assembled)
    with pytest.raises(AssertionError, match="AI label glyph pixels missing"):
        assert_export_pixels_and_audio(preview, 8)
    output, _ = export_labeled_media(assembled, expected_frames=192, audio_required=True)
    exported = tmp_path / "labeled.mp4"
    exported.write_bytes(output)
    assert_export_pixels_and_audio(exported, 8)
