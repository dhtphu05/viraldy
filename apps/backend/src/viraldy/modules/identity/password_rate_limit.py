from __future__ import annotations

import hashlib
import hmac
import ipaddress
import time

from fastapi import Request
from redis.asyncio import Redis
from redis.exceptions import RedisError

from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError


def auth_client_ip(request: Request, settings: Settings) -> str:
    peer = request.client.host if request.client else "unknown"
    secret = settings.auth_proxy_secret
    ip = request.headers.get("x-viraldy-client-ip", "")
    timestamp = request.headers.get("x-viraldy-client-time", "")
    signature = request.headers.get("x-viraldy-client-signature", "")
    if secret is None or not ip or len(ip) > 64 or len(timestamp) > 12 or len(signature) != 64:
        return peer
    try:
        normalized = str(ipaddress.ip_address(ip))
        if abs(time.time() - int(timestamp)) > 60:
            return peer
    except ValueError:
        return peer
    expected = hmac.new(
        secret.get_secret_value().encode(), f"{timestamp}:{ip}".encode(), hashlib.sha256
    ).hexdigest()
    return normalized if hmac.compare_digest(signature.encode(), expected.encode()) else peer


async def enforce_password_rate_limit(
    request: Request,
    settings: Settings,
    *,
    action: str,
    email: str = "",
) -> None:
    peer = auth_client_ip(request, settings)
    buckets = [(f"ip:{peer}", 30 if action in {"login", "register"} else 300)]
    if email:
        buckets.append((f"email:{email.lower()}", 8))
    client: Redis = Redis.from_url(settings.redis_url, socket_connect_timeout=3, socket_timeout=3)
    try:
        for bucket, limit in buckets:
            digest = hashlib.sha256(bucket.encode()).hexdigest()
            key = f"viraldy:password-auth:{action}:{digest}"
            # Transaction prevents an INCR without expiry if the process exits.
            async with client.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.expire(key, 60, nx=True)
                count, _ = await pipe.execute()
            if count > limit:
                raise AppError(
                    "RATE_LIMITED", "Too many attempts. Please try again in a minute.", 429
                )
    except RedisError as exc:
        raise AppError("AUTH_UNAVAILABLE", "Sign-in is temporarily unavailable.", 503) from exc
    finally:
        await client.aclose()
