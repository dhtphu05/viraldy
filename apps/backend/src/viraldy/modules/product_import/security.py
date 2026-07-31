from __future__ import annotations

import ipaddress
import socket
import urllib.request
from collections.abc import Callable
from typing import Any, cast
from urllib.parse import urlsplit, urlunsplit

from viraldy.shared.errors.base import AppError

Resolver = Callable[..., list[tuple[int, int, int, str, tuple[Any, ...]]]]
_DEFAULT_RESOLVER = cast(Resolver, socket.getaddrinfo)

_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "metadata",
        "metadata.google.internal",
    }
)


class PublicHttpRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        validate_public_http_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_PUBLIC_URL_OPENER = urllib.request.build_opener(PublicHttpRedirectHandler())


def validate_public_http_url(
    raw_url: str,
    *,
    resolver: Resolver = _DEFAULT_RESOLVER,
) -> str:
    value = raw_url.strip()
    if not value or len(value) > 2048:
        _reject_url()

    try:
        parsed = urlsplit(value)
        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    except ValueError:
        _reject_url()

    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").rstrip(".").lower()
    if (
        scheme not in {"http", "https"}
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or hostname in _BLOCKED_HOSTNAMES
        or hostname.endswith(".localhost")
    ):
        _reject_url()

    literal = _parse_ip(hostname)
    if literal is not None:
        if not literal.is_global:
            _reject_url()
    else:
        try:
            addresses = resolver(hostname, port, type=socket.SOCK_STREAM)
        except OSError:
            _reject_url()
        if not addresses:
            _reject_url()
        for address in addresses:
            sockaddr = address[4]
            if not sockaddr:
                _reject_url()
            resolved = _parse_ip(str(sockaddr[0]))
            if resolved is None or not resolved.is_global:
                _reject_url()

    return urlunsplit((scheme, parsed.netloc, parsed.path or "/", parsed.query, ""))


def is_public_http_url(raw_url: str, *, resolver: Resolver = _DEFAULT_RESOLVER) -> bool:
    try:
        validate_public_http_url(raw_url, resolver=resolver)
    except AppError:
        return False
    return True


def open_public_url(
    request: str | urllib.request.Request,
    *,
    timeout: float,
) -> Any:
    raw_url = request.full_url if isinstance(request, urllib.request.Request) else request
    validate_public_http_url(raw_url)
    return _PUBLIC_URL_OPENER.open(request, timeout=timeout)


def _parse_ip(hostname: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(hostname)
    except ValueError:
        return None


def _reject_url() -> None:
    raise AppError(
        code="PRODUCT_CRAWL_URL_INVALID",
        message="Provide a public HTTP or HTTPS product URL.",
        status_code=400,
    )
