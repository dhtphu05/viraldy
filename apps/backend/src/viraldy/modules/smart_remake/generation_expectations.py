"""Canonical, private-free generation and inspection requirements from owned server data."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from viraldy.shared.errors.base import AppError

EXPECTATIONS_VERSION: Literal["smart-remake-generation-expectations-v1"] = (
    "smart-remake-generation-expectations-v1"
)
OPENING_EXTRACTOR_VERSION = "source-opening-frame-v1"
HASH_PATTERN = r"^[a-f0-9]{64}$"
PRODUCT_FIELDS = (
    "mode",
    "productName",
    "productType",
    "visualIdentity",
    "productUsage",
    "mustPreserve",
    "canChange",
    "forbiddenErrors",
)
SOURCE_FIELDS = ("cameraStyle", "subjectPresence", "setting", "audioPlan", "visualStructure")


class FrozenExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ReferenceExpectation(FrozenExpectation):
    mediaHash: str = Field(pattern=HASH_PATTERN)


class SourceRangeExpectation(FrozenExpectation):
    startFrame: int = Field(ge=0)
    endFrame: int = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.endFrame <= self.startFrame:
            raise ValueError("Source range must have positive duration.")
        return self


class OpeningFrameExpectation(FrozenExpectation):
    sourceMediaHash: str = Field(pattern=HASH_PATTERN)
    frame: int = Field(ge=0)
    layoutHash: str | None = Field(default=None, pattern=HASH_PATTERN)
    extractorVersion: str = Field(min_length=1)


class ClipSelectionExpectation(FrozenExpectation):
    versionId: str = Field(min_length=1)
    inFrame: int = Field(ge=0, lt=192)
    outFrame: int = Field(gt=0, le=192)
    timebase: Literal["raw_group"] = "raw_group"

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.outFrame <= self.inFrame:
            raise ValueError("Selected range must have positive duration.")
        return self


class SceneExpectation(FrozenExpectation):
    renderUnitId: str = Field(min_length=1)
    sourceSceneId: str = Field(min_length=1)
    sceneIndex: int = Field(ge=0)
    sourceRange: SourceRangeExpectation
    openingFrame: OpeningFrameExpectation
    shotPlan: dict[str, Any]
    sourceSegment: dict[str, Any]
    prompt: str = Field(min_length=1)
    imagePrompt: str = Field(min_length=1)
    videoPrompt: str = Field(min_length=1)
    userEdits: str = ""
    selection: ClipSelectionExpectation | None = None

    @model_validator(mode="after")
    def opening_matches_source(self) -> Self:
        if self.openingFrame.frame != self.sourceRange.startFrame:
            raise ValueError("Opening must use the first absolute source frame.")
        return self


class GenerationExpectations(FrozenExpectation):
    schemaVersion: Literal[1] = 1
    version: Literal["smart-remake-generation-expectations-v1"] = EXPECTATIONS_VERSION
    fps: Literal[24] = 24
    productLock: dict[str, Any]
    requirements: dict[str, Any]
    requirementsHash: str = Field(pattern=HASH_PATTERN)
    references: dict[Literal["source", "product", "character"], ReferenceExpectation]
    sourceContext: dict[str, Any]
    scenes: list[SceneExpectation] = Field(min_length=1)

    @model_validator(mode="after")
    def bindings(self) -> Self:
        if set(self.productLock) - set(PRODUCT_FIELDS) or set(self.sourceContext) - set(
            SOURCE_FIELDS
        ):
            raise ValueError("Only canonical product and source fields are permitted.")
        if _safe_json(self.model_dump(mode="json")) != self.model_dump(mode="json"):
            raise ValueError("Private locator keys do not belong in generation expectations.")
        if not {"source", "product"} <= self.references.keys():
            raise ValueError("Source and product references are required.")
        if len({scene.renderUnitId for scene in self.scenes}) != len(self.scenes):
            raise ValueError("Render unit IDs must be unique.")
        previous_ranges: dict[str, SourceRangeExpectation] = {}
        for scene in self.scenes:
            previous = previous_ranges.get(scene.sourceSceneId)
            if previous is not None and scene.sourceRange.startFrame < previous.endFrame:
                raise ValueError("Fragments of a source scene must be ordered and nonoverlapping.")
            previous_ranges[scene.sourceSceneId] = scene.sourceRange
            if scene.openingFrame.sourceMediaHash != self.references["source"].mediaHash:
                raise ValueError("Opening reference is bound to another source.")
        validate_product_lock(self.productLock)
        return self


def _required() -> AppError:
    return AppError(
        "SMART_REMAKE_EXPECTATIONS_REQUIRED",
        "Update the source analysis and scene plan before generating new media.",
        409,
    )


def validate_product_lock(product_lock: Any) -> dict[str, Any]:
    """A product title alone is not evidence that visual analysis succeeded."""
    lock = product_lock if isinstance(product_lock, dict) else {}
    visual = lock.get("visualIdentity") or {}
    unknown = {"", "unknown", "not visible", "unobserved", "unspecified", "n/a", "none"}
    observed = (
        [
            *(visual.get("colors") or []),
            visual.get("shape"),
            visual.get("material"),
            visual.get("texture"),
            visual.get("pattern"),
            visual.get("visibleBranding"),
        ]
        if isinstance(visual, dict)
        else []
    )
    if not any(
        isinstance(value, str) and value.strip().lower() not in unknown for value in observed
    ):
        raise AppError(
            "SMART_REMAKE_PRODUCT_ANALYSIS_INCOMPLETE",
            "The product image has no usable observed identity details. Update its analysis.",
            409,
        )
    return copy.deepcopy(lock)


def expectations_hash(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()


def validate_generation_expectations(
    value: Any, expected_hash: str | None = None
) -> dict[str, Any]:
    try:
        saved = GenerationExpectations.model_validate(value).model_dump(mode="json")
        if expected_hash is not None and expectations_hash(saved) != expected_hash:
            raise _required()
        return saved
    except (ValidationError, TypeError, ValueError, AppError):
        raise _required() from None


def _safe_json(value: Any) -> Any:
    """Only descriptive data belongs in a model/QA contract, never private media locators."""
    if isinstance(value, dict):
        return {
            key: _safe_json(item)
            for key, item in value.items()
            if not any(token in key.lower() for token in ("url", "storagekey", "apikey", "token"))
            and key != "forbiddenReuse"
        }
    if isinstance(value, list):
        return [_safe_json(item) for item in value]
    return copy.deepcopy(value)


def build_generation_expectations(
    context: dict[str, Any],
    *,
    scenes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build only from the frozen owned context; never mutate or call an AI provider."""
    # The legacy engine package eagerly imports its compiler, which itself uses
    # product validation. Keep the pure contract import independent of that graph.
    from .engine.prompt_edits import scene_edit_directions
    from .engine.prompt_sanitizer import (
        sanitize_generation_requirements,
        sanitize_generation_scene,
        validate_generation_payload,
    )

    product_lock = validate_product_lock(context.get("productLock"))
    analysis = context.get("referenceAnalysis") or {}
    lock = _safe_json({key: product_lock[key] for key in PRODUCT_FIELDS if key in product_lock})
    p0 = context.get("p0") or {}
    assets = p0.get("assets") or {}
    references = {
        role: {"mediaHash": asset.get("mediaHash")}
        for role, asset in assets.items()
        if role in {"source", "product", "character"}
    }
    for role in ("source", "product"):
        references.setdefault(role, {"mediaHash": context.get(f"{role}MediaHash")})
    units = (context.get("renderPlan") or {}).get("units") or []
    sources = {
        source["id"]: source for source in (context.get("sourceSceneMap") or {}).get("scenes", [])
    }
    compiled = scenes if scenes is not None else (context.get("sceneMap") or {}).get("scenes", [])
    if not units or len(units) != len(compiled):
        raise _required()
    fitted = (context.get("sourceSceneMap") or {}).get("timingMode") == "fit_target"
    if fitted:
        _validate_fragment_ranges(units, sources)
    canonical = []
    for index, (unit, scene) in enumerate(zip(units, compiled, strict=True)):
        source_id = unit.get("sourceSceneId")
        source = sources.get(source_id)
        if source is None:
            raise _required()
        clean = sanitize_generation_scene(scene, analysis, product_lock)
        validate_generation_payload(clean, analysis, product_lock)
        start = unit["sourceStartFrame"] if fitted else source["startFrame"]
        end = unit["sourceEndFrame"] if fitted else source["endFrame"]
        opening = (context.get("sourceOpeningFrames") or {}).get(
            unit["id"] if fitted else source_id
        ) or {}
        if fitted and not opening.get("layoutHash"):
            raise _required()
        canonical.append(
            {
                "renderUnitId": unit["id"],
                "sourceSceneId": source_id,
                "sceneIndex": index,
                "sourceRange": {"startFrame": start, "endFrame": end},
                "openingFrame": {
                    "sourceMediaHash": opening.get("sourceMediaHash", opening.get("sourceHash"))
                    or references["source"]["mediaHash"],
                    "frame": opening.get(
                        "frame", opening.get("absoluteFrame", start)
                    ),
                    "layoutHash": opening.get("layoutHash"),
                    "extractorVersion": opening.get("extractorVersion", OPENING_EXTRACTOR_VERSION),
                },
                "shotPlan": _safe_json(clean.get("shotPlan") or {}),
                "sourceSegment": _safe_json(clean.get("sourceSegment") or {}),
                **{key: clean.get(key, "") for key in ("prompt", "imagePrompt", "videoPrompt")},
                "userEdits": scene_edit_directions(clean),
            }
        )
    source_context = sanitize_generation_scene(
        {key: analysis[key] for key in SOURCE_FIELDS if key in analysis},
        analysis,
        product_lock,
    )
    value = {
        "schemaVersion": 1,
        "version": EXPECTATIONS_VERSION,
        "fps": 24,
        "productLock": lock,
        "requirements": _safe_json(
            sanitize_generation_requirements(
                p0.get("requirements") or {},
                analysis,
                product_lock,
            )
        ),
        "requirementsHash": expectations_hash(p0.get("requirements") or {}),
        "references": references,
        "sourceContext": _safe_json(source_context),
        "scenes": canonical,
    }
    validate_generation_payload(value, analysis, product_lock)
    return validate_generation_expectations(value)


