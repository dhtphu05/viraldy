# Viraldy Web

TanStack Start + Vite frontend for Viraldy. `/ugc-review` is wired end to end to
the workspace-scoped UGC Review API, including immutable upload/revision,
processing progress, recommendation actions, evidence seeking, and Draft 1 →
Draft 2 comparison. Some unrelated legacy feature screens still use seeded mock
data.

## Commands

```bash
pnpm install
pnpm dev
pnpm lint
pnpm exec tsc --noEmit
pnpm test
pnpm build
```

Local API configuration:

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

The browser never receives a configured development bearer token. In local-test mode, use the
button on `/login`; the TanStack server route creates an HttpOnly session cookie. Production uses
OIDC Authorization Code + PKCE with `/api/auth/callback` as the callback URL. Configure the public
OIDC endpoints and client ID on the backend with the `OIDC_*` variables in the root `.env.example`.
The provider must issue `email`, `name`, and E.164 `phone_number` claims, plus boolean
`email_verified=true` and `phone_number_verified=true`. Include `offline_access` so the provider
can issue a refresh token for a durable session.

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
