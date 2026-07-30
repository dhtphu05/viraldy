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
from typing import Any, cast

import httpx

AUTH_TOKEN = "local-test"  # noqa: S105 - documented local-only development token.
EXPECTED_CONCEPT_COUNT = 3


@dataclass(frozen=True)
class SmokeContext:
    workspace_id: str
    product_id: str
    product_context_version: int
    primary_category: str
    board_id: str
    reference_ids: tuple[str, str]
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
        identity = client.get("/me")
        assert_equal(identity["status"], "active", "Authenticated user status")

        with TemporaryDirectory(prefix="viraldy-smoke-") as temp_dir:
            media_path = prepare_media(args, Path(temp_dir))
            ctx = load_context(client, args, media_path)
            quick_run, quick_job_id = run_quick_scorer(client, ctx, args, completed_job_ids)
            dna_ids = [
                run_reference_dna(client, ctx, reference_id, index, args, completed_job_ids)
                for index, reference_id in enumerate(ctx.reference_ids, start=1)
            ]
            pattern = run_pattern_kit(client, ctx, dna_ids, args)
            viral = run_viral_kit(client, ctx, pattern, args)
            concept_id, pack_id, pack_version_id = select_concept_and_compile_pack(
                client,
                ctx,
                viral,
            )
            preflight_run = run_preflight(
                client,
                ctx,
                pack_version_id,
                args,
                completed_job_ids,
            )
            recommendation_id = run_learning_loop(
                client,
                ctx,
                pattern,
                viral,
                preflight_run,
                pack_id,
            )

            if args.verify_db:
                verify_database(
                    expect_mode=args.expect_mode,
                    workspace_id=ctx.workspace_id,
                    completed_job_ids=completed_job_ids,
                    pattern_kit_id=pattern["kit"]["id"],
                    viral_kit_id=viral["kit"]["id"],
                )

            print(
                json.dumps(
                    {
                        "status": "ok",
                        "mode": args.expect_mode,
                        "workspace_id": ctx.workspace_id,
                        "quick_score_run_id": quick_run["id"],
                        "creative_dna_version_ids": dna_ids,
                        "pattern_kit_id": pattern["kit"]["id"],
                        "viral_kit_id": viral["kit"]["id"],
                        "selected_concept_id": concept_id,
                        "campaign_pack_id": pack_id,
                        "campaign_pack_version_id": pack_version_id,
                        "preflight_run_id": preflight_run["id"],
                        "recommendation_id": recommendation_id,
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
        second_reference = find_or_create_reference(
            client,
            workspace_id,
            board["id"],
            product["id"],
            references,
            quick_asset_id,
            "Fixture comparison reference",
        )
        ugc_asset_id = find_fixture_asset(assets, args.ugc_fixture_id)
    else:
        if media_path is None:
            raise SmokeFailure("Mock/live smoke requires a media file to upload.")
        quick_asset_id = upload_asset(client, workspace_id, product["id"], media_path, "quick")
        reference_asset_id = upload_asset(
            client, workspace_id, product["id"], media_path, "reference"
        )
        second_reference_asset_id = upload_asset(
            client,
            workspace_id,
            product["id"],
            media_path,
            "reference-comparison",
        )
        ugc_asset_id = upload_asset(client, workspace_id, product["id"], media_path, "ugc")
        reference = create_reference(
            client,
            workspace_id,
            board["id"],
            product["id"],
            reference_asset_id,
            f"Smoke {args.expect_mode} reference",
        )
        second_reference = create_reference(
            client,
            workspace_id,
            board["id"],
            product["id"],
            second_reference_asset_id,
            f"Smoke {args.expect_mode} comparison reference",
        )
    metadata = product.get("metadata_json") or {}
    return SmokeContext(
        workspace_id=workspace_id,
        product_id=product["id"],
        product_context_version=int(product.get("product_context_version") or 1),
        primary_category=str(
            metadata.get("category") or metadata.get("fixture_category") or "home_organization"
        ),
        board_id=board["id"],
        reference_ids=(reference["id"], second_reference["id"]),
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
    asset_type = "reference" if label.startswith("reference") else "ugc"
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
    asset = cast(
        dict[str, Any],
        client.post(f"/workspaces/{workspace_id}/assets/{session['asset_id']}/complete-upload"),
    )
    return str(asset["id"])


def create_reference(
    client: ApiClient,
    workspace_id: str,
    board_id: str,
    product_id: str,
    asset_id: str,
    title: str,
) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        client.post(
            f"/workspaces/{workspace_id}/references",
            {
                "board_id": board_id,
                "asset_id": asset_id,
                "product_id": product_id,
                "source_platform": "tiktok",
                "title": title,
                "notes": "Created by the private beta fixture/mock E2E smoke flow.",
            },
        ),
    )


def find_or_create_reference(
    client: ApiClient,
    workspace_id: str,
    board_id: str,
    product_id: str,
    references: list[dict[str, Any]],
    asset_id: str,
    title: str,
) -> dict[str, Any]:
    for reference in references:
        if str(reference.get("asset_id")) == asset_id:
            return reference
    return create_reference(
        client,
        workspace_id,
        board_id,
        product_id,
        asset_id,
        title,
    )


def run_quick_scorer(
    client: ApiClient, ctx: SmokeContext, args: argparse.Namespace, completed_job_ids: list[str]
) -> tuple[dict[str, Any], str]:
    payload: dict[str, object] = {
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
    client: ApiClient,
    ctx: SmokeContext,
    reference_id: str,
    reference_number: int,
    args: argparse.Namespace,
    completed_job_ids: list[str],
) -> str:
    result = client.post(
        f"/workspaces/{ctx.workspace_id}/references/{reference_id}/analyze",
        idempotency_key=f"smoke-{args.run_id}-dna-{reference_number}",
    )
    job = poll_job(client, ctx.workspace_id, result["job"]["id"], args.timeout_seconds)
    completed_job_ids.append(job["id"])
    dna_id = str((job.get("output_json") or {}).get("creative_dna_version_id") or "")
    if not dna_id:
        raise SmokeFailure("Reference analysis completed without creative_dna_version_id.")
    dna = client.get(f"/workspaces/{ctx.workspace_id}/creative-dna/{dna_id}")
    assert_equal(dna["analysis_mode"], args.expect_mode, "Creative DNA mode")
    return dna_id


def run_pattern_kit(
    client: ApiClient,
    ctx: SmokeContext,
    dna_ids: list[str],
    args: argparse.Namespace,
) -> dict[str, Any]:
    pattern = client.post(
        f"/workspaces/{ctx.workspace_id}/pattern-kits",
        {
            "name": f"Smoke evidence pattern {args.run_id}",
            "kind": "multi_asset_cluster",
            "scope": "workspace_private",
            "source_creative_dna_version_ids": dna_ids,
            "primary_category": ctx.primary_category,
            "target_platforms": ["tiktok_shop"],
            "target_markets": ["US"],
            "objectives": ["tiktok_shop_affiliate_test"],
            "extraction_mode": "ai_assisted",
            "review_notes": "Private beta fixture/mock E2E review.",
        },
    )
    source = pattern["latest_version"]["pattern"]["source"]
    assert_equal(source["source_asset_count"], len(dna_ids), "PatternKit source count")
    assert_equal(
        set(source["creative_dna_version_ids"]),
        set(dna_ids),
        "PatternKit Creative DNA lineage",
    )
    pattern_kit_id = pattern["kit"]["id"]
    client.post(
        f"/workspaces/{ctx.workspace_id}/pattern-kits/{pattern_kit_id}/actions",
        {"action": "reviewed", "reason": "Smoke reviewer confirmed evidence linkage."},
    )
    client.post(
        f"/workspaces/{ctx.workspace_id}/pattern-kits/{pattern_kit_id}/actions",
        {"action": "validated", "reason": "Smoke human validation gate."},
    )
    reviewed = cast(
        dict[str, Any],
        client.get(f"/workspaces/{ctx.workspace_id}/pattern-kits/{pattern_kit_id}"),
    )
    assert_equal(reviewed["kit"]["status"], "validated", "PatternKit review status")
    return reviewed


def run_viral_kit(
    client: ApiClient,
    ctx: SmokeContext,
    pattern: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    viral = cast(
        dict[str, Any],
        client.post(
            f"/workspaces/{ctx.workspace_id}/viral-kits",
            {
                "product_id": ctx.product_id,
                "expected_product_context_version": ctx.product_context_version,
                "pattern_kit_version_ids": [pattern["latest_version"]["id"]],
                "objective": "tiktok_shop_affiliate_test",
                "platform": "tiktok_shop",
                "target_market": "US",
                "concept_count": EXPECTED_CONCEPT_COUNT,
                "creator_constraints": {
                    "delivery_style_preferences": ["demonstration"],
                },
                "production_constraints": {
                    "max_duration_ms": 30000,
                    "required_aspect_ratio": "9:16",
                },
                "commercial_constraints": {
                    "product_tag_required": True,
                    "shipping_claim_policy": "use_product_context_only",
                },
                "notes": f"Private beta {args.expect_mode} E2E {args.run_id}.",
            },
        ),
    )
    concepts = viral["latest_version"]["viral_kit"]["concepts"]
    assert_equal(len(concepts), EXPECTED_CONCEPT_COUNT, "ViralKit concept count")
    if any(concept["buyer_persona_label"] == concept["creator_persona"] for concept in concepts):
        raise SmokeFailure("ViralKit confused buyer persona with creator persona.")
    return viral


def select_concept_and_compile_pack(
    client: ApiClient,
    ctx: SmokeContext,
    viral: dict[str, Any],
) -> tuple[str, str, str]:
    viral_kit_id = viral["kit"]["id"]
    concept_id = viral["latest_version"]["viral_kit"]["concepts"][0]["id"]
    client.post(
        f"/workspaces/{ctx.workspace_id}/viral-kits/{viral_kit_id}/concept-actions",
        {
            "concept_id": concept_id,
            "action": "selected",
            "reason": "Seller selected the E2E concept for production.",
        },
    )
    pack = client.post(
        f"/workspaces/{ctx.workspace_id}/viral-kits/{viral_kit_id}"
        f"/concepts/{concept_id}/campaign-pack",
        {"rights_note": "Seller-owned fixture/mock media only."},
    )
    if not pack.get("campaign_pack_version_id"):
        raise SmokeFailure("ViralKit Campaign Pack compile returned no version.")
    return concept_id, pack["campaign_pack_id"], pack["campaign_pack_version_id"]


def run_preflight(
    client: ApiClient,
    ctx: SmokeContext,
    campaign_pack_version_id: str,
    args: argparse.Namespace,
    completed_job_ids: list[str],
) -> dict[str, Any]:
    result = client.post(
        f"/workspaces/{ctx.workspace_id}/preflight-runs",
        {"ugc_asset_id": ctx.ugc_asset_id, "campaign_pack_version_id": campaign_pack_version_id},
        idempotency_key=f"smoke-{args.run_id}-preflight",
    )
    job = poll_job(client, ctx.workspace_id, result["job"]["id"], args.timeout_seconds)
    completed_job_ids.append(job["id"])
    run = cast(
        dict[str, Any],
        client.get(
            f"/workspaces/{ctx.workspace_id}/preflight-runs/{result['preflight_run']['id']}"
        ),
    )
    assert_equal(run["analysis_mode"], args.expect_mode, "Preflight mode")
    assert_range(run["preflight_score"], 0, 100, "Preflight score")
    if not run["revision_message"]:
        raise SmokeFailure("Preflight did not return a revision message.")
    if run["action_label"] == "spark_ready_pending_rights":
        if "rights" not in run["revision_message"].lower():
            raise SmokeFailure("Spark-ready Preflight did not expose pending-rights wording.")
    return run


def run_learning_loop(
    client: ApiClient,
    ctx: SmokeContext,
    pattern: dict[str, Any],
    viral: dict[str, Any],
    preflight_run: dict[str, Any],
    campaign_pack_id: str,
) -> str:
    recommendations = client.get(f"/workspaces/{ctx.workspace_id}/recommendations")
    recommendation = next(
        (item for item in recommendations if item.get("subject_id") == preflight_run["id"]),
        None,
    )
    if recommendation is None:
        raise SmokeFailure("Preflight completed without a recommendation.")
    client.post(
        f"/workspaces/{ctx.workspace_id}/recommendations/{recommendation['id']}/actions",
        {
            "action_type": "accepted",
            "metadata_json": {"source": "private_beta_smoke"},
        },
    )
    client.post(
        f"/workspaces/{ctx.workspace_id}/feedback",
        {
            "subject_type": "preflight",
            "subject_id": preflight_run["id"],
            "field_path": "revision_message",
            "feedback_type": "correct",
            "ai_value_json": preflight_run["revision_message"],
            "user_value_json": preflight_run["revision_message"],
            "comment": "E2E reviewer confirmed the revision guidance.",
        },
    )
    client.post(
        f"/workspaces/{ctx.workspace_id}/pattern-kits/{pattern['kit']['id']}/feedback",
        {
            "subject_version": pattern["latest_version"]["version"],
            "field_path": "adaptation_instructions",
            "feedback_type": "correct",
            "comment": "E2E reviewer confirmed the adaptation policy.",
        },
    )
    client.post(
        f"/workspaces/{ctx.workspace_id}/viral-kits/{viral['kit']['id']}/feedback",
        {
            "subject_version": viral["latest_version"]["version"],
            "field_path": "concepts[0].hook",
            "feedback_type": "correct",
            "comment": "E2E reviewer confirmed the selected hook.",
        },
    )
    events = client.get(f"/workspaces/{ctx.workspace_id}/events?limit=500")
    event_subjects = {(event["event_type"], str(event.get("subject_id") or "")) for event in events}
    required_event_subjects = {
        ("pattern_kit_created", str(pattern["kit"]["id"])),
        ("pattern_kit_reviewed", str(pattern["kit"]["id"])),
        ("pattern_kit_validated", str(pattern["kit"]["id"])),
        ("viral_kit_created", str(viral["kit"]["id"])),
        ("concept_selected", str(viral["kit"]["id"])),
        ("campaign_pack_created", campaign_pack_id),
        ("recommendation_accepted", str(recommendation["id"])),
        ("pattern_kit_corrected", str(pattern["kit"]["id"])),
    }
    missing = required_event_subjects - event_subjects
    if missing:
        raise SmokeFailure(f"Learning-loop events or subjects are missing: {sorted(missing)}")
    return str(recommendation["id"])


def poll_job(
    client: ApiClient, workspace_id: str, job_id: str, timeout_seconds: int
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        job = cast(
            dict[str, Any],
            client.get(f"/workspaces/{workspace_id}/jobs/{job_id}"),
        )
        if job["status"] in {"succeeded", "completed"}:
            return job
        if job["status"] in {"failed", "cancelled"}:
            raise SmokeFailure(
                f"Job {job_id} ended as {job['status']}: "
                f"{job.get('error_code')} {job.get('error_message')}"
            )
        time.sleep(1.0)
    raise SmokeFailure(f"Job {job_id} did not succeed within {timeout_seconds}s.")


def verify_database(
    *,
    expect_mode: str,
    workspace_id: str,
    completed_job_ids: list[str],
    pattern_kit_id: str,
    viral_kit_id: str,
) -> None:
    from sqlalchemy import create_engine, text

    url = os.getenv("DATABASE_SYNC_URL")
    if not url:
        raise SmokeFailure("DATABASE_SYNC_URL is required when --verify-db is set.")
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            succeeded_job_ids = set(
                connection.execute(
                    text(
                        "select distinct processing_job_id::text from processing_job_events "
                        "where processing_job_id::text = any(:job_ids) "
                        "and status in ('succeeded', 'completed')"
                    ),
                    {"job_ids": completed_job_ids},
                ).scalars()
            )
            missing_job_events = set(completed_job_ids) - succeeded_job_ids
            if missing_job_events:
                raise SmokeFailure(
                    "Missing terminal processing_job_events for smoke jobs: "
                    f"{sorted(missing_job_events)}"
                )
            completed_model_subjects = set(
                connection.execute(
                    text(
                        "select subject_type from ai_model_runs "
                        "where workspace_id::text = :workspace_id "
                        "and analysis_mode = :mode and status = 'completed' "
                        "and ((subject_type = 'pattern_kit' and subject_id::text = :pattern_id) "
                        "or (subject_type = 'viral_kit' and subject_id::text = :viral_id))"
                    ),
                    {
                        "workspace_id": workspace_id,
                        "mode": expect_mode,
                        "pattern_id": pattern_kit_id,
                        "viral_id": viral_kit_id,
                    },
                ).scalars()
            )
            missing_model_subjects = {
                "pattern_kit",
                "viral_kit",
            } - completed_model_subjects
            if missing_model_subjects:
                raise SmokeFailure(
                    f"Missing completed {expect_mode} model runs for: "
                    f"{sorted(missing_model_subjects)}"
                )
    finally:
        engine.dispose()


def find_fixture_asset(assets: list[dict[str, Any]], fixture_id: str) -> str:
    for asset in assets:
        if (asset.get("metadata_json") or {}).get("fixture_id") == fixture_id:
            return str(asset["id"])
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
