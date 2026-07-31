from __future__ import annotations

import json
import shutil
import subprocess
from argparse import Namespace
from pathlib import Path
from typing import Any

import pytest

from scripts import smoke_mvp_flow as smoke


class _RecordingClient:
    def __init__(self) -> None:
        self.deleted_paths: list[str] = []

    def delete(self, path: str) -> None:
        self.deleted_paths.append(path)


def _context() -> smoke.SmokeContext:
    return smoke.SmokeContext(
        workspace_id="workspace-1",
        product_id="product-1",
        product_context_version=1,
        primary_category="test",
        viral_objective="test",
        board_id="board-1",
        reference_ids=("reference-1", "reference-2"),
        quick_asset_id="quick-1",
        ugc_asset_id="ugc-1",
    )


def test_delete_and_verify_workspace_runs_both_steps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _RecordingClient()
    verified: list[str] = []

    def verify(workspace_id: str) -> str:
        verified.append(workspace_id)
        return "succeeded"

    monkeypatch.setattr(smoke, "verify_workspace_deletion", verify)

    status = smoke.delete_and_verify_workspace(client, "workspace-1")  # type: ignore[arg-type]

    assert status == "succeeded"
    assert client.deleted_paths == ["/workspaces/workspace-1"]
    assert verified == ["workspace-1"]


def test_isolated_context_setup_failure_cleans_created_workspace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cleaned: list[str] = []

    class SetupClient:
        def __init__(self) -> None:
            self.calls = 0

        def post(self, path: str, payload: dict[str, object]) -> dict[str, Any]:
            self.calls += 1
            if self.calls == 1:
                return {"id": "workspace-setup"}
            raise smoke.SmokeFailure("product setup failed")

    monkeypatch.setattr(
        smoke,
        "delete_and_verify_workspace",
        lambda _client, workspace_id: cleaned.append(workspace_id) or "succeeded",
    )
    args = Namespace(
        run_id="setup-failure",
        golden_case=None,
        expect_mode="mock",
        quick_fixture_id="quick",
        reference_fixture_id="reference",
        ugc_fixture_id="ugc",
    )

    with pytest.raises(smoke.SmokeFailure, match="product setup failed"):
        smoke.create_isolated_context(SetupClient(), args, tmp_path / "media.mp4")  # type: ignore[arg-type]

    assert cleaned == ["workspace-setup"]


def test_main_failure_after_context_creation_cleans_workspace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cleaned: list[str] = []
    client_closed: list[bool] = []
    ctx = _context()

    class MainClient:
        def __init__(
            self,
            _base_url: str,
            _token: str,
            timeout_seconds: int,
        ) -> None:
            assert timeout_seconds == 300

        def get(self, path: str) -> dict[str, str]:
            if path == "/system/ai-readiness":
                return {"mode": "mock"}
            if path == "/me":
                return {"status": "active"}
            raise AssertionError(path)

        def close(self) -> None:
            client_closed.append(True)

    args = Namespace(
        run_id="flow-failure",
        expect_mode="mock",
        golden_case=None,
        base_url="http://test/api/v1",
        token=smoke.AUTH_TOKEN,
        isolated_lifecycle=True,
        verify_db=False,
        result_path=None,
        timeout_seconds=300,
    )
    monkeypatch.setattr(smoke, "parse_args", lambda: args)
    monkeypatch.setattr(smoke, "ApiClient", MainClient)
    monkeypatch.setattr(smoke, "prepare_media", lambda _args, _temp: tmp_path / "media.mp4")
    monkeypatch.setattr(
        smoke,
        "prepare_revision_media",
        lambda _args, _temp, _media: tmp_path / "revision.mp4",
    )
    monkeypatch.setattr(smoke, "load_context", lambda _client, _args, _media: ctx)
    monkeypatch.setattr(
        smoke,
        "run_quick_scorer",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            smoke.SmokeFailure("workflow failed")
        ),
    )
    monkeypatch.setattr(
        smoke,
        "delete_and_verify_workspace",
        lambda _client, workspace_id: cleaned.append(workspace_id) or "succeeded",
    )

    with pytest.raises(smoke.SmokeFailure, match="workflow failed"):
        smoke.main()

    assert cleaned == ["workspace-1"]
    assert client_closed == [True]


def test_live_qualification_requires_local_tts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(smoke.shutil, "which", lambda _name: None)
    args = Namespace(expect_mode="live", qualification_tts=None)

    with pytest.raises(smoke.SmokeFailure, match="local TTS"):
        smoke._render_qualification_narration(
            args,
            tmp_path,
            "Qualification narration.",
            "golden-case",
        )


def test_rendered_qualification_video_stream_covers_full_story(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("ffmpeg and ffprobe are required for qualification media regression")
    scenario = smoke.load_application_scenario(
        "home_travel_steamer",
        run_id="media-regression",
    )
    monkeypatch.setattr(smoke.shutil, "which", lambda _name: None)
    rendered = smoke.render_qualification_media(
        Namespace(
            expect_mode="mock",
            ffmpeg=ffmpeg,
            qualification_tts=None,
        ),
        tmp_path,
        scenario.draft_story,
        "qualification.mp4",
    )

    raw_probe = subprocess.check_output(  # noqa: S603  # nosec B603
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=duration",
            "-of",
            "json",
            str(rendered),
        ],
        text=True,
    )
    stream_duration = float(json.loads(raw_probe)["streams"][0]["duration"])

    assert stream_duration >= scenario.draft_story.duration_seconds - 0.1
