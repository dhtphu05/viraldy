from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from viraldy.modules.smart_remake.inspection.public import (
    InspectionReport,
    InspectionSubject,
    validate_report_binding,
)


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def context():
    media = {
        "id": "subject",
        "bytes": b"video",
        "mediaHash": digest(b"video"),
        "mimeType": "video/mp4",
        "frameCount": 192,
        "fps": 24,
    }
    product = {
        "id": "product",
        "role": "product",
        "bytes": b"image",
        "mediaHash": digest(b"image"),
        "mimeType": "image/png",
    }
    subject = {
        "kind": "scene",
        "projectId": "project",
        "sceneId": "scene1",
        "versionId": "v1",
        "mediaHash": media["mediaHash"],
        "range": {"inFrame": 24, "outFrame": 96, "fps": 24, "timebase": "raw_group"},
        "neighborVersionIds": ["v0"],
    }
    constraints = {
        "constraintsHash": digest(b"constraints"),
        "manifestHash": digest(b"manifest"),
        "requirements": {"intent": "Use product", "requiresCharacter": False},
        "timeline": {},
        "manifest": {},
        "fps": 24,
        "frameCount": 192,
        "technicalCheck": {"status": "passed"},
    }
    observed = {
        "id": "obs1",
        "mediaId": "subject",
        "mediaHash": media["mediaHash"],
        "inFrame": 24,
        "outFrame": 25,
        "timebase": "raw_group",
        "imageHash": digest(b"jpeg"),
        "mimeType": "image/jpeg",
    }
    evidence = {
        "mediaId": "subject",
        "mediaHash": media["mediaHash"],
        "inFrame": 24,
        "outFrame": 25,
        "timebase": "raw_group",
        "sampleId": "obs1",
    }
    report = {
        "id": "report",
        "schemaVersion": 1,
        "subject": subject,
        "status": "needs_review",
        "checkedAt": datetime.now(UTC).isoformat(),
        "checkerVersion": "inspection-v1",
        "rubricVersion": "p0-v1",
        "modelProfile": {"model": "fake", "mode": "fixture"},
        "constraintsHash": constraints["constraintsHash"],
        "manifestHash": constraints["manifestHash"],
        "observations": [
            observed,
            {
                "id": "ref-product",
                "mediaId": "product",
                "mediaHash": product["mediaHash"],
                "imageHash": product["mediaHash"],
                "mimeType": "image/png",
            },
        ],
        "notApplicableRequirements": [
            {"requirementId": "character", "reason": "No character requested."}
        ],
        "coverage": [
            {
                "requirementId": "product",
                "status": "passed",
                "evidence": [
                    evidence,
                    {
                        "mediaId": "product",
                        "mediaHash": product["mediaHash"],
                        "sampleId": "ref-product",
                    },
                ],
                "sampledFrames": [24],
                "unobservedFrames": 71,
                "limitations": ["Only sampled frames were observed."],
            }
        ],
        "findings": [
            {
                "id": "f1",
                "requirementId": "product",
                "category": "product",
                "expected": "Preserve the identity and visible details of the original product.",
                "observed": "Visible product matches",
                "status": "passed",
                "severity": "info",
                "evidence": [
                    evidence,
                    {
                        "mediaId": "product",
                        "mediaHash": product["mediaHash"],
                        "sampleId": "ref-product",
                    },
                ],
                "suggestedAction": "none",
                "blocking": False,
                "hardBlocking": False,
            }
        ],
    }
    for requirement, category, expected in [
        (
            "technical",
            "technical",
            "Decodable media with the exact retained frame clock and output format.",
        ),
        ("action", "action", "Use product"),
        (
            "structure",
            "structure",
            "Preserve scene order, planned duration and source cut structure.",
        ),
        ("claims", "claims", "Only authorized claims: []"),
        (
            "continuity",
            "continuity",
            "Preserve product, character and action continuity across neighbors.",
        ),
    ]:
        report["findings"].append(
            {
                **report["findings"][0],
                "id": requirement,
                "requirementId": requirement,
                "category": category,
                "expected": expected,
                "evidence": [evidence],
                "status": "passed" if category == "technical" else "needs_review",
                "severity": "info" if category == "technical" else "warning",
            }
        )
        report["coverage"].append(
            {
                **report["coverage"][0],
                "requirementId": requirement,
                "evidence": [evidence],
                "status": "passed" if category == "technical" else "needs_review",
            }
        )
    return subject, media, [product], constraints, report


