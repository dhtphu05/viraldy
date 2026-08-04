from __future__ import annotations

ACTIVE_MVP_RULE_CODES = frozenset(
    {
        "TT-CONTENT-001",
        "TT-CLAIM-001",
        "TT-OFFER-001",
        "TT-URGENCY-001",
        "DISC-001",
        "FTC-SHIP-001",
        "POD-PERS-001",
        "POD-MOCK-001",
        "DROP-COMP-001",
        "DROP-SHIP-001",
        "UGC-REV-002",
        "UGC-RIGHTS-001",
        "PERF-PREFLIGHT-001",
        "PERF-TIME-001",
        "SYS-UNKNOWN-001",
        "SYS-PROV-001",
    }
)

EXPECTED_PACK_COUNTS = {
    "policies": 58,
    "patterns": 23,
    "mistakes": 20,
    "uncertainties": 15,
    "sources": 66,
}
