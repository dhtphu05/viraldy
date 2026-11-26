"""Self-authored synthetic assets for offline development, never measured AI output."""

from __future__ import annotations

import json
import math
import shutil
import struct
import subprocess
import wave
from pathlib import Path

from PIL import Image, ImageDraw

from .capture import canonical_hash, sha256_bytes
from .contracts import (
    Artifact,
    Attempt,
    Capture,
    CaseManifest,
    EvidenceBundle,
    PilotPreparation,
    Protocol,
    Rights,
)


def _make_clip(image: Path, output: Path, duration: int) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise ValueError("FFmpeg is required for the authored development corpus")
    subprocess.run(  # noqa: S603 - fixed argv, local authored image/output only
        [
            ffmpeg,
            "-n",
            "-loglevel",
            "error",
            "-loop",
            "1",
            "-framerate",
            "24",
            "-i",
            str(image),
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000",
            "-t",
            str(duration),
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "24",
            "-c:a",
            "aac",
            "-shortest",
            str(output),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )


def _draw_product(path: Path, *, wrong: bool = False, character: bool = False) -> None:
    image = Image.new("RGB", (180, 320), "#f5eee0")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((49, 96, 111, 245), radius=16, fill="#d43e39" if wrong else "#2470b8")
    draw.rectangle((62, 74, 99, 103), fill="#d9a13a")
    draw.ellipse((68, 144, 93, 169), fill="white")
    if character:
        draw.ellipse((124, 112, 153, 142), fill="#b98265")
        draw.line((139, 142, 139, 203), fill="#365044", width=9)
        draw.line((139, 161, 112, 155), fill="#365044", width=6)
        draw.line((139, 201, 126, 230), fill="#365044", width=6)
        draw.line((139, 201, 153, 230), fill="#365044", width=6)
    image.save(path)


def _write_tone(path: Path, duration: int = 8) -> None:
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(48000)
        samples = (
            int(3000 * math.sin(2 * math.pi * 440 * index / 48000))
            for index in range(48000 * duration)
        )
        stream.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))


