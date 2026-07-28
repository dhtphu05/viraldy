# Viraldy Web

TanStack Start + Vite frontend prototype for Viraldy. This app currently runs from mock data only; backend/API integration is intentionally out of scope for this phase.

## Commands

```bash
pnpm install
pnpm dev
pnpm lint
pnpm build
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
