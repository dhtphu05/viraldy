# Viraldy Web

TanStack Start + Vite frontend prototype for Viraldy. Most legacy feature screens still use
seeded mock data, while `/mvp` is wired to the backend MVP APIs for fixture/live Creative
Intelligence flows.

## Commands

```bash
pnpm install
pnpm dev
pnpm lint
pnpm build
```

Local API configuration:

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_LOCAL_AUTH_TOKEN=local-test
```

Root shortcuts:

```bash
make web-install
make web-dev
make web-lint
make web-build
```

## Structure

- `src/app` - router, root routes, global styles, app-level store.
- `src/routes` - TanStack file-route wrappers only.
- `src/features` - feature slices for dashboard, campaigns, creative library, UGC review, performance, products, and settings.
- `src/widgets` - composed application widgets such as the app shell.
- `src/shared` - UI primitives, shared hooks, utilities, shared mocks, and shared types.

## Deployment Baseline

- Build toolchain is direct Vite/TanStack Start configuration in `vite.config.ts`.
- Production build emits Nitro Cloudflare module output.
- Platform-specific sandbox bridge plugins and editor-owned error hooks are not part of this app.
