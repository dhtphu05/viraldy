# Khuyến nghị tối ưu trải nghiệm Smart Remake cho Viraldy

Ngày nghiên cứu: **25/11/2026**. Cập nhật luồng triển khai: **28/11/2026**.

Mục tiêu: giúp seller biến một video mẫu thành video cho sản phẩm của mình, sửa đúng cảnh chưa đạt và hoàn thành duyệt/xuất. Ưu tiên giảm số quyết định và thao tác cần thiết để có bản video được chấp nhận.

Tài liệu dựa trên [nghiên cứu Higgsfield và đối chiếu Viraldy](/Users/mac/Desktop/Viraldy/docs/product/higgsfield-remake-ux-research.md). Đây là khuyến nghị sản phẩm để thiết kế và kiểm chứng; mức cải thiện về thời gian, chi phí và tỷ lệ hoàn thành chưa được đo. Hiện trạng triển khai trong nghiên cứu là snapshot ngày 25/11/2026, cần kiểm tra lại trước khi giao việc kỹ thuật.

**Quyết định hiện hành 28/11/2026:** lượt mới dùng **Wan 3.0, 480P, 12 giây = hai call × 6 giây, `audio: true`**. UI hiển thị cấu hình này trước khi tạo. Toàn bộ cảnh nguồn vẫn được phân bổ theo thứ tự vào hai cửa sổ sáu giây; ảnh đầu/cuối, phiên bản, trim, tiến trình, QA và xuất file dùng đúng 144 frame mỗi clip và 288 frame toàn video trên clock 24 fps. Bản ghép giữ 480P và âm thanh. Plan/task 8 hoặc 16 giây đã lưu giữ nguyên thời lượng để xem và đối soát; không tự gửi thay thế. Hai clip live tám giây bên dưới là bằng chứng của lượt trước, chưa phải video 12 giây có tiếng.