def build_dev_corpus(root: Path) -> EvidenceBundle:
    """Generate fresh fixtures; refuse existing artifacts to preserve earlier evidence."""
    root.mkdir(parents=True, exist_ok=True)
    assets = root / "artifacts"
    assets.mkdir(exist_ok=False)
    _draw_product(assets / "product.png")
    _draw_product(assets / "illustrated-character.png", character=True)
    _draw_product(assets / "wrong-product.png", wrong=True, character=True)
    _make_clip(assets / "product.png", assets / "source.mp4", 16)
    _make_clip(assets / "product.png", assets / "pass.mp4", 8)
    _make_clip(assets / "wrong-product.png", assets / "repair.mp4", 8)
    _write_tone(assets / "tone.wav")
    authored = Rights(
        basis="self_authored",
        evidence_note="Generated solely by this repository's corpus.py with Pillow primitives, "
        "FFmpeg and a mathematical sine wave. Synthetic development use only; "
        "illustrated character depicts no real person. No seller or provider output.",
    )
    entries = [
        ("source", "source", "source.mp4", "video/mp4", 384),
        ("product", "product", "product.png", "image/png", None),
        ("character", "character", "illustrated-character.png", "image/png", None),
        ("audio", "audio", "tone.wav", "audio/wav", None),
        ("pass-output", "assembly", "pass.mp4", "video/mp4", 192),
        ("repair-output", "assembly", "repair.mp4", "video/mp4", 192),
        ("blocked-source", "source", "source.mp4", "video/mp4", 384),
    ]
    artifacts = [
        Artifact.model_validate(
            {
                "artifact_id": key,
                "role": role,
                "path": f"artifacts/{filename}",
                "sha256": sha256_bytes((assets / filename).read_bytes()),
                "mime_type": mime,
                "frame_count": frames,
                "width": None if mime == "audio/wav" else 180,
                "height": None if mime == "audio/wav" else 320,
                "rights": authored.model_copy(update={"declared": False})
                if key == "blocked-source"
                else authored,
            }
        )
        for key, role, filename, mime, frames in entries
    ]
    cases = [
        CaseManifest(
            case_id=f"dev-{outcome}",
            split="development",
            target_frames=192,
            input_artifact_ids=[
                "blocked-source" if outcome == "blocked" else "source",
                "product",
                "audio",
                *(["character"] if outcome == "needs_repair" else []),
            ],
            requirement_ids=[
                "technical",
                "product",
                "action",
                "structure",
                "claims",
                *(["character"] if outcome == "needs_repair" else []),
            ],
            requirements={
                "intent": "A steady showcase of the blue bottle with the amber cap",
                "keep": [],
                "replace": [],
                "forbid": [],
                "claims": [],
                "requiresCharacter": outcome == "needs_repair",
            },
            scene_frames=[48, 144],
            group_scene_ids=[["scene-1", "scene-2"]],
            requires_character=outcome == "needs_repair",
            expected_outcome=outcome,
        )
        for outcome in ("passed", "needs_repair", "blocked")
    ]
    protocol = Protocol(
        protocol_id="self-authored-development-v1",
        status="development",
        variants={"internal-grouped": "Offline shared-group workflow fixture"},
    )
    captures = []
    for case in cases:
        blocked = case.expected_outcome == "blocked"
        passed = case.expected_outcome == "passed"
        artifact_id = "pass-output" if passed else "repair-output"
        output = next(item for item in artifacts if item.artifact_id == artifact_id)
        captures.append(
            Capture(
                run_id=f"fixture-{case.case_id}",
                case_id=case.case_id,
                variant_id="internal-grouped",
                mode="fixture",
                provenance_schema="smart_remake_provenance_v1",
                outcome="blocked" if blocked else "accepted" if passed else "needs_repair",
                code_version=sha256_bytes(Path(__file__).read_bytes()),
                config_version="dev-v1",
                prompt_versions={"fixture": "no-model-prompt"},
                model_versions={"fixture": "no-provider-called"},
                output_artifact_id=None if blocked else artifact_id,
                media_hash=None if blocked else output.sha256,
                assembly_id=None if blocked else f"fixture-assembly-{case.case_id}",
                manifest_hash=None if blocked else canonical_hash(case.model_dump(mode="json")),
                constraints_hash=None if blocked else canonical_hash(case.requirement_ids),
                attempts=[]
                if blocked
                else [
                    Attempt(
                        attempt_id=f"fixture-attempt-{case.case_id}",
                        stage="compose",
                        purpose="initial",
                        status="completed",
                        request_hash=canonical_hash([case.case_id, "fixture"]),
                        provider="fixture",
                        cost_status="actual",
                        cost_usd="0",
                    )
                ],
                checker_labels={} if blocked else {"product": "passed" if passed else "failed"},
                failures=["RIGHTS_DECLARATION_MISSING"] if blocked else [],
            )
        )
    bundle = EvidenceBundle(
        bundle_id="self-authored-development-v1",
        mode="fixture",
        protocol=protocol,
        cases=cases,
        artifacts=artifacts,
        captures=captures,
        notes=[
            "Synthetic fixture expectations only; no semantic model or human scores measured.",
            "No approved live input or spend cap is supplied by this corpus.",
            "Media is a static authored product showcase; motion quality is unmeasured.",
        ],
    )
    (root / "bundle.json").write_text(
        json.dumps(bundle.model_dump(mode="json"), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return bundle


def build_pilot_inputs(root: Path) -> EvidenceBundle:
    """Prepare fresh authored inputs and conditional pilot scope, with no model outputs."""
    root.mkdir(parents=True, exist_ok=True)
    assets = root / "artifacts"
    assets.mkdir(exist_ok=False)
    _draw_product(assets / "product.png")
    _draw_product(assets / "illustrated-character.png", character=True)
    _make_clip(assets / "product.png", assets / "source-product.mp4", 16)
    _make_clip(assets / "illustrated-character.png", assets / "source-character.mp4", 16)
    _write_tone(assets / "authored-tone.wav", duration=16)
    rights = Rights(
        basis="self_authored",
        declared=True,
        provider_use_allowed=True,
        scope="Internal Smart Remake AI-provider pilot only, after explicit user spend cap "
        "and provider disclosure acknowledgement; no publishing or advertising grant.",
        evidence_note="Fresh original Pillow primitives, FFmpeg static showcase and mathematical "
        "sine audio generated by this repository. The illustrated character "
        "represents no real person. No third-party demo assets or likeness are used.",
    )
    entries = [
        ("source-product", "source", "source-product.mp4", "video/mp4", 384),
        ("source-character", "source", "source-character.mp4", "video/mp4", 384),
        ("product", "product", "product.png", "image/png", None),
        ("character", "character", "illustrated-character.png", "image/png", None),
        ("audio", "audio", "authored-tone.wav", "audio/wav", None),
    ]
    artifacts = [
        Artifact.model_validate(
            {
                "artifact_id": key,
                "role": role,
                "path": f"artifacts/{filename}",
                "sha256": sha256_bytes((assets / filename).read_bytes()),
                "mime_type": mime,
                "frame_count": frames,
                "rights": rights,
                "width": None if role == "audio" else 180,
                "height": None if role == "audio" else 320,
            }
        )
        for key, role, filename, mime, frames in entries
    ]
    cases = [
        CaseManifest(
            case_id=f"pilot-{'illustrated-character' if character else 'product'}",
            split="development",
            target_frames=384 if character else 192,
            input_artifact_ids=[
                "source-character" if character else "source-product",
                "product",
                "audio",
                *(["character"] if character else []),
            ],
            requirement_ids=[
                "technical",
                "product",
                "action",
                "structure",
                "claims",
                "continuity",
                *(["character"] if character else []),
            ],
            requirements={
                "intent": "Steady showcase of the blue bottle with the amber cap",
                "keep": [],
                "replace": [],
                "forbid": [],
                "claims": [],
                "requiresCharacter": character,
            },
            scene_frames=[72, 120, 96, 96] if character else [48, 144],
            group_scene_ids=[["scene-1", "scene-2"], ["scene-3", "scene-4"]]
            if character
            else [["scene-1", "scene-2"]],
            requires_character=character,
            real_person=False,
        )
        for character in (False, True)
    ]
    bundle = EvidenceBundle(
        bundle_id="self-authored-pilot-inputs-v1",
        mode="live",
        protocol=Protocol(
            protocol_id="internal-pilot-inputs-v1",
            status="development",
            variants={"internal-grouped": "Current grouped pipeline, pending pilot"},
        ),
        cases=cases,
        artifacts=artifacts,
        pilot_preparation=PilotPreparation(),
        notes=[
            "INPUT ONLY. Mode live is intended future execution, with zero captures or calls.",
            "No generated outputs, receipts, quality scores or real-person consent are claimed.",
            "Explicit user-approved spend cap and provider disclosure remain pending.",
            "Static authored showcases do not validate difficult hand motion or occlusion.",
        ],
    )
    (root / "bundle.json").write_text(
        json.dumps(bundle.model_dump(mode="json"), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return bundle
