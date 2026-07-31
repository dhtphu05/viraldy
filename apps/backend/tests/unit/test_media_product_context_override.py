from __future__ import annotations

from uuid import uuid4

import pytest

from viraldy.modules.assets.public import AssetVersionSnapshot
from viraldy.modules.media_analysis.service import (
    SyncMediaEvidencePipeline,
    _media_analysis_claim_hash,
)
from viraldy.modules.products.contracts import build_minimal_product_context
from viraldy.modules.products.public import ProductContextSnapshot
from viraldy.platform.config.settings import Settings


def test_explicit_product_snapshot_bypasses_mutable_product_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asset_snapshot = _asset_snapshot()
    immutable_snapshot = ProductContextSnapshot(
        product_id=uuid4(),
        workspace_id=asset_snapshot.workspace_id,
        context_schema_version="product_context_v1",
        product_context_version=7,
        product_context=build_minimal_product_context(
            name="Snapshotted product",
            description="Immutable scoring input",
            market="US",
        ),
    )
    pipeline = object.__new__(SyncMediaEvidencePipeline)

    def fail_mutable_lookup(_snapshot: AssetVersionSnapshot) -> None:
        raise AssertionError("mutable Product Context must not be read")

    monkeypatch.setattr(pipeline, "_product_context_snapshot", fail_mutable_lookup)

    resolved = pipeline._resolve_product_context_snapshot(
        asset_snapshot,
        immutable_snapshot,
    )
    resolved_without_product = pipeline._resolve_product_context_snapshot(
        asset_snapshot,
        None,
    )

    assert resolved is immutable_snapshot
    assert resolved_without_product is None


def test_media_claim_hash_tracks_exact_product_snapshot_content() -> None:
    snapshot = _asset_snapshot()
    settings = Settings(
        _env_file=None,
        ai_mode="live",
        ai_provider="openai",
        openai_api_key="test-key",
    )

    original = _media_analysis_claim_hash(
        snapshot,
        settings,
        product_context_version=7,
        product_context_hash="a" * 64,
    )
    changed_content = _media_analysis_claim_hash(
        snapshot,
        settings,
        product_context_version=7,
        product_context_hash="b" * 64,
    )
    changed_version = _media_analysis_claim_hash(
        snapshot,
        settings,
        product_context_version=8,
        product_context_hash="a" * 64,
    )

    assert original != changed_content
    assert original != changed_version


def _asset_snapshot() -> AssetVersionSnapshot:
    return AssetVersionSnapshot(
        asset_id=uuid4(),
        asset_version_id=uuid4(),
        workspace_id=uuid4(),
        product_id=uuid4(),
        storage_key="assets/video.mp4",
        original_filename="video.mp4",
        declared_mime_type="video/mp4",
        detected_mime_type="video/mp4",
        size_bytes=1234,
        checksum_sha256="abc123",
        metadata_json={},
    )