**Ảnh sản phẩm nhiều góc:** giữ một ảnh chính và dùng toàn bộ ảnh bổ sung của cùng sản phẩm, tối đa 14 ảnh. Bộ ảnh được upload, kiểm bytes/hash và đưa vào một lượt Product Lock, một lượt edit GPT cho mỗi bookend, Inspector thủ công và sửa cảnh. Ảnh cắt lớp dùng để hiểu cấu tạo, không biến thành thân bị khuyết. Hash mọi ảnh được đóng băng trong Expectations/cache/anchor; ảnh phụ đổi cũng làm kết quả cũ stale. Payload một ảnh cũ giữ serialization/hash. Bản sao thu gọn chỉ phục vụ phân tích Gemini; ảnh gốc đã lưu và ảnh gửi GPT không bị thay. Giới hạn ảnh dựa trên [tối đa 16 ảnh của OpenAI edits](https://developers.openai.com/api/reference/resources/images/methods/edit), dành hai vị trí cho frame nguồn và nhân vật. Dự án cũ chỉ upload ảnh chính không thể tự khôi phục ảnh phụ chưa từng lưu; seller cần bổ sung đủ tư liệu và cập nhật kịch bản.

**Cập nhật triển khai 26/11/2026:** vùng **Bước tiếp theo**, receipt của bản sửa và sửa cảnh bằng `RepairIntent` đã được nối. Theo quyết định mới, Smart Remake bỏ tự lưu/khôi phục nháp trên thiết bị và tự mở dự án lần trước; lỗi nháp không được chặn thao tác. Video, ảnh và nội dung sửa được giữ trong phiên đang mở. Quyết định hiện tại bỏ form cấp hạn mức USD, số lượt và thời gian; vẫn giữ preflight, ledger, đối soát và xác nhận quyền khi cần. Quyền còn hiệu lực thì hành động chạy trực tiếp sau kiểm tra mới; chưa có quyền hợp lệ thì modal xác nhận thực hiện luôn hành động đã chọn. [Biên bản khôi phục/sửa cảnh trước đây](/Users/mac/Desktop/Viraldy/artifacts/smart-remake/result-recovery-20261126/verification.md) mô tả cả cơ chế nháp đã ngừng dùng. Đợt phân tích toàn nguồn và nhóm provider được kiểm thử offline riêng; không dùng số test hoặc fixture để khẳng định chất lượng generation thật hay cải thiện hành vi seller.

**Cập nhật nhân vật và hình thể 28/11/2026:** đối chiếu hai task KIE cho thấy ảnh đầu/cuối của clip đầu không nhất quán về tóc và áo, video có ba tay ở khoảng 6,5 giây; task thứ hai bị bộ lọc `prominent public figure` từ chối. Đầu vào dùng đúng mode ảnh đầu/cuối, nên lỗi nhất quán ảnh thuộc phần chuẩn bị conditioning; thông báo bộ lọc không đủ để xác định ảnh hay đoạn prompt nào là tác nhân. Policy nhân vật mới giữ một anchor chuẩn theo nguồn/sản phẩm, truyền cùng ảnh nhân vật cho các khung sau kể cả metadata cảnh thiếu hoặc ghi hands-only. Cache độc lập không được ưu tiên hơn anchor hiện hành cho lượt mới; giữ nguyên input và receipt của các lượt đã gửi. Prompt giữ tóc/trang phục, chỉ lấy vùng nhân vật từ anchor, giữ đúng bố cục nguồn và diễn giải ảnh cắt lớp thành sản phẩm hoàn chỉnh khi quay sử dụng bình thường.

Ảnh và video cùng nhận chỉ dẫn vai trò tay theo từng người/từng panel: một tay giữ, tay kia thao tác, nhả điểm chạm trước khi chuyển thao tác; các cú cắt nhanh đi vào hành động đang diễn ra. Không thêm lượt model, không khôi phục chốt AI kiểm tra ảnh, và vẫn giữ **8 giây một lượt KIE; 16 giây hai lượt**. Kiểm thử xác nhận input, cache và đối soát, chưa xác nhận chất lượng hình ảnh của một generation mới. Anchor còn dựa vào metadata `person` để chọn ảnh đầu tiên, không có kiểm tra khuôn mặt hay bảo đảm hết lỗi hình thể. Mâu thuẫn cơ chế nguồn/đích phải được xử lý trước khi đóng băng Expectations; không tự sửa riêng hành động trong payload KIE để làm lệch cùng snapshot. [Bằng chứng ca lỗi và phạm vi bản sửa](/Users/mac/Desktop/Viraldy/artifacts/smart-remake/presenter-consistency-20261128/verification.md).

**Chuyển video sang Wan 28/11/2026:** plan mới dùng KIE `wan/3-0-video`, **480P**, hai cửa sổ tám giây cho đầu ra 16 giây. Ảnh GPT tham chiếu vẫn là 720 × 1280; đổi model/resolution không đổi Product Lock, cảnh hoặc snapshot của lượt test này, nên dùng lại bốn ảnh và cùng anchor nhân vật. Payload Wan dùng `first_frame_url` và `last_frame_url`, không gửi trường riêng của Veo. Model và resolution được lưu trong plan; plan Wan cũ thiếu resolution vẫn giữ 720P, lịch sử Veo giữ contract cũ. Task đã gửi chỉ được đối soát đúng model đã lưu; không tự gửi window còn thiếu khi cấu hình đã đổi. Chất lượng video thật phải được đánh giá từ kết quả của từng task, không suy ra từ kiểm thử offline. Lượt live cùng ngày đã lưu thành công hai clip 480 × 854, mỗi clip đúng tám giây, 64 credits/clip; bản ghép xem thử đúng 16 giây. Hai request thử gửi `audio: false` nên file không có tiếng; Wan hỗ trợ `audio: true`. Quan sát các frame toàn clip và dày hơn ở ba giây cuối chưa thấy lặp lỗi ba tay; đây là kiểm tra mẫu, chưa phải chứng nhận mọi khung hình hoặc mọi cảnh nguồn đều đạt.

Hệ thống phân tích toàn bộ video đã tải lên, giữ các cảnh được phân tích và prompt tương ứng, rồi phân bổ nhịp vào đầu ra 12 giây của lượt mới. Số cảnh không bị chốt ở bốn. Lượt tạo video KIE ban đầu là **hai lượt × sáu giây**. Cảnh vượt qua mốc đầu ra sáu giây có thể được chia thành hai phần thực thi, vẫn là cùng một cảnh nguồn. Các module phân tích hành động, beat và chuyển cảnh tiếp tục cung cấp dữ liệu cho kịch bản, generation và QA.

Màn tạo video hiển thị thời lượng clip theo plan đã lưu, sáu giây cho lượt mới, với trạng thái server: chuẩn bị ảnh, gửi KIE, tạo clip và kiểm tra kỹ thuật clip. Theo quyết định mới, **bỏ bước AI kiểm tra ảnh trước KIE**: ảnh được giữ hợp lệ sẽ đi thẳng sang tạo video, không chờ báo cáo nội dung ảnh. Số lượt dự kiến tách khỏi số lượt KIE đã thực sự gửi; request chưa rõ receipt không bị hiển thị thành 0. Mọi ảnh tham chiếu đã giữ hợp lệ xuất hiện ngay và có thể phóng to; clip đã giữ đúng hash/phạm vi có trình phát riêng, không đợi clip còn lại. Trạng thái dừng hoặc cần đối soát không tiếp tục animation; nhãn “Bản nháp” ở hành trình được bỏ. [Bằng chứng tiến trình tạo video trước thay đổi](/Users/mac/Desktop/Viraldy/artifacts/smart-remake/generation-progress-20261126/verification.md).

Inspector thủ công và báo cáo lịch sử vẫn xem được; báo cáo ảnh cũ không được tự sửa thành PASS. Một lần kiểm tra ảnh tự động của cơ chế cũ không còn chặn generation mới, nhưng ledger và chi phí chưa rõ vẫn được giữ nguyên. Request tạo ảnh/video thật sự chưa rõ kết quả tiếp tục phải đối soát, không tự tạo lượt thay thế. Ngoại lệ vận hành trong lần thử này cần người dùng xác nhận rõ rủi ro, gắn đúng receipt và một key thay thế; không mở khóa cho phân tích hay kiểm tra AI khác. Một POST từ browser lưu tác vụ tạo video không đồng nghĩa đã gửi các lượt tạo tới KIE; ảnh tham chiếu có thể đang được chuẩn bị trước đó. [Bằng chứng bỏ kiểm tra ảnh và tiếp tục dự án](/Users/mac/Desktop/Viraldy/artifacts/smart-remake/direct-generation-20261126/verification.md).

**Projects** hiển thị cả dự án chưa có clip, đang tạo ảnh/video và đã thất bại, kèm tiến độ từng nhóm provider. Seller bấm **Mở dự án** để quay lại đúng ID; URL giữ `projectId` nên reload đọc trạng thái server mà không gửi lại generation. **Tạo video mới** mở intake rỗng bằng lựa chọn rõ ràng. Danh sách và mở dự án chỉ đọc dữ liệu đã lưu; không tự đối soát provider hoặc gọi AI. Không khôi phục nháp nội dung trên thiết bị.

Thử tiếp dự án thật ngày 26/11 đã sửa upload bằng cách stream nguyên bytes ảnh theo từng phần; ba ảnh tham chiếu đã upload thành công trong lượt live mới. KIE xác nhận giới hạn prompt 60.000 ký tự bằng lỗi runtime; nén các câu lặp có kiểm chứng khôi phục chính xác đưa hai payload xuống 58.333 và 50.881 ký tự, giữ toàn bộ cảnh và yêu cầu. Người dùng đã cho phép một lượt thay thế có rủi ro tính thêm phí; xác nhận được gắn đúng receipt và key mới, giữ nguyên mọi bằng chứng và chi phí chưa rõ của lượt cũ. Tuy nhiên KIE vẫn trả lỗi nội bộ `500` không kèm task ID ở nhóm đầu; nhóm thứ hai chưa gửi và hiện chưa giữ được clip nào. Không coi đây là live E2E hoàn tất, không tự chuyển provider/mode hoặc gửi lặp POST trả phí. [Bằng chứng upload, payload và lượt thay thế](/Users/mac/Desktop/Viraldy/artifacts/smart-remake/upload-streaming-20261126/verification.md).

Rà soát lại theo yêu cầu người dùng: mặc định đã trở về đúng API công bố `POST /api/v1/jobs/createTask`, wrapper `model/input`, trường snake_case và model Lite nằm trong `input.model`. Schema lấy mới và request HTTPX được kiểm chứng offline không cho thấy vi phạm contract. Playground dùng cổng login chuyển tiếp khác; thử đường native vẫn trả cùng `500`, nên đã bỏ native CREATE khỏi mặc định và dừng generation. Ảnh sản phẩm WEBP và hai ảnh PNG đều đọc lại được từ CDN với hash trùng bản gốc. Chưa đủ bằng chứng quy nguyên nhân `500` cho schema, prompt hoặc việc KIE đọc ảnh; không tiếp tục thử bằng cách đổi contract suy đoán. [Audit API KIE](/Users/mac/Desktop/Viraldy/artifacts/smart-remake/upload-streaming-20261126/kie-integration-audit.json).

Tiến trình phân tích được hiển thị ngay trên trang, với video mẫu có điều khiển và ảnh sản phẩm có thể phóng to. Server lưu các mốc xử lý thật trong operation; UI đọc lại bằng GET project và chỉ hiện cảnh/hành động hoặc nhận diện sản phẩm khi có kết quả hợp lệ. Đây là cập nhật theo mốc xử lý, không giả lập token hoặc phần trăm. Sau 45 giây có thao tác đọc lại trạng thái; một lượt đọc treo được ngắt sau 15 giây để UI có thể kiểm tra lại, không giới hạn thời gian chạy AI. Reload, mất kết nối hoặc POST chưa trả về được khôi phục bằng kết quả GET đã khớp project và request; không gửi lại AI. Danh sách tiến trình xem trước tối đa 12 cảnh, còn tổng cảnh và kịch bản đầy đủ được giữ nguyên. [Bằng chứng tiến trình phân tích](/Users/mac/Desktop/Viraldy/artifacts/smart-remake/analysis-progress-20261126/verification.md).

Trong luồng phân tích toàn bộ video hiện tại, một lượt Gemini đọc nhanh chạy song song để hiện **Tóm tắt nhanh từ video** và tối đa ba nhận xét nhìn thấy được, bằng tiếng Việt. UI ghi rõ đây là nhận xét sơ bộ; dữ liệu này chỉ phục vụ màn chờ. Kịch bản, Product Lock, hành động, beat, chuyển cảnh và GenerationExpectations vẫn dùng phân tích chi tiết. Lượt đọc nhanh nhận proxy toàn nguồn 640 px/2 fps kèm audio đã giảm dung lượng; nếu chỉ chuẩn bị được frame mẫu thì không nhận diện audio từ các ảnh đó. Lượt đọc nhanh có một request riêng, tối đa 1.280 output tokens và thời gian chờ HTTP 30 giây; không cam kết thời gian provider trả kết quả. Lỗi, timeout hoặc dữ liệu sai định dạng không chặn phân tích chính; trạng thái và chi phí chưa rõ vẫn được giữ trong ledger. GET, reload và kiểm tra trạng thái không gọi lại lượt đọc nhanh. Số lượt KIE ban đầu vẫn là một cho 8 giây, hai cho 16 giây. [Bằng chứng tóm tắt trong lúc chờ](/Users/mac/Desktop/Viraldy/artifacts/smart-remake/quick-summary-20261126/verification.md).

Phần **Âm thanh trong video mẫu** bổ sung lời thoại nghe được, nhận diện nhạc nền và nhịp âm thanh vào các response Gemini hiện có, không mở thêm lượt gọi model. Nhận diện sơ bộ xuất hiện khi lượt đọc nhanh trả về; kết quả phân tích đầy đủ được ưu tiên và giữ lại trên màn duyệt kịch bản sau reload. Transcript giữ ngôn ngữ nguồn, chỉ là phần lời nghe được, không có timestamp/BPM chính xác; thiếu dữ liệu hoặc chưa nghe rõ được ghi đúng trạng thái. Dữ liệu này tách khỏi `audioPlan` hướng dẫn sinh video, không thay prompt generation hoặc hash GenerationExpectations và không tự phân tích lại dự án cũ.

Khi AI đã trả mô tả hành động nhưng mốc cảnh còn cần đối chiếu, màn chờ hiện **AI đã đọc được** dưới dạng nhận định sơ bộ, không gắn timestamp hoặc coi là cảnh đã xác nhận. Lượt đọc nhanh không trả kết quả được báo đúng trạng thái thay vì quay chờ giả. Tác vụ thất bại dừng đồng hồ/animation; nhận định đã lưu còn hiện trong **Từ lượt phân tích trước** khi quay lại tư liệu. Projection có thể đọc checkpoint của lượt cũ mà không gọi AI hoặc sửa DB. [Bằng chứng khắc phục màn chờ](/Users/mac/Desktop/Viraldy/artifacts/smart-remake/analysis-responsiveness-20261126/verification.md).

Khi cập nhật phân tích thất bại, trang phải phân biệt lượt vừa lỗi với kịch bản đã lưu: không mở kịch bản cũ như kết quả mới sau reload. Hành động chính dựa trên trạng thái do server xác minh. Nếu có bằng chứng Gemini đã trả response đầy đủ nhưng không giữ được kết quả hợp lệ, seller có thể chủ động **Phân tích lại** trong cùng dự án; lượt cũ và khoản phí chưa rõ vẫn được giữ. Nếu chưa biết request đã kết thúc hay chưa, chỉ **Kiểm tra trạng thái**, không tự gửi lại AI. **Xem kịch bản đã lưu** là lựa chọn riêng; mở lại trang hoặc đọc trạng thái không phát sinh generation. [Bằng chứng phục hồi phân tích](/Users/mac/Desktop/Viraldy/artifacts/smart-remake/analysis-recovery-20261126/verification.md).

Màn **Xem & ghép** phân biệt chưa tạo được clip với sửa một clip đã có. Nếu yêu cầu ảnh đầu bị provider từ chối có bằng chứng, trước khi gửi KIE, server trả trạng thái khôi phục để UI hiện một hành động **Tiếp tục tạo video** và lựa chọn **Xem kịch bản** đã lưu. Không hiện player đen, trim hay form sửa cảnh khi chưa có clip; không yêu cầu phân tích lại kịch bản còn hợp lệ. Lượt thử lại phải do người dùng bấm, dùng key mới khi đã xác nhận đúng request cũ thất bại, giữ nguyên kịch bản/render plan/GenerationExpectations nếu chưa chỉnh sửa. Request chưa rõ kết quả chỉ được đối soát; phí chưa rõ không được đổi thành 0 USD để bỏ chốt. Lỗi 429 thiếu subcode giữ thông báo trung lập; quota/chi tiêu yêu cầu kiểm tra hạn mức, chỉ `credit_balance_exhausted` mới đề nghị thêm credit. Số cảnh nguồn và số đoạn dựng được ghi riêng khi một cảnh đi qua ranh giới tám giây. [Bằng chứng khôi phục generation](/Users/mac/Desktop/Viraldy/artifacts/smart-remake/generation-recovery-20261126/verification.md).

**1. Định hướng trải nghiệm**

Giữ luồng **Tư liệu → Kịch bản → Xem & ghép**. Mỗi bước giúp seller trả lời một câu hỏi:

| Bước | Câu hỏi của seller | Kết quả cần có |
| --- | --- | --- |
| Tư liệu | Tôi muốn học từ video nào và bán sản phẩm nào? | Video mẫu, sản phẩm, thời lượng đầu ra và yêu cầu đủ rõ. |
| Kịch bản | Video mới sẽ diễn ra thế nào? | Kế hoạch từng cảnh dễ đọc, biết phần học từ mẫu và phần dùng sản phẩm của mình. |
| Xem & ghép | Tôi cần sửa gì để dùng được video này? | Preview rõ, sửa đúng cảnh, so sánh phiên bản và hoàn thành duyệt/xuất. |

Bài học từ Higgsfield là bắt đầu từ ví dụ, diễn đạt thay đổi bằng ngôn ngữ thường và giữ ngữ cảnh khi chỉnh sửa. Ad Multiplier dùng video mẫu và thay đổi mong muốn làm đường vào; Editing Room đặt đoạn được chọn, lịch sử và giá tạo lại trong cùng workspace. [Ad Multiplier](https://higgsfield.ai/blog/ad-multiplier-ads-studio), [Editing Room](https://higgsfield.ai/blog/higgsfield-editing-room).

**2. Những năng lực hiện có cần tận dụng**

Theo snapshot nghiên cứu, Viraldy đã có đường vào từ Creative Library, prompt tự động thu gọn, tóm tắt giữ/thay, sửa từng cảnh, candidate, so sánh, lịch sử và kiểm tra trước xuất. Một số chi tiết cấu hình, quyền/ngân sách và rubric đã được đưa vào phần thu gọn.

Các khuyến nghị dưới đây tập trung hoàn thiện hành trình quanh những năng lực đó. Khi triển khai, đối chiếu lại giao diện và contract hiện tại để tránh xây trùng phần đã hoàn thành.

**3. Thứ tự ưu tiên**

| Thứ tự | Khuyến nghị | Kết quả mong muốn | Phạm vi phụ thuộc |
| --- | --- | --- | --- |
| 1 | Gọn bước Tư liệu | Seller bắt đầu bằng video mẫu và sản phẩm, hiểu mặc định của hệ thống. | Tổ chức UI, copy và điều kiện nhập liệu. |
| 2 | Làm rõ phạm vi và chi phí | Seller biết hành động sắp chạy và phần phí đã biết/chưa rõ. | Preflight, dữ liệu usage/receipt và ledger ở backend. |
| 3 | Thống nhất tiến trình Xem & ghép | Seller biết việc cần làm tiếp và lý do chưa tải được. | State flow của ghép, kiểm tra, duyệt và xuất. |
| 4 | Hoàn thiện sửa cảnh theo ý định | Seller sửa chi tiết sai mà không cần mở prompt. | Yêu cầu có cấu trúc, reference theo cảnh và candidate. |
| 5 | Tiếp tục dự án và tái dùng tư liệu | Lần làm tiếp theo không bắt đầu lại từ upload. | Danh sách project, lưu draft và phiên bản asset. |
| 6 | Thử nghiệm preview ghép tự chuẩn bị | Giảm thao tác chọn đoạn lặp lại. | Contract riêng cho preview chưa duyệt và kiểm tra media. |
| 7 | Biến thể có mục tiêu, sau đó batch | Tạo thêm phương án từ một bản đã phù hợp. | Chất lượng, chi phí và capability được xác thực. |

Đây là thứ tự ưu tiên định tính, chưa phải ước lượng công sức hoặc cam kết tiến độ.

**4. Gọn bước Tư liệu**

Màn hình đầu ưu tiên ba thành phần: **video mẫu**, **sản phẩm của tôi**, **yêu cầu thêm nếu có**. Video và ảnh sản phẩm cần preview được ngay. Hỗ trợ đường vào từ Creative Library và upload trong cùng luồng.

Cho biết mặc định trước khi người dùng tiếp tục: hệ thống dùng cách mở đầu, trình bày và nhịp của mẫu làm định hướng, rồi tạo nội dung cho sản phẩm đã chọn. Không trình bày việc tái tạo như bảo đảm giữ nguyên chuyển động hoặc mọi chi tiết hình ảnh.

Các yêu cầu giữ/thay, điều cấm xuất hiện và claims đặt trong mục bổ sung. Chỉ mở phần nhân vật khi người dùng cần dùng nhân vật. Quyền sử dụng gắn với tư liệu cụ thể; xác nhận cần thiết vẫn hoàn thành trước khi gửi tư liệu cho AI. Cho biết bước tạo kịch bản phân tích bằng AI và chưa tạo video.

CTA dùng **Tạo kịch bản** hoặc **Cập nhật kịch bản** để thể hiện đây là hành động AI. Có video và ảnh hợp lệ thì bấm tiếp tục được, không có điều kiện nhập ngân sách. Quyền chưa hợp lệ thì mở modal chưa tích sẵn checkbox; xác nhận gọi thẳng hành động. Quyền còn hiệu lực thì chạy trực tiếp sau preflight mới. Thiếu tư liệu thì báo lỗi cạnh trường và đưa focus tới đó. Tác vụ đang chạy hoặc chưa rõ kết quả đưa tới tiến trình/đối soát, không gửi lượt mới. Khi chờ phân tích, dùng animation và trạng thái tác vụ, không dựng phần trăm hoàn tất giả.

Tiêu chí kiểm chứng: seller tự bắt đầu được, hiểu phần nào hệ thống sẽ học từ mẫu và không cần giải thích model hoặc thuật ngữ keep/replace.

**5. Làm rõ phạm vi và chi phí, bỏ cấp hạn mức**

Khuyến nghị cũ yêu cầu seller chọn trần ngân sách, số lượt và thời gian đã được thay thế theo quyết định ngày 26/11. Luồng hiện tại không có form cấp hạn mức và không chặn chỉ vì các trường đó rỗng. Preflight vẫn đọc plan, revision và ledger để mô tả đúng phạm vi, số lượt từng loại và tác vụ cần đối soát; không tự gọi provider.

Ledger vẫn ghi phí thực đã biết, reservation và receipt. Phí hoặc ước tính chưa rõ phải hiển thị là chưa xác định, không đổi thành 0 USD. Luồng unlimited không cần server khai báo giá trần cho từng model để tiếp tục; policy hữu hạn của API cũ được giữ tương thích, còn app chuyển sang policy unlimited trước hành động mới. Timeout kỹ thuật được tính từ workload trên server và đóng băng cùng job; seller không phải cấp thời gian chạy.

Lượt Wan mới tạo hai clip sáu giây cho đầu ra 12 giây, độc lập số cảnh nguồn. Plan lịch sử 8/16 giây giữ số lượt và thời lượng đã đóng băng. Preflight dự phòng ảnh tham chiếu và video theo plan, không dự phòng lượt AI kiểm tra ảnh tự động; kiểm tra thủ công là hành động riêng. Prompt theo contract provider: [schema Wan 3.0 đã đối chiếu ngày 28/11](https://api.kie.ai/api/v1/models/wan/3-0-video/schema) quy định tối đa 20.000 ký tự; [schema Veo 3.1](https://docs.kie.ai/veo3-api/generate-veo-3-video) chưa công bố `maxLength`, nhưng API runtime đã xác nhận giới hạn 60.000 ký tự cho contract Veo cũ. Kiểm tra payload cuối sau khi thêm yêu cầu đã lưu; chỉ nén nội dung lặp khi khôi phục được chính xác. Không cắt bỏ cảnh hoặc tăng lượt KIE để né lỗi prompt. Lỗi provider phải được hiển thị đúng để người dùng quyết định bước tiếp theo.

Tiêu chí kiểm chứng: seller tiếp tục được mà không tìm ô ngân sách, hiểu đang phân tích hay tạo video và phân biệt được phí đã biết với phí chưa rõ. Một receipt chưa rõ kết quả chỉ được đối soát; không tự tạo lượt trả phí thay thế.

**6. Thống nhất màn Xem & ghép**

Luồng hiện hành ưu tiên xem toàn bộ video: khi đủ hai clip Wan sáu giây đã giữ lại và đạt kiểm tra kỹ thuật, worker tự chuyển sang ghép preview miễn phí bằng các đoạn gợi ý đã gắn đúng version/range. Seller không phải xác nhận từng đoạn trước khi xem. Số đoạn theo phân tích nguồn; trường hợp 25 đoạn không tạo thêm 25 thao tác bắt buộc.

Trên desktop, đặt preview lớn và hành động tiếp theo lên trước. Danh sách cảnh, trim, so sánh và lịch sử nằm trong **Nâng cao**, chỉ mở khi seller muốn đối chiếu hoặc sửa vấn đề. Luồng chính là **xem cả video → sửa nếu cần → kiểm tra đúng bản → duyệt → tải**. Preview luôn là bản chưa duyệt; tạo preview không tích `reviewed` cho từng đoạn, không tạo approval và không tự xuất file.

| Trạng thái | Thông tin cần hiện | Hành động chính đề xuất |
| --- | --- | --- |
| Đã đủ hai clip hợp lệ | Đang tự ghép preview miễn phí | Xem tiến trình |
| Đã có preview | Xem toàn bộ 12 giây có âm thanh; chưa duyệt nội dung | Xem video |
| Preview cần kiểm tra | Chưa có báo cáo đúng bản đang xem | Kiểm tra bản ghép |
| Có vấn đề | Vấn đề, cảnh liên quan và cách xử lý | Xem và sửa vấn đề |
| Sẵn sàng duyệt | Đúng phiên bản và báo cáo hiện tại | Duyệt nội dung bản này |
| Đã duyệt | Bản có thể tải và trạng thái lưu | Tải video có nhãn AI |

Lỗi ghép cục bộ có trạng thái và thao tác thử lại riêng, không biến lượt KIE đã hoàn tất thành generation thất bại. Sau reload hoặc polling, không tạo job preview mới hay gửi lại AI; worker có thể tiếp tục đúng receipt/job đã lưu, hoặc seller chủ động yêu cầu ghép lại miễn phí. Đổi trim, active version hoặc yêu cầu làm preview/báo cáo/approval cũ hết hiệu lực theo snapshot hiện tại. Dự án 12 giây hoàn tất trước khi có cơ chế này có thể được ghép preview từ clip đã giữ lại bằng thao tác miễn phí, không tạo lại video.

Giữ chi tiết model, job, rubric và ledger trong vùng thu gọn phù hợp. Các chốt active version, hash media, phạm vi thực, technical check, GenerationExpectations, quyền sử dụng, QA và duyệt nội dung toàn bản vẫn được thực thi. Những thông tin ảnh hưởng quyết định như chất lượng, giá, lỗi và khả năng tiếp tục sau khi đóng trang cần xuất hiện đúng lúc.

Tiêu chí kiểm chứng: seller tìm được hành động tiếp theo, phân biệt chọn đoạn với duyệt nội dung và hiểu vì sao video chưa sẵn sàng để tải.

**7. Sửa clip bằng yêu cầu thông thường**

Tận dụng ô yêu cầu sửa ngắn và prompt thu gọn đã có. Bổ sung cách biểu đạt có cấu trúc:

- Vấn đề cần sửa: sai chi tiết sản phẩm, thiếu hành động hoặc cần phương án sáng tạo khác.
- Kết quả mong muốn: một câu dễ hiểu, có ảnh tham chiếu đúng cảnh khi cần.
- Phạm vi: chọn **Clip 1 · 0–6 giây** hoặc **Clip 2 · 6–12 giây**, rồi mô tả vấn đề trong clip đó.
- Phần giữ lại: clip còn lại, toàn bộ cảnh logic và thời điểm đã phân bổ, reference sản phẩm và yêu cầu đã chốt.
- Chi phí và trạng thái: bản đang dùng, candidate mới, đang xử lý hoặc cần xem lại.

Ví dụ: “Cảnh 2 đang sai màu nắp. Dùng nắp xanh như ảnh này, giữ ý định quay cận sản phẩm.” Hệ thống chuyển yêu cầu thành thay đổi có kiểm tra mâu thuẫn với ràng buộc sản phẩm; không chỉ coi việc nối câu vào prompt là đã giải quyết đầy đủ ý định.

Candidate cần được so với clip đang dùng và reference, sau đó người dùng chọn áp dụng hoặc giữ bản cũ. Sửa một lỗi ngắn vẫn tạo lại toàn bộ clip sáu giây đã chọn, nên cần xem lại cả clip; clip còn lại được giữ nguyên. Danh sách cảnh, trim và prompt chỉ là phần nâng cao, không tạo thêm 25 quyết định bắt buộc.

Phạm vi triển khai mới: request có `repairScope: "provider_group"`, còn `RepairIntent` v1 giữ nguyên. Server tự xác định nhóm và đóng băng tất cả phiên bản/đoạn đang dùng. Preflight tính **tối đa một lượt Gemini chuẩn hóa cả nhóm, hai ảnh đầu/cuối GPT và một lượt Wan sáu giây có âm thanh**. Không tạo một lượt video cho từng cảnh logic. Phần không sửa trong nhóm giữ ý định đã được chấp nhận; hành động của clip lân cận lấy từ snapshot phiên bản đang dùng. Mâu thuẫn sản phẩm, thiếu căn cứ hoặc phạm vi thay đổi thì dừng trước tạo ảnh/video và nêu lý do.

Các candidate của nhóm dùng chung một media đã kiểm hash và giữ đúng offset từng cảnh. Receipt xác nhận đủ mọi thành viên, task và media của đúng yêu cầu; không đoán từ phiên bản mới nhất. **Dùng bản mới** đổi toàn bộ nhóm trong một lần kiểm revision/base/hash/range, rồi tự lên lịch ghép lại preview 12 giây bằng FFmpeg, không gọi AI thêm. Preview lỗi chỉ được thử lại việc ghép miễn phí; không làm tác vụ tạo video đã hoàn tất chạy lại. Polling/restore chỉ đọc trạng thái, không gửi sửa mới hoặc tự chấp nhận candidate. Preview vẫn cần QA và duyệt nội dung toàn bản trước khi tải.

Request cũ không có scope giữ nguyên serialization/hash và cách sửa từng cảnh; plan/task 8/16 giây đã lưu không tự chuyển sang luồng mới. Đợt sửa theo nhóm được kiểm thử offline; chưa chạy generation trả phí để xác nhận chất lượng clip sửa thật.

Tiêu chí kiểm chứng: seller chọn một trong hai clip và mô tả lỗi mà không mở prompt; candidate không tự thay bản đang dùng; áp dụng candidate đổi đủ nhóm, giữ nguyên clip còn lại và tự cập nhật bản xem trước.

**8. Tiếp tục dự án và tái dùng tư liệu**

Theo yêu cầu mới ngày 26/11/2026, ngừng tự lưu và khôi phục nháp IndexedDB, tự mở lại kịch bản đã kết thúc từ localStorage và nhập nháp sửa cảnh cũ trong luồng Smart Remake. Không hiển thị trạng thái lưu nháp hoặc khóa nút vì database trên thiết bị đang tải, thiếu Blob, quota hay baseline xung đột. Dữ liệu nháp cũ không bị tự xóa. Tư liệu và chỉnh sửa trong phiên đang mở vẫn giữ nguyên khi phân tích thất bại. Reload URL có `projectId` mở đúng dự án đã chọn từ server; URL tạo mới không tự mở kịch bản cũ. Thông tin nhận diện tác vụ đã gửi chỉ dùng để đọc trạng thái lượt còn chạy hoặc thật sự chưa rõ kết quả; không tự nạp nháp hay gửi lại AI.

Danh sách **Projects** và tiếp tục dự án bằng lựa chọn rõ ràng đã được nối. Danh sách lấy cả dự án chưa có video bằng tùy chọn chỉ đọc `includeUnfinished=true`, hiển thị số clip dự kiến/đã gửi/hoàn tất theo cửa sổ provider đã lưu: sáu giây cho lượt Wan 12 giây mới, tám giây cho lịch sử tương ứng. Dự án chưa có clip không mở player rỗng; trạng thái đang chạy được cập nhật qua GET. Picker sản phẩm/nhân vật vẫn là hướng mở rộng sau. Submission marker và receipt của yêu cầu sửa đã gửi tiếp tục dùng để chống submit lặp; đây là trạng thái tác vụ, không phải autosave nháp nội dung.

Phân biệt kho trong trình duyệt với tư liệu đã lưu theo workspace. Khi thay ảnh hoặc variant sản phẩm, giữ phiên bản tham chiếu của project cũ để tránh làm thay đổi ngầm ý nghĩa của các bản đã tạo.

Tiêu chí kiểm chứng hiện tại: không tự đọc/ghi nháp hoặc tự mở kịch bản cũ đã kết thúc; lỗi lưu trữ thiết bị không khóa nút tạo kịch bản; phân tích thất bại giữ tư liệu trong phiên; đổi tài khoản/workspace không làm lẫn dữ liệu và đọc trạng thái tác vụ đã gửi không gọi lại AI.

**9. Preview đã triển khai và hướng mở rộng tiếp theo**

**Preview ghép tự chuẩn bị đã nối backend:** dùng assembly hiện có với `reviewMode: "whole_video"`, chỉ bỏ yêu cầu xác nhận trim từng đoạn. Marker preview và trạng thái generation hoàn tất được commit cùng nhau; job compose dùng khóa xác định từ render operation và snapshot. GET/poll không enqueue preview mới. Lỗi local preview không tạo lượt trả phí thay thế. Contract cũ không thêm field mặc định vào serialization/hash. Kiểm thử offline đã bao phủ replay, lỗi local/DB, snapshot stale và việc không tự cấp approval; chất lượng bản live cần được xem riêng trên đúng đầu ra.

**Biến thể có mục tiêu:** bắt đầu từ một bản seller chấp nhận rồi chọn mục tiêu như đổi hook, CTA hoặc sản phẩm. Chỉ mở lựa chọn đã được backend hỗ trợ và có cách kiểm chứng. Mỗi biến thể giữ quan hệ với bản gốc, phạm vi thay đổi và chi phí rõ ràng. Batch triển khai sau khi chất lượng và chi phí của vòng tạo đơn đã được đo.

**10. Cách kiểm chứng và quyết định triển khai**

Khởi đầu bằng ba ưu tiên đầu. Với ưu tiên có phụ thuộc giá hoặc backend chưa sẵn sàng, thiết kế trạng thái trung thực trước khi nối hành động thực.

Đề xuất thử định tính với **5–8 seller** đúng nhóm sử dụng; đây là cỡ mẫu discovery, không phải cơ sở kết luận uplift thống kê. Mỗi người thực hiện ba task: tạo kịch bản từ mẫu, sửa một cảnh sai sản phẩm, mở lại dự án và hoàn tất tải video đã duyệt.

| Chỉ số | Cách dùng |
| --- | --- |
| Thời gian thao tác tới bản được chấp nhận | Tách thời gian seller thao tác khỏi thời gian chờ AI. |
| Tỷ lệ hoàn thành và thời gian chờ thực tế | Tính cả phiên bỏ cuộc hoặc thất bại; không dùng thời gian cấp phép đã bỏ. |
| Tổng chi phí tới video được chấp nhận | Bao gồm tạo, kiểm tra, sửa và dựng theo chi phí thực tế. |
| Số lần cần hướng dẫn | Ghi thao tác hoặc thuật ngữ gây vướng. |
| Mức hiểu đúng phạm vi sửa | Kiểm tra seller biết cảnh nào thay và phần nào cần xem lại. |
| Candidate được áp dụng và rollback | Đánh giá vòng sửa có giải quyết vấn đề mong muốn. |
| Lỗi còn sót và khả năng phục hồi | Kiểm tra sai sản phẩm/timing, mất draft và generation trùng. |

Thiết lập baseline trước khi so sánh. Chốt mục tiêu sau khi có dữ liệu ban đầu. Mở rộng khi seller hiểu luồng, tự hoàn thành công việc tốt hơn và chất lượng/chi phí vẫn chấp nhận được. Nếu ma sát chủ yếu nằm ở chất lượng output, ưu tiên reference, ý định cảnh và vòng sửa trước khi thêm công cụ.
