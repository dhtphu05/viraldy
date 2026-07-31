# Viraldy

Vertical Creative Intelligence & Iteration OS backend foundation for TikTok Shop US, POD, dropshipping, and cross-border ecommerce sellers.

This repository is a greenfield Viraldy foundation. ViralScore is legacy/frozen and is not a runtime dependency.

## Quick Start

1. Install `uv`.
2. Copy `.env.example` to `.env`.
3. Start local infrastructure:
   ```bash
   make infra-up
   ```
4. Install backend dependencies:
   ```bash
   make backend-install
   ```
5. Run migrations:
   ```bash
   make migrate
   ```
6. Seed local data:
   ```bash
   make seed
   ```
7. Start the API:
   ```bash
   make api
   ```
8. Start the worker in another shell:
   ```bash
   make worker
   ```
9. Check health:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/ready
   ```
10. Run the backend smoke test:
    ```bash
    make smoke
    ```
11. Export OpenAPI:
    ```bash
    make openapi
    ```

## Local Auth

For local development, set `AUTH_MODE=local_test` and send:

```http
Authorization: Bearer local-test
```

The seed command creates the matching local user and workspace. Production fails fast if `AUTH_MODE=local_test` or `AUTH_DISABLED=true`.

## Processes

- `viraldy-api`: FastAPI stateless control plane.
- `viraldy-worker`: Celery compute plane.
- PostgreSQL: source of truth.
- Redis: queue, coordination, cache.
- MinIO/S3-compatible storage: binary media.

The TanStack frontend lives in `apps/web`; run `make web-install` and
`make web-dev` after the API is available. See
[apps/web/README.md](apps/web/README.md).
