from __future__ import annotations

import hashlib
import hmac
import secrets
import time

import pytest
from starlette.requests import Request

from viraldy.modules.identity.password_rate_limit import auth_client_ip
from viraldy.platform.config.settings import Settings


def request(headers: dict[str, str]) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/auth/login",
            "client": ("127.0.0.1", 12345),
            "headers": [(k.encode(), v.encode()) for k, v in headers.items()],
        }
    )


def signed_headers(secret: str, ip: str, timestamp: str | None = None) -> dict[str, str]:
    stamp = timestamp or str(int(time.time()))
    return {
        "x-viraldy-client-ip": ip,
        "x-viraldy-client-time": stamp,
        "x-viraldy-client-signature": hmac.new(
            secret.encode(), f"{stamp}:{ip}".encode(), hashlib.sha256
        ).hexdigest(),
    }


def test_signed_clients_behind_one_bff_have_separate_rate_limit_addresses() -> None:
    secret = secrets.token_hex(32)
    settings = Settings(_env_file=None, auth_proxy_secret=secret)
    assert (
        auth_client_ip(request(signed_headers(secret, "203.0.113.10")), settings) == "203.0.113.10"
    )
    assert (
        auth_client_ip(request(signed_headers(secret, "203.0.113.11")), settings) == "203.0.113.11"
    )


@pytest.mark.parametrize(
    "change",
    [
        {"x-forwarded-for": "203.0.113.1"},
        {"x-viraldy-client-ip": "not-an-ip"},
        {"x-viraldy-client-signature": "forged"},
        {"x-viraldy-client-time": "invalid"},
        {"x-viraldy-client-time": "0"},
        {"x-viraldy-client-signature": "é" * 64},
    ],
)
def test_untrusted_or_expired_forwarding_does_not_change_peer(change: dict[str, str]) -> None:
    secret = secrets.token_hex(32)
    headers = signed_headers(secret, "203.0.113.10")
    if "x-forwarded-for" in change:
        headers = change
    else:
        headers = {**headers, **change}
    assert (
        auth_client_ip(request(headers), Settings(_env_file=None, auth_proxy_secret=secret))
        == "127.0.0.1"
    )
