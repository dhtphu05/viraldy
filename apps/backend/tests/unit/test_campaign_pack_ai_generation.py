from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr

from viraldy.modules.adaptations.contracts import AdaptationConceptV2, AdaptationOutputV2
from viraldy.modules.ai_gateway.context import ViraldyOperationContextV1
from viraldy.modules.ai_gateway.usage import ProviderUsage
from viraldy.modules.campaign_packs.provider import (
    CampaignPackGenerationProvider,
    CampaignPackProviderExecution,
    build_campaign_pack_output_validator,
)
from viraldy.modules.campaign_packs.schemas import CreateCampaignPackRequest
from viraldy.modules.campaign_packs.service import CampaignPackService, _brief_from_concept
from viraldy.modules.products.contracts import (
    BuyerPersonaV1,
    ClaimRuleV1,
    CreativeContextV1,
    ProductContextV1,
    ProductGovernanceV1,
    ProductIdentityV1,
)
from viraldy.modules.products.public import ProductContextSnapshot
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, _value: object) -> None:
        return None


class FakeAdaptationRepository:
    def __init__(self, adaptation: SimpleNamespace) -> None:
        self.adaptation = adaptation

    async def get(self, workspace_id: UUID, adaptation_id: UUID) -> SimpleNamespace | None:
        if workspace_id == self.adaptation.workspace_id and adaptation_id == self.adaptation.id:
            return self.adaptation
        return None


class FakeProductQueries:
    def __init__(self, snapshot: ProductContextSnapshot) -> None:
        self.snapshot = snapshot

    async def get_product_context_snapshot(
        self,
        workspace_id: UUID,
        product_id: UUID,
    ) -> ProductContextSnapshot | None:
        if workspace_id == self.snapshot.workspace_id and product_id == self.snapshot.product_id:
            return self.snapshot
        return None


class FakeCampaignPackRepository:
    def __init__(self) -> None:
        self.created: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> tuple[SimpleNamespace, SimpleNamespace]:
        self.created.append(kwargs)
        now = datetime.now(UTC)
        pack_id = uuid4()
        version_id = uuid4()
        version = SimpleNamespace(
            id=version_id,
            campaign_pack_id=pack_id,
            version_number=1,
            brief_json=kwargs["brief_json"],
            brief_schema_version="campaign_pack_brief_v1",
            product_snapshot_json=kwargs["product_snapshot_json"],
            compiled_requirements_json=kwargs["compiled_requirements_json"],
            requirements_schema_version=kwargs["requirements_schema_version"],
            change_note="Initial generated brief",
            source_adaptation_run_id=kwargs["adaptation_run_id"],
            source_model_run_id=kwargs["source_model_run_id"],
            source_prompt_version=kwargs["source_prompt_version"],
            source_schema_version=kwargs["source_schema_version"],
            created_at=now,
        )
        pack = SimpleNamespace(
            id=pack_id,
            workspace_id=kwargs["workspace_id"],
            product_id=kwargs["product_id"],
            adaptation_run_id=kwargs["adaptation_run_id"],
            status="draft",
            current_version_id=version_id,
            created_at=now,
            updated_at=now,
        )
        return pack, version


class FakeModelRunRepository:
    def __init__(self) -> None:
        self.created: list[dict[str, object]] = []
        self.completed: list[tuple[SimpleNamespace, dict[str, object]]] = []
        self.failed: list[tuple[SimpleNamespace, str]] = []

    async def create_running(self, **kwargs: object) -> SimpleNamespace:
        self.created.append(kwargs)
        return SimpleNamespace(id=uuid4(), status="running")

    async def complete(
        self,
        run: SimpleNamespace,
        output_summary: dict[str, object],
        http_status: int | None,
        provider_request_id: str | None,
        latency_ms: int | None,
        **kwargs: object,
    ) -> SimpleNamespace:
        run.status = "completed"
        run.http_status = http_status
        run.provider_request_id = provider_request_id
        run.latency_ms = latency_ms
        run.usage_json = kwargs.get("usage_json", {})
        run.repair_attempt_count = kwargs.get("repair_attempt_count", 0)
        self.completed.append((run, output_summary))
        return run

    async def fail(
        self,
        run: SimpleNamespace,
        code: str,
        _message: str,
        **kwargs: object,
    ) -> SimpleNamespace:
        run.status = "failed"
        run.provider_request_id = kwargs.get("provider_request_id")
        run.http_status = kwargs.get("http_status")
        run.repair_attempt_count = kwargs.get("repair_attempt_count")
        self.failed.append((run, code))
        return run


