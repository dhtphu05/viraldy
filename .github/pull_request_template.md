## Summary

## Test Plan

## Security Notes

## Architecture Checklist

- [ ] Business logic is not in routers.
- [ ] Repository queries for business resources are scoped by `workspace_id`.
- [ ] Cross-module calls use `public.py`.
- [ ] No module imports another module's `models.py`, `repository.py`, `service.py`, or internal provider code.
- [ ] No business state is stored in RAM.
- [ ] Worker tasks pass stable IDs only and do not carry binary or large payloads through Redis.
- [ ] Worker tasks stay thin and delegate durable work to services/repositories.
- [ ] Tokens, secrets, and full presigned URLs are not logged.
- [ ] Database changes include a new Alembic migration.
- [ ] Business rules have tests.
- [ ] API contract changes are intentional and documented.
- [ ] No unnecessary abstraction, generic repository, command bus, or query bus was added.
- [ ] Error codes and HTTP status codes remain stable unless intentionally changed.
