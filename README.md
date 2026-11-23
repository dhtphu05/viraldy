# Viraldy

Viraldy là nền tảng hỗ trợ đội ngũ thương mại điện tử phân tích creative và phát triển nội dung quảng cáo sản phẩm. Tính năng **Smart Remake** giúp biến một video tham khảo thành hướng triển khai video mới, tập trung vào sản phẩm và thương hiệu của bạn.

## Smart Remake

Smart Remake dành cho những lúc bạn đã tìm được một video có cách mở đầu, nhịp dựng hoặc cách trình bày đáng học hỏi, nhưng cần chuyển ý tưởng đó thành creative phù hợp với sản phẩm của mình.

### Giá trị mang lại

- Rút ngắn quá trình từ video tham khảo đến một kịch bản quảng cáo có thể duyệt và triển khai.
- Giữ sản phẩm làm trọng tâm, đồng thời đưa các yêu cầu về thương hiệu, thông điệp và phong cách vào cùng một brief.
- Xem trước cấu trúc từng cảnh và toàn bộ prompt trước khi tạo video để dễ kiểm tra, chỉnh hướng sáng tạo và phối hợp trong nhóm.
- Tạo nội dung video dọc 9:16 theo hai lựa chọn thời lượng: 8 giây hoặc 16 giây.

Smart Remake hỗ trợ quá trình sáng tạo; kết quả quảng cáo và hiệu quả kinh doanh vẫn phụ thuộc vào sản phẩm, nội dung, đối tượng và chiến dịch.

### Ai sẽ dùng Smart Remake?

- **Seller và chủ thương hiệu thương mại điện tử** cần thường xuyên làm nội dung quảng cáo cho danh mục sản phẩm.
- **Performance marketer** muốn thử nhiều hướng creative dựa trên cấu trúc video đang thu hút sự chú ý.
- **Đội ngũ social và content** cần chuyển brief sản phẩm thành kịch bản video ngắn dễ xem và dễ duyệt.
- **Agency và đội ngũ creative** cần một quy trình thống nhất để xử lý video tham khảo, yêu cầu thương hiệu và đầu ra cho nhiều khách hàng.

### Luồng sử dụng

1. **Chọn video tham khảo** — tải video bạn muốn phân tích lên Smart Remake.
2. **Thêm sản phẩm** — tải ảnh sản phẩm lên hoặc dán đường dẫn trang sản phẩm để lấy thông tin và hình ảnh phù hợp.
3. **Định hướng nội dung** — chọn thời lượng 8 hoặc 16 giây, ngôn ngữ, hướng sáng tạo và các yêu cầu cần giữ cho sản phẩm/thương hiệu.
4. **Phân tích và xem kịch bản** — Smart Remake phân tích video cùng thông tin sản phẩm, sau đó trình bày cấu trúc cảnh, thông tin sản phẩm cần giữ và prompt đầy đủ ở dạng dễ đọc lẫn JSON.
5. **Tạo và xem video** — sau khi duyệt kịch bản, bắt đầu tạo video và xem kết quả ngay trong luồng làm việc.

Đầu ra được trình bày theo khung hình dọc 9:16. Bản 8 giây gồm một phần nội dung; bản 16 giây gồm hai phần liên tiếp.

### Kiến trúc phân tích AI

Smart Remake tách việc hiểu video tham khảo khỏi việc nhận diện sản phẩm. Backend ghép hai kết quả này ở bước biên dịch kịch bản:

```mermaid
flowchart TD
    UI[Smart Remake] --> API[POST /workspaces/{id}/smart-remake/compile]
    Video[Video tham khảo] --> API
    Product[Ảnh sản phẩm] --> API
    URL[Link sản phẩm] --> Crawl[Product Import: lấy ảnh và metadata]
    Crawl --> API
    API --> Validate[Kiểm tra loại file, dung lượng và đầu vào]
    Validate --> VideoAI[Gemini: phân tích video]
    VideoAI --> Cuts[FFmpeg: bổ sung mốc cắt cảnh]
    Cuts --> LockAI[Gemini: tạo Product Lock]
    Product --> LockAI
    LockAI --> Compile[Creative Router + Timeline Compiler]
    Cuts --> Compile
    Compile --> Guard[Chuẩn hóa, lọc prompt và kiểm tra payload]
    Guard --> Result[Product Lock + Scene Map + prompts + warnings]
    Result -. payload compile .-> Render[POST /workspaces/{id}/smart-remake/render]
    Product --> Render
    Render --> Provider[FlowKit hoặc Unifically]
    Provider --> Assemble[Ghép các cảnh, xử lý âm thanh và lưu video]
```

#### 1. Tiếp nhận và kiểm tra đầu vào

