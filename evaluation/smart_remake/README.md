# Smart Remake captured evidence

This harness is separate from PatternKit/ViralKit evaluation. It validates retained
inputs, all attempts, media hashes, selected-range mappings and human ratings,
then recomputes deterministic reports **without provider calls**.

Official B0/B1/B2 and the three ablations are pending authoritative definitions.
`protocol-pending.json` preserves the planned `20 × 3 + 8 × 3` matrix. Unknown
selectors are rejected. Development fixtures never qualify this official corpus.

Run from `apps/backend`:

```sh
uv run python scripts/evaluate_smart_remake.py dev-corpus --output-dir /tmp/remake-dev-unique
uv run python scripts/evaluate_smart_remake.py validate /tmp/remake-dev-unique/bundle.json
uv run python scripts/evaluate_smart_remake.py replay /tmp/remake-dev-unique/bundle.json --output-dir /tmp/remake-dev-unique/report
uv run python scripts/evaluate_smart_remake.py blind /tmp/remake-dev-unique/bundle.json --seed locked-review-order-v1 --output /tmp/remake-dev-unique/blind-map.json
```

Prepare a separate, fresh **input-only** package for an internal provider pilot:

```sh
uv run python scripts/evaluate_smart_remake.py prepare-pilot-inputs --output-dir /tmp/remake-pilot-inputs-unique
uv run python scripts/evaluate_smart_remake.py validate /tmp/remake-pilot-inputs-unique/bundle.json
```

This creates new original source/product/illustrated-character/audio assets,
8-second and 16-second planned cases, and authorship/scope hashes. Scope permits
internal AI-provider pilot processing after an explicit user cap and disclosure;
it grants no publishing or advertising use. The input-only manifest records
`cap_usd: null`, `authorized: false` and disclosure pending. `mode: live` means
intended future execution **with zero captures**, not a completed provider run.
It creates no generated output, receipt or score and never relabels fixture media.
Use [the pilot runbook](PILOT_RUNBOOK.md) before any separately authorized run.

Choose a fresh directory. The generator creates an original illustrated bottle,
an illustrated character representing no real person, static showcase video and
a mathematical tone. Rights metadata records authorship and internal fixture use;
it does not claim seller consent, provider clearance or live quality. Pass,
needs-repair and intentionally rights-blocked cases have fixture expectations;
human ratings start empty. Generated media and reports belong outside Git.

`rubric-v1.json` describes independent human judgments. Import `HumanRating`
records plus the retained blind assignment mapping into `bundle.json`; bind every
rating to exact output hash, rubric, reviewer and UTC annotation time. Keep the
mapping separate from the rater-facing anonymized videos. Character is N/A where
not requested. Checker false-positive/false-negative rates are unmeasured until
human labels exist. The rates count reviewer/category judgments, and conflicting
judgments require adjudication. No model score is a correctness probability.

Capture uses the versioned public runtime export:

```sh
uv run python scripts/evaluate_smart_remake.py capture /path/to/retained-bundle.json --provenance /path/to/public-provenance.json --context /path/to/capture-context.json --output /path/to/captured.json
```

The runtime adapter maps A's documented `smart_remake_provenance_v1` projection
(`project`, `run`, `inputs`, `attempts`, `assemblies`, `inspections`, `release`,
`stageTimings`, `failures`) without reading private lifecycle JSON. Retain source,
product/character, raw clips and final assembly bytes under the bundle root first;
their hashes must match the public export. Capturing cannot manufacture missing
media. Start a new bundle without synthetic captures for an application run.

`capture-context.json` uses `RuntimeCaptureContext`: `case_id`, `run_id`,
`variant_id`, `mode`, optional `phase`/`parent_run_id`/`assembly_id`, optional
`code_version`, `config_version`, `prompt_versions`. Context supplies the explicit
manifest-to-project mapping; conflicting non-null runtime IDs are rejected.
Null runtime versions remain null unless the operator supplies independently
recorded versions in the context. The complete sanitized public export is retained
alongside normalization, so operator context is distinguishable from runtime data.

`fixture`/`mock` context records controlled fake-provider execution; it never proves
live calls. Live capture additionally requires public `run.mode: live`, genuine
provider receipts and valid release/report bindings. `run.serverMode` and
`run.providerExecution` describe configuration/uncertainty and cannot upgrade a
missing verified mode. If a runtime export lacks
mode, live capture fails closed. Shared provider-independent Inspector validation
checks actual retained bytes, identities, hashes, clocks, observations, coverage
and required checks. Evidence frame image retention/extraction specifications
must accompany a live qualification bundle; this harness never auto-declares live
verification. Secret fields and signed URL queries are removed on capture/report.

Previously normalized captures can be imported without `--context` using a
separate envelope `schemaVersion: smart_remake_capture_v1` plus `captures`.
This retained-record format is distinct from A's runtime projection.

Shared attempt IDs may appear in parent/repair captures only with identical
provenance; totals count them once. All failed/unknown attempts remain included.
Cost per accepted output is unmeasured when cost is unknown/estimated or there
are zero accepted outputs. Reports retain missing labels and incomplete runs.

Live pilot preflight is deliberately read-only:

```sh
uv run python scripts/evaluate_smart_remake.py pilot-check /path/to/live-bundle.json --cap-usd USER_APPROVED_DECIMAL --authorized
```

There is no default budget, no batch-84 runner and no paid execution in this
script. Supply actual rights-backed development cases, applicable consent and an
explicit user-approved cap; then use the normal application API, which reserves
budget and records receipts before each model call. `--authorized` records an
operator assertion; it cannot substitute for user authorization. Fixture assets
are offline-only. Self-authored pilot inputs can be prepared without seller materials;
an approved numeric cap and disclosure remain required before live submission.
Ready-for-live-pilot and live-verified are distinct: this replay never declares
live verification automatically.
