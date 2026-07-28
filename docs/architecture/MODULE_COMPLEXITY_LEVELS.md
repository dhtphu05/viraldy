# Module Complexity Levels

Viraldy uses a lean modular monolith. Start every module flat and add deeper structure only when the domain actually needs it.

## Level 1: Simple CRUD

Use for straightforward resources such as `products`, `workspaces`, and recommendation actions.

Files:

- `models.py`
- `schemas.py`
- `repository.py`
- `service.py`
- `router.py`
- `public.py` only if another module calls it
- `validators.py` only when validation is shared or non-trivial

Rules:

- Repository methods must scope business resources by `workspace_id`.
- Service owns transaction boundaries.
- Router parses/authenticates/calls service only.
- No command/query objects, mapper layer, domain entity copy, generic repository, or handler class.

## Level 2: Business Workflow

Use for modules with state transitions, background work, or provider coordination, such as `assets` and `jobs`.

Additional files allowed:

- `policies.py`
- `validators.py`
- `dispatcher.py`
- `public.py`

Rules:

- Workflow state changes live in services or policies.
- Celery tasks stay thin and call module services/repositories with stable IDs.
- External providers stay behind adapters such as storage, auth, queue, and model gateway.

## Level 3: Complex Domain

Reserved for future modules such as `creative_genome`, `preflight`, `performance`, campaigns, rights, and sample ROI when rules become genuinely complex.

Allowed only when justified:

- `domain/`
- explicit entities
- explicit mappers
- richer policy/rule objects

Do not create Level 3 folders as placeholders.