class FakeProvider:
    calls: list[dict[str, object]] = []
    output: CampaignPackProviderExecution | AppError | None = None

    def __init__(self, _settings: Settings) -> None:
        return None

    def generate_with_metadata(self, **kwargs: object) -> CampaignPackProviderExecution:
        self.calls.append(kwargs)
        if isinstance(self.output, AppError):
            raise self.output
        assert self.output is not None
        return self.output


@pytest.mark.asyncio
async def test_fixture_create_is_deterministic_and_links_own_model_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _harness(monkeypatch, _settings("fixture"))
    FakeProvider.calls = []

    response = await harness.service.create(
        harness.workspace_id,
        harness.user_id,
        CreateCampaignPackRequest(
            adaptation_run_id=harness.adaptation.id,
            concept_id=harness.concept.id,
        ),
    )

    assert FakeProvider.calls == []
    assert harness.model_runs.created[0]["operation"] == "campaign_pack_generate"
    assert harness.model_runs.created[0]["provider"] == "fixture"
    assert harness.model_runs.created[0]["attempt_count"] == 1
    assert harness.model_runs.created[0]["repair_attempt_count"] == 0
    assert harness.model_runs.completed
    assert harness.campaign_packs.created[0]["source_model_run_id"] == (
        harness.model_runs.completed[0][0].id
    )
    assert harness.campaign_packs.created[0]["source_model_run_id"] != (
        harness.adaptation.primary_model_run_id
    )
    assert response.current_version is not None
    assert (
        response.current_version.source_prompt_version == "campaign_pack_generation_v2_few_shot_v1"
    )
    assert response.current_version.source_schema_version == "campaign_pack_brief_v1"
    requirements = response.current_version.brief_json.must_show
    assert requirements[0].requirement_type == "product"
    assert requirements[0].expected_before_ms == 1500
    assert requirements[2].requirement_type == "cta"
    assert requirements[2].expected_before_ms is None


