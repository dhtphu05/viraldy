# Internal Smart Remake pilot preparation

Run from `apps/backend`:

```sh
uv run python scripts/evaluate_smart_remake.py prepare-pilot-inputs --output-dir /tmp/remake-pilot-inputs-unique
uv run python scripts/evaluate_smart_remake.py validate /tmp/remake-pilot-inputs-unique/bundle.json
```

The package contains fresh, self-authored drawings/video/audio, with no model call
or generated result. It is separate from the offline pass/repair/blocked fixtures.
Its conditional scope covers internal AI-provider processing after user spend-cap
approval and provider disclosure. No real person is depicted; no human likeness
consent or publishing permission is asserted.

| Planned case | Timeline | Required inputs |
| --- | --- | --- |
| `pilot-product` | `2+6` seconds, one raw group | `source-product.mp4`, `product.png`, source audio |
| `pilot-illustrated-character` | `3+5+4+4`, two raw groups | `source-character.mp4`, `product.png`, `illustrated-character.png`, source audio |

Both cases preserve the illustrated blue bottle and amber cap. The second also
preserves the illustrated character. These static showcases exercise reference
binding and lifecycle; hand motion, occlusion and real seller product fidelity
remain separate unmeasured cases. Character is N/A in the product-only case.

1. Record the explicit user-approved USD cap, attempt/time limits and server stage
   cost bounds. No numeric live cap is provided by this package. Leave the package
   at `inputs_prepared_awaiting_cap_and_disclosure` until these are available.
2. Use the normal Smart Remake UI/API to create the owned intake with source,
   product, optional illustrated character, authorship declarations and provider
   disclosure acknowledgement. Intake must make zero model calls. Do not set
   consent for a real person or copy verification fields from a GET response.
3. Confirm exact source range/cuts and requirements; record code/config/prompt/model
   versions and frozen plan before generation. Use only the current budgeted
   pipeline. Unknown submission/receipt or billing requires reconciliation, never
   blind resubmission. No batch 84 is authorized by this runbook.
4. Retain every attempt, failure, raw clip/version, selected range, assembly,
   inspection/review and checked export. Obtain the authenticated public
   `/projects/{id}/provenance`; retain local artifact bytes using authorized review
   access. Never print signed URLs or secrets. Preserve both the inspected assembly
   bytes and separately labeled export bytes; their hashes can differ.
5. Create an explicit `RuntimeCaptureContext` for the development case/run/variant.
   Populate independently recorded versions or leave missing values null. Capture
   the public projection with `--context`, then `replay`/`report` offline. Test
   exports remain `mock`/`fixture`; live capture requires authoritative server mode
   plus real receipts. Missing metadata/artifacts remain visible or fail validation.
6. Blind output identities before independent human ratings. Review product,
   optional character, action, structure, claims, physics and usefulness separately.
   Preserve all judgments and adjudicate disagreements. No scores are prefilled.

Do not mark `LIVE_VERIFIED` from code, fixture results, a playable preview, a model
score or this preparation package. The official B0/B1/B2/ablation protocol remains
pending; these two internal development cases do not qualify the BTC benchmark.
