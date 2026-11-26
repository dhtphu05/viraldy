# Smart Remake V2 — backlog triển khai

Ngày lập: **25/11/2026**. Nguồn yêu cầu: cuộc trò chuyện [Branch · tphu· Hanoi nam ay moi nhat](chatgpt-conversation://6b068a45-2ee0-83ec-8361-29d12b669a43), đối chiếu working tree của Viraldy. Đây là **danh sách việc cần hoàn thiện và nghiệm thu**, không phải báo cáo các tính năng đã phát hành.

**Handoff hiện hành cho yêu cầu chạy hai chat:** dùng [phân công P0 hai cuộc trò chuyện](smart-remake-p0-two-chat-handoff.md), bám SR-01…SR-10 của [trang Notion](https://app.notion.com/p/42342dfd177f8073b8d1ce5ab6b52208). Hai prompt trong handoff khóa ownership và contract; P1 không là điều kiện chạy pilot P0. Notion §9.1 chọn kế hoạch `20×3 + 8×3 = 84`, thay phương án ablation `6×4` từng xuất hiện trong hội thoại; định nghĩa từng nhánh vẫn cần khóa trước benchmark chính thức.

**Tiến độ V2-01:** đã chạy 34 integration tests hiện có và thêm một test DB `0022 → head → 0022 → head` bảo toàn dữ liệu legacy, tổng **35 passed**; scoped lint/mypy bảy file đạt và provider profile đã đối chiếu tài liệu. Live account/output chưa được qualify; xem handoff để biết phạm vi và lint nền còn lại. Kết quả này không đồng nghĩa P0 đã hoàn tất.

Mục tiêu: dùng cấu trúc một video tham chiếu để tạo quảng cáo cho sản phẩm đích, kiểm tra được từng cảnh, sửa đúng phần lỗi và xuất đúng phiên bản đã duyệt. Hiệu quả bán hàng được kiểm chứng riêng ở V2-14.

## 1. Điểm xuất phát và quyết định phạm vi

- Branch được kiểm tra: `feat/assets`, HEAD `b68d34d`. Workspace có nhiều thay đổi và file mới chưa commit, gồm cả Smart Remake và Creative Library. Mỗi task phải tiếp nhận/review phần WIP liên quan; không xây lại, reset hoặc stage toàn bộ workspace.
- Backend thực tế là FastAPI/SQLAlchemy/Celery trong `apps/backend`; frontend là React/TanStack/Vite trong `apps/web`. Dùng Makefile, uv và pnpm tại đúng thư mục; không có `package.json` ở root.
- Đã có code cho KIE Veo Lite, OpenAI Images trực tiếp, nhóm sinh video, cache ảnh, Timeline v2, candidate sửa một cảnh, duyệt khoảng trim và ghép FFmpeg. Wizard ba bước và so sánh current/candidate cũng đã có.
- Timeline hiện tại: 24 fps, thành phẩm 8 hoặc 16 giây, tối đa bốn cảnh, mỗi cảnh tối đa 192 frame. Nhóm gồm các cảnh liền nhau với tổng không quá 192 frame; mỗi request hiện sinh clip thô tám giây. Khả năng sinh clip bốn giây là thử nghiệm sau, không phải điều kiện để hoàn tất bản đầu.
- Inspector hiện mới có kiểm tra kỹ thuật. Chưa có đủ semantic findings, ngân sách tiền, bộ benchmark Smart Remake có provenance và quyết định duyệt xuất cuối cùng. Scene versions đã có; lịch sử assembly immutable cần bổ sung.
- Profile ảnh trong cuộc trò chuyện từng là Flare/low. Code và phần bàn giao mới nhất đã chuyển sang **Sunburst/max/high**. Giữ nguyên cấu hình hiện hành trong lượt chia task này; V2-01 phải đối soát profile và đóng băng trước pilot. Không tự hạ chất lượng hoặc đổi cấu hình tác vụ đã lưu.
- Model ID, payload, capability, quyền truy cập API và giá trong hội thoại không được dùng như kết quả qualification. V2-01 đối chiếu nguồn chính thức và lưu ngày kiểm tra; giá thực chi thuộc V2-04.
- Không thêm provider/model video khác, GPU serving, fine-tuning, editor canvas lớn hoặc dashboard thí nghiệm riêng. Tái sử dụng workflow và UI hiện có.

Đọc cùng [kế hoạch sửa cảnh](smart-remake-controlled-scene-repair-plan.md), [product brief](../product/smart-remake-product-brief.md) và [audit thực nghiệm](../audit/EXPERIMENT_EVIDENCE_AUDIT.md). Các audit ngày 24/11 và đoạn lịch sử của kế hoạch không thay thế source hiện tại.

**Bằng chứng của lượt lập backlog:** chạy offline `uv run pytest tests/unit/test_smart_remake* -q --no-cov` tại `apps/backend`: **323 passed**. Đây là unit tests với provider giả; không đo coverage, không chứng minh chất lượng AI hoặc integration. Không gọi API có phí trong lượt này.

## 2. Bảng giao việc

Vai trò: **A** = AI/backend; **B** = frontend/media; **C** = sản phẩm/dữ liệu/QA. Một người làm integrator cho các file dùng chung. Đây là trách nhiệm, không yêu cầu đúng ba nhân sự.

| ID | Ưu tiên | Task | Owner | Phụ thuộc để nghiệm thu |
| --- | --- | --- | --- | --- |
| V2-01 | P0 | Kiểm chứng nền WIP và profile provider | A + C | Không |
| V2-02 | P0 | Khóa protocol B0/B1/B2, ablation và dataset | C | Có thể bắt đầu ngay |
| V2-03 | P0 | Xác nhận yêu cầu sản phẩm, quyền và vòng đời asset | A; B làm form | 01 |
| V2-04 | P0 | Ledger lần gọi, chi phí và giới hạn ngân sách | A | 01 |
| V2-05 | P0 | Kiểm tra ảnh điều kiện, từng cảnh và bản cuối | A | 03, 04 |
| V2-06 | P0 | UI xem nguồn, findings và bằng chứng | B | Contract 03, 05 đã khóa |
| V2-07 | P0 | Hoàn thiện Scene Fix và lịch sử assembly | A; B nối UI | 04, 05 |
| V2-08 | P0 | Duyệt xuất theo đúng phiên bản | A + B | 03, 05, 07 |
| V2-09 | P0 | Harness thực nghiệm và báo cáo chạy lại offline | C + A | 02, 04; tích hợp 05, 07 |
| V2-10 | P0 | E2E, recovery và kiểm chứng release | C; A/B sửa lỗi thuộc phần mình | 06, 08, 09 |
| V2-11 | P0 | Pilot thật: gộp cảnh so với tạo riêng | A + C | 01, 03–10; dev protocol đã khóa |
| V2-12 | P0 | Chạy benchmark và đóng gói evidence BTC | C | 02 đã đối soát BTC, 11 đạt |
| V2-13 | P1 | Hai biến thể hook hoặc CTA | A + B | 08, 11 đạt |
| V2-14 | P1 | Pilot seller về hiệu quả quảng cáo | C | 08, 11 đạt; seller và kế hoạch đo sẵn sàng |

Không khóa ngày hoàn thành khi profile live, tài sản thử và protocol BTC chưa chốt. V2-11/12 là batch có chi phí: lập dự toán cụ thể trước khi giao chạy; backlog này không khởi tạo các batch đó.

## 3. Các task có thể giao thực hiện

### V2-01 — Kiểm chứng nền WIP và profile provider

**Context:** đường render, grouping, cache ảnh và sửa cảnh đã có source và unit tests; chưa đủ căn cứ gọi là release hoặc đã chạy thành công với provider thật.

**Phạm vi/file:** tiếp nhận `models.py`, `repair_repository.py`, `timeline_planner.py`, `timeline_compile.py`, `timeline_service.py`, `kie_workflow.py`, `image_workflow.py`, `engine/kie_{adapter,client,polling}.py`, `engine/openai_images.py` trong `apps/backend/src/viraldy/modules/smart_remake/`; migration `apps/backend/alembic/versions/0023_smart_remake_scene_repair.py`; nối worker/registry hiện có. Không viết adapter thay thế.

**Việc làm:** review WIP và ghi snapshot source; kiểm tra migration trên DB mới và DB nâng cấp; chạy các integration suite hiện có. Đối chiếu API chính thức để khóa model/mode/resolution, profile ảnh và policy reference thực tế. Hiện nhóm dùng ảnh sản phẩm thật cùng ảnh bố cục của cảnh đầu/cuối, tối đa ba reference; không mặc định sinh ảnh cho mọi cảnh. Giữ tương thích plan cũ và trạng thái cần đối soát sau timeout.

**Nghiệm thu/test:** PostgreSQL xác nhận isolation, revision conflict và idempotency đồng thời; `3+5+4+4` tạo hai nhóm, `2+2+2+2` tạo một nhóm, `5+5+6` tạo ba nhóm; reload/retry giữ nguyên snapshot. Chạy bốn integration suite ở phần 5. Hoàn tất offline chưa được ghi là provider live đã đạt.

**Rollback:** tắt entry mới khi chưa đạt; giữ dữ liệu và plan cũ, không sửa nội dung migration đã được áp dụng ở môi trường khác.

### V2-02 — Protocol và dataset thực nghiệm

**Context:** chưa tìm thấy yêu cầu BTC gốc hoặc định nghĩa B0/B1/B2 chính thức trong repo. Hội thoại còn hai cách tổ chức 24 ablation: `8 case × 3` và `6 case × 4`. Cần đối soát trước khi khóa kết quả nộp.

**Owner/file:** C sở hữu đặc tả và manifest dưới `evaluation/`; cập nhật `evaluation/README.md` để phân biệt harness PatternKit/ViralKit hiện có với Smart Remake. Không sửa các audit lịch sử thành kết quả mới.

**Việc làm:** lưu nguồn/yêu cầu BTC, version và mapping từng nhánh, ablation, rubric, trần ngân sách/thời gian/lượt sửa. Mapping hội thoại “B0 generic, B1 reference-conditioned, B2 đầy đủ” chỉ là đề xuất tới khi đối soát. Chọn ca phát triển tách khỏi ca báo cáo; manifest có case ID, hashes, quyền, constraints và timeline. Khóa group plan theo case và dùng chung giữa các nhánh; công bố rõ khác biệt conditioning của nhánh text-only.

**Nghiệm thu/test:** validator từ chối nhánh chưa định nghĩa, ca thiếu quyền/hash hoặc ma trận không khớp protocol. Chốt quy mô trước chạy; `20 × 3 = 60` và 24 ablation là kế hoạch cần xác nhận, không phải 84 file đã tạo hay 84 API calls. Thiếu nguồn BTC chỉ chặn qualification bộ nộp; V2-03–10 và dev pilot vẫn tiến hành với protocol nội bộ được ghi rõ.

**Rollback:** tạo version protocol mới; giữ mapping và kết quả cũ, không đổi nhãn hồi tố cho video không có provenance.

### V2-03 — Yêu cầu đã xác nhận và quyền asset

**Context:** compiler/ProductLock/SceneMap có sẵn. Cần nối yêu cầu seller xác nhận với những gì provider nhận và Inspector kiểm tra.

**Owner/file:** A sở hữu schema/service mới trong `smart_remake/`, tái sử dụng `engine/schemas.py`, `modules/assets/{schemas,service,models}.py`; B bổ sung vào bước kịch bản hiện có, không tạo wizard mới. Integrator xử lý router và migration nếu cần.

**Việc làm:** lưu “giữ/thay/cấm/tiêu chí/bằng chứng” theo yêu cầu và asset đích. Đánh dấu thao tác reference không tương thích sản phẩm để seller sửa yêu cầu; không chuyển công dụng, giá hoặc lời chứng thực của sản phẩm cũ sang sản phẩm mới. Lưu trạng thái khai báo quyền tách khỏi đã kiểm tra bằng chứng, phạm vi gửi provider, consent nhân vật/giọng và nghĩa vụ ghi công. Kiểm tra quyền tại backend trước paid submission, với cả source frame và audio. Định nghĩa và thực thi xóa input cùng dữ liệu dẫn xuất trong phạm vi hệ thống quản lý.

**Nghiệm thu/test:** thiếu quyền hoặc sai workspace bị chặn trước gọi provider; fake provider ghi nhận zero calls. Quyền bị thu hồi không tiếp tục generation/export; job đang chạy được xử lý theo policy đã ghi. Xóa project xử lý reference, cache, clip dùng chung và output theo dependency, không xóa media còn được project khác tham chiếu. Có trạng thái kết quả và giới hạn xử lý dữ liệu phía provider.

**Rollback:** tắt khả năng dùng asset chưa đủ metadata; không tự mặc định quyền là hợp lệ cho dữ liệu cũ.

### V2-04 — Chi phí, ngân sách và attempt ledger

**Context:** operation key, submit intent và task receipt đã có; giới hạn số operation hiện tại không thay cho giới hạn tiền.

**Owner/file:** A tạo module budget/attempt trong `smart_remake/`; nối `image_workflow.py`, `kie_workflow.py`, các bước phân tích/Inspector. Cùng integrator đánh giá tái sử dụng `modules/ai_gateway/{usage,models}.py`; không thêm một framework billing mới.

**Việc làm:** reserve ngân sách atomically trước mỗi tác vụ có phí; settle/reconcile theo kết quả. Ledger nối case/run/operation/group/scene/version, model/profile/prompt/config hashes, task/request ID, timestamps, usage, lỗi và lý do retry. Phân biệt lỗi kỹ thuật với sinh lại vì chất lượng; tính cả phân tích, ảnh, video, review và các lần thất bại. Giá estimate phải có nguồn/ngày; actual và unknown là hai trạng thái riêng. Chặn tác vụ không thể giữ trong giới hạn đã đặt theo policy bảo thủ được công bố.

**Nghiệm thu/test:** hai worker cạnh tranh không vượt hạn mức; cached image không tính thành request mới; poll/download/trim/compose không sinh thêm paid task. Timeout chưa rõ kết quả giữ reservation và trạng thái đối soát; không gán chi phí bằng 0 hoặc retry mù. Test crash trước/sau submit intent, sau receipt, trước lưu media và khi giao job lặp. Tổng ledger khớp báo cáo theo operation.

**Rollback:** ngừng tạo paid work mới khi ledger không khả dụng; tiếp tục đọc/đối soát task cũ, không giải phóng reservation chưa xác định kết quả.

### V2-05 — Kiểm tra ảnh điều kiện và từng đoạn sử dụng

**Context:** `repair_media.py:technical_check` chỉ xác nhận một số điều kiện media. Các scene trong cùng nhóm có thể cùng trỏ một MP4; pass của MP4 không chứng minh mọi cảnh bên trong đạt.

**Owner/file:** A tạo contract và service Inspector trong `smart_remake/`; tái sử dụng `repair_media.py`, `timeline_media.py`, API checks và multimodal gateway hiện có. C sở hữu bộ video có nhãn và rubric để đo checker.

**Việc làm:** mỗi finding có requirement ID, loại media, quan sát, status `passed/failed/needs_review/insufficient_evidence`, mức độ, scene/version/hash, evidence và hành động đề xuất; media có timeline lưu thêm khoảng thời gian. Trước gửi Veo, kiểm tra ảnh GPT điều kiện với ảnh sản phẩm thật và yêu cầu bố cục: SKU, hình dáng/màu, nhãn khi nhìn rõ, số lượng và quan hệ tay–vật thể. Chỉ ảnh đã qua gate kiểm tra/duyệt mới được dùng; ảnh chưa rõ cần người xem, không tự coi là đạt hoặc tự sinh lại ngoài ngân sách. Cache acceptance gắn đúng hash/profile/constraints; đổi ảnh hoặc reference phải kiểm tra lại, không đổi kết quả lịch sử của media cũ.

Với video, kiểm tra đủ/thứ tự cảnh, điểm cắt thực, footage đủ thời lượng, product/character/action/claims. Kiểm tra raw group để định vị cảnh, rồi kiểm tra chính in/out được chọn và ranh giới lân cận; kiểm tra bản MP4 ghép cuối. Ghi phạm vi lấy mẫu, không mô tả sampled review là kiểm tra mọi frame.

**Nghiệm thu/test:** ảnh điều kiện sai sản phẩm hoặc chưa được duyệt tạo zero Veo submissions; dùng cache khác hash/profile không tái dùng acceptance. Bác timestamp ngoài media, evidence không tồn tại hoặc sai hash/version. Occlusion, checker lỗi và thiếu quan sát trả trạng thái chưa đủ bằng chứng/cần xem. Ca yêu cầu `3+5` nhưng clip thành `4+4` không được pass chỉ vì đủ tám giây; trim thiếu hành động bắt buộc không được pass. Trước live pilot, khóa hard checks và quy tắc duyệt thủ công bằng fixtures cùng bộ có nhãn. Đo false positive/false negative của semantic checker; V2-11 hiệu chỉnh và khóa version cho benchmark sau đó. Không yêu cầu V2-05 phải có kết quả live pilot để hoàn tất gate offline, cũng không tự bật auto-pass semantic khi chưa hiệu chỉnh.

**Rollback:** tắt checker semantic lỗi, giữ technical findings và chuyển người duyệt; không tự đổi kết quả chưa kiểm tra thành đạt.

### V2-06 — UI nguồn, findings và bằng chứng

**Context:** `use-remake-studio.ts` đã khôi phục source media cho Timeline v2, nhưng Result chưa đưa source vào player; current/candidate comparison đã có.

**Owner/file:** B sở hữu `apps/web/src/features/smart-remake/components/{remake-output,remake-player,remake-version-review}.tsx` và helper review mới. Integrator nối `use-remake-studio.ts` cùng type API dùng chung.

**Việc làm:** đưa reference/current/candidate vào trải nghiệm Result hiện có; danh sách finding chọn đúng cảnh và khoảng playback. Có trạng thái chờ kiểm tra/duyệt ảnh điều kiện trước sinh video, giữ các ảnh đã được duyệt khi cấu hình không đổi. Hiển thị evidence, trạng thái chưa rõ, checker/version/thời điểm; tách technical check khỏi nhận xét nội dung. Mapping riêng source time, raw group time và final timeline time; ghi nhận xác nhận/bác bỏ finding theo actor và version. Hiển thị chi phí/ngân sách từ server, không ước lượng bằng timer frontend.

**Nghiệm thu/test:** với cảnh 2 trong nhóm `3+5`, finding cục bộ giây 1 nhảy đúng raw group giây 4; source có offset vẫn mở đúng vị trí. Test reload, source hết hạn, finding của version cũ, keyboard/focus và màn desktop 1280/1440. Finding cũ không xuất hiện như kết quả kiểm tra bản mới.

**Rollback:** bỏ view Inspector mới, giữ player và thao tác sửa/duyệt hiện có; API giữ khả năng đọc dự án cũ.

### V2-07 — Scene Fix, lịch sử và vô hiệu kết quả cũ

**Context:** tạo candidate, explicit accept và scene history đã có. `publishedTimeline` và final pointer hiện giữ snapshot gần nhất, chưa phải toàn bộ assembly history immutable.

**Owner/file:** A mở rộng `repair_service.py`, `timeline_service.py`, module lưu assembly history mới; B nối compare/restore hiện có. Integrator xử lý persistence và migration kế tiếp nếu cần, không tái sử dụng số 0023.

**Việc làm:** tạo lại riêng cảnh lỗi, giữ version/hash của cảnh tốt; snapshot constraints, prompt và chi phí cho từng attempt. Candidate chưa thay active. Mỗi lần ghép lưu immutable assembly manifest/hash, parent và người áp dụng. Accept/trim/đổi yêu cầu làm invalid kết quả liên quan; continuity còn phụ thuộc version cảnh lân cận. Khôi phục bản cũ là hành động có lịch sử, không ghi đè assembly cũ.

**Nghiệm thu/test:** sửa cảnh 2 trong nhóm chung không sinh lại cảnh 1; clip chung còn được tham chiếu vẫn tồn tại. Apply candidate đặt trim cần duyệt lại; lỗi FFmpeg/storage giữ output đang dùng. Concurrent revision bị chặn; restore mở đúng bytes/manifest và cần duyệt theo policy hiện hành. Semantic checks của context cũ không được tái dùng sau đổi hàng xóm hoặc trim.

**Rollback:** giữ current pointer cũ nếu assembly mới lỗi; tắt tạo candidate mới mà vẫn xem/khôi phục được dữ liệu đã lưu.

### V2-08 — Duyệt thành phẩm và xuất riêng tư

**Context:** “đã duyệt đoạn” hoặc có final URL chưa phải quyết định duyệt xuất. Cần một điểm backend thực thi trạng thái release cho đúng assembly.

**Owner/file:** A tạo release/export service nhỏ cạnh workflow hiện có; B nối nút duyệt/tải tại `remake-output.tsx`. Integrator nối router, API types và storage có sẵn.

**Việc làm:** quyết định duyệt gắn assembly ID/hash/revision, constraints và inspection context, actor/time. Backend kiểm tra quyền, hard findings, technical checks bản cuối, các mục bắt buộc và nhãn AI trước export; ghi công theo metadata asset. Preview riêng tư vẫn phục vụ kiểm tra, còn export đi qua endpoint đã kiểm tra policy. Không fallback ra public copy. Sửa tiếp tạo bản cần kiểm tra/duyệt lại.

**Nghiệm thu/test:** gọi export trực tiếp cho bản chưa duyệt, sai workspace, stale hash, thiếu quyền hoặc hard failure đều bị chặn; nút “đã xem” không vượt hard block. Chỉ đúng assembly đã duyệt nhận file xuất; URL giới hạn thời gian và kiểm tra quyền lại khi cấp mới. Không tuyên bố có thể thu hồi file đã tải hoặc URL đã cấp trước thời điểm thu hồi quyền.

**Rollback:** khóa export mới khi gate lỗi; giữ preview riêng tư và lịch sử quyết định, không mở đường tải thay thế bỏ qua policy.

### V2-09 — Harness Smart Remake và replay offline

**Context:** `evaluation/README.md` và `scripts/run_evaluation.py` hiện phục vụ captured PatternKit/ViralKit. Không đổi nhãn harness đó thành benchmark video.

**Owner/file:** C/A tạo contract, runner, reporting dưới `apps/backend/src/viraldy/evaluation/` và entry script dưới `apps/backend/scripts/`; manifest/rubric ở `evaluation/`. Tái sử dụng convention mode, IDs và sanitization của `evaluation/qualification/`.

**Việc làm:** triển khai selectors theo protocol V2-02; dùng cùng code/adapter render đã qualify, không dựng pipeline benchmark thứ hai. Nối input → plan → all attempts → raw clips → selected ranges → assembly → human ratings theo hashes. Lưu failures/timeout/budget stop và request/response đã loại dữ liệu nhạy cảm; giữ media trong kho dự án thay vì phụ thuộc provider URL. Thu first-pass và sau sửa dưới cùng trần cho phép, công bố actual spend.

**Nghiệm thu/test:** từ bundle fixture có thể tính lại cùng báo cáo mà không gọi provider. Rating mù nối đúng output hash/rater/rubric; report có số mẫu, mean/dispersion, paired differences, rater disagreement, failures và missingness. Chi phí mỗi thành phẩm đạt tính mọi attempt; mẫu số 0 hoặc thiếu giá được ghi unmeasured. Mode live thiếu receipt/media hash không được hợp thức hóa chỉ bằng label.

**Rollback:** dừng runner live; giữ schema/version/bundle gốc và replay offline, không sửa số liệu thô để làm report pass.

### V2-10 — E2E và qualification release

**Context:** frontend hiện có Vitest/helper tests; không coi rendered-markup tests là browser E2E. Unit baseline 323 tests không bao phủ PostgreSQL, Celery, storage và trình duyệt.

**Owner/file:** C sở hữu browser test tối thiểu và fixtures tại test surface hiện có; A/B chỉ sửa phần production tương ứng khi có lỗi. Dùng fake provider có kiểm soát cùng FFmpeg thật cho offline E2E.

**Việc làm:** nối hành trình chuẩn bị → xác nhận → render hai nhóm → inspect bốn cảnh → sửa một cảnh → compare → accept → recheck → ghép → duyệt xuất → reload/restore. Kiểm chứng cả runtime recovery, workspace isolation và xóa asset. Dùng lại tests integration/grouping hiện có; chỉ bổ sung hành vi còn thiếu.

**Nghiệm thu/test:** double-click Generate, duplicate job delivery, timeout chưa rõ receipt, download/storage fail, hết ngân sách, cut sai, evidence sai, đổi version sau duyệt và xóa đều có trạng thái đúng. Assert số paid-call giả, media hashes của cảnh giữ lại và gate backend; không chỉ assert text trên UI. Có ba ca demo: đạt, cần sửa, bị chặn, đều ghi rõ fixture/live.

**Rollback:** giữ feature chưa qualify sau capability flag; lỗi không được giải quyết bằng đường demo tự bật trong mode live.

### V2-11 — Pilot thật về chất lượng và gộp cảnh

**Context:** giảm số task không chứng minh giảm tổng chi phí hoặc giữ đúng timeline. Chỉ chạy pilot sau khi có budget cap, quyền, capture/replay và workflow đã qualify offline.

**Owner/output:** A + C; bundle development tách khỏi benchmark cuối. Chuẩn bị batch nhỏ được giao chạy với trần tiền cụ thể; không tự chạy toàn bộ 84 lượt.

**Việc làm:** dùng Veo Lite cùng profile ảnh được khóa, so B2 một cảnh/task với B2 gộp cảnh trên cùng input và tiêu chí. Bao gồm `3+5+4+4`, `2+2+2+2`, cảnh tương tác tay/che khuất và trường hợp cần tách nhóm. Đo cut thực, đủ footage theo cảnh, thứ tự, product/action, repair calls, total cost/accepted output và latency. Thử ba/bốn cảnh trong bốn giây chỉ khi capability đã xác minh, ghi thành cấu hình riêng.

**Nghiệm thu:** lưu cả ca fail và ambiguity; mở được một finding tới evidence thật, sửa một cảnh và truy ngược chi phí. Chọn policy gộp/tách bằng kết quả sau sửa. Nếu không đủ footage hoặc vượt cap, kết luận chưa đạt và điều chỉnh trên dev set; không đổi cấu hình trong bộ báo cáo cuối. Pilot nội bộ không cần được gắn nhãn kết quả BTC khi định nghĩa chính thức còn thiếu.

**Rollback:** tách nhóm tại compile cho kế hoạch mới; giữ snapshot/cost của lần đã chạy. Không tự thay provider video.

### V2-12 — Benchmark và bộ bàn giao BTC

**Context:** chỉ bắt đầu sau khi protocol chính thức V2-02 đã đối soát, pilot đạt và code/config/prompt/rubric đã khóa.

**Owner/output:** C điều phối, A hỗ trợ chạy batch; manifest, attempts, media, human ratings và report theo V2-09. Người xây hệ thống không phải toàn bộ nhóm chấm độc lập.

**Việc làm:** chạy đúng paired cases và ma trận đã khóa; cùng ranh giới nhóm, model/resolution và budget policy giữa các nhánh, công bố khác biệt mode/input. Chấm video chuyển động bằng rubric mù; không lấy điểm VLM thay cho điểm người. Báo cáo chất lượng lượt đầu, sau sửa, lỗi nghiêm trọng/bỏ sót/cảnh báo nhầm của Inspector, thời gian thao tác người, máy và total cost/accepted output.

**Nghiệm thu:** từ một bảng số liệu mở được raw rating → assembly hash → trim → scene version → task receipts → inputs/config. Replay offline tái tạo report. Failed/cancelled/ambiguous runs không bị loại khỏi population đã định nghĩa. Count số thực chạy, valid outputs và rated outputs riêng; không đếm người chấm hoặc nhiều file export thành mẫu độc lập. Thiếu BTC gốc hoặc dữ liệu thật được ghi là chưa đủ điều kiện nộp, không dựng số minh họa.

**Rollback:** nếu đổi compiler/profile/prompt/rubric, tạo benchmark version mới và chạy lại nhóm ảnh hưởng; giữ bundle trước đó.

### V2-13 — Hai biến thể hook hoặc CTA

**Context:** P1, làm sau vòng tạo–kiểm tra–sửa–duyệt ổn định. Không mở đồng thời thay sản phẩm, nhân vật, ngôn ngữ và offer.

**Owner/file:** A tạo child variant operation dùng lại pipeline; B bổ sung entry từ kết quả đã duyệt. Không tạo generator hoặc editor mới.

**Nghiệm thu/test:** đúng hai biến thể, có lineage tới assembly gốc, chỉ sinh lại phần chịu ảnh hưởng và giữ IDs/hashes phần còn lại; không phát sinh generation khi chỉ đổi lớp hậu kỳ có thể dựng bằng code. Mỗi variant qua budget, checks và release riêng. Chữ đã nằm trong pixel phải được tạo lại nếu cần; preview form không được báo là MP4 đã đổi.

**Rollback:** tắt tạo variants; giữ project gốc và outputs con đã lưu.

### V2-14 — Pilot seller về hiệu quả quảng cáo

**Context:** benchmark kỹ thuật không chứng minh video đổi sản phẩm vẫn viral/bán tốt. Đây là task đo ngoài sản phẩm, không cần xây performance platform.

**Owner/output:** C chuẩn bị protocol và bảng thu số liệu tối thiểu; seller cung cấp nguồn chỉ số và quyền sử dụng. Việc gửi nội dung/chạy quảng cáo chỉ tiến hành khi được giao riêng cùng giới hạn chi phí.

**Việc làm/nghiệm thu:** so remake với phương án quảng cáo khác cho **cùng sản phẩm đích**; ghi organic/paid, khoảng thời gian, offer, audience, phân phối, spend và chỉ số bán hàng khi có. Chốt chỉ số và cách phân nhóm trước xem kết quả; thiếu traffic/dữ liệu chuyển đổi thì kết luận chưa đủ bằng chứng. Không suy hiệu quả bán hàng từ lượt xem hoặc doanh số sản phẩm gốc. Báo cáo số liệu thô, yếu tố nhiễu và giới hạn, không hứa kết quả viral.

**Rollback:** dừng thử nghiệm khi chạm cap hoặc seller yêu cầu; giữ dữ liệu quan sát theo quyền đã thỏa thuận.

## 4. Chạy song song và tránh xung đột file

1. Bắt đầu **01 và 02 song song**. 01 khóa nền source/provider; 02 chốt dữ liệu/protocol, không chặn các phần kỹ thuật độc lập.
2. Sau 01, **03 và 04 song song**. B có thể chuẩn bị màn review bằng contract mock đã khóa, tách rõ dữ liệu fixture.
3. Sau khi khóa schema, **05 backend và 06 frontend song song**; **09** xây validator/replay từ 02/04, rồi tích hợp findings/version khi có. 07 tiếp nối contract Inspector.
4. Hoàn tất **08 → 10 → 11 → 12**. 13 và 14 có thể mở độc lập sau 11, không là điều kiện hoàn thành benchmark chính.

Integrator sở hữu các điểm ghép `router.py`, `models.py`, đăng ký DB/worker, migration, `apps/web/src/shared/api/smart-remake.ts` và `use-remake-studio.ts`. Worker giao module/test riêng; gửi thay đổi contract cho integrator thay vì cùng sửa các file đó. Không tách worktree rồi quên mang WIP chưa commit vào baseline.

Mỗi task giữ branch `codex/sr-v2-XX-<ten-ngan>` sau khi baseline đã được chọn, một PR có thể review độc lập, và bằng chứng test gắn đúng snapshot. Việc tạo PR/push/commit không được thực hiện chỉ vì tài liệu này nêu workflow. Nếu phát hiện dependency mới, cập nhật bảng trước khi giao task tiếp; không để code dựa trên contract chưa được chốt.

## 5. Kiểm chứng và điều kiện hoàn tất

Từ repository root, dùng command surface thực tế:

```bash
make lint
make typecheck
make test-unit
make test-contract
make web-build
make web-lint
```

Tại `apps/web`:

```bash
pnpm test
pnpm typecheck
```

Bốn suite integration Smart Remake hiện có, chạy tại `apps/backend` khi Docker/PostgreSQL và FFmpeg sẵn sàng:

```bash
uv run pytest --no-cov \
  tests/integration/test_smart_remake_repair_persistence.py \
  tests/integration/test_smart_remake_kie_workflow.py \
  tests/integration/test_smart_remake_timeline.py \
  tests/integration/test_smart_remake_grouped_generation.py
```

Các lệnh trên là checklist nghiệm thu tương lai, không phải tất cả đã chạy trong lượt lập backlog. Test viết trước cho hành vi mới/lỗi hồi quy; ưu tiên checks có thể phát hiện sai hành vi. Đo coverage **ít nhất 80% cho phạm vi module được giao**, ghi rõ command/phạm vi. Cấu hình pytest hiện đặt ngưỡng toàn repo 70%; pass ngưỡng đó hoặc chạy `--no-cov` không chứng minh đạt 80%. Browser E2E mới và live pilot báo cáo riêng, không tính chung với unit tests.

Trước sửa symbol, làm GitNexus impact theo `AGENTS.md` và báo direct callers/processes/risk; HIGH/CRITICAL phải được nêu trước sửa. Index đang phản ánh source cũ, chưa đủ file WIP, nên refresh từ baseline đã chốt trước dùng để kết luận blast radius. Trước commit chạy `detect_changes`; review diff của đúng task, không nhận nhầm thay đổi có sẵn là của task đó. Có review độc lập cho correctness/security sau implementation.

**P0 hoàn tất** khi một ca có quyền sử dụng đi hết tạo theo nhóm → kiểm tra từng khoảng → sửa riêng cảnh lỗi → so sánh/khôi phục → kiểm tra bản cuối → duyệt/xuất đúng assembly, với ngân sách và provenance đầy đủ; đồng thời bộ benchmark đã khóa có input/output/log/điểm người/báo cáo tính lại được. Một video demo đẹp hoặc một bộ fixture pass chưa đủ điều kiện này.