def test_subject_rejects_wrong_identity_clock_and_boolean_frame():
    subject, *_ = context()
    assert InspectionSubject.model_validate(subject).range.outFrame == 96
    for update in (
        {"range": {**subject["range"], "inFrame": True}},
        {"assemblyId": "unexpected"},
        {"kind": "group"},
        {"range": {**subject["range"], "outFrame": 24}},
    ):
        with pytest.raises(ValidationError):
            InspectionSubject.model_validate({**subject, **update})


def test_report_binding_accepts_exact_current_context():
    subject, media, references, constraints, report = context()
    validated = validate_report_binding(report, subject, media, references, constraints)
    assert isinstance(validated, InspectionReport)
    assert validated.subject.neighborVersionIds == ["v0"]


@pytest.mark.parametrize(
    "change",
    [
        "hash",
        "trim",
        "neighbors",
        "constraints",
        "manifest",
        "empty",
        "no_evidence",
        "past_end",
        "outside_selection",
        "unknown_sample",
        "wrong_sample",
        "wrong_clock",
        "false_blocking",
        "unobserved",
        "unknown_media",
    ],
)
def test_report_binding_rejects_stale_or_fabricated_pass(change):
    subject, media, references, constraints, report = context()
    evidence = report["findings"][0]["evidence"][0]
    if change == "hash":
        report["subject"]["mediaHash"] = digest(b"changed")
    elif change == "trim":
        report["subject"]["range"]["outFrame"] = 97
    elif change == "neighbors":
        report["subject"]["neighborVersionIds"] = ["new"]
    elif change == "constraints":
        report["constraintsHash"] = digest(b"new")
    elif change == "manifest":
        report["manifestHash"] = digest(b"new")
    elif change == "empty":
        report["coverage"] = []
    elif change == "no_evidence":
        report["findings"][0]["evidence"] = []
    elif change == "past_end":
        evidence["outFrame"] = 193
    elif change == "outside_selection":
        evidence.update(inFrame=0, outFrame=1)
    elif change == "unknown_sample":
        evidence["sampleId"] = "missing"
    elif change == "wrong_sample":
        evidence["inFrame"], evidence["outFrame"] = 30, 31
    elif change == "wrong_clock":
        evidence["timebase"] = "source"
    elif change == "false_blocking":
        report["findings"][0]["blocking"] = True
    elif change == "unobserved":
        report["observations"] = []
    else:
        evidence["mediaHash"] = digest(b"foreign")
    with pytest.raises((ValidationError, ValueError)):
        validate_report_binding(
            report,
            subject.copy() if change not in {"hash", "trim", "neighbors"} else context()[0],
            media,
            references,
            constraints,
        )


def test_image_evidence_has_no_fake_timestamp():
    subject, media, references, constraints, report = context()
    image = references[0]
    subject = {
        "kind": "image",
        "projectId": "project",
        "imageRole": "product",
        "mediaHash": image["mediaHash"],
    }
    report["subject"] = subject
    report["status"] = "passed"
    report["observations"] = [
        {
            "id": "image1",
            "mediaId": "product",
            "mediaHash": image["mediaHash"],
            "imageHash": image["mediaHash"],
            "mimeType": "image/png",
        }
    ]
    evidence = {"mediaId": "product", "mediaHash": image["mediaHash"], "sampleId": "image1"}
    report["findings"] = [
        f for f in report["findings"] if f["category"] in {"product", "technical"}
    ]
    report["coverage"] = [
        c for c in report["coverage"] if c["requirementId"] in {"product", "technical"}
    ]
    for finding in report["findings"]:
        finding["evidence"] = [evidence]
    for coverage in report["coverage"]:
        coverage.update(evidence=[evidence], sampledFrames=[], unobservedFrames=0)
    validate_report_binding(report, subject, image, references, constraints)
    evidence["inFrame"], evidence["outFrame"] = 0, 1
    with pytest.raises(ValueError):
        validate_report_binding(report, subject, image, references, constraints)