@pytest.mark.parametrize("mode", ["mock", "live"])
@pytest.mark.asyncio
async def test_non_fixture_create_invokes_provider_and_persists_provider_metadata(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    harness = _harness(monkeypatch, _settings(mode))
    generated = _expected_brief(harness)
    FakeProvider.calls = []
    FakeProvider.output = CampaignPackProviderExecution(
        output=generated,
        provider="openai" if mode == "live" else "openai_compatible",
        model="gpt-5" if mode == "live" else "mock-text",
        endpoint_family="responses" if mode == "live" else "chat_completions",
        provider_request_id=f"{mode}-request",
        http_status=200,
        latency_ms=23,
        usage_json={
            "input_tokens": 101,
            "output_tokens": 202,
            "total_tokens": 303,
            "cached_input_tokens": 0,
        },
        repair_attempt_count=1 if mode == "live" else 0,
    )

    response = await harness.service.create(
        harness.workspace_id,
        harness.user_id,
        CreateCampaignPackRequest(
            adaptation_run_id=harness.adaptation.id,
            concept_id=harness.concept.id,
        ),
    )

    assert len(FakeProvider.calls) == 1
    assert FakeProvider.calls[0]["product_context_version"] == 7
    assert FakeProvider.calls[0]["selected_concept"] == harness.concept
    created_run = harness.model_runs.created[0]
    assert created_run["operation"] == "campaign_pack_generate"
    assert created_run["prompt_name"] == "campaign_pack_generation"
    assert created_run["input_summary"] == {
        "adaptation_run_id": str(harness.adaptation.id),
        "concept_id": harness.concept.id,
        "objective": harness.adaptation.objective,
        "product_context_version": 7,
        "product_id": str(harness.product.product_id),
        "target_market": harness.adaptation.target_market,
    }
    run = harness.model_runs.completed[0][0]
    assert run.provider_request_id == f"{mode}-request"
    assert run.usage_json["total_tokens"] == 303
    assert run.repair_attempt_count == (1 if mode == "live" else 0)
    assert response.current_version is not None
    assert response.current_version.source_model_run_id == run.id
    assert response.current_version.source_model_run_id != (harness.adaptation.primary_model_run_id)


@pytest.mark.asyncio
async def test_live_failure_marks_own_model_run_failed_without_creating_pack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _harness(monkeypatch, _settings("live"))
    FakeProvider.calls = []
    FakeProvider.output = AppError(
        "OPENAI_OUTPUT_INVALID",
        "Campaign Pack output failed validation.",
        details={
            "provider_request_id": "request-failed",
            "http_status": 200,
            "repair_attempt_count": 1,
        },
    )

    with pytest.raises(AppError, match="Campaign Pack output failed validation"):
        await harness.service.create(
            harness.workspace_id,
            harness.user_id,
            CreateCampaignPackRequest(
                adaptation_run_id=harness.adaptation.id,
                concept_id=harness.concept.id,
            ),
        )

    assert harness.model_runs.failed[0][1] == "OPENAI_OUTPUT_INVALID"
    failed_run = harness.model_runs.failed[0][0]
    assert failed_run.provider_request_id == "request-failed"
    assert failed_run.http_status == 200
    assert failed_run.repair_attempt_count == 1
    assert harness.campaign_packs.created == []
    assert harness.session.commits == 1


@pytest.mark.asyncio
async def test_mock_provider_failure_marks_run_failed_without_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _harness(monkeypatch, _settings("mock"))
    FakeProvider.output = AppError(
        "CAMPAIGN_PACK_OUTPUT_INVALID",
        "Mock provider returned an invalid Campaign Pack.",
        details={
            "provider_request_id": "mock-invalid",
            "http_status": 200,
            "repair_attempt_count": 0,
        },
    )

    with pytest.raises(AppError, match="Mock provider returned an invalid Campaign Pack"):
        await harness.service.create(
            harness.workspace_id,
            harness.user_id,
            CreateCampaignPackRequest(
                adaptation_run_id=harness.adaptation.id,
                concept_id=harness.concept.id,
            ),
        )

    assert harness.model_runs.completed == []
    assert harness.model_runs.failed[0][1] == "CAMPAIGN_PACK_OUTPUT_INVALID"
    assert harness.campaign_packs.created == []


@pytest.mark.asyncio
async def test_stale_adaptation_product_snapshot_is_rejected_before_model_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _harness(monkeypatch, _settings("live"))
    stale = harness.product.product_context.model_copy(
        update={
            "identity": harness.product.product_context.identity.model_copy(
                update={"variant": "stale-variant"}
            )
        }
    )
    harness.adaptation.product_snapshot_json = stale.model_dump(mode="json")

    with pytest.raises(AppError) as exc_info:
        await harness.service.create(
            harness.workspace_id,
            harness.user_id,
            CreateCampaignPackRequest(
                adaptation_run_id=harness.adaptation.id,
                concept_id=harness.concept.id,
            ),
        )

    assert exc_info.value.code == "CAMPAIGN_PACK_PRODUCT_SNAPSHOT_STALE"
    assert harness.model_runs.created == []
    assert FakeProvider.calls == []


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda payload: payload["product_snapshot"]["identity"].update(  # type: ignore[union-attr]
                {"name": "Different product"}
            ),
            "product snapshot",
        ),
        (
            lambda payload: payload.update({"source_concept_id": "different"}),
            "source concept",
        ),
        (
            lambda payload: payload.update({"source_adaptation_run_id": str(uuid4())}),
            "source adaptation",
        ),
        (
            lambda payload: payload["audience"].update(  # type: ignore[union-attr]
                {"persona_label": "different buyer"}
            ),
            "buyer",
        ),
        (
            lambda payload: payload["creator_direction"].update(  # type: ignore[union-attr]
                {"persona": "busy pet parent"}
            ),
            "buyer and creator",
        ),
        (
            lambda payload: payload["claim_guardrails"].update(  # type: ignore[union-attr]
                {"prohibited": []}
            ),
            "prohibited claims",
        ),
        (
            lambda payload: payload["claim_guardrails"].update(  # type: ignore[union-attr]
                {"required_disclosures": []}
            ),
            "required disclosures",
        ),
        (
            lambda payload: payload["rights_note"].update(  # type: ignore[union-attr]
                {"note": "All rights granted."}
            ),
            "rights",
        ),
    ],
)
def test_output_validator_rejects_protected_semantic_drift(
    mutation: Any,
    message: str,
) -> None:
    workspace_id = uuid4()
    product = _product(workspace_id)
    concept = _concept()
    expected = _brief_from_concept(
        "tiktok_shop_conversion",
        "US",
        {"persona_id": "buyer_pet_parent"},
        product.product_context.model_dump(mode="json"),
        concept.model_dump(mode="json"),
        uuid4(),
        concept.id,
    )
    payload = expected.model_dump(mode="json")
    mutation(payload)
    candidate = type(expected).model_validate(payload)

    with pytest.raises(ValueError, match=message):
        build_campaign_pack_output_validator(expected)(candidate)


