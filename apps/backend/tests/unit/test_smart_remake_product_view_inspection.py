# ruff: noqa: F811 -- pytest resolves the shared offline video fixture.
"""All product angles stay ordered, distinct, observed evidence for Inspector."""

from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest
from test_smart_remake_inspection_runtime import inputs, passing_model, video  # noqa: F401
from test_smart_remake_lifecycle_inspections import setup  # noqa: F401

from tests.smart_remake_expectations import install_expectations
from tests.unit.test_smart_remake_inspection_expectations import canonical
from viraldy.modules.smart_remake.conditioning_inspection import _snapshot as conditioning_snapshot
from viraldy.modules.smart_remake.generation_expectations import (
    expectations_hash,
    validate_generation_expectations,
)
from viraldy.modules.smart_remake.inspection.expectations import validate_expectation_references
from viraldy.modules.smart_remake.inspection.public import inspect_subject, validate_report_binding
from viraldy.modules.smart_remake.inspection_service import _snapshot as inspection_snapshot
from viraldy.shared.errors.base import AppError


def reference_namespace(hashes=("a" * 64, "b" * 64), *, declared=True):
    product_refs = [
        SimpleNamespace(id=f"product-{i}", role="product", mediaHash=value)
        for i, value in enumerate(hashes)
    ]
    refs = [
        *product_refs,
        SimpleNamespace(id="source", role="source", mediaHash="c" * 64, frameCount=192),
    ]
    expectation = SimpleNamespace(
        references={
            "product": SimpleNamespace(mediaHash="a" * 64),
            "source": SimpleNamespace(mediaHash="c" * 64),
        },
        scenes=[],
        productReferenceHashes=["a" * 64, "b" * 64] if declared else None,
    )
    return (
        SimpleNamespace(role="conditioning", id="output"),
        refs,
        SimpleNamespace(expectations=expectation),
    )


def test_all_angles_bind_primary_first_without_last_role_overwriting_primary():
    media, refs, constraints = reference_namespace()
    validate_expectation_references(media, refs, constraints)


@pytest.mark.parametrize("hashes", [("a" * 64,), ("b" * 64, "a" * 64), ("a" * 64, "d" * 64)])
def test_missing_reordered_or_changed_angle_cannot_bind_old_expectations(hashes):
    media, refs, constraints = reference_namespace(hashes)
    with pytest.raises(ValueError, match="references"):
        validate_expectation_references(media, refs, constraints)


def test_legacy_single_reference_stays_single_and_does_not_silently_upgrade():
    media, refs, constraints = reference_namespace(("a" * 64,), declared=False)
    validate_expectation_references(media, refs, constraints)
    refs.insert(1, SimpleNamespace(id="extra", role="product", mediaHash="b" * 64))
    with pytest.raises(ValueError, match="references"):
        validate_expectation_references(media, refs, constraints)


def test_product_view_ids_must_be_unique_even_with_different_hashes():
    media, refs, constraints = reference_namespace()
    refs[1].id = refs[0].id
    with pytest.raises(ValueError, match="references"):
        validate_expectation_references(media, refs, constraints)


def multiview_inputs(video):
    from tests.unit.test_smart_remake_image_workflow import image

    subject, media, refs, constraints = inputs(video)
    secondary = image((90, 160), "blue")
    references = [
        refs[0],
        {
            **refs[0],
            "id": "product-reference-2",
            "bytes": secondary,
            "mediaHash": hashlib.sha256(secondary).hexdigest(),
        },
        *refs[1:],
    ]
    value = canonical(subject, refs, constraints["requirements"])
    value["productReferenceHashes"] = [
        item["mediaHash"] for item in references if item.get("role") == "product"
    ]
    value = validate_generation_expectations(value)
    constraints.update(expectations=value, expectationsHash=expectations_hash(value))
    return subject, media, references, constraints