API kiểm tra quyền truy cập workspace, thời lượng đầu ra 8/16 giây, tỷ lệ đầu ra 9:16, loại file và dung lượng. Ảnh sản phẩm có thể được tải trực tiếp hoặc lấy từ đường dẫn sản phẩm qua module Product Import; tiêu đề và mô tả của trang được dùng làm metadata bổ sung.

#### 2. Phân tích video tham khảo

Gemini nhận video tham khảo cùng brief và trả về JSON có cấu trúc. Phân tích tập trung vào những gì quan sát được: hook mở đầu, loại creative, thứ tự cảnh, nhịp/cut, góc máy, chuyển động camera, hành động vật lý, hiện diện của người, trạng thái trước/sau, kết quả trình diễn và kế hoạch âm thanh. Nội dung gốc như danh tính người thật, thương hiệu, logo, caption hoặc câu thoại nguyên văn không được dùng làm nội dung cần sao chép.

FFmpeg bổ sung thông tin ranh giới cảnh khi cần để bù các cut Gemini bỏ sót. Backend chuẩn hóa JSON, kiểm tra các trường và enum, rồi tạo cảnh báo nếu cấu trúc nguồn khó chuyển thể. Nếu thông tin thiếu, các giá trị mặc định an toàn được dùng; nếu cấu trúc không phù hợp, lỗi được trả về thay vì đưa payload sai sang bước tiếp theo.

#### 3. Product Lock — khóa danh tính và cách dùng sản phẩm

Gemini phân tích ảnh sản phẩm riêng, kết hợp với metadata và các yêu cầu người dùng để tạo `Product Lock`. Đây là hợp đồng mô tả sản phẩm được truyền xuyên suốt vào từng prompt/cảnh:

| Nhóm thuộc tính        | Nội dung được giữ hoặc kiểm soát                                                                              |
| ---------------------- | ------------------------------------------------------------------------------------------------------------- |
| Nhận diện hình ảnh     | Tên, loại sản phẩm, màu, hình dáng, tỷ lệ, hoa văn, chất liệu, kết cấu, thành phần và branding nhìn thấy được |
| Những gì phải giữ      | `mustPreserve` liệt kê các chi tiết quan trọng có căn cứ trong ảnh hoặc brief                                 |
| Những gì được thay đổi | `canChange` ghi nhận các yếu tố người dùng cho phép thay đổi                                                  |
| Cách sử dụng           | Điểm cầm/tiếp xúc, bề mặt phù hợp, tỷ lệ, hướng thao tác và giới hạn vật lý hợp lý                            |
| Lỗi cần tránh          | Ví dụ: đổi màu, sai tỷ lệ, thiếu/lặp bộ phận, tự thêm logo hoặc thao tác không khả thi                        |

Thứ tự ưu tiên được thiết kế rõ ràng: **ảnh sản phẩm quyết định sản phẩm nào xuất hiện; video tham khảo quyết định cách trình diễn và kết quả cần thể hiện; metadata/brief bổ sung thông tin nhưng không được phép bịa thuộc tính ẩn, giá, chứng nhận hay tuyên bố hiệu quả.** Khi công dụng chưa rõ, ràng buộc cách dùng được giữ thận trọng thay vì tự nghĩ ra một công dụng mới. Backend hỗ trợ chế độ `off`, `auto`, `strict`; luồng giao diện hiện dùng `auto` mặc định. `off` bỏ các danh sách `mustPreserve` và `forbiddenErrors` do AI tạo, nhưng ảnh sản phẩm vẫn là ảnh tham chiếu cho danh tính sản phẩm.

Product Lock là một hợp đồng dữ liệu và ràng buộc bằng ngôn ngữ tự nhiên gửi tới model, không phải bảo đảm đồng nhất tuyệt đối từng pixel. Các prompt render nhấn trực tiếp vào ảnh tham chiếu, nhận diện hình ảnh, `mustPreserve` và hướng dẫn sử dụng; các trường như `canChange` và `forbiddenErrors` cũng được trả về để xem xét nhưng không phải trường nào cũng được renderer áp thành một luật độc lập. Vì vậy, đầu ra cuối vẫn cần được kiểm tra bằng mắt.

#### 4. Chọn cấu trúc và biên dịch cảnh

Creative Router phân loại cấu trúc như trình diễn sản phẩm, vấn đề–giải pháp, trước–sau, biến đổi, mở hộp, so sánh hoặc quay liên tục rồi chọn chiến lược phù hợp. Timeline Compiler chuyển kết quả thành các cảnh dọc 8 giây: bản 8 giây có một cảnh, bản 16 giây chia thành hai cảnh theo đúng thứ tự nguồn.