def test_output_validator_rejects_prohibited_claim_in_creator_copy() -> None:
    workspace_id = uuid4()
    product = _product(workspace_id)
    concept = _concept()
    expected = _brief_from_concept(
        "tiktok_shop_conversion",
        "US",
        {"persona_id": "buyer_pet_parent"},
        product.product_context.model_dump(mode="json"),
        concept.model_dump(mode="json"),
        uuid4(),
        concept.id,
    )
    payload = expected.model_dump(mode="json")
    payload["hooks"][0]["spoken_text"] = "Guaranteed delivery date"  # type: ignore[index]
    candidate = type(expected).model_validate(payload)

    with pytest.raises(ValueError, match="used a prohibited claim"):
        build_campaign_pack_output_validator(expected)(candidate)


def test_native_provider_uses_strict_campaign_pack_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from viraldy.modules.campaign_packs import provider as provider_module

    workspace_id = uuid4()
    product = _product(workspace_id)
    concept = _concept()
    adaptation_run_id = uuid4()
    expected = _brief_from_concept(
        "tiktok_shop_conversion",
        "US",
        {"persona_id": "buyer_pet_parent"},
        product.product_context.model_dump(mode="json"),
        concept.model_dump(mode="json"),
        adaptation_run_id,
        concept.id,
    )
    captured: dict[str, object] = {}

    def fake_execute(
        settings: Settings,
        context: object,
        output_model: object,
        **kwargs: object,
    ) -> SimpleNamespace:
        captured.update(
            {
                "settings": settings,
                "context": context,
                "output_model": output_model,
            }
        )
        validator = kwargs["output_validator"]
        assert callable(validator)
        validator(expected)
        return SimpleNamespace(
            parsed_output=expected,
            provider="openai",
            endpoint_family=SimpleNamespace(value="responses"),
            model="gpt-5",
            provider_request_id="req-native",
            http_status=200,
            latency_ms=41,
            usage=ProviderUsage(
                input_tokens=10,
                output_tokens=20,
                total_tokens=30,
                cached_input_tokens=2,
            ),
            repair_attempt_count=1,
        )

    monkeypatch.setattr(provider_module, "execute_structured_operation", fake_execute)
    result = CampaignPackGenerationProvider(_settings("live")).generate_with_metadata(
        workspace_id=workspace_id,
        actor_user_id=uuid4(),
        model_run_id=uuid4(),
        product_id=product.product_id,
        product_context=product.product_context,
        product_context_version=product.product_context_version,
        adaptation_run_id=adaptation_run_id,
        selected_concept=concept,
        objective="tiktok_shop_conversion",
        target_market="US",
        target_buyer={"persona_id": "buyer_pet_parent"},
        adaptation_constraints={},
        deterministic_baseline=expected,
    )

    context = captured["context"]
    assert isinstance(context, ViraldyOperationContextV1)
    assert captured["output_model"] is type(expected)
    assert context.operation.value == "campaign_pack_generate"
    assert context.product_context_version == 7
    assert context.source_version_ids == [adaptation_run_id]
    assert result.provider_request_id == "req-native"
    assert result.usage_json["total_tokens"] == 30
    assert result.repair_attempt_count == 1


