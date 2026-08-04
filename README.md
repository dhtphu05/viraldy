# Viraldy

Viraldy là nền tảng Vertical Creative Intelligence & Iteration OS cho seller TikTok Shop US, POD, dropshipping và cross-border ecommerce. Repo này chứa backend API, worker xử lý nền, hạ tầng local và frontend dashboard phục vụ các luồng phân tích creative như TikTok Scorer và UGC Review.

ViralScore là hệ thống legacy/frozen. Dự án này không phụ thuộc runtime vào ViralScore.

## Nội Dung Repo

| Khu vực | Mục đích |
| --- | --- |
| `apps/backend` | FastAPI API, Celery worker, domain modules, Alembic migrations, test/evaluation scripts |
| `apps/web` | TanStack Start + Vite frontend |
| `docs` | ADR, kiến trúc, runbook vận hành và hướng dẫn phát triển |
| `infrastructure/docker` | Dockerfile backend |
| `docker-compose.yml` | PostgreSQL, Redis, MinIO và các service backend local |
| `Makefile` | Lệnh tắt cho install, dev, test, lint, migration, smoke |

## Tech Stack

| Layer | Công nghệ chính |
| --- | --- |
| Backend | Python 3.12, FastAPI, Pydantic, SQLAlchemy async, Alembic |
| Worker | Celery, Redis |
| Database | PostgreSQL 16 |
| Object storage | MinIO/S3-compatible storage |
| Frontend | React 19, TanStack Start/Router, Vite, Tailwind CSS 4 |
| Tooling | `uv`, `pnpm`, Ruff, mypy, pytest, Vitest, ESLint |

## Yêu Cầu Cài Đặt

Cần có các công cụ sau trên máy local:

- Docker Desktop hoặc Docker Engine có Docker Compose v2.
- Python 3.12.
- `uv` cho backend Python.
- Node.js và `pnpm` cho frontend.

Cài `uv` trên macOS/Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Cài hoặc bật `pnpm` bằng Corepack:

```bash
corepack enable pnpm
```

Kiểm tra nhanh:

```bash
docker compose version
python3.12 --version
uv --version
node --version
pnpm --version
```

