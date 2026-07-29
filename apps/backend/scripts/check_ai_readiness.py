from __future__ import annotations

import json

import httpx

from viraldy.modules.ai_gateway.readiness import ai_readiness
from viraldy.platform.config.settings import get_settings


def main() -> int:
    settings = get_settings()
    readiness = ai_readiness(settings)
    print(json.dumps(readiness.model_dump(mode="json"), indent=2, sort_keys=True))
    if not readiness.configured:
        return 1
    if readiness.mode == "fixture":
        return 0
    base_url = (settings.ai_base_url or "").rstrip("/")
    health_base_url = base_url.removesuffix("/v1")
    try:
        response = httpx.get(f"{health_base_url}/health", timeout=5)
    except httpx.HTTPError:
        return 2
    return 0 if response.status_code < 500 else 2


if __name__ == "__main__":
    raise SystemExit(main())