def _validate_fragment_ranges(units: list[dict[str, Any]], sources: dict[str, Any]) -> None:
    """Keep logical source evidence complete while provider fragments use their own clock."""
    cursors = {source_id: source["startFrame"] for source_id, source in sources.items()}
    for unit in units:
        source_id = unit.get("sourceSceneId")
        if not isinstance(source_id, str):
            raise _required()
        source = sources.get(source_id)
        start, end = unit.get("sourceStartFrame"), unit.get("sourceEndFrame")
        if (
            source is None
            or type(start) is not int
            or type(end) is not int
            or start != cursors[source_id]
            or not source["startFrame"] <= start < end <= source["endFrame"]
        ):
            raise _required()
        cursors[source_id] = end
    if any(cursors[source_id] != source["endFrame"] for source_id, source in sources.items()):
        raise _required()


def require_generation_expectations(context: dict[str, Any]) -> dict[str, Any]:
    """New work requires a current snapshot; historical context is never silently upgraded."""
    if (
        context.get("expectationsStale")
        or not context.get("generationExpectations")
        or not context.get("expectationsHash")
    ):
        raise _required()
    saved = validate_generation_expectations(
        context["generationExpectations"],
        context["expectationsHash"],
    )
    if any(not scene["openingFrame"]["layoutHash"] for scene in saved["scenes"]):
        raise _required()
    if expectations_hash(build_generation_expectations(context)) != context["expectationsHash"]:
        raise _required()
    return saved


def expectations_scene(snapshot: Any, render_unit_id: str) -> dict[str, Any]:
    value = validate_generation_expectations(snapshot)
    for scene in value["scenes"]:
        if scene["renderUnitId"] == render_unit_id:
            return copy.deepcopy(scene)
    raise _required()
