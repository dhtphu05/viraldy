# Smart Remake — góc nhìn AI Product, Business và Seller

Ngày: 2026-11-24. Đây là định hướng sản phẩm và các giả thuyết cần xác thực, không phải bằng chứng về hành vi seller, khả năng chuyển đổi hoặc hiệu quả quảng cáo đã đo được.

**Cập nhật 2026-11-25:** phần cuối “Desktop, Veo Lite và sinh video theo nhóm” thay thế cấu hình Fast và giới hạn một cảnh/một task được ghi trong lịch sử bàn giao. Quyết định ảnh mới nhất là [Sunburst, quality max, complexity high](#cấu-hình-ảnh-sunburst-max-high); các mô tả Flare/low bên dưới là snapshot trước đó.

## Quyết định sản phẩm

Smart Remake giúp seller chuyển cách triển khai sáng tạo của video tham chiếu thành video mới phù hợp với sản phẩm của mình, sau đó chỉnh đến khi có bản họ chấp nhận sử dụng. Vòng sửa riêng cảnh bảo vệ phần đã tốt và giảm việc bắt đầu lại khi một phần output chưa đạt.

Ưu tiên editor ý định của cảnh: mục tiêu bán hàng, sản phẩm/reference, hành động, bố cục và những gì muốn giữ/thay đổi. Typography/canvas hậu kỳ là nhánh bổ sung. Không lấy số công cụ editor làm thước đo độ phong phú của feature.

Định hướng này thay thế trọng tâm mockup overlay trước đó trong [plan kỹ thuật](../implementation/smart-remake-controlled-scene-repair-plan.md). Phạm vi các đợt và estimate cần chốt lại theo scope chính, không mặc định mang toàn bộ công cụ hậu kỳ vào bản đầu.

## Seller và công việc cần hoàn thành

Persona khởi đầu đề xuất: seller có sản phẩm, ảnh/reference sản phẩm và video mẫu, muốn có bản video có thể review và sử dụng; mức thành thạo prompt không được coi là điều kiện đầu vào. Chưa có nghiên cứu để kết luận đây là persona đem lại retention hoặc doanh thu tốt nhất.

Job statement: “Tôi muốn dùng cách video mẫu thu hút và trình bày sản phẩm để làm video cho hàng của tôi. Nếu một cảnh chưa đạt, tôi muốn sửa đúng cảnh đó, biết phải chờ/tốn thêm bao nhiêu và không mất phần đã ổn.”

Các câu hỏi giao diện phải trả lời:

- Video này đang bán đúng sản phẩm/variant của tôi chưa?
- Có giữ cách mở đầu, hành động hoặc nhịp của mẫu mà tôi chọn không?
- Cảnh chưa đạt ở đâu, bằng chứng là gì, sửa theo cách nào?
- Lần tạo lại này giữ gì, thay gì, chi phí/phạm vi ra sao?
- Bản mới có sửa vấn đề tôi chọn và phát sinh vấn đề khác không?
- Tôi có thể quay lại bản trước hoặc giao draft tiếp cho người khác không?

## AI Product: điều khiển ý định và thu hẹp lỗi

### Ba loại vấn đề có ba cách xử lý

| Vấn đề | Ví dụ | Hành động phù hợp |
| --- | --- | --- |
| Output không hợp lệ hoặc lỗi sinh hình | Không có clip, khung đen, tay/sản phẩm méo | Retry kỹ thuật hoặc tạo lại cảnh với brief/reference rõ hơn |
| Output không đúng brief/sản phẩm | Sai variant, thiếu hành động yêu cầu, sai cách sử dụng | Sửa reference/facts/scene plan, sau đó tạo lại |
| Đạt brief nhưng seller muốn phương án khác | Hook nhẹ, sản phẩm xuất hiện muộn, muốn hero shot khác | Tạo phương án sáng tạo mới; không gọi bản trước là lỗi kỹ thuật |

Trường hợp thiếu thông tin sản phẩm hoặc yêu cầu mâu thuẫn cần hỏi/chốt thông tin trước khi generate. Không giải quyết mọi vấn đề bằng cách bấm retry với cùng input.

### Đơn vị thao tác chính là “cảnh phục vụ mục đích gì”

Scene card cần hiển thị: clip/thumbnail, vị trí, vai trò Hook/Demo/Proof/CTA nếu thực sự phù hợp nội dung, yêu cầu hiện tại và trạng thái review. Không ép mọi video vào công thức bán hàng giống nhau.

Repair editor có bốn phần:

1. Vấn đề muốn sửa: chọn taxonomy ngắn hoặc viết tự do, có timestamp/range nếu biết.
2. Kết quả mong muốn: mô tả dễ hiểu, AI có thể gợi ý brief để người dùng sửa/chốt.
3. Giữ nguyên: clip cảnh khác, reference sản phẩm/variant, ý đồ đang tốt; giải thích control nào là bảo đảm hệ thống và control nào là mục tiêu generation.
4. Phạm vi và chi phí: cảnh nào được tạo lại, cả block dài bao nhiêu, lượt thử còn lại và ước lượng nếu thực sự tính được.

Prompt chi tiết/compiler output nằm trong “Nâng cao”. Trước khi submit, server tạo patch có cấu trúc từ ý định, so với brief gốc và kiểm tra mâu thuẫn với product lock. Không chỉ nối câu người dùng vào cuối prompt cũ.

### Phân biệt cam kết chắc chắn và mục tiêu xác suất

- Có thể bảo đảm cảnh không được chọn giữ nguyên asset bằng manifest/version và kiểm tra hash.
- Trong cảnh tạo lại, product identity, actor, motion và framing là mục tiêu conditioning/QA, không phải cam kết mọi pixel ngoài vùng lỗi giữ nguyên.
- Marker lỗi chỉ xác định đoạn cần xem. Hiện đơn vị tạo lại là block 8 giây; chọn lỗi dài một giây không có nghĩa chỉ một giây đó sẽ được generate lại.
- Kiểm tra khác biệt theo ý định sửa: đã sửa/còn lỗi/vấn đề mới/chưa xác nhận được. Không dùng một điểm tổng hợp để che mất kết quả này.
- QA tách technical validity, brief/product consistency và seller preference. QA kỹ thuật đạt không đồng nghĩa seller chấp nhận hoặc video sẽ bán tốt.

### Ví dụ nghiệm thu sản phẩm

Video 16 giây: cảnh 1 mở hộp được seller chấp nhận; cảnh 2 cận sản phẩm có nắp sai màu.

Người dùng chọn cảnh 2, chọn “Sai chi tiết sản phẩm”, xác định màu đúng từ reference đã cung cấp, giữ hành động quay cận. Hệ thống hiển thị cảnh 1 giữ nguyên, cảnh 2 dài 8 giây được tạo lại. Candidate mới được so với product reference và clip cũ; seller xem cả đoạn nối trước khi áp dụng. Nếu model vẫn sai hoặc QA không chắc, bản cũ còn nguyên và kết quả được ghi rõ, không tự áp dụng.

## AI Business: tối ưu video được chấp nhận

Giả thuyết giá trị: sửa đúng phần chưa đạt sẽ tăng cơ hội hoàn thành video trong một ngân sách và thời gian seller chấp nhận. Cần đo thay vì hứa tỷ lệ tiết kiệm hoặc tăng doanh số.

Đơn vị giá trị đề xuất là video seller chấp nhận sử dụng. Chỉ số chất lượng kinh tế là tổng generation + QA + compose + compute/storage phân bổ trên số video được chấp nhận. Job count hoặc số lượt retry có thể tăng trong khi giá trị sản phẩm giảm.

Các quyết định đề xuất:

- Giữ clip tốt; chỉ submit cảnh cần thay. Vẫn tính phần kiểm tra và ghép video cuối, không coi đó là miễn phí.
- Trước submit có phạm vi và mức chi phí/credits dự kiến hoặc giới hạn rõ ràng; không hiển thị số giả khi provider chưa có estimate.
- Có ngân sách/lượt thử cho phiên sửa và điểm dừng. Hai hoặc nhiều lần cùng lỗi không được kéo thành vòng auto-retry vô hạn; đánh giá lại input, brief hoặc cách tạo.
- Phân biệt lỗi hệ thống/provider với yêu cầu tạo phương án sáng tạo mới. Chính sách credits cần thiết kế sao cho seller không chịu phí do operation trùng hoặc lỗi của nền tảng; đây là đề xuất chính sách, chưa phải billing hiện có.
- Đặt technical QA và thông tin phiên bản trong trải nghiệm cốt lõi. Tính năng biến thể/batch chỉ mở sau khi đã chứng minh chi phí và acceptance của từng cảnh.
- Lưu intent sửa, reason từ chối/chấp nhận, version và provider metadata để phân tích failure patterns. Không tuyên bố hệ thống đã tự học/cá nhân hóa chỉ vì lưu feedback, và không mặc định dùng nội dung seller để train.

Khác biệt sản phẩm cần kiểm chứng nằm ở vòng reference → product constraints → scene intent → targeted repair → evidence → seller decision. Một textbox prompt và nút generate dễ bị thay thế nếu không giúp hoàn thành công việc tốt hơn.

## UX: seller đưa ra quyết định, hệ thống thực hiện kỹ thuật

Workspace chính: danh sách cảnh + preview kết quả + repair inspector. Timeline hỗ trợ tìm vị trí lỗi; không đẩy seller vào dựng phim nhiều track từ bước đầu.

Trạng thái liên tục: Đang dùng → Có yêu cầu sửa → Đang tạo bản mới → Cần review → Đã kiểm tra → Đang ghép → Đã áp dụng. Chỉ expose stage thật, không giả lập phần trăm.

Một CTA chính cho mỗi stage: “Tạo lại cảnh 2”, “Kiểm tra bản mới”, “Áp dụng bản này”. Nhãn luôn nói rõ đối tượng. A/B phải phân biệt bản đang dùng và candidate, cùng playhead và chỉ một audio phát.

Đề xuất ưu tiên xác thực bằng usability tasks: người dùng có hiểu mình đang sửa yêu cầu chứ chưa sửa MP4; biết cảnh nào sẽ thay; hiểu “giữ nguyên” ở phạm vi nào; biết lý do QA yêu cầu xem lại; tìm được cách quay về bản cũ.

Nguyên tắc này phù hợp với hướng dẫn [Support efficient correction của Microsoft HAX](https://www.microsoft.com/en-us/haxtoolkit/guideline/support-efficient-correction/) và [Feedback + Control của Google PAIR](https://pair.withgoogle.com/guidebook-v2/chapter/feedback-controls/). Đây là nền tảng thiết kế, không phải bằng chứng feature này đã phù hợp thị trường.

## Thứ tự phát triển và quyết định go/no-go

1. Xác nhận brief trước render: đủ product facts/reference và yêu cầu cảnh có thể thực hiện; UI giải thích kế hoạch theo ngôn ngữ seller.
2. Vòng sửa một cảnh hoàn chỉnh: chọn vấn đề, sửa ý định, tạo candidate, QA/evidence, A/B, apply/rollback và cost/quota rõ ràng.
3. Cải thiện chất lượng sửa: gợi ý hành động theo loại lỗi, product checks tốt hơn, kiểm tra ranh giới cảnh và phân tích repeated failures.
4. Sau khi có dữ liệu: biến thể sáng tạo, batch và hậu kỳ caption nếu seller thực sự cần. Chọn thư viện miễn phí theo nhu cầu được xác thực; Konva không phải prerequisite cho editor ý định dạng form/reference/video.

Chỉ nên triển khai targeted repair vào production khi có stable scene IDs, media phiên bản bền vững và khả năng generation độc lập; giao diện đẹp không khắc phục được thiếu các khả năng này.

## Thử nghiệm và chỉ số

Đề xuất discovery: 5–8 seller đúng persona, dùng sản phẩm/reference của họ với quyền sử dụng phù hợp. Đây là nghiên cứu định tính, không phải cỡ mẫu chứng minh uplift thống kê. Quan sát ba task: hiểu scene plan trước tạo; sửa lỗi sai sản phẩm ở một cảnh; so sánh và duyệt bản mới.

Sau usability, dùng một tập brief/output lỗi cố định để so sánh quy trình hiện tại với repair workflow. Ghi cả trường hợp không hoàn thành; đặt budget và time cap trước khi thử. Chưa tự gọi paid jobs cho thử nghiệm này trong lượt lập kế hoạch.

Chỉ số cần baseline:

- Tỷ lệ phiên đạt ít nhất một video seller chấp nhận trong budget/time cap.
- Thời gian và tổng chi phí tới video được chấp nhận; không bỏ các phiên thất bại khỏi báo cáo.
- Candidate acceptance, lượt sửa/cảnh và tỷ lệ rollback.
- Tỷ lệ cảnh không được chọn thực sự giữ nguyên asset; duplicate paid jobs.
- QA false-positive/false-negative/unknown trên bộ review có nhãn của người.
- Usability: số người hiểu đúng phạm vi sửa và hoàn thành vòng repair không cần hướng dẫn.
- Sử dụng lại với sản phẩm/brief tiếp theo; doanh thu và hiệu quả ads chỉ đánh giá sau khi có dữ liệu thực tế, không suy ra từ QA score.

Go nếu seller hiểu và sử dụng được vòng sửa, chất lượng chấp nhận cải thiện ở chi phí phù hợp và không mất phần đã duyệt. Nếu nhiều lần cùng lỗi không sửa được hoặc seller phải trở thành prompt engineer, ưu tiên sửa product-reference/scene compiler/provider strategy trước khi thêm công cụ giao diện.

## Thiết kế trải nghiệm seller từ lúc vào feature

Đây là đặc tả UX/capability đề xuất để triển khai. Prototype chỉ mô phỏng chuyển trạng thái bằng dữ liệu ví dụ, không render video hoặc gọi AI. Thiết kế này thay thế luồng mặc định chỉnh chữ trên canvas trong prototype trước.

### Capability và phạm vi

Seller trong workspace tạo project từ video mẫu và sản phẩm, duyệt/chỉnh ý định từng cảnh, tạo video, sửa một cảnh chưa đạt, duyệt candidate và tải output đang dùng. Đầu ra là một video được seller chọn; không hứa doanh số hoặc khả năng sửa chính xác từng pixel bằng AI.

Ba bước cố định trên thanh tiến trình: **Chuẩn bị → Duyệt kịch bản → Video của bạn**. Phân tích và render là trạng thái xử lý giữa các bước, không thêm bước onboarding. Repair/compare/history nằm trong bước Video của bạn.

### Vào lần đầu

Mở ngay màn hình Chuẩn bị. Tiêu đề “Tạo video mới từ video mẫu”, dòng giải thích “Dùng cách kể chuyện và nhịp của mẫu cho sản phẩm của bạn.” Không yêu cầu chọn mode, học prompt hoặc hoàn thành tour.

Hai khu vực input cạnh nhau trên desktop, xếp dọc trên mobile:

| Khu vực | Thông tin/hành vi | Microcopy |
| --- | --- | --- |
| Video mẫu | Chọn/tải file, kiểm tra loại/dung lượng/media có đọc được, thumbnail + tên file + đổi file | “Chọn video có cách mở đầu hoặc cách giới thiệu sản phẩm bạn muốn làm theo.” |
| Sản phẩm | Chọn từ sản phẩm đã lưu nếu có capability; hoặc tải ảnh; hoặc dán link để lấy dữ liệu rồi xác nhận ảnh/variant | “Ảnh rõ sản phẩm và đúng phiên bản bạn đang bán.” |
| Ảnh chính | Hiển thị primary reference, seller có thể đổi; tên/variant có thể xác nhận sửa | “Ảnh này sẽ làm tham chiếu nhận diện sản phẩm.” |
| Tùy chọn | 8/16 giây, 9:16 cố định, ngôn ngữ, mô tả điều cần giữ | “Bạn có thể dùng gợi ý hiện tại và chỉnh tiếp ở kịch bản.” |

Không dựng các thành phần kết quả rỗng lớn cạnh form. Input bắt buộc được đánh dấu, mục phong cách/ghi chú là tùy chọn. Một câu bên CTA nói chính xác còn thiếu gì; trường sai có lỗi inline và cách sửa, không chỉ disable nút.

CTA chính: **Phân tích video mẫu**. Trước khi bấm, mục phân tích được phân biệt với render có phí theo chính sách chi phí thật. Không tuyên bố phân tích miễn phí khi chưa có quyết định billing.

Khi upload/link crawl chưa xong, không cho submit dữ liệu chưa sẵn sàng; giữ các input đã hợp lệ. Link không đọc được: “Chưa lấy được ảnh từ link này. Bạn có thể tải ảnh sản phẩm lên.”

### Seller quay lại

Entry có project gần đây ở phần phụ: thumbnail, tên sản phẩm, trạng thái và nút Tiếp tục. Không mở một bảng KPI chung trước tác vụ tạo video.

- Chưa có project: giữ entry ở form tạo mới.
- Có draft: “Tiếp tục bản đang làm” mở đúng bước đã lưu; action Tạo mới riêng biệt.
- Có job: hiển thị stage từ server, mở đúng project; reload không submit lại.
- Có video: mở output đang dùng cùng lịch sử; đổi input qua “Chỉnh thông tin dự án”.
- Thay video mẫu/product reference sau khi đã duyệt kế hoạch: lưu revision mới, đánh dấu plan bị ảnh hưởng và cần xác nhận lại trước render; không xóa các video/version cũ.

Chỉ hiển thị cam kết autosave/tiếp tục và cho rời trang khi server thật sự persist draft/job. Trước đó phải có trạng thái chưa lưu và hành động lưu/thử lại.

### Đang phân tích

Giữ context thumbnail video mẫu + sản phẩm. Heading “Đang chuẩn bị kịch bản cho sản phẩm của bạn”. Các stage chỉ hiện khi backend phát event tương ứng: đọc tư liệu → phân tích cấu trúc → chuẩn bị cảnh. Nếu chỉ biết running thì dùng indeterminate progress, không chạy timer giả phần trăm.

Lỗi đọc file trả về input liên quan; lỗi phân tích cho retry từ asset đã lưu. Seller không phải upload lại mọi tư liệu sau lỗi ở bước sau. Hủy chỉ xuất hiện khi backend có semantics hủy rõ ràng; rời trang không được ngầm hiểu là hủy hoặc hoàn credit.

### Duyệt kịch bản

Câu hỏi chính: “Video mới sẽ thể hiện sản phẩm của tôi như thế nào?”

Desktop: storyboard chiếm phần rộng, summary sản phẩm/video mẫu chiếm khoảng 280–320px. Mobile: summary thu gọn, scene cards xếp dọc. Mỗi card có:

- “Cảnh 1 · 00:00–00:08”, vai trò nội dung khi phù hợp, thời lượng rõ ràng.
- Hình nguồn được gắn nhãn “Khung hình tham chiếu”, không gọi là video kết quả hoặc dựng thumbnail AI giả.
- “Điều sẽ diễn ra”, “Sản phẩm xuất hiện thế nào”, lời thoại/chữ nếu có trong plan và provider hỗ trợ.
- Nút “Chỉnh cảnh” mở editor ý định ngay tại card, không chuyển sang video timeline nhiều track.

Editor trước render gồm mô tả hành động, cách xuất hiện sản phẩm, shot/framing phù hợp scene schema và reference được chọn. Prompt kỹ thuật trong “Nâng cao”. Lưu chỉnh sửa phải recompile/validate scene spec; báo những mâu thuẫn cần người dùng xử lý. Không tạo clip khi chỉ lưu plan.

Summary trước tạo hiển thị sản phẩm/variant, duration, aspect ratio và phạm vi generation. Nếu có credits/estimate, server phải trả estimate + expiry hoặc giới hạn cho phép; không tự đặt giá trong UI. Nếu chưa thể estimate, chính sách có thể dùng budget ceiling đã xác nhận; cách tính này vẫn là quyết định mở.

CTA chính: **Tạo video · 16 giây** hoặc 8 giây đúng lựa chọn. Không bắt seller tick đồng ý ở mọi card; chỉ yêu cầu xử lý thông tin thiếu/mâu thuẫn thực tế.

### Đang tạo video

Giữ plan đang render được snapshot; sửa plan mới không làm thay đổi job cũ. Thông điệp “Đang tạo video cho [sản phẩm]”, scene-level status nếu có. ETA chỉ hiện khi có dữ liệu đáng tin; không dựng thời gian còn lại từ timer.

Nếu một cảnh thành công, một cảnh thất bại: giữ clip thành công, chỉ rõ cảnh chưa có video, cho thử lại đúng cảnh. Output chưa ghép đủ không được gắn nhãn video hoàn chỉnh hoặc cho export file không hợp lệ.

### Video của bạn

Preview lớn là trọng tâm. Header có tên project và nhãn “Bản đang dùng · v1”. Cảnh hiển thị dưới preview hoặc rail bên cạnh theo chiều rộng. Technical checks và mục cần seller xem phân biệt rõ; không mặc định đánh giá creative taste là lỗi.

Hành động chính khi output hợp lệ: **Tải video**. Hành động theo cảnh: **Sửa cảnh này**. Tải bản hiện tại không bắt seller đi qua vòng sửa. Có thể đánh dấu “Tôi sẽ dùng bản này” để đo acceptance riêng; không coi download tự động là chấp nhận và không cần thêm bước blocking.

Nếu QA phát hiện vấn đề kỹ thuật làm file không dùng được, chặn export/accept tương ứng và chỉ rõ sửa gì. Các vấn đề nội dung/unknown trình bày “Cần bạn kiểm tra…” với evidence/scene; không gọi là “Đạt để đăng” hoặc dự đoán bán tốt.

### Sửa cảnh ngay trong project

Từ scene card chọn “Sửa cảnh này”, mở repair inspector; context video/product/scene không biến mất. Giao diện hỏi:

1. **“Cảnh này chưa đạt ở đâu?”**: Sản phẩm chưa đúng / Hành động chưa đúng / Hình ảnh bị lỗi / Muốn cách thể hiện khác.
2. **“Bạn muốn thay đổi thế nào?”**: brief điền từ scene hiện tại, gợi ý tương ứng taxonomy nhưng seller sửa được. Ô trống có ví dụ, không mặc định thêm claim/số liệu sản phẩm.
3. **“Ảnh tham chiếu”**: ảnh chính đang dùng; đổi/chọn reference được validate. Chưa gọi đây là sửa sản phẩm nếu chỉ thay thumbnail mà không chuyển reference vào pipeline.
4. **“Phạm vi tạo lại”**: “Tạo lại cảnh 2, từ 8–16 giây. Cảnh 1 giữ nguyên clip.” Hiển thị cả block, không hứa sửa đúng một frame.
5. **“Ưu tiên giữ trong cảnh mới”**: hành động/style đã đúng. Phân biệt best-effort với bảo toàn asset của cảnh khác.

CTA **Tạo lại cảnh 2 · 8 giây**. Khi chưa submit, có thể thoát về video hiện tại và giữ draft; không tự tạo job vì đổi tab hoặc bấm lưu. Double click/resume không tạo paid job trùng. Budget hết phải báo trước hành động phụ thuộc budget.

### So sánh, kiểm tra và áp dụng

Candidate render xong chưa tự thay active. Desktop A/B có nhãn “Bản đang dùng / Bản mới”, cùng playhead và một audio phát. Mobile dùng toggle cùng vị trí playback. Có nút xem đoạn nối trước/sau hoặc toàn video ở dạng preview manifest; ghi rõ chưa phải final export nếu chưa compose.

Phía phải là yêu cầu sửa và kết quả kiểm tra gắn đúng candidate: Đã sửa / Còn vấn đề / Phát sinh mới / Cần bạn xác nhận. Nếu QA còn chạy, hiển thị stage và giữ candidate; lỗi dịch vụ QA cho thử lại kiểm tra mà không tạo lại video.

CTA chính **Dùng cảnh mới** sau technical gate; action phụ **Giữ cảnh hiện tại** và **Chỉnh yêu cầu và thử lại**. Finding uncertain cần review/ack theo chính sách rõ, không ép system tự quyết định thay seller.

Bấm dùng cảnh mới → compose + QA video cuối → đổi active output thành revision mới. Trong lúc ghép, video hiện tại vẫn dùng được. Nếu ghép fail, candidate không mất. Hai tab xung đột phải cho xem active mới, giữ candidate của tab cũ, không ghi đè âm thầm.

Thành công: “Đã thay cảnh 2. Cảnh 1 giữ nguyên.” CTA **Tải video mới**; liên kết **Xem lịch sử** để so sánh/khôi phục. Rollback cũng tạo revision manifest mới và recompose nếu cần; không xóa lịch sử.

### State/action contract

| State | Primary action | Khả năng phục hồi |
| --- | --- | --- |
| Empty/invalid inputs | Phân tích khi đủ dữ liệu | Báo lỗi đúng trường, không mất file khác |
| Analyzing | Xem tiến trình | Resume/retry theo job |
| Plan ready/draft | Tạo video | Lưu sửa plan, snapshot revision |
| Generating/partial failure | Xem tiến trình hoặc thử lại cảnh lỗi | Giữ clip thành công |
| Output ready | Tải video | Sửa cảnh là action cục bộ |
| Repair draft | Tạo lại cảnh cụ thể | Giữ brief khi thoát |
| Candidate pending checks | Xem tiến trình kiểm tra | Retry check không regenerate |
| Candidate review | Dùng cảnh mới | Giữ cũ/thử lại, QA đúng version/context |
| Composing | Xem tiến trình ghép | Active cũ còn nguyên |
| New output ready | Tải video mới | History/rollback |
| Stale/conflict/save failure | Tải active mới hoặc thử lưu lại | Giữ draft/candidate và thông báo tại chỗ |

### Layout, accessibility và motion

- Giữ AppShell/tokens/font hiện có, primary coral của Viraldy. Không thêm landing page hero vào đầu tác vụ.
- Entry/plan max content khoảng 1120–1280px, padding 24–32px desktop, 16px mobile. Bắt đầu bằng hai input ngang, không workspace ba cột trống.
- Result/repair có rail 200–240px, preview min 360px, inspector 320–360px khi đủ chỗ. Từ <=1100px chuyển rail thành horizontal scene strip; <=800px preview trên, inspector dưới/Sheet. Không thu nhỏ nguyên desktop để vừa mobile.
- Stepper có text và current/completed states, không cho bước chưa có output trông như đã mở. Cho quay lại bước đã có; input edits không silently invalidate active media.
- Control >=44px touch target trên coarse pointer, font form >=16px mobile, focus rõ, error mô tả bằng text; scene/issue không chỉ dựa vào màu. Các thao tác hover đều có nút thay thế.
- Bàn phím hoạt động trên control native; Space play ngoài form, Escape đóng panel mà không xóa draft. Focus chuyển tới heading/region khi đổi bước; không giật focus khi job poll.
- Motion 120–200ms phục vụ mở inspector/đổi state, có reduced motion. Không dùng scroll pinning, animation trang trí hoặc progress giả cạnh video.

### Implementation contract và dependencies

Actors: seller có workspace access; backend compile/generation/QA/compose và worker. UI đọc scene/job/version state từ server; UI store chỉ quản lý form/selection và draft pending save.

Capabilities hiện có: upload/compile, product link preview, render toàn bộ và output URL. Capabilities cần bổ sung: project persistence, revisioned scene plan editing, single-scene generation, partial completion resume, stable scene assets, QA theo version/context, candidate compare, accept/compose/rollback. Không thể hoàn thành feature chỉ bằng sửa React UI.

Đặc biệt cần xử lý trước khi hứa product link dùng được xuyên suốt: UI hiện compile được metadata từ link nhưng live render helper vẫn yêu cầu uploaded `productImage`. Thiết kế cần tải/lưu ảnh primary từ link thành asset hợp lệ server-side và dùng cùng source-of-truth trong compile/render/repair. UI hiện nhận nhiều ảnh nhưng đường render chủ yếu dùng ảnh đầu; phải chỉ rõ ảnh chính, chỉ hứa multi-reference khi adapter thực sự hỗ trợ.

Interface tối thiểu: project/revisions và asset IDs; plan patch + expected revision; estimate/quota khi có; create render/repair operation idempotent; job status có stage/per-scene state; candidate QA có evidence/coverage; accept với expected active revision; output download URL có thể cấp lại. Server kiểm tra mọi relation thuộc workspace, không chỉ kiểm tra format IDs.

Chỉ dùng bộ thư viện miễn phí đã có cho core journey: Radix/shared UI, TanStack Router/Query, Zustand, React Hook Form/Zod, Lucide, react-resizable-panels khi cần workspace. Editor ý định không bắt buộc Konva; WaveSurfer chỉ thêm khi có audio-specific task. Không đưa SDK thương mại vào prerequisite.

Billing/quota policy, ETA và cancellation semantics vẫn là quyết định cần backend/product chốt trước production. Prototype dùng nhãn minh họa và không giả giá/ETA; không coi đó là quyết định billing hoặc provider capability.

Handoff: đủ để triển khai interaction/frontend states trên fixture, đồng thời cần contract/backend review trước khi nối live cho persistence/repair/QA/cost. Không phát hành các cam kết resume/targeted repair khi dependencies chưa có.

### Acceptance cho trải nghiệm

1. Seller mới biết phải thêm gì và thực hiện phân tích mà không đọc tài liệu prompt.
2. Duyệt plan thấy rõ đây là dự định/reference, chưa phải video đã tạo; đổi yêu cầu không tự chạy generation.
3. Seller quay lại đúng project/bước; refresh job không submit trùng hoặc mất draft đã lưu.
4. Link/upload/reference được dùng thống nhất từ compile đến repair; chọn đúng variant/primary image.
5. Từ kết quả, seller tìm và sửa một cảnh trong cùng context; biết cả block 8 giây sẽ thay.
6. Candidate không thay active trước khi dùng; scene khác giữ nguyên asset; QA cũ/context cũ không pass candidate mới.
7. QA/compose fail, quota hết, conflict hoặc source hết hạn đều có action phục hồi và không làm mất output đang dùng.
8. Có thể tải video hợp lệ mà không bị bắt regenerate; download và acceptance là hai event khác nhau.
9. Kiểm thử task trên desktop/laptop/mobile, keyboard và long Vietnamese labels; không tràn ngang hoặc che primary action.
10. Prototype không gọi provider và không có nút export giả tạo file MP4 từ hình minh họa; live implementation phải có media thật và check phù hợp.

## Review usability trước implementation

Kết luận review ngày 2026-11-24: giữ kiến trúc ba bước nhưng prototype chưa đủ để gọi là layout đã được xác thực dễ dùng. Đây là đánh giá heuristic và kiểm tra artifact; chưa có task-based usability test với seller. Các sửa đổi dưới đây là yêu cầu cho lần thiết kế tiếp theo, chưa được áp dụng vào prototype hiện tại.

### Các quyết định UX thay thế mô tả trước ở nơi có xung đột

| Ưu tiên | Vấn đề quan sát được | Sửa thiết kế | Acceptance |
| --- | --- | --- | --- |
| P1 | “Video của bạn” hiện chỉ cho thấy cảnh đang chọn, mặc định cảnh cuối. Global download ở cạnh scene repair dễ làm sai mental model | Mặc định preview **Toàn bộ video**, có timecode tổng. Chọn scene chuyển sang **Cảnh 2 · 8–16 giây** và có nút về toàn video. Download luôn ghi rõ output toàn video | Seller biết mình đang xem cảnh hay cả video và file nào sẽ được tải |
| P1 | Duyệt kịch bản chủ yếu là card chữ; summary mô tả video mẫu chưa giúp đối chiếu trực quan | Card có frame nguồn được gắn nhãn reference, image sản phẩm, hành động dự kiến và marker sản phẩm xuất hiện. Mở thêm frame/chi tiết khi cần; không giả định ảnh tham chiếu là preview video tạo ra | Seller hiểu cảnh mong muốn qua visual + câu mô tả ngắn; reference thực có thể truy cập |
| P1 | Mobile giữ hai khung dọc A/B cạnh nhau, khó thấy chi tiết; summary sản phẩm bị `display:none` <=760px | Mobile dùng một player đủ rộng, toggle Bản đang dùng/Bản mới giữ playhead; nút/accordion Reference luôn còn truy cập. Không xóa context thiết yếu theo breakpoint | Kiểm tra màu/chi tiết sản phẩm ở 320/390px mà không cần phóng trang |
| P1 | Candidate không được dùng còn trong state nhưng thiếu nơi mở lại sau “Giữ cảnh hiện tại”; UI chỉ có rollback, chưa có history thật | Scene card có entry “1 bản mới chưa dùng”; panel lịch sử có thumbnail, bản đang dùng, candidate và tình trạng kiểm tra. Tách **Về bản đang dùng** (giữ candidate) khỏi **Bỏ bản mới** (hành động tường minh, có thể phục hồi theo policy) | Seller rời comparison rồi quay lại được candidate, không cần tạo lại |
| P1 | Bấm kiểm tra → chờ → tick “Tôi đã xem…” → bấm dùng tạo bước thừa | Tự chạy technical checks sau render candidate; comparison mở ngay với trạng thái đang kiểm tra. Nút kiểm tra lại chỉ cần khi retry/stale hoặc người dùng chủ động rerun. **Dùng cảnh mới** là hành động duyệt; không bắt checkbox xác nhận chung lặp lại. Với finding uncertain/blocking, chỉ hỏi quyết định cụ thể cần thiết | Happy path review chỉ cần một hành động duyệt sau khi check đủ điều kiện; lỗi QA không regenerate media |
| P1 | Active CTA coral #ff385c và chữ trắng 14px có contrast tính từ CSS khoảng 3.52:1, thấp hơn 4.5:1 cho text thường | Dùng token coral đậm đủ contrast cho nền nút, ví dụ token có sẵn #e00b41 đạt khoảng 4.89:1 với trắng. Giữ màu brand sáng cho mark phù hợp; kiểm tra hover/disabled/focus riêng | Text/button contrast đạt mức áp dụng của WCAG; không tuyên bố toàn UI compliant chỉ từ check này |
| P2 | CTA ở cuối nội dung có thể nằm ngoài màn đầu ở laptop/mobile; tiến trình và tác vụ có nguy cơ đòi cuộn quá nhiều | Layout app có action bar rõ và dễ tiếp cận, có thể sticky trong production sau khi kiểm tra bàn phím/zoom/safe area. Chỉ một CTA chính, summary phạm vi/chi phí sát CTA | Nút tạo/dùng không bị keyboard/overlay che; nội dung vẫn tiếp cận được ở zoom và màn nhỏ |
| P2 | Stepper cho quay lại có thể làm thay đổi input/plan trong khi output trước vẫn tồn tại mà chưa giải thích revision | Tách tư liệu/plan revision khỏi output đang dùng. Đổi input báo “Kịch bản cần cập nhật; video hiện tại vẫn được giữ”. Đang chạy job thì resume đúng snapshot, không tự submit do chuyển bước | Không âm thầm mất output/draft hoặc gắn plan mới cho video cũ |

Độ tương phản đối chiếu [WCAG 2.2 SC 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html). Các đề xuất về scope rõ, ít phải nhớ và khả năng quay lại dựa trên [NN/g usability heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/); cách bố trí cụ thể vẫn cần seller test.

### Điều cần kiểm chứng thay vì chấm điểm cảm tính

Cho 5–8 seller thuộc persona làm ba task không có hướng dẫn thao tác: tạo plan từ video+product; phát hiện/chọn và sửa một cảnh; so sánh rồi dùng candidate hoặc quay về bản cũ. Quan sát completion, nhầm scope, yêu cầu trợ giúp, lỗi thao tác và khả năng mở lại draft/candidate. Đây là vòng qualitative discovery, chưa chứng minh uplift thống kê.

Prototype hiện dùng minh họa thay media thật, chưa có upload/download/job/backend thật. Các phần đó giới hạn mức kiểm chứng usability playback và thời gian chờ, không phải bằng chứng bản thiết kế production chắc chắn dùng tốt. Handoff đúng: sửa các gap P1 trước, nối media/fixture thực và kiểm thử task; sau đó mới chốt layout để implement rộng.

## Thiết kế cập nhật: no-border, visual journey và micro UX

Ngày 2026-11-24. Đây là đặc tả thiết kế mới cho prototype và handoff; các quyết định ở đây thay thế mô tả layout/tương tác trước nếu xung đột. Chưa thay đổi UI runtime, chưa nối render/QA/backend và chưa xác thực bằng seller test. Review heuristic phía trên vẫn là danh sách cần kiểm chứng sau khi prototype được cập nhật.

### Ngôn ngữ thiết kế

**Studio nhẹ, tập trung vào sản phẩm và video.** Bề mặt dùng nền khác độ sáng, khoảng trắng và shadow nhẹ để chia vùng; không dùng đường viền trang trí quanh card, input, chip, player hoặc panel. Chỉ vùng đang tương tác mới có highlight. Giữ focus indicator rõ cho bàn phím; “no-border” không được làm mất trạng thái điều khiển.

- Canvas trung tính hơi ấm; surface trắng hoặc tối nâng một cấp; coral chỉ dành cho CTA chính, trạng thái đang chọn và điểm nhấn có ý nghĩa.
- Font kế thừa app; heading 28/34px, section 20/28px, body 15/22px, label 13/18px; input mobile tối thiểu 16px. Không dùng chữ siêu nhỏ để nhồi thông tin.
- Nhịp spacing 4/8/12/16/24/32/48px. Card radius 24px, control 12px, chip pill. CTA cao 48px; icon control ít nhất 44×44px.
- Mỗi màn chỉ có một CTA chính. Công cụ cục bộ dùng text/icon cùng label khi chưa quen; không giấu thao tác quan trọng sau hover.
- Light và dark dùng cùng hierarchy; dark dùng nền/surface khác độ sáng, tránh viền xám bao quanh mọi khối. Theme theo AppShell, không tạo công tắc theme riêng cho feature.

Token tham chiếu, ánh xạ về token AppShell khi implement; không thay toàn bộ design system của app:

```css
:root {
  --sr-canvas: #f7f6f8;
  --sr-surface: #ffffff;
  --sr-surface-raised: #ffffff;
  --sr-inset: #efedf2;
  --sr-text: #211e27;
  --sr-muted: #665e70;
  --sr-primary: #e00b41;
  --sr-primary-hover: #c90939;
  --sr-on-primary: #ffffff;
  --sr-selection: #fff0f3;
  --sr-focus: #336bd1;
  --sr-shadow: 0 8px 32px rgb(33 30 39 / 6%);
  --sr-radius-card: 24px;
  --sr-radius-control: 12px;
  --sr-motion-fast: 140ms;
  --sr-motion-panel: 200ms;
  --sr-ease: cubic-bezier(.2, .8, .2, 1);
}
[data-theme="dark"] {
  --sr-canvas: #151318;
  --sr-surface: #211e26;
  --sr-surface-raised: #2b2632;
  --sr-inset: #19161e;
  --sr-text: #f7f3fa;
  --sr-muted: #bfb4ca;
  --sr-selection: #3d202d;
  --sr-focus: #95b7ff;
  --sr-shadow: 0 8px 32px rgb(0 0 0 / 18%);
}
```

Primary coral đậm dùng với chữ trắng; brand coral sáng chỉ dùng ở vùng không yêu cầu đọc chữ trắng nhỏ. Kiểm tra contrast của từng trạng thái thực tế, nhất là text phụ, hover và focus; không suy ra accessibility toàn UI chỉ từ một token. Focus dùng outline 3px, offset 3px; outline là dấu tương tác, không phải decorative border.

### Visual hóa từng bước

**Thanh hành trình 3 thumbnail:** `Tư liệu → Kịch bản → Video`. Mỗi bước có tên + câu mô tả ngắn, thumbnail chỉ xuất hiện khi có dữ liệu thật. Chưa có dữ liệu dùng icon trung tính và “Chưa bắt đầu”; bước hiện tại có nền selection + số bước; bước hoàn thành có check + thumbnail; bước chưa mở có lý do bằng text. Trạng thái không chỉ mã hóa bằng màu. Không tạo phần trăm hoàn thành từ số bước.

1. **Tư liệu:** hai surface “Video mẫu” và “Sản phẩm của bạn”; sau upload, biến thành preview có thumbnail, metadata ngắn và nút Đổi. Giữa hai vùng là dấu “+” có caption “Lấy cách thể hiện từ mẫu, dùng sản phẩm của bạn”. Không dựng output giả cạnh form. Nút phân tích kèm câu còn thiếu tư liệu nào; tài liệu ví dụ phải được gắn “Minh họa”.
2. **Kịch bản:** storyboard theo thời gian. Mỗi cảnh có frame mẫu gắn “Tham chiếu”, ảnh sản phẩm đang dùng và mô tả hành động tối đa hai dòng trước khi mở rộng. Chọn card mở ý định cảnh ngay cạnh; thay đổi text làm nổi bật tóm tắt đã đổi. Một visual nối `Khung hình mẫu → Sản phẩm → Ý định cảnh` giải thích phép chuyển đổi; nhãn cuối là “Dự kiến”, không giả preview video AI.
3. **Video:** video đang dùng là tâm điểm; mặc định **Toàn bộ video · 16 giây · v1**. Filmstrip dưới player dùng thumbnail media thật + khoảng thời gian + status text. Chọn cảnh đổi heading thành **Cảnh 2 · 00:08–00:16**, làm rõ phạm vi trong player và có **Về toàn video**. CTA tải luôn ghi **Tải toàn bộ video**.

Output có ba cấp visual rõ ràng: tư liệu/reference, cảnh đã tạo, video đã ghép. Mỗi cấp có nhãn riêng; đang chờ thì dùng vùng trạng thái có stage, không dùng hình mẫu làm output. Thumbnail storyboard không bị coi là file có thể tải. Preview minh họa luôn có badge cố định “Minh họa · chưa tạo video”.

### Layout responsive và vùng thao tác

- Entry/plan max-width 1200px; desktop gap 24px, padding 32px; mobile padding 16px. Stepper luôn thấy tên bước hiện tại; màn nhỏ dùng “Bước 2/3 · Kịch bản” cùng nút mở toàn hành trình.
- Result mặc định có preview rộng + summary gọn. Khi sửa mới mở inspector 340px; không để panel sửa trống chiếm một phần ba màn hình. Cảnh dạng strip ngang ở dưới preview, badge “Có bản mới” luôn truy cập được.
- Từ 1100px trở xuống chuyển inspector sang vùng dưới; từ 800px trở xuống dùng một cột. Reference mở qua accordion/Sheet, không bị xóa khỏi mobile. Action bar cuối vùng tác vụ có safe-area và chừa chỗ để không che nội dung/focus.
- Desktop compare có hai player đồng bộ, một audio. Mobile compare chỉ một player lớn với segmented control **Đang dùng / Bản mới**, giữ playhead và trạng thái play/pause khi đổi. Nếu media lệch duration thì clamp về thời điểm hợp lệ và thông báo ngắn.
- Candidate luôn còn trong lịch sử cảnh dù seller quay về output; scene chip ghi số bản mới đang chờ. Không tự xóa candidate sau khi bấm “Giữ cảnh hiện tại”. History đánh dấu **Đang dùng / Chưa dùng / Bản trước**, kèm ngày tạo và kết quả kiểm tra.

### Micro UX contract

| Tương tác | Trigger | Feedback/UI | Acceptance |
| --- | --- | --- | --- |
| Nhận tư liệu | Chọn file hoặc thả file | Highlight drop zone; hiện upload từng file, thumbnail khi đọc được; lỗi ngay tại file | File khác đã hợp lệ được giữ; chọn lại cùng file không tạo asset trùng ngoài ý muốn |
| CTA chưa sẵn sàng | Thiếu video/product hoặc đang upload | Câu “Thêm ảnh sản phẩm để tiếp tục” cạnh nút; progress upload tách khỏi validation | Seller hiểu lý do mà không cần hover nút disabled; lỗi liên kết đúng input |
| Chuyển bước | Bấm CTA thành công hoặc quay lại bước có dữ liệu | Transition nhẹ; focus tới heading; thumbnail stepper cập nhật theo state thật | Không chạy job do navigation; bước chưa có dữ liệu không mở như đã hoàn tất |
| Chỉnh ý định | Sửa brief/reference rồi lưu | “Chưa lưu → Đang lưu → Đã lưu”; highlight phần tóm tắt thay đổi | Chỉ báo đã lưu sau server ack; save fail giữ draft và có Thử lại |
| Rời draft | Đổi cảnh, đóng inspector hoặc rời trang | Draft đã persist được khôi phục; draft chưa lưu có Lưu/Ở lại/Bỏ thay đổi rõ ràng | Escape không xóa draft; không hứa autosave khi backend chưa hỗ trợ |
| Chạy generation | Bấm tạo/tạo lại | Nút phản hồi ngay, khóa submit trùng, hiện đúng cảnh + stage server | Double click không tạo operation trùng; không dùng progress %, ETA hoặc giá giả |
| Tìm cảnh lỗi | Chọn scene chip/finding | Player tới timecode, chip được chọn + nhãn phạm vi; inspector mở đúng cảnh | Cả touch/keyboard đều làm được; scene chưa có clip không phát clip khác |
| Candidate mới | Render xong | Technical QA chạy tự động; badge “Bản mới đang kiểm tra”; thông báo không giật focus | Có thể mở xem ngay; lỗi QA chỉ retry check, không regenerate; không checkbox xác nhận chung |
| So sánh | Đổi tab Đang dùng/Bản mới | Giữ playhead; nhãn version luôn visible; brief sửa và reference mở tại chỗ | Không phát hai audio; không mất candidate khi rời compare |
| Dùng cảnh mới | Candidate đủ technical gate, seller bấm dùng | “Đang ghép video”; active cũ vẫn xem được; hoàn tất có toast + Mở lịch sử | Chỉ chuyển active sau compose/check hợp lệ; lỗi giữ candidate và có Thử ghép lại |
| Hoàn tác an toàn | Đổi reference/brief hoặc thay bản đã thành công | Toast 6 giây với Hoàn tác cho sửa draft; thay output dùng Khôi phục bản trước qua revision | Undo draft không tạo paid job; undo output giữ lịch sử, không giả revert ngay khi cần compose |
| Điều khiển/motion | Hover, focus, mở panel, reduced motion | Hover đổi surface; press scale rất nhẹ; tooltip có label; reduced motion tắt transform/slide | Không phụ thuộc animation để hiểu state; status có live region phù hợp, không đọc lại mỗi lần poll |

Toast chỉ xác nhận hành động ngắn; lỗi ảnh hưởng khả năng tiếp tục phải hiện inline và tồn tại đến khi xử lý. Skeleton chỉ che vùng dữ liệu thật đang tải; stop shimmer theo reduced motion. Loading không đổi chiều rộng nút hoặc làm layout nhảy. Không phát confetti, tự phát audio hoặc tự cuộn khỏi vùng seller đang xem.

### Handoff implementation và kiểm chứng

Core dùng CSS variables + CSS transitions và stack miễn phí đã có: shared UI/Radix cho Sheet/Tooltip/Toast, Lucide cho icon, React Hook Form/Zod cho form và TanStack Query/Zustand cho dữ liệu/state cục bộ. Không thêm thư viện motion, canvas hoặc video editor chỉ để thực hiện thiết kế này. Player dùng media thật khi nối live; prototype chỉ mô phỏng state, không giả xuất MP4.

Component đề xuất: `VisualJourneyStepper`, `SourceAssetSurface`, `SceneStoryboardCard`, `OutputPreview`, `SceneFilmstrip`, `RepairInspector`, `CandidateCompare`, `SceneVersionHistory`, `ActionBar`, `SaveStatus`. Dữ liệu reference/active/candidate/QA phải tách theo ID và revision; tên component là handoff, chưa phải xác nhận component runtime hiện có.

Kiểm tra artifact ở 390px, 768px, 1280px và 1440px; desktop zoom 200%, keyboard từ đầu đến cuối, text tiếng Việt dài, reduced motion và đủ light/dark token. Task acceptance: seller nhận biết reference khác output; phân biệt toàn video với cảnh; tạo lại đúng một cảnh; mở lại candidate sau khi rời compare; dùng/khôi phục mà không mất output trước. Chỉ sau vòng seller test mới chốt mức dễ dùng và mở rộng implementation.

### Responsive theo khung video

Responsive có hai lớp độc lập: **viewport/container** quyết định vị trí panel và controls; **aspect ratio của media** quyết định kích thước vùng phát. Không lấy breakpoint màn hình để ép video vào một khung sai tỷ lệ. Output hiện tại là video dọc 9:16; video mẫu có thể khác tỷ lệ và vẫn cần xem trọn khung.

- Metadata media thật là nguồn quyết định tỷ lệ preview: đọc `videoWidth`/`videoHeight` sau `loadedmetadata` hoặc metadata đã xác thực từ asset; dùng tỷ lệ project làm placeholder khi output chưa có metadata. Nếu metadata output khác contract 9:16, báo lỗi kỹ thuật thay vì crop để che sai lệch.
- Player nằm trong stage trung tính, `object-fit: contain`, không stretch hoặc crop; cả video mẫu và output đều phát full-frame. `cover` chỉ dùng cho thumbnail/filmstrip khi cần đồng nhất bố cục; nhãn thumbnail không được ngụ ý phần bị crop đã biến mất khỏi media.
- Preview bị giới hạn đồng thời bởi chiều rộng container và chiều cao còn lại sau header/controls/action bar. Với tỷ lệ `r = width / height`, dùng `previewWidth = min(availableWidth, availableHeight × r)` và `previewHeight = previewWidth / r`; stage có thể letterbox. Không kéo player 9:16 cao đến mức che CTA trên laptop thấp.
- Mobile portrait ưu tiên một player vừa chiều rộng và chiều cao khả dụng; mobile landscape dùng stage thấp hơn, controls chuyển thành hàng gọn, inspector chuyển dưới/Sheet. Xoay màn hình không reset scene, version, playhead hoặc trạng thái play/pause.
- Compare chỉ dùng A/B cạnh nhau khi container thực đủ chỗ cho hai player và controls đọc được; nếu không thì chuyển một player + toggle, kể cả trên desktop khi inspector/sidebar đang mở. Toggle giữ playhead và play/pause; chờ metadata mới rồi seek, clamp nếu duration khác và chỉ phát một audio.
- Trong lúc tải metadata, giữ stage/controls ổn định bằng tỷ lệ project hoặc asset đã biết; skeleton nằm trong stage, không đẩy nội dung. Khi metadata về, chỉ resize vùng media trong stage; không làm layout nhảy, tự cuộn hoặc reset focus.
- Repair giữ ratio, scene timing và tổng thời lượng theo contract project. Không hiển thị bộ chọn 1:1/16:9 hoặc công cụ đổi format output trước khi backend/compose hỗ trợ; hỗ trợ xem source khác tỷ lệ không đồng nghĩa hỗ trợ render mọi format.

Acceptance bổ sung: kiểm tra source 9:16/16:9/1:1 và output 9:16 trên container hẹp, laptop thấp, điện thoại dọc/ngang và compare mở inspector; không mất mép sản phẩm/chữ trong playback, không tràn ngang, action vẫn truy cập được và đổi layout không mất vị trí xem.

### Hiệu chỉnh entry: khung tư liệu và câu chữ

Quy tắc tỷ lệ native áp dụng ngay từ **bước chọn tư liệu**, không chỉ ở output. Video mẫu 9:16 phải nằm trong một frame dọc 9:16 thực; không nhét vào ô ngang rồi crop để làm card đều nhau. Các điểm này thay thế mọi minh họa entry trước chưa làm đúng.

- Sau khi chọn video, dùng metadata để xác định frame preview, `aspect-ratio` đúng media và `object-fit: contain`. Giới hạn kích thước bằng cả chiều rộng và chiều cao khả dụng; khoảng trống đặt ngoài frame, không cắt đầu/cuối video. Video mẫu 16:9 hoặc 1:1 vẫn giữ tỷ lệ của chính nó.
- Card tư liệu có header, vùng preview và hàng action riêng. **Chọn video khác / Xóa** nằm dưới hoặc bên cạnh frame, không đè giữa hình. Chỉ control phát video thông dụng được nằm trên video; không phủ lớp tối mạnh lên toàn frame để làm nền cho nút upload/đổi file.
- Ảnh sản phẩm hiển thị toàn ảnh bằng `object-fit: contain`, lấy tỷ lệ từ `naturalWidth`/`naturalHeight`; không kéo ảnh thành video dọc hoặc crop vào ô ngang. Nền trung tính nhẹ làm rõ ảnh; không cần làm tối ảnh sản phẩm để đặt chữ trắng.
- Video và ảnh sản phẩm không phải có cùng tỷ lệ hoặc cùng chiều cao. Desktop giữ header/action thẳng hàng nhưng cho mỗi preview có kích thước tự nhiên trong stage giới hạn; mobile xếp dọc, giữ nhãn và action cạnh đúng tư liệu. Trước khi có media, dùng upload surface gọn, không giả một frame đã biết tỷ lệ.
- Metadata, tên file và hướng dẫn nằm ngoài ảnh/video. Nhãn **Video mẫu / Ảnh sản phẩm** đủ rõ; tỷ lệ và thời lượng là thông tin phụ, không cạnh tranh với hình. Error cũng đặt dưới vùng liên quan, không che chi tiết cần seller kiểm tra.

Copy dùng tiếng Việt tự nhiên, gọi đúng vật seller đang thao tác và nói rõ hành động tiếp theo. Mỗi helper một ý, ưu tiên một câu ngắn; tránh mô tả hệ thống kiểu “asset”, “generation”, “product lock” hoặc diễn đạt dịch sát tiếng Anh trong luồng chính. Mô tả ý định AI không biến thành cam kết kết quả chính xác.

| Câu hiện có/cần tránh | Câu dùng trong thiết kế |
| --- | --- |
| “Lấy cách thể hiện từ mẫu, dùng sản phẩm của bạn” | “Làm video theo mẫu cho sản phẩm của bạn.” |
| “Chọn video có cách mở đầu hoặc cách giới thiệu sản phẩm bạn muốn làm theo.” | “Chọn video có cách quay hoặc mở đầu bạn thích.” |
| “Ảnh này sẽ làm tham chiếu nhận diện sản phẩm.” | “Chọn ảnh rõ nhất của đúng sản phẩm bạn đang bán.” |
| “Ưu tiên giữ trong cảnh mới” | “Phần nào bạn muốn giữ?” |
| “Phạm vi tạo lại” | “Chỉ tạo lại cảnh 2 · 8 giây” và dòng phụ “Video cảnh 1 được giữ nguyên.” |
| “AI sẽ giữ chính xác mọi chi tiết sản phẩm” | “AI dùng ảnh này làm tham chiếu. Bạn hãy kiểm tra sản phẩm trong video mới.” |

CTA cụ thể theo tác vụ: **Chọn video**, **Thêm ảnh sản phẩm**, **Phân tích video mẫu**, **Tạo lại cảnh 2**, **Dùng cảnh mới**. Tránh label chung như “Thực hiện”, “Xử lý ngay” hoặc “Tiếp tục” khi có thể gọi tên hành động. Button không nhồi description; helper ở cạnh CTA giải thích điều cần biết trước khi bấm.

Acceptance entry: nhìn thấy trọn đầu/cuối frame video 9:16 và toàn ảnh sản phẩm; nút đổi/xóa không che hình; không dim tư liệu để bù contrast; đổi sang source 16:9/1:1 thì frame đổi đúng tỷ lệ. Seller đọc heading/CTA biết cần đưa gì vào và bước sau làm gì, không phải hiểu thuật ngữ AI. Đây là hiệu chỉnh prototype/spec, chưa thay runtime.

## Ghi nhận bàn giao implementation

Cập nhật ngày 2026-11-24. Phần này ghi trạng thái code đã triển khai, thay thế các câu “chưa thay runtime” ở những bản thiết kế phía trên đối với phạm vi dưới đây; các đề xuất chưa nêu vẫn cần kiểm chứng/triển khai riêng.

- **Luồng seller đã vào runtime:** ba bước Chuẩn bị → Duyệt kịch bản → Video của bạn; surface không có viền trang trí, focus indicator vẫn rõ. Preview input giữ tỷ lệ media thật, dùng `contain`, nút chọn/đổi nằm ngoài hình; không đặt video dọc vào khung preview ngang có nền màu.
- **Chọn video từ kho:** bước chuẩn bị có “Chọn từ kho video”, đọc cùng dữ liệu Creative Library hiện tại. Có tìm kiếm không dấu, xem trước đúng tỷ lệ, tên lựa chọn và xác nhận “Dùng video này”; ảnh sản phẩm và thiết lập đang nhập được giữ. Chỉ thay video sau khi tải/kiểm tra file thành công, không tự chạy phân tích. Mục chỉ có metadata chưa có file được vô hiệu hóa; blob upload đã hết hiệu lực cần tải lại trong kho. Giới hạn Smart Remake là 30 MB, dù kho cho phép file lớn hơn.
- **Kho video cho seller:** mặc định mở “Đã lưu”, tách “Khám phá video” sang tab riêng. Bộ lọc nhanh ưu tiên mục có nguồn video, hiển thị số lượng và phân biệt mục chưa có file; tìm theo tên, câu mở đầu, người đăng, ghi chú và từ khóa, hỗ trợ tiếng Việt không dấu. Card có nút xem trước và tạo với Smart Remake; video giữ đúng tỷ lệ, không tự phát khi rê chuột. Dialog xem trước chỉ chuyển sang Smart Remake sau khi seller xác nhận và file tải/kiểm tra thành công; đóng trước khi tải xong sẽ hủy lựa chọn. Giao diện có dạng lưới/danh sách gọn, bộ sưu tập thu gọn trên mobile, trạng thái không có kết quả và cách đặt lại bộ lọc.
- **Thêm tư liệu và khám phá:** mặc định tải file từ máy, có lựa chọn lưu link tham khảo hoặc thử minh họa. Link gốc được giữ trong ghi chú; link người dùng thêm không bị gắn nhãn minh họa. Form tìm TikTok có nhãn tiếng Việt, bộ lọc nâng cao thu gọn, vùng chạm tối thiểu 44px ở các điều khiển đã sửa và không tự phát video kết quả. UI nói rõ phạm vi thị trường nguồn hỗ trợ, không suy diễn dữ liệu tham khảo thành doanh số hay dự đoán bán hàng.
- **Kịch bản và prompt tự động:** hệ thống phân tích video mẫu và ảnh sản phẩm để sinh kịch bản, prompt ảnh và prompt video. Mặc định mục tiêu làm theo cách quay, hành động và nhịp mẫu, thay bằng sản phẩm tải lên; seller có thể thêm yêu cầu riêng, để trống vẫn dùng mục tiêu mặc định. Màn duyệt hiển thị nội dung cảnh; cả ba prompt thật từ compile result nằm trong mục nâng cao thu gọn, không bắt seller viết prompt. Các ô vẫn tồn tại khi xóa nội dung. Có sao chép cả ba prompt, thông báo đúng kết quả clipboard và vùng chọn thủ công khi sao chép lỗi. Prompt video sửa có bộ đếm/giới hạn snapshot 12.000 ký tự; không tự cắt prompt gốc. Backend chuyển phần thay đổi có kiểm soát vào prompt thực dùng tạo cảnh, giữ các ràng buộc sản phẩm; việc gửi ràng buộc không bảo đảm AI giữ đúng mọi chi tiết hình ảnh.
- **Project và phiên bản đã lưu:** backend lưu project, revision/manifest, media cảnh, candidate và operation qua migration `0023_smart_remake_scene_repair`. Migration đã được áp dụng trên môi trường local của lượt triển khai này; chưa phải xác nhận đã áp dụng trên môi trường triển khai khác.
- **Sửa cảnh có kiểm soát:** tạo lại đúng block 8 giây đã chọn; clip của cảnh còn lại được giữ. Candidate chưa tự thay bản đang dùng. Có so sánh, dùng cảnh mới, khôi phục bản trước và tải output qua URL ký có thời hạn; UI giữ rõ phạm vi toàn video/cảnh và phiên bản đang dùng.
- **Fixture và demo được phân biệt:** trạng thái fixture/demo có nhãn minh họa; tư liệu thử chỉ vào luồng khi người dùng chọn thử. Media minh họa không được trình bày như bằng chứng AI vừa tạo hoặc kiểm tra video thật.
- **KIE Veo 3.1 đã vào runtime:** khi live và có `KIE_API_KEY`, frontend ưu tiên KIE. Render đầu và tạo lại cảnh chạy qua job Celery đã lưu; API trả project pending để seller theo dõi. Mỗi cảnh là một task dọc 8 giây dùng ảnh sản phẩm; contract v1 ghép video 16 giây từ hai cảnh, còn Timeline v2 cho phép tới bốn cảnh với đoạn sử dụng riêng. Prompt, product lock, phiên bản, kiểm tra kỹ thuật và bước seller duyệt vẫn được giữ. API/worker nạp `.env` qua các target Makefile; không đặt key ở frontend.

### Giới hạn vận hành cần giữ trong handoff

Bộ sưu tập hiện lưu trong trình duyệt bằng store hiện có, **chưa phải kho đồng bộ qua tài khoản hoặc thiết bị**. File tải lên dùng blob URL và có thể cần tải lại sau khi tải lại trang/kết thúc phiên. Video lưu từ tìm kiếm TikTok đi vào workspace backend, **chưa tự xuất hiện trong bộ sưu tập local hoặc picker Smart Remake**; hai bề mặt đã ghi rõ ranh giới này. Nhãn “có nguồn video” phản ánh có URL trong dữ liệu, không bảo đảm URL còn tải được; bước xác nhận vẫn kiểm tra file thực tế.

**KIE dùng durable jobs/worker** cho render đầu và tạo lại cảnh. Project/operation, ý định submit và task ID được lưu trước khi chờ kết quả; worker retry và GET đối soát được serialize theo operation. PostgreSQL, broker/Redis, worker, private storage và beat phải hoạt động để xử lý/phục hồi tác vụ. Chỉ đóng trang sau khi đã nhận project pending; nếu mất response POST trước khi nhận project ID rồi reload, frontend chưa tự khôi phục request key/snapshot đó. Không hứa exactly-once với provider khi kết quả submit không rõ.

Unifically/FlowKit vẫn được `await` trong request; phần triển khai KIE không chuyển các provider cũ sang worker.

Operation mà provider có thể vẫn xử lý được giữ ở trạng thái `running`, ngăn tự submit thêm một yêu cầu có phí. Với KIE, task ID đã biết được dùng lại khi worker retry hoặc kiểm tra kết quả; download/lưu media lỗi không tạo generation mới. Nếu submit chưa rõ kết quả và chưa xác nhận được task ID, vẫn cần vận hành đối soát lịch sử KIE thủ công; refresh không tự gửi thay thế. UI hiển thị lỗi terminal bằng tiếng Việt và giữ các cảnh/bản đang dùng. Unifically/FlowKit chỉ phục hồi qua task ID đã lưu trong phạm vi repair; initial render của provider cũ chưa có vòng durable KIE. FlowKit bị ngắt ở bước tạo ảnh vẫn cần đối soát thủ công.

### Bằng chứng và phần chưa được xác thực

Frontend build, typecheck và 409 tests đã chạy thành công ở local sau đợt tích hợp KIE. Lint trong phạm vi Smart Remake/shared API đạt; lượt kiểm tra Creative Library trước đó không có lỗi, còn ba cảnh báo Fast Refresh có sẵn ở analysis-jobs-runner/filter-sheet. Lint toàn source ở lượt kiểm tra trước vẫn có 393 lỗi có sẵn ngoài phạm vi này. Đã kiểm tra preview video mẫu đúng tỷ lệ trong browser và luồng chọn video từ kho trên desktop/mobile 390px, giữ ảnh sản phẩm và không tràn ngang; kiểm tra thêm tìm theo câu mở đầu, dạng danh sách gọn, mặc định nhập file và form khám phá/bộ lọc nâng cao. Các kiểm tra này xác nhận phạm vi kỹ thuật đã chạy, không chứng minh chất lượng mọi video từ provider hoặc trải nghiệm seller đã tối ưu.

Backend đạt 36 tests trong phạm vi Smart Remake, gồm migration/concurrency trên PostgreSQL thật và xử lý media bằng FFmpeg; coverage đo được của phần core mới là **82,17%**, không phải coverage toàn backend. Ruff và mypy trong phạm vi thay đổi đạt; lượt kiểm tra độc lập 19 tests cũng đạt.

Lượt tích hợp KIE tiếp theo đạt **133 backend tests**, gồm 10 integration tests KIE với PostgreSQL thật, migration và media dọc 8 giây qua FFmpeg. Năm module KIE mới đạt **91,94% coverage** (không phải coverage toàn backend); Ruff trong phạm vi thay đổi và mypy 10 source files đạt. Thêm 14 tests setup local đạt. Browser fixture và HTTP xác nhận fixture không tạo KIE task thật; kiểm thử integration thay KIE bằng provider giả, không phát sinh generation có phí.

Chưa xác nhận vòng AI có phí thực tế cho toàn bộ hành trình; không suy ra từ fixture hoặc đặt tỷ lệ coverage khi chưa đo. Seller usability test được đề xuất phía trên vẫn chưa thực hiện. Trước khi chốt khả năng dùng rộng, cần kiểm chứng tạo/sửa/ghép với provider thật và cho seller tự hoàn thành các task đã nêu, trong ngân sách được chấp thuận.

## Bàn giao đợt Timeline trực quan · 2026-11-25

**Timeline v2 đã vào runtime**, giữ project v1 tương thích. Ba bước hiện tại là **Tư liệu → Kịch bản → Xem & ghép**. Seller chọn một đoạn mẫu 8/16 giây, duyệt mốc cắt trên filmstrip đúng tỷ lệ thời lượng rồi chọn phần phù hợp từ từng clip AI. Đầu ra giữ 9:16, tối đa bốn cảnh, mỗi cảnh nguồn không quá tám giây; timing lưu bằng frame 24 fps, không tự đổi nhịp hoặc gộp cảnh để vừa kế hoạch.

Một cảnh nguồn 3 giây dùng một task KIE Veo 3.1 Fast sinh clip thô 8 giây; seller chọn đoạn 3 giây sẽ dùng. Gợi ý đoạn cắt có nhãn chưa duyệt, cần “Dùng đoạn này”; chỉ bật ghép khi mọi cảnh đã có clip và đoạn hợp lệ được xác nhận. Ví dụ 3 + 5 + 4 + 4 giây tương ứng bốn lượt tạo và video hoàn chỉnh 16 giây, không phải hai cảnh bắt buộc.

Preview nguồn giữ nguyên khung; filmstrip dùng thumbnail thật và chọn cảnh sẽ tua một player nguồn. Có kéo chọn, nhập thời gian, vị trí phát hiện tại và điều khiển bàn phím. Prompt vẫn hiển thị trong từng cảnh. Bước kết quả phân biệt clip AI thô, đoạn sử dụng, bản nháp và video đã xuất; layout sáng ít viền, panel xuống dưới preview ở khung hẹp, timeline cuộn trong vùng riêng. Không thêm SDK timeline.

Compile v2 lưu draft và tư liệu gốc trong PostgreSQL/private S3 ngay cả ở fixture mode. KIE hoàn tất chưa tự ghép; duyệt candidate cập nhật draft và yêu cầu duyệt lại đoạn cắt. Worker FFmpeg ghép snapshot scene/version đã chọn, không gọi KIE. Ghép lỗi giữ bản đã xuất trước đó và cho thử ghép lại. Tái sử dụng migration `0023`, không thêm migration mới. Chi tiết contract/API và cách kiểm chứng nằm trong [bàn giao kỹ thuật](../implementation/smart-remake-controlled-scene-repair-plan.md#bàn-giao-timeline-v2--2026-11-25).

Lượt kiểm tra Timeline đạt **197 backend tests / 474 frontend tests**, coverage sáu module Timeline backend mới **90,29%**, helper timeline frontend **96% lines**; scoped lint, typecheck và production build đạt. Đây là coverage các phạm vi logic đã nêu, không phải toàn bộ UI/repository. Giữ riêng các số đo lịch sử ở phần trước. Browser đã kiểm tra layout 390/768/1280/1440px và luồng sửa mốc → duyệt bốn đoạn → ghép video 3–5–4–4 giây → mở lại sau reload bằng media fixture. Chưa xác nhận zoom 200% và cảm ứng trên thiết bị thật. Provider giả và media fixture không phát sinh generation KIE có phí; chất lượng giữ sản phẩm, chữ/logo, trải nghiệm seller và kết quả kinh doanh vẫn cần kiểm chứng riêng.

## Desktop, Veo Lite và sinh video theo nhóm · 2026-11-25

Ưu tiên hiện tại là seller làm việc trên desktop. Giữ nền sáng, preview trọn khung media, card trong cùng hàng cân kích thước và nội dung dài không đẩy lệch layout. Ba bước **Tư liệu → Kịch bản → Xem & ghép** tiếp tục là luồng chính; không thêm bước kỹ thuật để seller phải hiểu provider trước khi tạo video.

Video mới dùng **Veo 3.1 Lite trên KIE**; ảnh tạo/chỉnh dùng **GPT Image trực tiếp từ OpenAI Platform**. Cảnh vẫn là đơn vị seller xem, chỉnh prompt, kiểm tra và tạo lại. Nhóm sinh video là cách backend kết hợp các cảnh liền nhau vào cùng một task 8 giây khi tổng không quá tám giây, giữ nguyên từng cảnh và không chia một cảnh qua hai task.

| Timeline seller muốn giữ | Kế hoạch video mặc định |
| --- | --- |
| 3 + 5 + 4 + 4 giây | 4 cảnh · 2 lượt tạo video · 16 giây thành phẩm |
| 2 + 2 + 2 + 2 giây | 4 cảnh · 1 lượt tạo video · 8 giây thành phẩm |
| 5 + 5 + 6 giây | 3 cảnh · 3 lượt tạo video · 16 giây thành phẩm |

Kịch bản phải làm rõ nhóm nào chứa những cảnh nào và mốc cục bộ trong clip nhóm; cho tách nhóm bằng mốc rõ ràng rồi cập nhật kịch bản trước tạo. Không hiển thị số lượt tạo bằng số cảnh một cách mặc định. Các project cũ không có nhóm giữ cách chia đã lưu; operation/task đang chạy không bị chuyển kế hoạch.

Mỗi nhóm tham chiếu ảnh sản phẩm gốc và ảnh GPT của cảnh đầu/cuối, tối đa ba ảnh gửi KIE; nhóm một cảnh chỉ cần một ảnh GPT. Ảnh GPT dựa trên sản phẩm thật và bố cục nguồn. Cấu hình khởi đầu là `gpt-image-2.6-flare`, PNG 720×1280, `n: 1`, quality `low`; có chính sách `medium` được đóng băng khi lập kế hoạch. Không tự nâng quality để tạo thêm lượt ảnh. Ảnh đã hợp lệ được dùng lại khi media, prompt và cấu hình không đổi, kể cả draft mới từ cùng project sở hữu và tư liệu khớp hash.

Usage ảnh được lưu để tính chi phí thực tế, không dùng đơn giá ảnh KIE cố định cho OpenAI. Ít task video hơn chỉ là một yếu tố kinh tế; cần đo tổng ảnh + video + QA + dựng và số phiên thất bại trên mỗi video seller chấp nhận.

Ở bước xem, cảnh thứ hai trong nhóm 3 + 5 giây được gợi ý đoạn 3–8 giây của clip chung, không tự chọn lại 0–5 giây. Mọi gợi ý vẫn **chưa duyệt**. Seller xem từng cảnh, chọn đoạn thực tế phù hợp và “Dùng đoạn này” rồi mới ghép. Timestamp gửi model là mục tiêu, không phải bằng chứng cảnh đã diễn ra đúng mốc.

Nếu một cảnh lỗi, Scene Fix tiếp tục tạo candidate riêng cảnh đó bằng Lite và giữ media cảnh tốt, kể cả chúng từng dùng chung clip nhóm. Dùng candidate chỉ cập nhật cảnh được chọn trong draft; cần duyệt lại đoạn cắt. Lưu trim hoặc thử ghép lại không sinh ảnh/video AI mới, và ghép lỗi giữ bản đã xuất trước. Kết quả submit provider chưa rõ cần đối soát, không tự tạo một lượt trả phí thay thế.

Contract giữ `schemaVersion: 2`, bổ sung nhóm vào plan đã lưu và tiếp tục dùng JSONB/migration `0023`; không thêm migration mới. Chi tiết kỹ thuật ở [bàn giao nhóm sinh video](../implementation/smart-remake-controlled-scene-repair-plan.md#veo-lite-ảnh-openai-và-nhóm-sinh-video--2026-11-25).

Cấu hình được đối chiếu với [KIE Veo 3.1](https://docs.kie.ai/veo3-api/generate-veo-3-video) và [OpenAI GPT Image 2.6 Flare](https://developers.openai.com/api/docs/models/gpt-image-2.6-flare). [Ví dụ multi-shot của Google](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1) hỗ trợ hướng timestamp prompting; độ chính xác điểm cắt của Veo Lite trên dữ liệu của sản phẩm vẫn cần đo riêng.

**Bằng chứng đợt cập nhật:** 320 backend tests và 516 frontend tests đạt; coverage 10 module backend liên quan **92,85%**, helper nhóm/preview mới **100%**. Typecheck, build, scoped lint và mypy đạt trong phạm vi đã ghi rõ ở bàn giao kỹ thuật. Review độc lập không còn P1/P2. Các số 197 backend / 474 frontend phía trên là baseline lịch sử, không phải số mới.

Browser desktop 1280/1440px đã kiểm tra không overflow chữ/trang và card nhóm cân kích thước; luồng tách nhóm yêu cầu cập nhật kịch bản trước tạo hoạt động. Hai clip fixture dùng chung cho bốn cảnh hiển thị đúng gợi ý 0–3, 3–8, 0–4 và 4–8 giây; chọn cảnh 2 xem từ giây 3 và duyệt độc lập. Đã hoàn thành **duyệt 4/4 → ghép qua Celery/FFmpeg → lưu và xem output 720×1280, 384 frame** trong browser; metadata container khoảng 16,021 giây do audio AAC. Chưa gọi OpenAI/KIE có phí hoặc chạy seller usability trong lượt này; chưa xác nhận chất lượng hay mức tiết kiệm bằng output AI thật. Mobile không phải trọng tâm nghiệm thu của đợt cập nhật này.

## Cấu hình ảnh Sunburst max high

Theo quyết định chất lượng mới nhất, kế hoạch mới dùng **GPT Image 2.6 Sunburst trực tiếp từ OpenAI**, **quality max và complexity high**, thay cho profile Flare/low trong snapshot ban đầu. Giữ PNG 720×1280, một ảnh mỗi request và cách tham chiếu sản phẩm/bố cục đã chốt. Video tiếp tục Veo Lite và ưu tiên gộp cảnh liền nhau; trọng tâm trải nghiệm vẫn là desktop.

Quality kiểm soát chất lượng render; complexity kiểm soát mức lập kế hoạch của Images API trước khi tạo ảnh. Đây là hai tham số riêng; complexity không phải `reasoning_effort` của chat. Profile chọn max, mức quality cao nhất trong các mức được tài liệu GPT Image 2.6 hỗ trợ. [Tài liệu Sunburst](https://developers.openai.com/api/docs/models/gpt-image-2.6-sunburst), [quality cho GPT Image 2.6](https://developers.openai.com/api/docs/guides/image-generation#size-and-quality-options) và [complexity trong Images edit API](https://developers.openai.com/api/reference/resources/images/methods/edit) là nguồn đối chiếu. Cấu hình cao không thay thế việc seller kiểm tra sản phẩm và chuyển động trong output thật.

Model, quality và complexity được lưu trong plan/hash trước tạo; cache chỉ tái sử dụng khi cả cấu hình và đầu vào khớp. Ảnh Flare/low cũ không được coi là ảnh đạt profile Sunburst/max mới. Plan/job cũ giữ cấu hình đã đóng băng, không tự nâng model hoặc tạo thêm lượt ảnh vì đổi mặc định. Seller cần **cập nhật kịch bản** để lập plan mới khi muốn áp profile chất lượng mới.

Profile mới đã qua **357 backend tests** (323 unit và 34 integration), **522 frontend tests** trong 53 files; typecheck, build, scoped lint và mypy phạm vi sửa đạt. Coverage sáu module backend trong lượt unit-only là **85,75%**, gồm client ảnh 94% và image workflow 93%; phạm vi này khác lượt 10 module có integration ở phần trước. Review độc lập không còn P1/P2.

Browser đã compile plan fixture Sunburst/MAX/HIGH và hiển thị đúng model, “Chất lượng tối đa”, “Suy tính cao”; desktop 1280/1440px không overflow, card nhóm cân chiều cao. Số đo 320 backend / 516 frontend và nghiệm thu dựng fixture phía trên được giữ làm lịch sử. Chưa có generation OpenAI/KIE có phí để kết luận chất lượng hay chi phí thực tế của Sunburst/max/high trên dữ liệu seller.