Tham khảo chính thức: [uv installation](https://docs.astral.sh/uv/getting-started/installation/) và [pnpm installation](https://pnpm.io/installation).

## Cài Đặt Local

Từ thư mục root của repo:

```bash
cd /Users/mac/Desktop/Viraldy
```

Tạo file môi trường cho backend:

```bash
cp .env.example apps/backend/.env
```

Tạo file môi trường cho frontend:

```bash
printf "VITE_API_BASE_URL=http://localhost:8000/api/v1\n" > apps/web/.env
```

Cài dependencies:

```bash
make backend-install
make web-install
```

Mặc định `.env.example` dùng:

- `AUTH_MODE=local_test`
- PostgreSQL local tại `localhost:5432`
- Redis local tại `localhost:6379`
- MinIO local tại `localhost:9000`
- AI fixture mode, không cần API key

Không commit các file `.env`.

## Chạy Dự Án

Khởi động hạ tầng local:

```bash
make infra-up
```

Chạy database migrations và seed dữ liệu demo:

```bash
make migrate
make seed
```

Mở 3 terminal riêng:

```bash
make api
```

```bash
make worker
```

```bash
make web-dev
```

URL mặc định:

- Frontend: <http://localhost:5173>
- API: <http://localhost:8000>
- Swagger/OpenAPI UI: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>
- Readiness check: <http://localhost:8000/ready>
- MinIO console: <http://localhost:9001>

Nếu cần chạy job bảo trì định kỳ, mở thêm terminal:

```bash
make beat
```

## Đăng Nhập Local

Local development dùng `AUTH_MODE=local_test`. Lệnh `make seed` tạo user và workspace demo tương ứng.

Trên frontend, vào <http://localhost:5173/login> và dùng nút đăng nhập local.

Khi gọi API trực tiếp, gửi bearer token:

```http
Authorization: Bearer local-test
```

Ví dụ:

```bash
curl -H "Authorization: Bearer local-test" http://localhost:8000/api/v1/workspaces
```

Production/staging không được dùng `AUTH_MODE=local_test` hoặc `AUTH_DISABLED=true`; backend sẽ fail fast khi cấu hình không an toàn.

## Kiểm Tra Sau Khi Chạy

Kiểm tra API:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

Chạy smoke test backend:

```bash
make smoke
```

Smoke test mặc định dùng fixture mode. Có thể chạy biến thể:

```bash
make smoke-fixture
make smoke-mock
```

## Lệnh Thường Dùng

Backend:

| Lệnh | Mục đích |
| --- | --- |
| `make backend-install` | Cài Python dependencies bằng `uv` |
| `make infra-up` | Chạy PostgreSQL, Redis, MinIO |
| `make infra-down` | Dừng hạ tầng local |
| `make api` | Chạy FastAPI dev server |
| `make worker` | Chạy Celery worker |
| `make beat` | Chạy Celery beat |
| `make migrate` | Upgrade database tới Alembic head |
| `make migration name="message"` | Tạo Alembic migration mới |
| `make downgrade` | Rollback 1 migration |
| `make seed` | Seed user/workspace/product demo |
| `make openapi` | Export OpenAPI vào `docs/api/openapi.json` |
| `make lint` | Ruff check backend |
| `make format` | Ruff format backend |
| `make typecheck` | mypy backend |
| `make test` | pytest backend |
| `make test-unit` | Unit tests backend |
| `make test-integration` | Integration tests backend |
| `make test-contract` | Contract tests backend |
| `make security` | Bandit và pip-audit |

Frontend:

| Lệnh | Mục đích |
| --- | --- |
| `make web-install` | Cài frontend dependencies |
| `make web-dev` | Chạy Vite/TanStack dev server |
| `make web-lint` | ESLint frontend |
| `make web-build` | Build frontend |
| `cd apps/web && pnpm test` | Vitest |
| `cd apps/web && pnpm typecheck` | TypeScript check |
| `cd apps/web && pnpm format` | Prettier format |

Docker:

| Lệnh | Mục đích |
| --- | --- |
| `make docker-build` | Build image backend local |
| `docker compose up --build api worker beat` | Chạy backend stack bằng Docker |
| `make logs` | Theo dõi logs `api` và `worker` |

Lưu ý: các service `api`, `worker`, `beat` trong `docker-compose.yml` đọc env từ `apps/backend/.env`.

## Chạy Bằng Docker Cho Backend

Local dev khuyến nghị chạy API/worker bằng `make api` và `make worker` để reload nhanh. Nếu muốn chạy backend hoàn toàn qua Docker:

```bash
cp .env.example apps/backend/.env
docker compose up -d postgres redis minio minio-init
docker compose build api worker beat
docker compose run --rm api alembic upgrade head
docker compose run --rm api python scripts/seed_local.py
docker compose up --build api worker beat
```

Frontend vẫn chạy riêng:

```bash
make web-install
make web-dev
```

## AI Mode

Mặc định local dùng fixture mode:

```env
AI_MODE=fixture
```

Chế độ này deterministic, không gọi provider và không cần API key.

Để dùng OpenAI live, merge cấu hình từ `.env.openai.example` vào `apps/backend/.env`, điền `OPENAI_API_KEY`, rồi kiểm tra readiness:

```bash
cd apps/backend
uv run python scripts/check_ai_readiness.py
```

Chỉ chạy live qualification khi thật sự cần vì sẽ gọi model thật. Xem thêm:

- `docs/runbooks/AI_PROVIDER_READINESS.md`
- `docs/runbooks/OPENAI_PROVIDER.md`
- `docs/runbooks/OPENAI_LIVE_QUALIFICATION.md`

## Cấu Trúc Chính

Backend:

- `src/viraldy/api/main.py`: entry point FastAPI, middleware, router registration.
- `src/viraldy/modules`: domain modules như products, assets, jobs, TikTok Scorer, UGC Review, AI gateway.
- `src/viraldy/platform`: config, auth, database, storage, observability, queue.
- `src/viraldy/worker`: Celery app và background tasks.
- `alembic/versions`: database migrations.
- `tests`: unit, integration, contract và architecture tests.

Frontend:

- `src/routes`: TanStack file routes.
- `src/features`: feature slices.
- `src/shared/api`: API clients và response envelope handling.
- `src/shared/ui`: UI primitives.
- `src/widgets/app-shell`: app shell, navigation, workspace switcher.

## Tài Liệu Nên Đọc Tiếp

- `apps/web/README.md`: chi tiết frontend.
- `docs/architecture/SYSTEM_ARCHITECTURE.md`: sơ đồ hệ thống.
- `docs/architecture/MODULE_BOUNDARIES.md`: ranh giới module backend.
- `docs/development/ADDING_AN_ENDPOINT.md`: thêm endpoint mới.
- `docs/development/ADDING_A_JOB.md`: thêm background job.
- `docs/development/ADDING_A_MIGRATION.md`: thêm migration.
- `docs/runbooks/LOCAL_DEVELOPMENT.md`: runbook local.
- `docs/runbooks/DEPLOYMENT.md`: triển khai.
- `docs/runbooks/OBJECT_STORAGE.md`: object storage và retention.
- `SECURITY.md`: nguyên tắc bảo mật.

## Troubleshooting

Backend không đọc env:

- Đảm bảo file nằm ở `apps/backend/.env`.
- `make api`, `make migrate`, `make seed` đều chạy trong `apps/backend`, nên root `.env` không đủ cho backend.

Frontend không gọi được API:

- Đảm bảo API đang chạy ở `http://localhost:8000`.
- Kiểm tra `apps/web/.env` có `VITE_API_BASE_URL=http://localhost:8000/api/v1`.
- Đăng nhập lại ở `/login` nếu gặp `401`.

Database hoặc Redis không kết nối:

```bash
make infra-up
docker compose ps
```

Port `8000` bị chiếm:

```bash
API_PORT=8001 make api
printf "VITE_API_BASE_URL=http://localhost:8001/api/v1\n" > apps/web/.env
make web-dev
```

Muốn reset toàn bộ dữ liệu local:

```bash
docker compose down -v
make infra-up
make migrate
make seed
```
