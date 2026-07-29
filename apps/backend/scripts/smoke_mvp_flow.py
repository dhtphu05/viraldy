from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import httpx

AUTH_TOKEN = "local-test"  # noqa: S105 - documented local-only development token.
EXPECTED_CONCEPT_COUNT = 3


@dataclass(frozen=True)
class SmokeContext:
    workspace_id: str
    product_id: str
    board_id: str
    reference_id: str
    quick_asset_id: str
    ugc_asset_id: str


class SmokeFailure(RuntimeError):
    pass


class ApiClient:
    def __init__(self, base_url: str, token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )

    def close(self) -> None:
        self._client.close()

    def get(self, path: str) -> Any:
        return self._request("GET", path)

    def post(
        self,
        path: str,
        payload: dict[str, object] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        return self._request("POST", path, json=payload, headers=headers)

    def upload(self, upload_url: str, path: Path, headers: dict[str, str]) -> None:
        with path.open("rb") as file:
            response = httpx.put(upload_url, content=file.read(), headers=headers, timeout=30.0)
        if response.status_code >= 400:
            raise SmokeFailure(
                f"Upload to object storage failed: HTTP {response.status_code} {response.text}"
            )

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._client.request(method, path, **kwargs)
        try:
            envelope = response.json()
        except json.JSONDecodeError as exc:
            raise SmokeFailure(
                f"{method} {path} returned non-JSON HTTP {response.status_code}"
            ) from exc
        error = envelope.get("error")
        if response.status_code >= 400 or error:
            code = (error or {}).get("code", "API_ERROR")
            message = (error or {}).get("message", response.text)
            raise SmokeFailure(f"{method} {path} failed: {response.status_code} {code}: {message}")
        return envelope["data"]


def main() -> None:
    args = parse_args()
    args.run_id = args.run_id or f"{args.expect_mode}-{int(time.time())}"
    client = ApiClient(args.base_url, args.token)
    completed_job_ids: list[str] = []
    try:
        readiness = client.get("/system/ai-readiness")
        assert_equal(readiness["mode"], args.expect_mode, "AI readiness mode")

        with TemporaryDirectory(prefix="viraldy-smoke-") as temp_dir:
            media_path = prepare_media(args, Path(temp_dir))
            ctx = load_context(client, args, media_path)
            quick_run, quick_job_id = run_quick_scorer(client, ctx, args, completed_job_ids)
            dna_id = run_reference_dna(client, ctx, args, completed_job_ids)
            adaptation = run_adaptation(client, ctx, dna_id, args)
            pack = run_campaign_pack(client, ctx, adaptation["id"])
            pack_version_id = run_pack_version(client, ctx, pack["id"], pack["current_version"])
            run_preflight(client, ctx, pack_version_id, args, completed_job_ids)

            if args.verify_db:
                verify_database(args.expect_mode, completed_job_ids)

            print(
                json.dumps(
                    {
                        "status": "ok",
                        "mode": args.expect_mode,
                        "workspace_id": ctx.workspace_id,
                        "quick_score_run_id": quick_run["id"],
                        "creative_dna_version_id": dna_id,
                        "adaptation_run_id": adaptation["id"],
                        "campaign_pack_id": pack["id"],
                        "campaign_pack_version_id": pack_version_id,
                        "completed_job_ids": completed_job_ids,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
    finally:
        client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-test both Viraldy MVP flows through HTTP.")
    parser.add_argument(
        "--base-url",
        default=os.getenv("SMOKE_BASE_URL", "http://localhost:8000/api/v1"),
    )
    parser.add_argument("--token", default=os.getenv("SMOKE_AUTH_TOKEN", AUTH_TOKEN))
    parser.add_argument("--expect-mode", choices=["fixture", "mock", "live"], required=True)
    parser.add_argument(
        "--media-file",
        type=Path,
        default=os.getenv("SMOKE_MEDIA_FILE"),
        help="MP4 file to upload in mock/live mode. If omitted, ffmpeg creates a tiny test video.",
    )
    parser.add_argument(
        "--ffmpeg",
        default=os.getenv("FFMPEG_BIN") or shutil.which("ffmpeg"),
        help="ffmpeg binary for generating mock/live smoke video.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=90)
    parser.add_argument("--run-id", default=os.getenv("SMOKE_RUN_ID"))
    parser.add_argument("--verify-db", action="store_true")
    parser.add_argument("--product-name", default=os.getenv("SMOKE_PRODUCT_NAME"))
    parser.add_argument(
        "--reference-fixture-id",
        default=os.getenv("SMOKE_REFERENCE_FIXTURE_ID", "viraldy-demo-reference-v1"),
    )
    parser.add_argument(
        "--quick-fixture-id",
        default=os.getenv("SMOKE_QUICK_FIXTURE_ID", "viraldy-demo-quick-v1"),
    )
    parser.add_argument(
        "--ugc-fixture-id",
        default=os.getenv("SMOKE_UGC_FIXTURE_ID", "viraldy-demo-ugc-fixable-v1"),
    )
    return parser.parse_args()


def load_context(
    client: ApiClient, args: argparse.Namespace, media_path: Path | None
) -> SmokeContext:
    workspace = first(client.get("/workspaces"), "workspace")
    workspace_id = workspace["id"]
    products = client.get(f"/workspaces/{workspace_id}/products")
    assets = client.get(f"/workspaces/{workspace_id}/assets")
    references = client.get(f"/workspaces/{workspace_id}/references")
    boards = client.get(f"/workspaces/{workspace_id}/reference-boards")

    product = (
        find_product(products, args.product_name)
        if args.product_name
        else first(products, "product")
    )
    board = first(boards, "reference board")
    if args.expect_mode == "fixture":
        reference_asset_id = find_fixture_asset(assets, args.reference_fixture_id)
        reference = find_reference_for_asset(references, reference_asset_id)
        quick_asset_id = find_fixture_asset(assets, args.quick_fixture_id)
        ugc_asset_id = find_fixture_asset(assets, args.ugc_fixture_id)
    else:
        if media_path is None:
            raise SmokeFailure("Mock/live smoke requires a media file to upload.")
        quick_asset_id = upload_asset(client, workspace_id, product["id"], media_path, "quick")
        reference_asset_id = upload_asset(
            client, workspace_id, product["id"], media_path, "reference"
        )
        ugc_asset_id = upload_asset(client, workspace_id, product["id"], media_path, "ugc")
        reference = client.post(
            f"/workspaces/{workspace_id}/references",
            {
                "board_id": board["id"],
                "asset_id": reference_asset_id,
                "product_id": product["id"],
                "source_platform": "Smoke",
                "source_url": "https://example.com/viraldy-smoke-reference",
                "title": f"Smoke {args.expect_mode} reference",
                "notes": "Uploaded by scripts/smoke_mvp_flow.py.",
            },
        )
    return SmokeContext(
        workspace_id=workspace_id,
        product_id=product["id"],
        board_id=board["id"],
        reference_id=reference["id"],
        quick_asset_id=quick_asset_id,
        ugc_asset_id=ugc_asset_id,
    )


def prepare_media(args: argparse.Namespace, temp_dir: Path) -> Path | None:
    if args.expect_mode == "fixture":
        return None
    if args.media_file:
        path = Path(args.media_file)
        if not path.exists():
            raise SmokeFailure(f"Smoke media file does not exist: {path}")
        return path
    if not args.ffmpeg:
        raise SmokeFailure("ffmpeg is required to generate mock/live smoke media.")
    output = temp_dir / "smoke-video.mp4"
    subprocess.run(  # noqa: S603 - smoke operator controls the ffmpeg binary path.
        [
            str(args.ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=360x640:rate=24",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880:sample_rate=16000",
            "-t",
            "4",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-y",
            str(output),
        ],
        check=True,
    )
    return output


def upload_asset(
    client: ApiClient, workspace_id: str, product_id: str, media_path: Path, label: str
) -> str:
    asset_type = "reference" if label == "reference" else "ugc"
    session = client.post(
        f"/workspaces/{workspace_id}/assets/upload-sessions",
        {
            "filename": f"smoke-{label}.mp4",
            "declared_mime_type": "video/mp4",
            "declared_size_bytes": media_path.stat().st_size,
            "asset_type": asset_type,
            "product_id": product_id,
        },
    )
    client.upload(session["upload_url"], media_path, session["required_headers"])
    asset = client.post(f"/workspaces/{workspace_id}/assets/{session['asset_id']}/complete-upload")
    return asset["id"]


def run_quick_scorer(
    client: ApiClient, ctx: SmokeContext, args: argparse.Namespace, completed_job_ids: list[str]
) -> tuple[dict[str, Any], str]:
    payload = {
        "asset_id": ctx.quick_asset_id,
        "product_id": ctx.product_id,
        "objective": "generic_structure",
    }
    result = client.post(
        f"/workspaces/{ctx.workspace_id}/tiktok-scores",
        payload,
        idempotency_key=f"smoke-{args.run_id}-quick",
    )
    job = poll_job(client, ctx.workspace_id, result["job"]["id"], args.timeout_seconds)
    completed_job_ids.append(job["id"])
    score_run = client.get(
        f"/workspaces/{ctx.workspace_id}/tiktok-scores/{result['score_run']['id']}"
    )
    assert_equal(score_run["analysis_mode"], args.expect_mode, "Quick scorer mode")
    assert_range(score_run["structural_score"], 0, 100, "Quick scorer structural score")
    return score_run, job["id"]


def run_reference_dna(
    client: ApiClient, ctx: SmokeContext, args: argparse.Namespace, completed_job_ids: list[str]
) -> str:
    result = client.post(
        f"/workspaces/{ctx.workspace_id}/references/{ctx.reference_id}/analyze",
        idempotency_key=f"smoke-{args.run_id}-dna",
    )
    job = poll_job(client, ctx.workspace_id, result["job"]["id"], args.timeout_seconds)
    completed_job_ids.append(job["id"])
    dna_id = str((job.get("output_json") or {}).get("creative_dna_version_id") or "")
    if not dna_id:
        raise SmokeFailure("Reference analysis completed without creative_dna_version_id.")
    dna = client.get(f"/workspaces/{ctx.workspace_id}/creative-dna/{dna_id}")
    assert_equal(dna["analysis_mode"], args.expect_mode, "Creative DNA mode")
    return dna_id


def run_adaptation(
    client: ApiClient, ctx: SmokeContext, dna_id: str, args: argparse.Namespace
) -> dict[str, Any]:
    adaptation = client.post(
        f"/workspaces/{ctx.workspace_id}/adaptations",
        {
            "product_id": ctx.product_id,
            "creative_dna_version_id": dna_id,
            "objective": "tiktok_shop_affiliate_test",
            "target_market": "US",
            "target_buyer": {
                "persona": "small apartment renter",
                "pain": "limited counter space",
                "desired_outcome": "faster organization",
            },
            "constraints": {"must_avoid": ["exact script copy", "unsupported claims"]},
        },
    )
    assert_equal(adaptation["analysis_mode"], args.expect_mode, "Adaptation mode")
    concepts = (adaptation.get("result_json") or {}).get("concepts") or []
    assert_equal(len(concepts), EXPECTED_CONCEPT_COUNT, "Adaptation concept count")
    return adaptation


def run_campaign_pack(client: ApiClient, ctx: SmokeContext, adaptation_id: str) -> dict[str, Any]:
    pack = client.post(
        f"/workspaces/{ctx.workspace_id}/campaign-packs",
        {"adaptation_run_id": adaptation_id, "concept_id": "concept_1"},
    )
    if not pack.get("current_version"):
        raise SmokeFailure("Campaign Pack was created without a current version.")
    versions = client.get(f"/workspaces/{ctx.workspace_id}/campaign-packs/{pack['id']}/versions")
    if len(versions) < 1:
        raise SmokeFailure("Campaign Pack version history is empty after creation.")
    return pack


def run_pack_version(
    client: ApiClient, ctx: SmokeContext, pack_id: str, current_version: dict[str, Any]
) -> str:
    created = client.post(
        f"/workspaces/{ctx.workspace_id}/campaign-packs/{pack_id}/versions",
        {"brief": current_version["brief_json"], "change_note": "Smoke edited version"},
    )
    versions = client.get(f"/workspaces/{ctx.workspace_id}/campaign-packs/{pack_id}/versions")
    if len(versions) < 2:
        raise SmokeFailure("Campaign Pack version history did not retain edited version.")
    numbers = [version["version_number"] for version in versions]
    if max(numbers) < 2:
        raise SmokeFailure("Campaign Pack version numbers did not advance.")
    return created["id"]


def run_preflight(
    client: ApiClient,
    ctx: SmokeContext,
    campaign_pack_version_id: str,
    args: argparse.Namespace,
    completed_job_ids: list[str],
) -> None:
    result = client.post(
        f"/workspaces/{ctx.workspace_id}/preflight-runs",
        {"ugc_asset_id": ctx.ugc_asset_id, "campaign_pack_version_id": campaign_pack_version_id},
        idempotency_key=f"smoke-{args.run_id}-preflight",
    )
    job = poll_job(client, ctx.workspace_id, result["job"]["id"], args.timeout_seconds)
    completed_job_ids.append(job["id"])
    run = client.get(
        f"/workspaces/{ctx.workspace_id}/preflight-runs/{result['preflight_run']['id']}"
    )
    assert_equal(run["analysis_mode"], args.expect_mode, "Preflight mode")
    assert_range(run["preflight_score"], 0, 100, "Preflight score")
    if not run["revision_message"]:
        raise SmokeFailure("Preflight did not return a revision message.")
    if run["action_label"] == "spark_ready_pending_rights":
        if "rights" not in run["revision_message"].lower():
            raise SmokeFailure("Spark-ready Preflight did not expose pending-rights wording.")


def poll_job(
    client: ApiClient, workspace_id: str, job_id: str, timeout_seconds: int
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        job = client.get(f"/workspaces/{workspace_id}/jobs/{job_id}")
        if job["status"] == "completed":
            return job
        if job["status"] in {"failed", "cancelled"}:
            raise SmokeFailure(
                f"Job {job_id} ended as {job['status']}: "
                f"{job.get('error_code')} {job.get('error_message')}"
            )
        time.sleep(1.0)
    raise SmokeFailure(f"Job {job_id} did not complete within {timeout_seconds}s.")


def verify_database(expect_mode: str, completed_job_ids: list[str]) -> None:
    from sqlalchemy import create_engine, text

    url = os.getenv("DATABASE_SYNC_URL")
    if not url:
        raise SmokeFailure("DATABASE_SYNC_URL is required when --verify-db is set.")
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            event_count = connection.execute(
                text(
                    "select count(*) from processing_job_events "
                    "where processing_job_id::text = any(:job_ids)"
                ),
                {"job_ids": completed_job_ids},
            ).scalar_one()
            if int(event_count) < len(completed_job_ids):
                raise SmokeFailure("Missing processing_job_events for completed smoke jobs.")
            if expect_mode != "fixture":
                model_runs = connection.execute(
                    text("select count(*) from ai_model_runs where analysis_mode = :mode"),
                    {"mode": expect_mode},
                ).scalar_one()
                if int(model_runs) < 1:
                    raise SmokeFailure(f"No ai_model_runs persisted for {expect_mode} mode.")
    finally:
        engine.dispose()


def find_fixture_asset(assets: list[dict[str, Any]], fixture_id: str) -> str:
    for asset in assets:
        if (asset.get("metadata_json") or {}).get("fixture_id") == fixture_id:
            return asset["id"]
    raise SmokeFailure(f"Missing seeded fixture asset: {fixture_id}")


def find_product(products: list[dict[str, Any]], product_name: str) -> dict[str, Any]:
    for product in products:
        if product.get("name") == product_name:
            return product
    raise SmokeFailure(f"Missing seeded product: {product_name}")


def find_reference_for_asset(references: list[dict[str, Any]], asset_id: str) -> dict[str, Any]:
    for reference in references:
        if str(reference.get("asset_id")) == asset_id:
            return reference
    raise SmokeFailure(f"Missing seeded reference for fixture asset: {asset_id}")


def first(items: list[dict[str, Any]], label: str) -> dict[str, Any]:
    if not items:
        raise SmokeFailure(f"Missing seeded {label}.")
    return items[0]


def assert_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise SmokeFailure(f"{label}: expected {expected!r}, got {actual!r}.")


def assert_range(value: object, minimum: int, maximum: int, label: str) -> None:
    if not isinstance(value, int | float) or not minimum <= value <= maximum:
        raise SmokeFailure(f"{label}: expected {minimum}-{maximum}, got {value!r}.")


if __name__ == "__main__":
    main()
