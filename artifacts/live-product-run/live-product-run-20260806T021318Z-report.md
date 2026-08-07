# Viraldy Live Product Run Audit

Run ID: `live-product-run-20260806T021318Z`
Date: `2026-08-06 09:13-09:24 Asia/Ho_Chi_Minh`
Media: `/Users/mac/Desktop/Viraldy/apps/web/public/demo-media/download (95) copy.mp4`
Mode: `AI_MODE=live`, provider `openai`

## Verdict

End-to-end Product Run is not ready to call usable yet.

The real OpenAI key worked and the pipeline produced useful partial intelligence:

- Quick TikTok scorer completed in live mode.
- Two Creative DNA runs completed in live mode.
- Creative DNA extracted specific, evidence-linked content from the uploaded video.

But the full seller/client flow did not complete:

- `adaptation_generate` failed with `OPENAI_INCOMPLETE`.
- No PatternKit, ViralKit, Campaign Pack, Preflight, seller summary, or creator/client final output was generated in this run.
- The isolated workspace cleanup also failed because the API connection was gone during failure handling.

## Artifacts

- Raw smoke result: `/Users/mac/Desktop/Viraldy/artifacts/live-product-run/live-product-run-20260806T021318Z.json`
- DB/model evidence log: `/Users/mac/Desktop/Viraldy/artifacts/live-product-run/live-product-run-20260806T021318Z.evidence.json`
- Frontend screenshot: `/Users/mac/Desktop/Viraldy/artifacts/live-product-run/screenshots/live-product-run-20260806T021318Z-frontend-home.png`
- Login/local demo screenshot: `/Users/mac/Desktop/Viraldy/artifacts/live-product-run/screenshots/live-product-run-20260806T021318Z-login-result.png`
- AI readiness screenshot: `/Users/mac/Desktop/Viraldy/artifacts/live-product-run/screenshots/live-product-run-20260806T021318Z-ai-readiness.png`
- Report screenshot: `/Users/mac/Desktop/Viraldy/artifacts/live-product-run/screenshots/live-product-run-20260806T021318Z-report-md.png`
- Evidence JSON screenshot: `/Users/mac/Desktop/Viraldy/artifacts/live-product-run/screenshots/live-product-run-20260806T021318Z-evidence-json.png`

No Product Run step-by-step UI screenshot was captured for this run. The backend smoke flow was executed through HTTP/API, and it failed at `adaptation` before seller/client Product Run result screens existed. A later Chrome headless attempt to open `/mvp` after login did not complete rendering within the tool window, so this report should not be read as UI-qualified.

## Screenshots

![Frontend home](/Users/mac/Desktop/Viraldy/artifacts/live-product-run/screenshots/live-product-run-20260806T021318Z-frontend-home.png)

![Login/local demo](/Users/mac/Desktop/Viraldy/artifacts/live-product-run/screenshots/live-product-run-20260806T021318Z-login-result.png)

![AI readiness](/Users/mac/Desktop/Viraldy/artifacts/live-product-run/screenshots/live-product-run-20260806T021318Z-ai-readiness.png)

## Run Result

Smoke result:

```json
{
  "status": "error",
  "mode": "live",
  "failure_stage": "adaptation",
  "safe_error_code": "SMOKE_FLOW_FAILED",
  "safe_error_type": "SmokeFailure",
  "workspace_deletion_status": "failed",
  "cleanup_safe_error_type": "ConnectError"
}
```

AI readiness before the run:

```json
{
  "mode": "live",
  "provider": "openai",
  "state": "not_yet_qualified",
  "configured": true,
  "capabilities": {
    "text_chat": true,
    "vision_chat": true,
    "audio_transcription": true,
    "json_schema": true,
    "image_url": false,
    "base64_image": true
  },
  "missing": []
}
```

## Model Run Summary

- Total model run records: `11`
- Completed: `10`
- Failed: `1`
- Known GPT-5 tokens logged: `140495`
- Audio transcription calls: `4`
- GPT-5 media/creative/adaptation calls: `7`

Important operations:

| Operation | Status | Model | Repair attempts | Latency | Notes |
| --- | --- | --- | ---: | ---: | --- |
| `media_observation` | completed | `gpt-5` | 1 | 113744 ms | quick scorer, validator repaired first output |
| `creative_dna_build` | completed | `gpt-5` | 1 | 152287 ms | reference 1, 40 evidence items |
| `media_observation` | completed | `gpt-5` | 1 | 157373 ms | reference 2, validator repaired first output |
| `creative_dna_build` | completed | `gpt-5` | 0 | 56132 ms | reference 2, 40 evidence items |
| `adaptation_generate` | failed | `gpt-5` | 0 | n/a | `OPENAI_INCOMPLETE` |

## Content Log

### Quick Scorer

```json
{
  "structural_score": 87,
  "action": "structurally_ready",
  "confidence": "medium",
  "analysis_mode": "live"
}
```

There was also a frontend-triggered score job during the same worker session:

```json
{
  "structural_score": 94,
  "action": "structurally_ready",
  "confidence": "medium",
  "analysis_mode": "live"
}
```

This extra job likely came from the open local frontend and increased elapsed time/cost. Future qualification runs should isolate the worker/API from active UI sessions.

### Creative DNA Observations

The analyzer recognized the uploaded video as a scent booster / Febreze Plug style reference, not as the isolated test product category. Useful extracted content included:

- Spoken CTA: "You can find the Febreze plug scent booster, my hosting must have, at your local retailer."
- Demo type: `usage`
- Demo steps: close-up device in hands, device placed on table with power/light visible, top control/boost gesture, operating device while guests socialize.
- Product first appearance: about `38880 ms`
- Offer/price: not present or unknown.
- TikTok product tag: not visible.
- Proof type: testimonial.
- Strongest proof: guest says the room smells fresh.
- Proof strength: weak to weak/moderate because freshness is not visually verifiable.
- Key risk: off-platform CTA/local retailer and no visible TikTok Shop tag.

This is not generic. It is specific to the video and useful for creative diagnosis.

### Validator/Repair Log

Deterministic validation did real work:

- Media observation rejected an output where product first appearance did not match earliest appearance.
- Creative DNA rejected an output where `not_present` values missed evidence IDs.
- Both Creative DNA runs eventually passed with evidence links.

This is valuable intelligence infrastructure. The issue is stability/latency and adaptation failure, not absence of intelligence.

## Seller Usability

Current seller value: partially useful.

What a seller can use now:

- "This video is structurally ready" with score/confidence.
- The reference depends on testimonial proof more than observable proof.
- No TikTok Shop tag/offer/price is visible.
- CTA points to local retailer, which is misaligned for TikTok Shop affiliate/seller flow.
- Demo shows usage and device activation, but the result is hard to verify visually.

What is missing for seller use:

- No seller decision summary generated.
- No adaptation to the product context.
- No PatternKit/ViralKit.
- No campaign pack or creator-ready brief.
- No final approval/reshoot recommendation from the Product Run.

Seller output is not ready as a complete workflow yet.

## Client/Creator Usability

Current client/creator value: not ready as final output.

The system did not reach Campaign Pack or Preflight, so there is no creator-facing script, shot list, revision message, or client approval package from this run.

## Blockers

1. `adaptation_generate` needs retry/recovery for `OPENAI_INCOMPLETE`.
2. Smoke harness should capture partial successful outputs even when later stages fail.
3. Isolated cleanup should run reliably even if the API shuts down or the HTTP client loses connection.
4. Qualification runs should ensure no frontend/user-triggered jobs share the same worker queue.
5. Smoke harness was patched to normalize TikTok score detail shape because API returns detail under `score_run`.

## Recommendation

Do not present this as a completed full Product Run yet.

The next implementation pass should focus on adaptation resilience and partial-output reporting:

- Add bounded retry for incomplete OpenAI responses on `adaptation_generate`.
- Persist and expose a partial run report after any stage failure.
- Add a Product Run status page section that says exactly which stage failed and shows completed Creative DNA evidence.
- Add a single-run qualification command that prevents other UI jobs from using the worker queue during live qualification.
