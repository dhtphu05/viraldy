from __future__ import annotations

from types import SimpleNamespace

from viraldy.modules.domain_intelligence.router import get_domain_intelligence_status
from viraldy.modules.domain_intelligence.schemas import PolicyPackCounts, PolicyPackStatus


async def test_domain_status_returns_authenticated_global_registry_status(monkeypatch) -> None:
    expected = PolicyPackStatus(
        pack_name="Viraldy Domain, Creative and Workflow Research Pack",
        version="v1",
        content_hash="a" * 64,
        status="active",
        counts=PolicyPackCounts(
            policies=58,
            patterns=23,
            mistakes=20,
            uncertainties=15,
            sources=66,
        ),
        active_rule_codes=["SYS-UNKNOWN-001"],
    )

    class StubQueries:
        def __init__(self, _db) -> None:
            pass

        async def status(self) -> PolicyPackStatus:
            return expected

    monkeypatch.setattr(
        "viraldy.modules.domain_intelligence.router.DomainIntelligenceQueries",
        StubQueries,
    )

    envelope = await get_domain_intelligence_status(
        current_user=SimpleNamespace(id="user-1"),
        db=object(),
        request_id="request-1",
    )

    assert envelope.meta.request_id == "request-1"
    assert envelope.data == expected.model_dump(mode="json")
