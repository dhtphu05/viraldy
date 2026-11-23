# Viraldy Web

TanStack Start + React + Vite frontend for Viraldy, including Creative Library,
Smart Remake, and workspace management.

Use the shared guides rather than maintaining a second set of setup instructions:

- [Project overview and quick start](../../README.md)
- [Local development and environment setup](../../docs/runbooks/LOCAL_DEVELOPMENT.md)
- [Authentication contract](../../docs/frontend-integration/AUTH_CONTRACT.md)
- [Deployment](../../docs/runbooks/DEPLOYMENT.md)

After completing the local setup, run `make web-dev` from the repository root.
The frontend listens on `http://localhost:5173`.

Run frontend checks from `apps/web`:

```bash
pnpm typecheck
pnpm test
pnpm lint
pnpm build
```