def test_mock_provider_uses_shared_structured_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from viraldy.modules.campaign_packs import provider as provider_module

    workspace_id = uuid4()
    product = _product(workspace_id)
    concept = _concept()
    adaptation_run_id = uuid4()
    expected = _brief_from_concept(
        "tiktok_shop_conversion",
        "US",
        {"persona_id": "buyer_pet_parent"},
        product.product_context.model_dump(mode="json"),
        concept.model_dump(mode="json"),
        adaptation_run_id,
        concept.id,
    )
    captured: dict[str, object] = {}

    def fake_execute(
        settings: Settings,
        context: object,
        output_model: object,
        **kwargs: object,
    ) -> SimpleNamespace:
        captured.update(
            {
                "settings": settings,
                "context": context,
                "output_model": output_model,
                "validator": kwargs.get("output_validator"),
            }
        )
        validator = kwargs["output_validator"]
        assert callable(validator)
        validator(expected)
        return SimpleNamespace(
            parsed_output=expected,
            provider="openai_compatible",
            endpoint_family=SimpleNamespace(value="chat_completions"),
            model="mock-text",
            provider_request_id="req-compatible",
            http_status=200,
            latency_ms=17,
            usage=ProviderUsage(
                input_tokens=11,
                output_tokens=22,
                total_tokens=33,
                cached_input_tokens=4,
            ),
            repair_attempt_count=0,
        )

    monkeypatch.setattr(provider_module, "execute_structured_operation", fake_execute)
    result = CampaignPackGenerationProvider(_settings("mock")).generate_with_metadata(
        workspace_id=workspace_id,
        actor_user_id=uuid4(),
        model_run_id=uuid4(),
        product_id=product.product_id,
        product_context=product.product_context,
        product_context_version=product.product_context_version,
        adaptation_run_id=adaptation_run_id,
        selected_concept=concept,
        objective="tiktok_shop_conversion",
        target_market="US",
        target_buyer={"persona_id": "buyer_pet_parent"},
        adaptation_constraints={},
        deterministic_baseline=expected,
    )

    context = captured["context"]
    assert isinstance(context, ViraldyOperationContextV1)
    assert captured["output_model"] is type(expected)
    assert context.operation.value == "campaign_pack_generate"
    assert result.endpoint_family == "chat_completions"
    assert result.provider_request_id == "req-compatible"
    assert result.usage_json == {
        "input_tokens": 11,
        "output_tokens": 22,
        "total_tokens": 33,
        "cached_input_tokens": 4,
    }


def _settings(mode: str) -> Settings:
    if mode == "live":
        return Settings(
            ai_mode="live",
            ai_provider="openai",
            openai_api_key=SecretStr("test-key"),
            openai_text_model="gpt-5",
        )
    if mode == "mock":
        return Settings(
            ai_mode="mock",
            ai_provider="openai_compatible",
            ai_base_url="http://127.0.0.1:8787/v1",
            ai_api_key=SecretStr("mock-key"),
            ai_text_model="mock-text",
        )
    return Settings(ai_mode="fixture", ai_provider="openai_compatible")


def _product(workspace_id: UUID) -> ProductContextSnapshot:
    context = ProductContextV1(
        identity=ProductIdentityV1(
            name="Personalized Pet Hoodie",
            category="pod_personalized_apparel",
            variant="black hoodie",
            market="US",
        ),
        personas=[
            BuyerPersonaV1(
                id="buyer_pet_parent",
                label="busy pet parent",
                pain_points=["generic gifts feel impersonal"],
                desired_outcomes=["a visibly personalized keepsake"],
            )
        ],
        creative=CreativeContextV1(
            creator_personas=["pet lifestyle creator"],
            required_product_reveal_before_ms=1500,
        ),
        governance=ProductGovernanceV1(
            claims=[
                ClaimRuleV1(
                    id="no_delivery_guarantee",
                    text="Guaranteed delivery date",
                    rule_type="prohibited",
                    severity="critical",
                ),
                ClaimRuleV1(
                    id="handmade_qualification",
                    text="Handmade",
                    rule_type="allowed_with_qualification",
                    qualification="Only when seller confirms production method.",
                ),
            ],
            required_disclosures=["Personalized items cannot be returned."],
            rights_notes=["Spark authorization requires creator approval."],
        ),
    )
    return ProductContextSnapshot(
        product_id=uuid4(),
        workspace_id=workspace_id,
        context_schema_version=context.schema_version,
        product_context_version=7,
        product_context=context,
    )