@pytest.mark.asyncio
async def test_checker_receives_all_angles_with_separate_observation_bindings(video):
    subject, media, refs, constraints = multiview_inputs(video)
    seen = []

    async def model(request):
        seen.append(request)
        return await passing_model(request)

    report = await inspect_subject(subject, media, refs, constraints, model)
    assert seen
    product_observations = [
        o for o in report.observations if o.mediaId in {"product", "product-reference-2"}
    ]
    assert {o.mediaId for o in product_observations} == {"product", "product-reference-2"}
    assert next(f for f in report.findings if f.requirementId == "product").status == "passed"
    assert report.expectationsHash == constraints["expectationsHash"]


@pytest.mark.asyncio
async def test_product_pass_cannot_ignore_a_supplied_angle(video):
    subject, media, refs, constraints = multiview_inputs(video)

    async def partial(request):
        output = await passing_model(request)
        for finding in output["output"]["findings"]:
            if finding["requirementId"] == "product":
                finding["observationIds"] = [
                    identifier
                    for identifier in finding["observationIds"]
                    if identifier != "ref-product-reference-2"
                ]
        return output

    report = await inspect_subject(subject, media, refs, constraints, partial)
    assert next(f for f in report.findings if f.requirementId == "product").status != "passed"


@pytest.mark.asyncio
async def test_a_forged_passing_report_cannot_omit_the_second_product_angle(video):
    subject, media, refs, constraints = multiview_inputs(video)
    report = await inspect_subject(subject, media, refs, constraints, passing_model)
    forged = report.model_dump(mode="json")
    for item in forged["findings"]:
        if item["requirementId"] == "product":
            item["evidence"] = [
                e for e in item["evidence"] if e["mediaId"] != "product-reference-2"
            ]
    with pytest.raises(ValueError, match="product"):
        validate_report_binding(forged, subject, media, refs, constraints)


@pytest.mark.asyncio
async def test_conditioning_opening_pass_requires_each_product_view(video):
    subject, _, refs, constraints = multiview_inputs(video)
    media = {**refs[0], "id": "generated", "role": "conditioning"}
    subject = {
        "kind": "image",
        "projectId": "p1",
        "imageRole": "conditioning",
        "mediaHash": media["mediaHash"],
    }
    constraints["sceneIds"] = ["s1"]

    async def partial(request):
        output = await passing_model(request)
        for finding in output["output"]["findings"]:
            finding["observationIds"] = [
                identifier
                for identifier in finding["observationIds"]
                if identifier != "ref-product-reference-2"
            ]
        return output

    report = await inspect_subject(subject, media, refs, constraints, partial)
    assert (
        next(f for f in report.findings if f.requirementId == "scene:s1:opening").status != "passed"
    )


@pytest.mark.parametrize("kind", ["inspection", "conditioning"])
def test_server_snapshots_keep_distinct_views_and_reject_changed_supporting_image(setup, kind):
    _, row, _, request, _ = setup
    primary = row.context_json["p0"]["assets"]["product"]
    row.context_json["p0"]["additionalProductReferences"] = [
        {
            **primary,
            "id": "extra",
            "storageKey": primary["storageKey"] + "-extra",
            "mediaHash": "b" * 64,
            "role": "product",
        }
    ]
    value = install_expectations(row.context_json, state=row.state_json)
    scene = value["scenes"][0]
    binding = {
        "imageSceneId": scene["renderUnitId"],
        "expectations": value,
        "expectationsHash": row.context_json["expectationsHash"],
    }
    generated = {
        "renderUnitId": scene["renderUnitId"],
        "sourceSceneId": scene["sourceSceneId"],
        "openingFrame": scene["openingFrame"],
        "expectationsHash": binding["expectationsHash"],
        "mediaHash": "d" * 64,
    }

    def snapshot():
        if kind == "conditioning":
            return conditioning_snapshot(row, generated, binding)
        return inspection_snapshot(row, request.subject, row.workspace_id)

    references = snapshot()["references"]
    assert references["product"]["mediaHash"] == primary["mediaHash"]
    assert references["product-reference-2"]["mediaHash"] == "b" * 64
    assert references["product-reference-2"]["role"] == "product"
    row.context_json["p0"]["additionalProductReferences"][0]["mediaHash"] = "c" * 64
    with pytest.raises(AppError):
        snapshot()