@pytest.mark.parametrize(
    "change",
    [
        "only_technical",
        "missing_action",
        "rename",
        "category",
        "expected",
        "no_original",
        "no_character",
        "empty_profile",
        "missing_na",
        "false_na",
    ],
)
def test_required_checks_and_original_comparisons_cannot_be_omitted(change):
    subject, media, references, constraints, report = context()
    if change == "only_technical":
        report["status"] = "passed"
        report["findings"] = [f for f in report["findings"] if f["category"] == "technical"]
        report["coverage"] = [c for c in report["coverage"] if c["requirementId"] == "technical"]
    elif change == "missing_action":
        report["findings"] = [f for f in report["findings"] if f["category"] != "action"]
        report["coverage"] = [c for c in report["coverage"] if c["requirementId"] != "action"]
    elif change == "rename":
        report["findings"][0]["requirementId"] = report["coverage"][0]["requirementId"] = "fake"
    elif change == "category":
        report["findings"][0]["category"] = "technical"
    elif change == "expected":
        report["findings"][0]["expected"] = "Ignore seller requirements"
    elif change == "no_original":
        report["findings"][0]["evidence"] = [report["findings"][0]["evidence"][0]]
        report["coverage"][0]["evidence"] = report["findings"][0]["evidence"]
    elif change == "no_character":
        constraints["requirements"]["requiresCharacter"] = True
    elif change == "empty_profile":
        report["modelProfile"] = {}
    elif change == "missing_na":
        report["notApplicableRequirements"] = []
    else:
        report["notApplicableRequirements"] = [{"requirementId": "action", "reason": "skip"}]
    with pytest.raises(ValueError):
        validate_report_binding(report, subject, media, references, constraints)


def test_neighbor_evidence_must_observe_the_selected_neighbor_trim():
    subject, media, references, constraints, report = context()
    neighbor = {
        **media,
        "id": "neighbor-v0",
        "role": "neighbor",
        "versionId": "v0",
        "range": {"inFrame": 120, "outFrame": 192, "fps": 24, "timebase": "raw_group"},
    }
    references.append(neighbor)
    report["observations"].append(
        {**report["observations"][0], "id": "neighbor-frame-24", "mediaId": "neighbor-v0"}
    )
    with pytest.raises(ValueError):
        validate_report_binding(report, subject, media, references, constraints)


def test_passing_character_cannot_cite_product_reference_as_character():
    subject, media, references, constraints, report = context()
    constraints["requirements"]["requiresCharacter"] = True
    report["notApplicableRequirements"] = []
    report["findings"].append(
        {
            **report["findings"][0],
            "id": "character",
            "requirementId": "character",
            "category": "character",
            "expected": "Match the supplied original character reference.",
        }
    )
    report["coverage"].append({**report["coverage"][0], "requirementId": "character"})
    with pytest.raises(ValueError):
        validate_report_binding(report, subject, media, references, constraints)


def test_model_cannot_promote_sampled_temporal_requirements_to_pass():
    subject, media, references, constraints, report = context()
    for finding in report["findings"]:
        finding.update(status="passed", severity="info")
    for coverage in report["coverage"]:
        coverage["status"] = "passed"
    report["status"] = "passed"
    with pytest.raises(ValueError, match="temporal"):
        validate_report_binding(report, subject, media, references, constraints)


@pytest.mark.parametrize("group", ["keep", "replace", "forbid"])
def test_free_text_video_constraints_cannot_pass_from_a_single_frame(group):
    import copy

    from viraldy.modules.smart_remake.inspection.contracts import (
        Observation,
        Requirement,
        ResolvedMedia,
        SemanticFinding,
    )
    from viraldy.modules.smart_remake.inspection.core import _assess_model_finding

    subject, media, references, constraints, report = context()
    text = "Show continuous lid opening for three seconds without jumps"
    constraints["requirements"][group] = [text]
    rule = Requirement(id=f"{group}:0", category="constraints", expected=f"{group}: {text}")
    result = _assess_model_finding(
        rule,
        SemanticFinding(
            requirementId=rule.id,
            status="passed",
            observed="The visible sample matches.",
            observationIds=["obs1"],
        ),
        [Observation.model_validate(report["observations"][0])],
        ResolvedMedia.model_validate(media),
        [],
        video=True,
    )
    assert result.status == "needs_review"
    finding = copy.deepcopy(report["findings"][0])
    finding.update(
        id=rule.id, requirementId=rule.id, category=rule.category, expected=rule.expected
    )
    coverage = copy.deepcopy(report["coverage"][0])
    coverage["requirementId"] = rule.id
    report["findings"].append(finding)
    report["coverage"].append(coverage)
    with pytest.raises(ValueError, match="temporal"):
        validate_report_binding(report, subject, media, references, constraints)