Khi có shot boundary, thời lượng các shot được co giãn để vừa timeline mà vẫn giữ thứ tự và hành động nguồn. Khi chỉ có motion beats, compiler ưu tiên hook và các hành động/kết quả bắt buộc; beat phụ có thể được gộp hoặc bỏ để phù hợp thời lượng. Nếu vẫn quá dày hoặc nguồn có bố cục khó xử lý như split-screen, screen recording, nhiều sản phẩm, hook phụ thuộc caption/thoại hay comparison, hệ thống chọn cách chuyển thể gần nhất và trả về cảnh báo giải thích phần cần đơn giản hóa.

Mỗi cảnh có shot plan cùng các prompt riêng cho nội dung, tạo khung hình và chuyển động video. Prompt Sanitizer kiểm tra các nội dung bị cấm sao chép; renderer còn xác thực scene count, product identity reference và payload trước khi gửi tới dịch vụ tạo video.

#### 5. Tạo video và kiểm soát Product Lock

Backend tách hai API: `/compile` trả về phân tích, `Product Lock`, `Scene Map`, prompt và cảnh báo; `/render` nhận kết quả compile cùng ảnh sản phẩm và nhà cung cấp render. Toàn bộ file video tham khảo không được đưa vào payload tạo video. Nhà cung cấp nhận ảnh sản phẩm làm nguồn nhận diện, cùng scene plan/prompt đã biên dịch; các ràng buộc về hình dáng, màu, thành phần, thao tác và tính nhất quán được lặp lại trong prompt từng cảnh.

- **FlowKit:** tạo project/character từ ảnh sản phẩm, tạo ảnh cho các cảnh, sau đó tạo video theo scene và ghép kết quả theo thứ tự.
- **Unifically:** gửi prompt và ảnh sản phẩm cho từng scene, chờ trạng thái hoàn tất rồi ghép các đoạn video; kế hoạch âm thanh và lưu trữ được xử lý ở bước hoàn thiện.

Các lỗi định dạng JSON có bước yêu cầu Gemini sửa lại theo schema; lỗi quota hoặc lỗi máy chủ tạm thời được retry có giới hạn. Mọi cảnh báo về cấu trúc, độ dày shot hoặc yêu cầu không thể giữ nguyên được trả về cùng kết quả để người dùng xem trước.

## Các thành phần chính

| Khu vực                 | Vai trò                                                               |
| ----------------------- | --------------------------------------------------------------------- |
| `apps/web`              | Giao diện Viraldy, xây dựng bằng React, TanStack Start/Router và Vite |
| `apps/backend`          | API FastAPI, các module nghiệp vụ, migration và Celery worker         |
| `docs`                  | Tài liệu kiến trúc, phát triển và vận hành                            |
| `infrastructure/docker` | Dockerfile backend                                                    |
| `docker-compose.yml`    | PostgreSQL, Redis, MinIO và các dịch vụ local                         |

### Công nghệ

- Backend: Python 3.12, FastAPI, Pydantic, SQLAlchemy async và Alembic
- Background jobs: Celery và Redis
- Database: PostgreSQL 16
- Object storage: MinIO / S3-compatible storage
- Frontend: React 19, TanStack Start/Router, Vite và Tailwind CSS 4
- Tooling: `uv`, `pnpm`, Ruff, mypy, pytest, Vitest và ESLint

## Chạy Viraldy local

### Yêu cầu

- Docker Desktop hoặc Docker Engine với Docker Compose v2
- Python 3.12 và `uv`
- Node.js và `pnpm`

Cài `uv` trên macOS/Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Bật `pnpm` bằng Corepack nếu máy chưa có:

```bash
corepack enable pnpm
```

### Cài đặt

Tạo file cấu hình backend lần đầu. Nếu `apps/backend/.env` đã tồn tại, bỏ qua bước sao chép và cập nhật file hiện tại:

```bash
cp .env.example apps/backend/.env
```

Đăng ký/đăng nhập email và mật khẩu dùng `AUTH_MODE=password`. Tạo khóa ký JWT riêng bằng lệnh sau, rồi điền kết quả vào `AUTH_JWT_SECRET` trong `apps/backend/.env`:

```bash
openssl rand -hex 32
```

Giữ nguyên khóa qua các lần khởi động và dùng cùng khóa trên các instance backend. Không đưa khóa vào mã nguồn hoặc cấu hình trình duyệt. PostgreSQL lưu tài khoản và phiên đăng nhập; Redis cần hoạt động để giới hạn các lần thử đăng nhập. Xem [hướng dẫn xác thực](docs/runbooks/LOCAL_DEVELOPMENT.md) cho cấu hình triển khai và kiểm thử.

Để bật phân tích Smart Remake bằng Gemini, cấu hình các mục sau trong `apps/backend/.env`:

```env
AI_MODE=live
SMART_REMAKE_ENABLED=true
GEMINI_API_KEY=your-gemini-api-key
```

Giữ API key trong file môi trường local và không đưa file này lên Git. Có thể cấu hình model qua `SMART_REMAKE_GEMINI_MODEL`; mặc định backend sử dụng `gemini-2.5-flash`.

