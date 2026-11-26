from decimal import Decimal

import pytest

from viraldy.modules.smart_remake.budget_ledger import normalize_policy, usd_amount
from viraldy.shared.errors.base import AppError


def test_decimal_amount_has_no_float_or_nonfinite_or_rounding():
    assert usd_amount("0.12345678") == Decimal("0.12345678")
    for value in (0.1, "NaN", "Infinity", "-1", "0.000000001", "10000000000"):
        with pytest.raises(AppError):
            usd_amount(value)


def test_limited_budget_requires_explicit_positive_limits_and_keeps_acknowledgement():
    policy = normalize_policy(
        {"capUsd": "2.500", "maxAttempts": 5, "maxDurationSeconds": 3600, "approvedBy": "seller"}
    )
    assert policy["capUsd"] == "2.500"
    assert policy["approvedBy"] == "seller"
    for partial in (
        {"mode": "limited"},
        {"capUsd": "0", "maxAttempts": 1, "maxDurationSeconds": 60},
        {"capUsd": "3", "maxAttempts": True, "maxDurationSeconds": 60},
    ):
        with pytest.raises(AppError):
            normalize_policy(partial)
