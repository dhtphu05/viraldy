from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from viraldy.modules.domain_intelligence.golden import (
    FixtureArtifactMissingError,
    golden_case_to_review_input,
    load_golden_cases,
    load_semantic_regression_cases,
)
from viraldy.modules.domain_intelligence.importer import validate_policy_pack
from viraldy.modules.domain_intelligence.public import (
    EvaluationCandidate,
    NormalizedEvidence,
    NormalizedEvidenceBundle,
    UGCReviewContext,
    evaluate_review,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "domain_intelligence"
RESOURCE_DIR = ROOT / "resources" / "domain_intelligence" / "v1"
SEMANTIC_CASES = load_semantic_regression_cases(
    FIXTURE_DIR / "semantic_regression_tests_v1.jsonl"
)


@pytest.mark.parametrize(
    "case_id",
    ["GC-TTS-DEMO-001", "GC-POD-PERS-001", "GC-DROP-DEMO-001"],
)
def test_all_golden_cases_map_to_recommendation_first_contract(case_id: str) -> None:
    cases = {case.case_id: case for case in load_golden_cases(FIXTURE_DIR / "GoldenCasesV1.json")}
    validated = validate_policy_pack(
        RESOURCE_DIR / "DomainExpertPolicyPackV1.json",
        RESOURCE_DIR / "DomainExpertPolicyPackV1.schema.json",
        RESOURCE_DIR / "source_registry_v1.csv",
    )
    context, evidence = golden_case_to_review_input(cases[case_id])
    result = evaluate_review(
        review_id=case_id,
        context=context,
        evidence=evidence,
        rules=validated.active_rules,
        pack_version=validated.version,
        created_at=datetime(2026, 7, 31, tzinfo=UTC),
    )

    assert result.status == "completed"
    assert 2 <= len(result.strengths_to_keep) <= 5
    assert result.creator_revision_message
    assert result.fix_first
    assert any(item.fix_type in {"replace_copy", "reshoot_scene"} for item in result.fix_first)
    assert any(
        "expected" in evidence_item.observed.lower()
        and "observed" in evidence_item.observed.lower()
        for item in result.fix_first + result.improvements + result.confirmations
        for evidence_item in item.evidence
    )
    assert any(
        item.unknown_state
        in {"rights_incomplete", "economics_insufficient", "publish_check_required"}
        for item in result.confirmations
    )
    serialized = result.model_dump_json().lower()
    assert "blocked" not in serialized
    assert "winning" not in serialized
    assert "performance guarantee" not in serialized
    assert "predicted" not in serialized


def test_semantic_fixture_loader_fails_clearly_when_attached_artifact_is_missing(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "semantic_regression_tests_v1.jsonl"

    with pytest.raises(FixtureArtifactMissingError, match="semantic_regression_tests_v1.jsonl"):
        load_semantic_regression_cases(missing)


def test_semantic_fixture_contains_expected_case_count() -> None:
    assert len(SEMANTIC_CASES) == 35


@pytest.mark.parametrize(
    "case",
    SEMANTIC_CASES,
    ids=lambda case: str(case["id"]),
)
def test_semantic_regression_cases_validate_domain_contract(case: dict[str, object]) -> None:
    validated = validate_policy_pack(
        RESOURCE_DIR / "DomainExpertPolicyPackV1.json",
        RESOURCE_DIR / "DomainExpertPolicyPackV1.schema.json",
        RESOURCE_DIR / "source_registry_v1.csv",
    )
    context, evidence = _semantic_case_input(case)
    result = evaluate_review(
        review_id=str(case["id"]),
        context=context,
        evidence=evidence,
        rules=validated.active_rules,
        pack_version=validated.version,
        semantic_evaluator=_SemanticRegressionEvaluator(case),
        created_at=datetime(2026, 7, 31, tzinfo=UTC),
    )

    expected = case["expected"]
    assert isinstance(expected, dict)
    output = _customer_text(result)
    serialized = output.lower()
    assert result.status == "completed"
    assert "blocked asset" not in serialized
    assert "policy violation" not in serialized
    assert "performance guarantee" not in serialized
    assert "predicted gmv" not in serialized
    assert "guaranteed to win" not in serialized
    for phrase in _expected_strings(expected, "must_include"):
        assert phrase.lower() in serialized
    for key in ("must_not_include", "must_not_output"):
        for phrase in _expected_strings(expected, key):
            assert phrase.lower() not in serialized
    for key in ("must_not_say", "must_not_label"):
        phrase = expected.get(key)
        if phrase is not None:
            assert str(phrase).lower() not in serialized
    for value in _expected_values(expected, "must_not_hardcode"):
        assert str(value) not in output
    if expected.get("must_not_invent_due_date") is True:
        assert "due date" not in serialized
    reason_code = expected.get("reason_code")
    if isinstance(reason_code, str) and reason_code.startswith("M-"):
        assert any(
            recommendation.mistake_code == reason_code
            for recommendation in [
                *result.fix_first,
                *result.improvements,
                *result.confirmations,
            ]
        )
    unknown_state = _expected_unknown_state(expected)
    if unknown_state is not None:
        assert any(
            recommendation.unknown_state == unknown_state
            for recommendation in result.confirmations
        )
    if _requires_non_ready_action(expected):
        assert result.recommended_next_action != "use_as_is"


class _SemanticRegressionEvaluator:
    provider_name = "semantic_regression_fixture_v1"

    def __init__(self, case: dict[str, object]) -> None:
        self._case = case

    def evaluate(self, **_kwargs: object) -> list[EvaluationCandidate]:
        expected = self._case["expected"]
        assert isinstance(expected, dict)
        rule_code, mistake_code = _semantic_rule_and_mistake(self._case, expected)
        group = _semantic_group(expected)
        unknown_state = _expected_unknown_state(expected)
        evidence_id = f"{self._case['id']}:semantic"
        return [
            EvaluationCandidate(
                rule_code=rule_code,
                mistake_code=mistake_code,
                group=group,
                title=_semantic_title(group),
                reason=_semantic_reason(expected),
                why_it_matters=(
                    "The domain contract requires uncertainty and missing inputs "
                    "to remain explicit."
                ),
                owner="seller" if group == "confirm" else "editor",
                fix_type=(
                    "confirm_seller_input"
                    if group == "confirm"
                    else ("reshoot_scene" if _expects_reshoot(expected) else "replace_copy")
                ),
                instructions=_semantic_instructions(expected),
                strengths_to_preserve=["Keep unaffected footage and creator delivery."],
                completion_criteria=_semantic_completion(expected),
                evidence_ids=[evidence_id],
                confidence="low" if unknown_state == "insufficient_evidence" else "medium",
                unknown_state=unknown_state,
            )
        ]


def _semantic_case_input(
    case: dict[str, object],
) -> tuple[UGCReviewContext, NormalizedEvidenceBundle]:
    case_id = str(case["id"])
    expected = case["expected"]
    assert isinstance(expected, dict)
    rule_code, _mistake_code = _semantic_rule_and_mistake(case, expected)
    context = UGCReviewContext(
        commerce_domain=_semantic_commerce_domain(case_id),
        intended_use=_semantic_intended_use(case_id),
        creator_brief=f"Semantic regression contract for {case_id}",
        material_connection="yes" if case_id == "T015" else "unknown",
    )
    evidence = NormalizedEvidence(
        id=f"{case_id}:semantic",
        kind="semantic_regression",
        source="policy",
        observed=f"Source semantic regression case {case_id}.",
        confidence="high",
        value={"rule_code": rule_code},
    )
    return context, NormalizedEvidenceBundle(
        items=[evidence],
        coverage={"semantic_regression": True},
        strengths=["Keep useful footage that is unaffected by the required correction."],
        pipeline_version="semantic_regression_fixture_v1",
    )


def _semantic_rule_and_mistake(
    case: dict[str, object],
    expected: dict[str, object],
) -> tuple[str, str | None]:
    case_id = str(case["id"])
    reason_code = expected.get("reason_code")
    mistake_code = (
        reason_code if isinstance(reason_code, str) and reason_code.startswith("M-") else None
    )
    if mistake_code == "M-POD-002":
        return "POD-MOCK-001", mistake_code
    if mistake_code is not None:
        return _rule_for_mistake(mistake_code), mistake_code
    mapping = {
        "T002": ("SYS-UNKNOWN-001", None),
        "T003": ("SYS-UNKNOWN-001", None),
        "T004": ("SYS-UNKNOWN-001", None),
        "T010": ("TT-CLAIM-001", "M-CLAIM-001"),
        "T011": ("TT-CONTENT-001", "M-PROD-001"),
        "T012": ("DROP-SHIP-001", "M-SUP-001"),
        "T014": ("TT-CLAIM-001", "M-CLAIM-001"),
        "T015": ("DISC-001", "M-DISC-001"),
        "T016": ("SYS-UNKNOWN-001", "M-CTA-001"),
        "T017": ("UGC-RIGHTS-001", "M-RIGHTS-001"),
        "T018": ("UGC-RIGHTS-001", "M-RIGHTS-001"),
        "T019": ("UGC-RIGHTS-001", "M-RIGHTS-001"),
        "T020": ("UGC-REV-002", "M-REV-001"),
        "T021": ("PERF-PREFLIGHT-001", "M-CREATOR-001"),
        "T022": ("SYS-UNKNOWN-001", None),
        "T023": ("SYS-UNKNOWN-001", None),
        "T024": ("PERF-PREFLIGHT-001", None),
        "T025": ("PERF-PREFLIGHT-001", None),
        "T026": ("SYS-UNKNOWN-001", None),
        "T027": ("PERF-PREFLIGHT-001", None),
        "T028": ("SYS-UNKNOWN-001", None),
        "T029": ("UGC-REV-002", "M-REV-001"),
        "T030": ("SYS-PROV-001", None),
        "T031": ("TT-OFFER-001", "M-OFFER-001"),
        "T032": ("TT-URGENCY-001", "M-OFFER-002"),
        "T033": ("PERF-PREFLIGHT-001", "M-REV-001"),
        "T034": ("SYS-UNKNOWN-001", None),
        "T035": ("SYS-PROV-001", None),
    }
    return mapping.get(case_id, ("SYS-UNKNOWN-001", None))


def _rule_for_mistake(mistake_code: str) -> str:
    if mistake_code.startswith("M-PROD"):
        return "TT-CONTENT-001"
    if mistake_code == "M-POD-001":
        return "POD-PERS-001"
    if mistake_code.startswith("M-POD"):
        return "POD-MOCK-001"
    if mistake_code.startswith("M-OFFER"):
        return "TT-URGENCY-001" if mistake_code == "M-OFFER-002" else "TT-OFFER-001"
    if mistake_code.startswith("M-SUP"):
        return "DROP-SHIP-001"
    if mistake_code.startswith("M-DISC"):
        return "DISC-001"
    if mistake_code.startswith("M-RIGHTS"):
        return "UGC-RIGHTS-001"
    if mistake_code.startswith("M-CTA"):
        return "SYS-UNKNOWN-001"
    if mistake_code.startswith("M-REV"):
        return "UGC-REV-002"
    if mistake_code.startswith(("M-PROOF", "M-DEMO", "M-CREATOR")):
        return "PERF-PREFLIGHT-001"
    if mistake_code.startswith("M-CLAIM"):
        return "TT-CLAIM-001"
    return "SYS-UNKNOWN-001"


def _semantic_group(expected: dict[str, object]) -> str:
    if _expected_unknown_state(expected) is not None:
        return "confirm"
    if _requires_non_ready_action(expected):
        return "fix_first"
    return "improve"


def _expected_unknown_state(expected: dict[str, object]) -> str | None:
    status = expected.get("status")
    if status == "policy_conflict":
        return "policy_conflict"
    if status == "supplier_data_stale":
        return "supplier_data_stale"
    if status == "publish_check_required":
        return "publish_check_required"
    if status == "economics_insufficient":
        return "economics_insufficient"
    if status in {
        "unknown",
        "insufficient_evidence",
        "shipping_route_unknown",
        "seller_confirmation_or_physical_asset_required",
    }:
        return (
            "insufficient_evidence"
            if status == "insufficient_evidence"
            else "seller_confirmation_required"
        )
    if status == "expert_or_platform_confirmation":
        return "expert_review_required"
    if expected.get("paid_ready") is False or expected.get("spark_ready") is False:
        return "rights_incomplete"
    if expected.get("commerce_outcome") == "unknown" or expected.get("profit_status") == "unknown":
        return "economics_insufficient"
    return None


def _requires_non_ready_action(expected: dict[str, object]) -> bool:
    if any(
        expected.get(key) is False
        for key in (
            "paid_ready",
            "spark_ready",
            "publish_ready",
            "listing_ready",
            "publishable",
            "causal_update_allowed",
            "auto_stop",
        )
    ):
        return True
    if expected.get("activation_locked") is True:
        return True
    decision = expected.get("decision")
    return isinstance(decision, str) and decision not in {"use_as_is", "retain"}


def _expects_reshoot(expected: dict[str, object]) -> bool:
    decision = str(expected.get("decision") or "")
    return "reshoot" in decision or "correct_product" in decision


def _semantic_reason(expected: dict[str, object]) -> str:
    fragments: list[str] = []
    for key in (
        "label",
        "status",
        "decision",
        "classification",
        "activation",
        "profit_status",
        "finding",
        "test_status",
        "fatigue_status",
        "scope",
    ):
        value = expected.get(key)
        if value is not None:
            fragments.append(str(value).replace("_", " "))
    fragments.extend(_expected_strings(expected, "must_include"))
    fragments.extend(f"Missing: {value}" for value in _expected_strings(expected, "missing"))
    if not fragments:
        fragments.append("Needs seller confirmation before activation.")
    return ". ".join(fragments) + "."


def _semantic_instructions(expected: dict[str, object]) -> list[str]:
    instructions: list[str] = []
    ask = expected.get("ask")
    if ask is not None:
        instructions.append(f"Ask for {ask}.")
    next_action = expected.get("next_action")
    if next_action is not None:
        instructions.append(f"Next action: {str(next_action).replace('_', ' ')}.")
    action = expected.get("action")
    if action is not None:
        instructions.append(f"Action: {str(action).replace('_', ' ')}.")
    instructions.extend(
        f"Confirm missing input: {value}." for value in _expected_strings(expected, "missing")
    )
    return instructions or ["Confirm the missing source facts before seller activation."]


def _semantic_completion(expected: dict[str, object]) -> list[str]:
    completion = [
        "The reviewed asset preserves accurate source facts and does not invent outcomes."
    ]
    for key in ("format", "claim_status", "copycat_risk"):
        value = expected.get(key)
        if value is not None:
            completion.append(f"{key.replace('_', ' ')}: {str(value).replace('_', ' ')}.")
    return completion


def _semantic_title(group: str) -> str:
    if group == "confirm":
        return "Confirm the missing domain inputs"
    if group == "fix_first":
        return "Revise the source-sensitive claim"
    return "Keep the contract uncertainty explicit"


def _semantic_commerce_domain(case_id: str) -> str:
    if case_id in {"T008", "T009", "T010"}:
        return "pod_personalization"
    if case_id in {"T011", "T012", "T028"}:
        return "dropshipping"
    return "tiktok_shop_us"


def _semantic_intended_use(case_id: str) -> str:
    if case_id in {"T017", "T018", "T019", "T022", "T035"}:
        return "paid_candidate"
    if case_id == "T015":
        return "affiliate"
    return "unknown"


def _customer_text(result: object) -> str:
    dumped = result.model_dump()
    dumped.pop("created_at", None)
    dumped.pop("review_id", None)
    dumped.pop("policy_pack_version", None)
    return str(dumped)


def _expected_strings(expected: dict[str, object], key: str) -> list[str]:
    values = expected.get(key)
    if not isinstance(values, list):
        return []
    return [str(value) for value in values]


def _expected_values(expected: dict[str, object], key: str) -> list[object]:
    values = expected.get(key)
    return values if isinstance(values, list) else []
