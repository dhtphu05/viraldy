from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess  # nosec B404
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast

import httpx
from PIL import Image, ImageDraw, ImageFont

from viraldy.evaluation.qualification.application_scenarios import (
    GoldenApplicationScenario,
    QualificationMediaStory,
    load_application_scenario,
)
from viraldy.evaluation.qualification.catalog import CASE_ALIASES, resolve_case

# The isolated runner uses local-test auth and a locally selected ffmpeg executable only.
# Documented local-only token; production settings reject local-test auth mode.
AUTH_TOKEN = "local-test"  # noqa: S105  # nosec B105
EXPECTED_CONCEPT_COUNT = 3


@dataclass(frozen=True)
class SmokeContext:
    workspace_id: str
    product_id: str
    product_context_version: int
    primary_category: str
    viral_objective: str
    board_id: str
    reference_ids: tuple[str, str]
    quick_asset_id: str
    ugc_asset_id: str


class SmokeFailure(RuntimeError):
    pass


class ApiClient:
    def __init__(self, base_url: str, token: str, timeout_seconds: int = 30) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=float(timeout_seconds),
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

    def delete(self, path: str) -> None:
        self._request("DELETE", path)

    def upload(self, upload_url: str, path: Path, headers: dict[str, str]) -> None:
        with path.open("rb") as file:
            response = httpx.put(upload_url, content=file.read(), headers=headers, timeout=30.0)
        if response.status_code >= 400:
            raise SmokeFailure(
                f"Upload to object storage failed: HTTP {response.status_code} {response.text}"
            )

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._client.request(method, path, **kwargs)
        if response.status_code == 204:
            return None
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
    if args.golden_case is not None:
        args.golden_case = resolve_case(args.golden_case)
    client = ApiClient(args.base_url, args.token, args.timeout_seconds)
    completed_job_ids: list[str] = []
    ctx: SmokeContext | None = None
    deletion_status = "not_requested"
    workspace_deleted = False
    model_runs_verified = False
    failure_stage = "readiness"
    try:
        readiness = client.get("/system/ai-readiness")
        assert_equal(readiness["mode"], args.expect_mode, "AI readiness mode")
        failure_stage = "identity"
        identity = client.get("/me")
        assert_equal(identity["status"], "active", "Authenticated user status")

        with TemporaryDirectory(prefix="viraldy-smoke-") as temp_dir:
            failure_stage = "media_preparation"
            media_path = prepare_media(args, Path(temp_dir))
            revision_media_path = prepare_revision_media(
                args,
                Path(temp_dir),
                media_path,
            )
            failure_stage = "context_setup"
            ctx = load_context(client, args, media_path)
            failure_stage = "quick_score"
            quick_run, quick_job_id = run_quick_scorer(client, ctx, args, completed_job_ids)
            failure_stage = "reference_analysis"
            dna_ids = [
                run_reference_dna(client, ctx, reference_id, index, args, completed_job_ids)
                for index, reference_id in enumerate(ctx.reference_ids, start=1)
            ]
            failure_stage = "adaptation"
            adaptation = run_adaptation(client, ctx, dna_ids[0], args)
            failure_stage = "pattern_kit"
            pattern = run_pattern_kit(client, ctx, dna_ids, args)
            failure_stage = "viral_kit"
            viral = run_viral_kit(client, ctx, pattern, args)
            failure_stage = "campaign_pack"
            concept_id, pack_id, pack_version_id = select_concept_and_compile_pack(
                client,
                ctx,
                viral,
            )
            failure_stage = "preflight_draft_1"
            preflight_run = run_preflight(
                client,
                ctx,
                pack_version_id,
                args,
                completed_job_ids,
                run_label="draft-1",
            )
            failure_stage = "presentation_draft_1"
            presentation = run_presentation(
                client,
                ctx,
                preflight_run,
                expect_mode=args.expect_mode,
            )
            failure_stage = "learning_loop"
            recommendation_id = run_learning_loop(
                client,
                ctx,
                pattern,
                viral,
                preflight_run,
                pack_id,
            )
            failure_stage = "revision_upload"
            revision_version_id = upload_revision(
                client,
                ctx,
                revision_media_path,
                args,
            )
            revision_preflight_run = None
            revision_presentation = None
            if revision_version_id != "not-run":
                failure_stage = "preflight_draft_2"
                revision_preflight_run = run_preflight(
                    client,
                    ctx,
                    pack_version_id,
                    args,
                    completed_job_ids,
                    run_label="draft-2",
                )
                failure_stage = "presentation_draft_2"
                revision_presentation = run_presentation(
                    client,
                    ctx,
                    revision_preflight_run,
                    expect_mode=args.expect_mode,
                )
                failure_stage = "revision_comparison"
                verify_revision_comparison(
                    preflight_run,
                    revision_preflight_run,
                    revision_version_id,
                )
            failure_stage = "model_run_verification"
            model_runs = verify_learning_events(
                client,
                ctx,
                pattern,
                viral,
                creative_dna_ids=dna_ids,
                adaptation_id=str(adaptation["id"]),
                campaign_pack_id=pack_id,
                preflight_run_id=str(preflight_run["id"]),
                revision_preflight_run_id=(
                    str(revision_preflight_run["id"])
                    if revision_preflight_run is not None
                    else None
                ),
                recommendation_id=recommendation_id,
                revision_version_id=revision_version_id,
                isolated_lifecycle=args.isolated_lifecycle,
                expect_mode=args.expect_mode,
            )
            model_runs_verified = True

            if args.verify_db:
                failure_stage = "database_verification"
                verify_database(
                    expect_mode=args.expect_mode,
                    workspace_id=ctx.workspace_id,
                    completed_job_ids=completed_job_ids,
                    pattern_kit_id=pattern["kit"]["id"],
                    viral_kit_id=viral["kit"]["id"],
                )
            if args.isolated_lifecycle:
                failure_stage = "workspace_cleanup"
                deletion_status = delete_and_verify_workspace(client, ctx.workspace_id)
                workspace_deleted = deletion_status == "succeeded"

            summary = {
                "status": "ok",
                "mode": args.expect_mode,
                "golden_case": args.golden_case,
                "workspace_id": ctx.workspace_id,
                "quick_score_run_id": quick_run["id"],
                "creative_dna_version_ids": dna_ids,
                "adaptation_id": adaptation["id"],
                "pattern_kit_id": pattern["kit"]["id"],
                "viral_kit_id": viral["kit"]["id"],
                "selected_concept_id": concept_id,
                "campaign_pack_id": pack_id,
                "campaign_pack_version_id": pack_version_id,
                "preflight_run_id": preflight_run["id"],
                "preflight_action": preflight_run["action_label"],
                "presentation_sources": presentation["sources"],
                "recommendation_id": recommendation_id,
                "revision_asset_version_id": revision_version_id,
                "revision_preflight_run_id": (
                    revision_preflight_run["id"] if revision_preflight_run is not None else None
                ),
                "revision_preflight_action": (
                    revision_preflight_run["action_label"]
                    if revision_preflight_run is not None
                    else None
                ),
                "revision_presentation_sources": (
                    revision_presentation["sources"] if revision_presentation is not None else None
                ),
                "workspace_deletion_status": deletion_status,
                "completed_job_ids": completed_job_ids,
            }
            result_payload = dict(summary)
            if args.golden_case is not None:
                result_payload["qualification_evidence"] = {
                    "pattern_kit": pattern["latest_version"]["pattern"],
                    "adaptation": adaptation,
                    "viral_kit": viral["latest_version"]["viral_kit"],
                    "draft_1": {
                        "preflight": preflight_run,
                        "presentation": presentation,
                    },
                    "draft_2": (
                        {
                            "preflight": revision_preflight_run,
                            "presentation": revision_presentation,
                        }
                        if revision_preflight_run is not None
                        else None
                    ),
                    "model_runs": model_runs,
                }
            rendered_summary = json.dumps(summary, indent=2, sort_keys=True)
            if args.result_path is not None:
                args.result_path.parent.mkdir(parents=True, exist_ok=True)
                args.result_path.write_text(
                    json.dumps(result_payload, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
            print(rendered_summary)
    except Exception as original_error:
        if args.isolated_lifecycle and ctx is not None and not workspace_deleted:
            try:
                deletion_status = delete_and_verify_workspace(client, ctx.workspace_id)
                workspace_deleted = deletion_status == "succeeded"
            except Exception as cleanup_error:
                _write_failure_result(
                    args,
                    failure_stage=failure_stage,
                    original_error=original_error,
                    cleanup_error=cleanup_error,
                    model_runs_verified=model_runs_verified,
                    workspace_deletion_status="failed",
                )
                raise SmokeFailure(
                    "Smoke flow failed "
                    f"({type(original_error).__name__}) and isolated workspace cleanup failed "
                    f"({type(cleanup_error).__name__})."
                ) from original_error
        _write_failure_result(
            args,
            failure_stage=failure_stage,
            original_error=original_error,
            model_runs_verified=model_runs_verified,
            workspace_deletion_status=deletion_status,
        )
        raise
    finally:
        client.close()


def _write_failure_result(
    args: argparse.Namespace,
    *,
    failure_stage: str,
    original_error: Exception,
    model_runs_verified: bool,
    workspace_deletion_status: str,
    cleanup_error: Exception | None = None,
) -> None:
    result_path = getattr(args, "result_path", None)
    if not isinstance(result_path, Path):
        return
    payload = {
        "status": "error",
        "mode": args.expect_mode,
        "golden_case": args.golden_case,
        "run_id": args.run_id,
        "failure_stage": failure_stage,
        "model_runs_verified": model_runs_verified,
        "safe_error_code": "SMOKE_FLOW_FAILED",
        "safe_error_type": type(original_error).__name__,
        "workspace_deletion_status": workspace_deletion_status,
    }
    if cleanup_error is not None:
        payload.update(
            {
                "cleanup_failure_stage": "workspace_cleanup",
                "cleanup_safe_error_code": "WORKSPACE_CLEANUP_FAILED",
                "cleanup_safe_error_type": type(cleanup_error).__name__,
            }
        )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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
    parser.add_argument(
        "--qualification-tts",
        default=(
            os.getenv("QUALIFICATION_TTS_BIN")
            or shutil.which("say")
            or shutil.which("espeak-ng")
            or shutil.which("espeak")
        ),
        help="Local say/espeak executable used to narrate Golden qualification media.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=90)
    parser.add_argument("--run-id", default=os.getenv("SMOKE_RUN_ID"))
    parser.add_argument("--verify-db", action="store_true")
    parser.add_argument(
        "--isolated-lifecycle",
        action="store_true",
        help=(
            "Create an isolated workspace/product, upload all media, create a revision, "
            "then delete the workspace and verify database/object-storage cleanup."
        ),
    )
    parser.add_argument("--product-name", default=os.getenv("SMOKE_PRODUCT_NAME"))
    parser.add_argument(
        "--golden-case",
        choices=sorted(CASE_ALIASES),
        default=os.getenv("SMOKE_GOLDEN_CASE"),
        help="Run an isolated Golden Product Context and Draft 1/Draft 2 media pair.",
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=None,
        help="Optional path for the redacted machine-readable smoke result.",
    )
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
    if args.isolated_lifecycle:
        if media_path is None:
            raise SmokeFailure("Isolated lifecycle smoke requires a media file.")
        return create_isolated_context(client, args, media_path)

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
        viral_objective="tiktok_shop_affiliate_test",
        board_id=board["id"],
        reference_ids=(reference["id"], second_reference["id"]),
        quick_asset_id=quick_asset_id,
        ugc_asset_id=ugc_asset_id,
    )


def create_isolated_context(
    client: ApiClient,
    args: argparse.Namespace,
    media_path: Path,
) -> SmokeContext:
    run_slug = re.sub(r"[^a-z0-9-]+", "-", str(args.run_id).lower()).strip("-")
    workspace = cast(
        dict[str, Any],
        client.post(
            "/workspaces",
            {
                "name": f"Private beta smoke {args.run_id}",
                "slug": f"smoke-{run_slug[:64]}",
            },
        ),
    )
    workspace_id = str(workspace["id"])
    try:
        scenario = _selected_application_scenario(args)
        product = cast(
            dict[str, Any],
            client.post(
                f"/workspaces/{workspace_id}/products",
                (
                    scenario.product_payload
                    if scenario is not None
                    else isolated_product_payload(args.run_id)
                ),
            ),
        )
        product_id = str(product["id"])
        board = cast(
            dict[str, Any],
            client.post(
                f"/workspaces/{workspace_id}/reference-boards",
                {
                    "name": "Private beta creative research",
                    "description": "Isolated fixture/mock E2E reference board.",
                    "product_id": product_id,
                    "board_type": "creative_research",
                },
            ),
        )

        quick_asset_id = upload_asset(
            client,
            workspace_id,
            product_id,
            media_path,
            "quick-reference",
            fixture_id=args.quick_fixture_id if args.expect_mode == "fixture" else None,
        )
        reference_asset_id = upload_asset(
            client,
            workspace_id,
            product_id,
            media_path,
            "reference",
            fixture_id=args.reference_fixture_id if args.expect_mode == "fixture" else None,
        )
        ugc_asset_id = upload_asset(
            client,
            workspace_id,
            product_id,
            media_path,
            "ugc",
            fixture_id=args.ugc_fixture_id if args.expect_mode == "fixture" else None,
        )
        first_reference = create_reference(
            client,
            workspace_id,
            str(board["id"]),
            product_id,
            reference_asset_id,
            f"Isolated {args.expect_mode} primary reference",
        )
        second_reference = create_reference(
            client,
            workspace_id,
            str(board["id"]),
            product_id,
            quick_asset_id,
            f"Isolated {args.expect_mode} comparison reference",
        )
        metadata = product.get("metadata_json") or {}
        return SmokeContext(
            workspace_id=workspace_id,
            product_id=product_id,
            product_context_version=int(product["product_context_version"]),
            primary_category=str(metadata.get("category") or "home_organization"),
            viral_objective=(
                scenario.viral_objective if scenario is not None else "tiktok_shop_affiliate_test"
            ),
            board_id=str(board["id"]),
            reference_ids=(str(first_reference["id"]), str(second_reference["id"])),
            quick_asset_id=quick_asset_id,
            ugc_asset_id=ugc_asset_id,
        )
    except Exception as original_error:
        try:
            delete_and_verify_workspace(client, workspace_id)
        except Exception as cleanup_error:
            raise SmokeFailure(
                "Isolated context setup failed "
                f"({type(original_error).__name__}) and workspace cleanup failed "
                f"({type(cleanup_error).__name__})."
            ) from original_error
        raise


def isolated_product_payload(run_id: str) -> dict[str, object]:
    return {
        "name": f"CounterSpace Rack E2E {run_id}",
        "description": "A compact rack that creates observable usable counter space.",
        "market": "US",
        "metadata_json": {"category": "home_organization", "test_run_id": run_id},
        "product_context": {
            "schema_version": "product_context_v1",
            "identity": {
                "name": f"CounterSpace Rack E2E {run_id}",
                "brand": "Viraldy Test",
                "category": "home_organization",
                "subcategory": "counter_storage",
                "market": "US",
                "currency": "USD",
            },
            "personas": [
                {
                    "id": "small_kitchen_shopper",
                    "label": "Small-kitchen shopper",
                    "pain_points": ["limited counter space", "visible clutter"],
                    "desired_outcomes": ["more usable counter space"],
                    "objections": ["unclear size fit"],
                    "awareness_stage": "problem_aware",
                }
            ],
            "benefits": [
                {
                    "id": "counter_space",
                    "label": "Creates usable counter space",
                    "description": "Raises frequently used items above the working surface.",
                    "proof_available": ["visible before and after counter comparison"],
                    "claim_strength": "observed",
                }
            ],
            "features": [
                {
                    "id": "raised_storage",
                    "label": "Raised storage surface",
                    "description": "Keeps items accessible above the counter.",
                    "visual_demo_possible": True,
                    "visual_cues": ["clear before and after counter view"],
                }
            ],
            "commercial": {
                "price": "29.99",
                "shipping_text": "Use only the current product listing estimate.",
                "margin_band": "unknown",
            },
            "creative": {
                "primary_angles": ["visible counter reset"],
                "demonstration_mechanisms": ["before and after counter comparison"],
                "visual_differentiators": ["product remains visible during setup"],
                "available_proof": ["observable counter-space result"],
                "creator_personas": ["home organizer"],
                "preferred_delivery_styles": ["authentic_review", "demonstration"],
                "brand_voice": ["clear", "specific"],
                "prohibited_visuals": ["misleading scale"],
            },
            "governance": {
                "claims": [
                    {
                        "id": "no-guaranteed-result",
                        "text": "Do not guarantee an exact amount of space saved.",
                        "rule_type": "prohibited",
                        "severity": "high",
                    }
                ],
                "required_disclosures": ["Product tag identifies the exact listing."],
                "prohibited_content": ["unsupported superlatives"],
                "rights_notes": ["Use seller-owned E2E media only."],
            },
        },
    }


def prepare_media(args: argparse.Namespace, temp_dir: Path) -> Path | None:
    if args.expect_mode == "fixture" and not args.isolated_lifecycle:
        return None
    if args.media_file:
        path = Path(args.media_file)
        if not path.exists():
            raise SmokeFailure(f"Smoke media file does not exist: {path}")
        return path
    if not args.ffmpeg:
        raise SmokeFailure("ffmpeg is required to generate mock/live smoke media.")
    scenario = _selected_application_scenario(args)
    if scenario is not None:
        return render_qualification_media(
            args,
            temp_dir,
            scenario.draft_story,
            f"{scenario.scenario_id}-draft-1.mp4",
        )
    output = temp_dir / "smoke-video.mp4"
    # Operator-selected local executable, fixed argv, no shell, and a bounded timeout.
    subprocess.run(  # noqa: S603  # nosec B603
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
        timeout=30,
    )
    return output


def prepare_revision_media(
    args: argparse.Namespace,
    temp_dir: Path,
    primary_media_path: Path | None,
) -> Path | None:
    scenario = _selected_application_scenario(args)
    if scenario is None or args.media_file:
        return primary_media_path
    return render_qualification_media(
        args,
        temp_dir,
        scenario.revision_story,
        f"{scenario.scenario_id}-revision.mp4",
    )


def render_qualification_media(
    args: argparse.Namespace,
    temp_dir: Path,
    story: QualificationMediaStory,
    filename: str,
) -> Path:
    if not args.ffmpeg:
        raise SmokeFailure("ffmpeg is required to render Golden qualification media.")
    image_paths: list[Path] = []
    video_filters: list[str] = []
    palette = (
        "#204B57",
        "#3B394E",
        "#51432E",
        "#315044",
        "#533A43",
        "#344B63",
    )
    for index, scene in enumerate(story.scenes, start=1):
        image_path = temp_dir / f"{filename}-scene-{index:02d}.png"
        _render_qualification_frame(
            image_path,
            scene.text,
            palette[(index - 1) % len(palette)],
            scene_number=index,
        )
        image_paths.append(image_path)
        video_filters.append(
            f"[{index - 1}:v]"
            f"trim=duration={scene.end_seconds - scene.start_seconds:.3f},"
            f"setpts=PTS-STARTPTS[v{index - 1}]"
        )
    video_inputs = [
        item
        for image_path in image_paths
        for item in (
            "-loop",
            "1",
            "-framerate",
            "24",
            "-i",
            str(image_path),
        )
    ]
    video_filter = (
        ";".join(video_filters)
        + ";"
        + "".join(f"[v{index}]" for index in range(len(image_paths)))
        + f"concat=n={len(image_paths)}:v=1:a=0,"
        + f"trim=duration={story.duration_seconds:.3f},"
        + "setpts=PTS-STARTPTS,format=yuv420p[vout]"
    )
    output = temp_dir / filename
    narration_path = _render_qualification_narration(
        args,
        temp_dir,
        story.narration,
        filename,
    )
    audio_input = (
        ["-i", str(narration_path)]
        if narration_path is not None
        else [
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=mono:sample_rate=16000",
        ]
    )
    audio_filter = ["-af", "apad"] if narration_path is not None else []
    subprocess.run(  # noqa: S603  # nosec B603
        [
            str(args.ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            *video_inputs,
            *audio_input,
            "-filter_complex",
            video_filter,
            "-t",
            str(story.duration_seconds),
            "-map",
            "[vout]",
            "-map",
            f"{len(image_paths)}:a:0",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            *audio_filter,
            "-movflags",
            "+faststart",
            "-y",
            str(output),
        ],
        check=True,
        timeout=60,
    )
    return output


def _render_qualification_narration(
    args: argparse.Namespace,
    temp_dir: Path,
    narration: str,
    filename_stem: str,
) -> Path | None:
    executable = (
        getattr(args, "qualification_tts", None)
        or shutil.which("say")
        or shutil.which("espeak-ng")
        or shutil.which("espeak")
    )
    if not executable:
        if args.expect_mode == "live":
            raise SmokeFailure(
                "OpenAI live Golden qualification requires local TTS "
                "(macOS say, espeak-ng, or espeak)."
            )
        return None
    executable_name = Path(str(executable)).name.casefold()
    if executable_name == "say":
        output = temp_dir / f"{filename_stem}.aiff"
        command = [
            str(executable),
            "-r",
            "170",
            "-o",
            str(output),
            narration,
        ]
    elif executable_name in {"espeak", "espeak-ng"}:
        output = temp_dir / f"{filename_stem}.wav"
        command = [
            str(executable),
            "-s",
            "165",
            "-w",
            str(output),
            narration,
        ]
    else:
        raise SmokeFailure(
            "Qualification TTS executable must be macOS say, espeak-ng, or espeak."
        )
    try:
        subprocess.run(  # noqa: S603  # nosec B603
            command,
            check=True,
            capture_output=True,
            timeout=90,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise SmokeFailure("Failed to render local Golden qualification narration.") from exc
    if not output.is_file() or output.stat().st_size == 0:
        raise SmokeFailure("Local TTS did not produce Golden qualification narration.")
    return output


def _render_qualification_frame(
    path: Path,
    raw_text: str,
    background: str,
    *,
    scene_number: int,
) -> None:
    image = Image.new("RGB", (720, 1280), color=background)
    draw = ImageDraw.Draw(image)
    title_font = ImageFont.load_default(size=34)
    body_font = ImageFont.load_default(size=50)
    draw.rounded_rectangle(
        (48, 60, 672, 180),
        radius=16,
        fill="#F4F6F7",
    )
    draw.text(
        (76, 94),
        f"VIRALDY QUALIFICATION  |  SCENE {scene_number}",
        fill="#16252C",
        font=title_font,
    )
    lines = [
        wrapped
        for line in raw_text.splitlines()
        for wrapped in textwrap.wrap(line, width=25) or [""]
    ]
    text = "\n".join(lines)
    box = draw.multiline_textbbox(
        (0, 0),
        text,
        font=body_font,
        spacing=24,
        align="center",
    )
    text_width = box[2] - box[0]
    text_height = box[3] - box[1]
    x = (720 - text_width) / 2
    y = (1280 - text_height) / 2
    draw.rounded_rectangle(
        (max(36, x - 40), y - 48, min(684, x + text_width + 40), y + text_height + 48),
        radius=24,
        fill="#111820",
        outline="#FFFFFF",
        width=3,
    )
    draw.multiline_text(
        (x, y),
        text,
        fill="#FFFFFF",
        font=body_font,
        spacing=24,
        align="center",
    )
    image.save(path, format="PNG")


def _selected_application_scenario(
    args: argparse.Namespace,
) -> GoldenApplicationScenario | None:
    if args.golden_case is None:
        return None
    return load_application_scenario(
        str(args.golden_case),
        run_id=str(args.run_id),
    )


def upload_asset(
    client: ApiClient,
    workspace_id: str,
    product_id: str,
    media_path: Path,
    label: str,
    fixture_id: str | None = None,
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
    if fixture_id is not None:
        mark_asset_as_fixture(
            workspace_id=workspace_id,
            asset_id=str(asset["id"]),
            asset_version_id=str(session["asset_version_id"]),
            fixture_id=fixture_id,
        )
    return str(asset["id"])


def mark_asset_as_fixture(
    *,
    workspace_id: str,
    asset_id: str,
    asset_version_id: str,
    fixture_id: str,
) -> None:
    from sqlalchemy import create_engine, text

    url = os.getenv("DATABASE_SYNC_URL")
    if not url:
        raise SmokeFailure("DATABASE_SYNC_URL is required to identify uploaded fixture assets.")
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            asset_updated = connection.execute(
                text(
                    "update assets set metadata_json = "
                    "coalesce(metadata_json, '{}'::jsonb) || "
                    "jsonb_build_object('fixture_id', cast(:fixture_id as text)) "
                    "where id::text = :asset_id and workspace_id::text = :workspace_id"
                ),
                {
                    "workspace_id": workspace_id,
                    "asset_id": asset_id,
                    "fixture_id": fixture_id,
                },
            ).rowcount
            version_updated = connection.execute(
                text(
                    "update asset_versions set metadata_json = "
                    "coalesce(metadata_json, '{}'::jsonb) || "
                    "jsonb_build_object('fixture_id', cast(:fixture_id as text)) "
                    "where id::text = :version_id and asset_id::text = :asset_id"
                ),
                {
                    "asset_id": asset_id,
                    "version_id": asset_version_id,
                    "fixture_id": fixture_id,
                },
            ).rowcount
        if asset_updated != 1 or version_updated != 1:
            raise SmokeFailure("Failed to identify an uploaded asset/version as a known fixture.")
    finally:
        engine.dispose()


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
    score_detail = client.get(
        f"/workspaces/{ctx.workspace_id}/tiktok-scores/{result['score_run']['id']}"
    )
    score_run = dict(score_detail["score_run"])
    score_run["_detail"] = score_detail
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
            "objectives": [ctx.viral_objective],
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


def run_adaptation(
    client: ApiClient,
    ctx: SmokeContext,
    creative_dna_version_id: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    adaptation = cast(
        dict[str, Any],
        client.post(
            f"/workspaces/{ctx.workspace_id}/adaptations",
            {
                "product_id": ctx.product_id,
                "creative_dna_version_id": creative_dna_version_id,
                "objective": ctx.viral_objective,
                "target_market": "US",
                "target_buyer": {"persona": "primary Product Context buyer"},
                "constraints": {
                    "max_duration_seconds": 30,
                    "channel_constraints": ["TikTok Shop vertical UGC"],
                },
            },
        ),
    )
    assert_equal(adaptation["status"], "completed", "Adaptation status")
    assert_equal(adaptation["analysis_mode"], args.expect_mode, "Adaptation mode")
    concepts = (adaptation.get("result_json") or {}).get("concepts") or []
    assert_equal(len(concepts), EXPECTED_CONCEPT_COUNT, "Adaptation concept count")
    return adaptation


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
                "objective": ctx.viral_objective,
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
                "applicability_override_reason": (
                    "Automated MVP Product Run validation continued after PatternKit "
                    "extraction to verify downstream ViralKit and Campaign Pack wiring."
                ),
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
    export = client.post(
        f"/workspaces/{ctx.workspace_id}/campaign-packs/" f"{pack['campaign_pack_id']}/exports",
        {"format": "json"},
    )
    assert_equal(
        export["campaign_pack_version_id"],
        pack["campaign_pack_version_id"],
        "Campaign Pack export version",
    )
    exported_snapshot = json.loads(export["content"])
    assert_equal(
        exported_snapshot["campaign_pack_id"],
        pack["campaign_pack_id"],
        "Campaign Pack export snapshot",
    )
    return concept_id, pack["campaign_pack_id"], pack["campaign_pack_version_id"]


def run_preflight(
    client: ApiClient,
    ctx: SmokeContext,
    campaign_pack_version_id: str,
    args: argparse.Namespace,
    completed_job_ids: list[str],
    *,
    run_label: str,
) -> dict[str, Any]:
    result = client.post(
        f"/workspaces/{ctx.workspace_id}/preflight-runs",
        {"ugc_asset_id": ctx.ugc_asset_id, "campaign_pack_version_id": campaign_pack_version_id},
        idempotency_key=f"smoke-{args.run_id}-preflight-{run_label}",
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


def run_presentation(
    client: ApiClient,
    ctx: SmokeContext,
    preflight_run: dict[str, Any],
    *,
    expect_mode: str,
) -> dict[str, Any]:
    presentation = cast(
        dict[str, Any],
        client.post(
            f"/workspaces/{ctx.workspace_id}/preflight-runs/" f"{preflight_run['id']}/presentation",
            {"seller_locale": "en-US", "force_regenerate": False},
        ),
    )
    seller_summary = presentation.get("seller_summary") or {}
    if not seller_summary.get("one_sentence_decision"):
        raise SmokeFailure("Preflight presentation returned no seller decision.")
    if preflight_run["action_label"] == "revise":
        creator_revision = presentation.get("creator_revision") or {}
        if not creator_revision.get("required_changes"):
            raise SmokeFailure("Revise presentation returned no creator-ready required changes.")
    sources = presentation.get("sources") or {}
    if not sources.get("seller_summary"):
        raise SmokeFailure("Presentation did not expose its safe generation source.")
    if expect_mode == "live":
        expected_live_sources = {
            key: value
            for key, value in sources.items()
            if key == "seller_summary" or presentation.get("creator_revision") is not None
        }
        if not expected_live_sources or any(
            value != "openai" for value in expected_live_sources.values()
        ):
            raise SmokeFailure("Live presentation used a deterministic fallback instead of OpenAI.")
    return presentation


def verify_revision_comparison(
    draft_one: dict[str, Any],
    draft_two: dict[str, Any],
    revision_version_id: str,
) -> None:
    if str(draft_one["ugc_asset_version_id"]) == str(draft_two["ugc_asset_version_id"]):
        raise SmokeFailure("Draft 2 Preflight reused the Draft 1 asset version.")
    assert_equal(
        str(draft_two["ugc_asset_version_id"]),
        revision_version_id,
        "Draft 2 Preflight asset version",
    )
    if draft_one["campaign_pack_version_id"] != draft_two["campaign_pack_version_id"]:
        raise SmokeFailure("Draft comparison changed the locked Campaign Pack version.")


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
    return str(recommendation["id"])


def upload_revision(
    client: ApiClient,
    ctx: SmokeContext,
    media_path: Path | None,
    args: argparse.Namespace,
) -> str:
    if media_path is None:
        if args.isolated_lifecycle:
            raise SmokeFailure("Isolated lifecycle smoke requires revision media.")
        return "not-run"
    session = cast(
        dict[str, Any],
        client.post(
            f"/workspaces/{ctx.workspace_id}/assets/{ctx.ugc_asset_id}" "/versions/upload-sessions",
            {
                "filename": f"smoke-revision-{args.run_id}.mp4",
                "declared_mime_type": "video/mp4",
                "declared_size_bytes": media_path.stat().st_size,
            },
        ),
    )
    client.upload(session["upload_url"], media_path, session["required_headers"])
    version = cast(
        dict[str, Any],
        client.post(
            f"/workspaces/{ctx.workspace_id}/assets/{ctx.ugc_asset_id}/versions/"
            f"{session['asset_version_id']}/complete-upload"
        ),
    )
    assert_equal(version["version_number"], 2, "UGC revision version number")
    if not version["is_current"]:
        raise SmokeFailure("Completed UGC revision did not become the current asset version.")
    if args.expect_mode == "fixture":
        mark_asset_as_fixture(
            workspace_id=ctx.workspace_id,
            asset_id=ctx.ugc_asset_id,
            asset_version_id=str(version["id"]),
            fixture_id=args.ugc_fixture_id,
        )
    versions = client.get(f"/workspaces/{ctx.workspace_id}/assets/{ctx.ugc_asset_id}/versions")
    if [item["version_number"] for item in versions[:2]] != [2, 1]:
        raise SmokeFailure("UGC revision history did not preserve both immutable versions.")
    return str(version["id"])


def verify_learning_events(
    client: ApiClient,
    ctx: SmokeContext,
    pattern: dict[str, Any],
    viral: dict[str, Any],
    *,
    creative_dna_ids: list[str],
    adaptation_id: str,
    campaign_pack_id: str,
    preflight_run_id: str,
    revision_preflight_run_id: str | None,
    recommendation_id: str,
    revision_version_id: str,
    isolated_lifecycle: bool,
    expect_mode: str,
) -> list[dict[str, Any]]:
    events = client.get(f"/workspaces/{ctx.workspace_id}/events?limit=500")
    event_subjects = {(event["event_type"], str(event.get("subject_id") or "")) for event in events}
    required_event_subjects = {
        ("pattern_kit_created", str(pattern["kit"]["id"])),
        ("pattern_kit_reviewed", str(pattern["kit"]["id"])),
        ("pattern_kit_validated", str(pattern["kit"]["id"])),
        ("viral_kit_created", str(viral["kit"]["id"])),
        ("concept_selected", str(viral["kit"]["id"])),
        ("campaign_pack_created", campaign_pack_id),
        ("campaign_pack_exported", campaign_pack_id),
        ("preflight_viewed", preflight_run_id),
        ("recommendation_accepted", recommendation_id),
        ("pattern_kit_corrected", str(pattern["kit"]["id"])),
        *{("reference_analyzed", reference_id) for reference_id in ctx.reference_ids},
        *{("creative_dna_viewed", creative_dna_id) for creative_dna_id in creative_dna_ids},
    }
    if revision_version_id != "not-run":
        required_event_subjects.add(("revision_uploaded", ctx.ugc_asset_id))
    if revision_preflight_run_id is not None:
        required_event_subjects.add(("preflight_viewed", revision_preflight_run_id))
    if isolated_lifecycle:
        required_event_subjects.update(
            {
                ("workspace_created", ctx.workspace_id),
                ("product_created", ctx.product_id),
                ("ugc_uploaded", ctx.ugc_asset_id),
                *{("reference_uploaded", reference_id) for reference_id in ctx.reference_ids},
            }
        )
    missing = required_event_subjects - event_subjects
    if missing:
        raise SmokeFailure(f"Learning-loop events or subjects are missing: {sorted(missing)}")

    model_runs = client.get(f"/workspaces/{ctx.workspace_id}/model-runs?status=completed&limit=500")
    model_subjects = {
        (run["subject_type"], str(run["subject_id"]))
        for run in model_runs
        if run["analysis_mode"] == expect_mode
    }
    required_model_subjects = {
        ("pattern_kit", str(pattern["kit"]["id"])),
        ("viral_kit", str(viral["kit"]["id"])),
    }
    if expect_mode != "fixture":
        required_model_subjects.add(("adaptation_run", adaptation_id))
    if expect_mode == "live":
        required_model_subjects.add(("preflight_run", preflight_run_id))
        if revision_preflight_run_id is not None:
            required_model_subjects.add(("preflight_run", revision_preflight_run_id))
    missing_model_subjects = required_model_subjects - model_subjects
    if missing_model_subjects:
        raise SmokeFailure(
            f"HTTP model-run query is missing completed {expect_mode} subjects: "
            f"{sorted(missing_model_subjects)}"
        )
    return cast(list[dict[str, Any]], model_runs)


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


def verify_workspace_deletion(workspace_id: str) -> str:
    from sqlalchemy import create_engine, text

    from viraldy.platform.config.settings import get_settings
    from viraldy.platform.storage.s3 import S3StorageAdapter

    url = os.getenv("DATABASE_SYNC_URL")
    if not url:
        raise SmokeFailure("DATABASE_SYNC_URL is required to verify workspace deletion.")
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            workspace_count = connection.execute(
                text("select count(*) from workspaces where id::text = :workspace_id"),
                {"workspace_id": workspace_id},
            ).scalar_one()
            asset_version_count = connection.execute(
                text(
                    "select count(*) from asset_versions " "where storage_key like :storage_prefix"
                ),
                {"storage_prefix": f"workspaces/{workspace_id}/%"},
            ).scalar_one()
            audit = (
                connection.execute(
                    text(
                        "select id::text, status, deleted_object_count, deleted_row_counts_json "
                        "from deletion_audit_records "
                        "where workspace_id::text = :workspace_id "
                        "and resource_type = 'workspace' and resource_id::text = :workspace_id "
                        "order by created_at desc limit 1"
                    ),
                    {"workspace_id": workspace_id},
                )
                .mappings()
                .one_or_none()
            )
            if audit is None:
                raise SmokeFailure("Workspace deletion created no audit record.")
            batch = (
                connection.execute(
                    text(
                        "select status, deleted_object_count, object_keys_json "
                        "from storage_deletion_batches "
                        "where source_type = 'hard_delete' and source_id::text = :audit_id "
                        "order by created_at desc limit 1"
                    ),
                    {"audit_id": audit["id"]},
                )
                .mappings()
                .one_or_none()
            )
        if workspace_count != 0 or asset_version_count != 0:
            raise SmokeFailure("Workspace deletion left workspace-owned database rows behind.")
        if audit["status"] != "succeeded":
            raise SmokeFailure(f"Workspace deletion audit is not succeeded: {audit['status']}.")
        if batch is None or batch["status"] != "succeeded":
            raise SmokeFailure("Workspace storage deletion batch did not succeed.")
        if int(batch["deleted_object_count"]) != len(batch["object_keys_json"]):
            raise SmokeFailure("Workspace storage deletion count does not match its object batch.")

        remaining_objects = S3StorageAdapter(get_settings()).list_objects(
            f"workspaces/{workspace_id}/"
        )
        if remaining_objects:
            raise SmokeFailure(
                "Workspace object-storage prefix is not empty after deletion: "
                f"{[item.key for item in remaining_objects[:5]]}"
            )
        return str(audit["status"])
    finally:
        engine.dispose()


def delete_and_verify_workspace(client: ApiClient, workspace_id: str) -> str:
    client.delete(f"/workspaces/{workspace_id}")
    return verify_workspace_deletion(workspace_id)


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