Tạo cấu hình frontend trong `apps/web/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Cài dependencies:

```bash
make backend-install
make web-install
```

### Khởi động

Khởi động database, Redis và object storage:

```bash
make infra-up
```

Chạy migration và khởi tạo workspace local:

```bash
make migrate
make seed
```

Mở ba terminal riêng tại thư mục gốc repository:

```bash
make api
```

```bash
make worker
```

```bash
make web-dev
```

Mở URL frontend mà lệnh `make web-dev` in ra. Các địa chỉ local mặc định:

- Viraldy: <http://localhost:5173>
- API: <http://localhost:8000>
- API documentation: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>
- Readiness check: <http://localhost:8000/ready>
- MinIO console: <http://localhost:9001>

> Với `AUTH_MODE=password`, mở trang Create account để tạo tài khoản và workspace riêng. `AUTH_MODE=local_test` chỉ dùng cho kiểm thử local; staging/production chặn chế độ này. Khi triển khai, cấu hình HTTPS và `AUTH_PUBLIC_ORIGIN` trên server frontend.

### Cấu hình dịch vụ tạo video

Backend có thể kết nối dịch vụ tạo video qua Unifically hoặc FlowKit. Khi triển khai một trong các dịch vụ này, cấu hình thông tin tương ứng trong `apps/backend/.env`:

```env
UNIFICALLY_API_KEY=your-unifically-api-key
# Hoặc địa chỉ FlowKit mà backend có thể truy cập:
FLOWKIT_URL=http://127.0.0.1:8100
```

Backend cần `ffmpeg` và `ffprobe` để xử lý media. Nếu các lệnh này không nằm trong `PATH`, có thể đặt `SMART_REMAKE_FFMPEG_PATH` và `SMART_REMAKE_FFPROBE_PATH` tới đường dẫn cài đặt trên máy.

## Kiểm tra và lệnh thường dùng

| Lệnh                                | Mục đích                                       |
| ----------------------------------- | ---------------------------------------------- |
| `make infra-up` / `make infra-down` | Khởi động / dừng dịch vụ hạ tầng local         |
| `make api`                          | Chạy API server                                |
| `make worker`                       | Chạy Celery worker                             |
| `make beat`                         | Chạy Celery beat                               |
| `make migrate`                      | Cập nhật database theo Alembic migrations      |
| `make seed`                         | Khởi tạo dữ liệu cần thiết cho local workspace |
| `make test`                         | Chạy backend tests                             |
| `make lint` / `make typecheck`      | Kiểm tra style / kiểu dữ liệu backend          |
| `make web-lint`                     | Kiểm tra frontend                              |
| `make web-build`                    | Build frontend                                 |
| `cd apps/web && pnpm test`          | Chạy frontend tests                            |
| `cd apps/web && pnpm typecheck`     | Kiểm tra kiểu dữ liệu frontend                 |

## Cấu trúc mã nguồn

```text
apps/backend/src/viraldy/api/          API entry point và router
apps/backend/src/viraldy/modules/     Các module nghiệp vụ, gồm Smart Remake
apps/backend/src/viraldy/platform/    Cấu hình, auth, database, storage và queue
apps/backend/src/viraldy/worker/      Celery app và background tasks
apps/backend/alembic/versions/        Database migrations
apps/backend/tests/                   Backend tests
apps/web/src/routes/                  TanStack file routes
apps/web/src/features/                Giao diện theo tính năng
apps/web/src/shared/api/              Frontend API clients
apps/web/src/shared/ui/               UI components dùng chung
```

## Tài liệu liên quan

- [Frontend README](apps/web/README.md)
- [Kiến trúc hệ thống](docs/architecture/SYSTEM_ARCHITECTURE.md)
- [Ranh giới module backend](docs/architecture/MODULE_BOUNDARIES.md)
- [Hướng dẫn phát triển local](docs/runbooks/LOCAL_DEVELOPMENT.md)
- [Triển khai](docs/runbooks/DEPLOYMENT.md)
- [Object storage](docs/runbooks/OBJECT_STORAGE.md)
- [Security](SECURITY.md)

## Xử lý sự cố local

- **Backend không đọc cấu hình:** kiểm tra file `apps/backend/.env`; các lệnh `make api`, `make migrate` và `make seed` chạy trong `apps/backend`.
- **Frontend không kết nối được API:** kiểm tra `VITE_API_BASE_URL` trong `apps/web/.env` và xác nhận API đang chạy.
- **Không kết nối được database hoặc Redis:** chạy `make infra-up`, sau đó kiểm tra bằng `docker compose ps`.
- **Port API mặc định đang được sử dụng:** chạy `API_PORT=8001 make api` và cập nhật frontend thành `VITE_API_BASE_URL=http://localhost:8001/api/v1`.
