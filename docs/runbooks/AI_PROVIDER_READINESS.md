# AI Provider Readiness

Viraldy supports three MVP analysis modes:

- `fixture`: deterministic seeded assets only; no provider calls.
- `mock`: OpenAI-compatible HTTP path with the local mock provider and no paid key.
- `live`: same contracts as mock, with real provider configuration from environment.

## Environment

```bash
AI_MODE=fixture|mock|live
AI_PROVIDER=openai_compatible
AI_BASE_URL=
AI_API_KEY=
AI_TEXT_MODEL=
AI_VISION_MODEL=

ASR_PROVIDER=openai_compatible
ASR_BASE_URL=
ASR_API_KEY=
ASR_MODEL=

AI_SUPPORTS_JSON_SCHEMA=true
AI_SUPPORTS_IMAGE_URL=true
AI_REQUEST_TIMEOUT_SECONDS=120
AI_MAX_RETRIES=2
AI_MAX_OUTPUT_TOKENS=
```

`ASR_BASE_URL` and `ASR_API_KEY` may be omitted only when ASR uses the same base URL and key as the chat/vision provider.

## Readiness

From `apps/backend`:

```bash
PYTHONPATH=src python scripts/check_ai_readiness.py
```

Exit codes:

- `0`: configured for the selected mode.
- `1`: missing configuration.
- `2`: provider contract or health error.

The API endpoint is:

```http
GET /api/v1/system/ai-readiness
```

It reports missing capability/config names and never returns secrets.

## Mock Provider

From `apps/backend`:

```bash
PYTHONPATH=src MOCK_AI_PORT=8787 python scripts/mock_openai_provider.py
```

Use:

```bash
AI_MODE=mock
AI_BASE_URL=http://127.0.0.1:8787/v1
AI_TEXT_MODEL=mock-text
AI_VISION_MODEL=mock-vision
ASR_PROVIDER=openai_compatible
ASR_MODEL=mock-asr
```

Failure switches:

```bash
MOCK_AI_FAILURE=malformed_json
MOCK_AI_FAILURE=timeout
MOCK_AI_FAILURE=429
MOCK_AI_FAILURE=500
MOCK_AI_FAILURE=missing_field
```

## First Live Smoke

Set `AI_MODE=live`, real `AI_BASE_URL`, `AI_API_KEY`, `AI_TEXT_MODEL`, `AI_VISION_MODEL`, and `ASR_MODEL`. Set `ASR_BASE_URL` and `ASR_API_KEY` only if ASR uses different credentials.

Run readiness first. Then run one Quick TikTok Scorer job and one full Product -> Reference Board -> Creative DNA -> Product Adaptation -> Campaign Pack -> UGC Preflight loop.

## Unexercised Vendor Behavior

Mock mode validates Viraldy request/response contracts, retries, structured parsing, and safe error mapping. It does not prove provider-specific model quality, multimodal token limits, audio transcription accuracy, rate-limit policy details, or vendor-specific JSON-schema strictness.
