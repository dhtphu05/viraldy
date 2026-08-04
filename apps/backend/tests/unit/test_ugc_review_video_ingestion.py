from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest

from viraldy.modules.ugc_review.video_ingestion import (
    _safe_filename,
    _spool_upload,
    _video_content_type,
)
from viraldy.shared.errors.base import AppError, PayloadTooLargeError


def test_direct_upload_spools_without_loading_the_whole_video() -> None:
    payload = b"video-bytes"
    spooled = _spool_upload(BytesIO(payload), max_size_bytes=len(payload))
    try:
        assert spooled.size_bytes == len(payload)
        assert Path(spooled.path).read_bytes() == payload
    finally:
        Path(spooled.path).unlink(missing_ok=True)


def test_direct_upload_rejects_empty_and_oversized_files() -> None:
    with pytest.raises(AppError, match="must not be empty"):
        _spool_upload(BytesIO(b""), max_size_bytes=10)

    with pytest.raises(PayloadTooLargeError, match="upload limit"):
        _spool_upload(BytesIO(b"too-large"), max_size_bytes=2)


def test_direct_upload_accepts_only_supported_video_types() -> None:
    assert _video_content_type("draft.mp4", "application/octet-stream") == "video/mp4"
    assert _video_content_type("draft.mov", "video/quicktime") == "video/quicktime"
    with pytest.raises(AppError, match="supports MP4 and QuickTime"):
        _video_content_type("draft.avi", "application/octet-stream")


def test_direct_upload_strips_client_paths_from_filenames() -> None:
    assert _safe_filename(r"C:\fakepath\draft.mp4") == "draft.mp4"