def _concept() -> AdaptationConceptV2:
    return AdaptationConceptV2(
        id="concept_personalization_reveal",
        name="Personalized Pet Hoodie name reveal",
        strategic_axis="personalization_reveal",
        angle="Reveal the exact pet name on the physical hoodie",
        buyer_persona_id="buyer_pet_parent",
        buyer_persona_label="busy pet parent",
        buyer_pain="generic gifts feel impersonal",
        desired_outcome="a visibly personalized keepsake",
        creator_persona="pet lifestyle creator",
        delivery_style="warm_unboxing",
        hook_options=["I put Milo's name on this Personalized Pet Hoodie"],
        opening_visual="show Milo on the physical Personalized Pet Hoodie",
        demo_mechanism="close-up of the printed name and hoodie material",
        demo_sequence=[
            "show physical Personalized Pet Hoodie",
            "show Milo name close-up",
            "show hoodie worn in context",
        ],
        proof_mechanism="same physical hoodie remains visible through the reveal",
        offer_framing=None,
        cta_strategy="Use the product tag after showing the personalization.",
        claim_guardrails=["Guaranteed delivery date"],
        must_show=[
            "product visible before 1500ms",
            "Milo personalization close-up",
            "product tag CTA",
        ],
        risks=[],
        test_hypothesis="Test whether exact-name reveal improves qualified clicks.",
        source_evidence_ids=[],
    )


def _harness(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> SimpleNamespace:
    from viraldy.modules.campaign_packs import service as service_module

    FakeProvider.calls = []
    FakeProvider.output = None
    workspace_id = uuid4()
    user_id = uuid4()
    product = _product(workspace_id)
    concept = _concept()
    adaptation_output = AdaptationOutputV2(
        guidance=[],
        concepts=[
            concept,
            concept.model_copy(
                update={
                    "id": "concept_problem",
                    "strategic_axis": "problem_first",
                    "delivery_style": "problem_demo",
                }
            ),
            concept.model_copy(
                update={
                    "id": "concept_proof",
                    "strategic_axis": "proof_first",
                    "delivery_style": "proof_review",
                }
            ),
        ],
    )
    adaptation = SimpleNamespace(
        id=uuid4(),
        workspace_id=workspace_id,
        product_id=product.product_id,
        primary_model_run_id=uuid4(),
        objective="tiktok_shop_conversion",
        target_market="US",
        target_buyer_json={"persona_id": "buyer_pet_parent"},
        constraints_json={"must_include": ["Milo personalization close-up"]},
        result_json=adaptation_output.model_dump(mode="json"),
        product_snapshot_json=product.product_context.model_dump(mode="json"),
        status="completed",
    )
    campaign_packs = FakeCampaignPackRepository()
    model_runs = FakeModelRunRepository()
    session = FakeSession()
    monkeypatch.setattr(
        service_module,
        "CampaignPackRepository",
        lambda _session: campaign_packs,
    )
    monkeypatch.setattr(
        service_module,
        "AdaptationRepository",
        lambda _session: FakeAdaptationRepository(adaptation),
    )
    monkeypatch.setattr(
        service_module,
        "ProductQueries",
        lambda _session: FakeProductQueries(product),
    )
    monkeypatch.setattr(
        service_module,
        "AiModelRunRepository",
        lambda _session: model_runs,
    )
    monkeypatch.setattr(
        service_module,
        "CampaignPackGenerationProvider",
        FakeProvider,
    )
    service = CampaignPackService(session, settings)  # type: ignore[arg-type]
    return SimpleNamespace(
        service=service,
        session=session,
        workspace_id=workspace_id,
        user_id=user_id,
        product=product,
        concept=concept,
        adaptation=adaptation,
        campaign_packs=campaign_packs,
        model_runs=model_runs,
    )


def _expected_brief(harness: SimpleNamespace) -> Any:
    return _brief_from_concept(
        harness.adaptation.objective,
        harness.adaptation.target_market,
        harness.adaptation.target_buyer_json,
        harness.product.product_context.model_dump(mode="json"),
        harness.concept.model_dump(mode="json"),
        harness.adaptation.id,
        harness.concept.id,
    )
