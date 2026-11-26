import {
    renderSmartRemake,
    type SmartRemakeCompileResult,
    type SmartRemakeHealth,
    type SmartRemakeProject,
    type SmartRemakeRenderResult,
    type SmartRemakeGenerationRecovery,
    type SmartRemakeProviderError,
} from "@/shared/api/smart-remake";
import { ApiError } from "@/shared/api/errors";
import { isDemoVideoAvailable } from "@/shared/lib/optional-demo-media";

export type SmartRemakeRenderState = Pick<SmartRemakeRenderResult, "finalVideoUrl" | "status"> &
    Partial<
        Pick<SmartRemakeRenderResult, "repairProject" | "warnings" | "targetDuration" | "provider">
    > & {
        isDemo?: boolean;
    };

const DEMO_OUTPUT_VIDEO = "/smart-remake/02_After.mp4";

export function getRemakeErrorMessage(cause: unknown): string {
    if (!(cause instanceof ApiError))
        return cause instanceof Error ? cause.message : "Chưa hoàn tất. Bạn thử lại nhé.";
    switch (cause.code) {
        case "SMART_REMAKE_RIGHTS_ATTESTATION_REQUIRED":
        case "SMART_REMAKE_RIGHTS_POLICY_OUTDATED":
            return "Đọc chính sách sử dụng tư liệu và xác nhận lại quyền cho bộ tư liệu hiện tại trước khi tiếp tục.";
        case "SMART_REMAKE_REVISION_CONFLICT":
        case "SMART_REMAKE_PROJECT_CHANGED":
            return "Dự án đã được cập nhật ở tab khác. Đã tải bản mới nhất; kiểm tra lại lựa chọn trước khi lưu nhé.";
        case "SMART_REMAKE_FIXTURE_MODE":
            return "Chế độ kiểm thử chỉ kiểm tra kịch bản, chưa tạo clip AI. Kết nối KIE ở môi trường chạy thật để tiếp tục nhé.";
        case "SMART_REMAKE_OPERATION_BUSY":
            return "Dự án đang xử lý yêu cầu trước. Chờ hoàn tất hoặc bấm Kiểm tra lại trước khi tiếp tục nhé.";
        case "SMART_REMAKE_MODEL_ATTEMPT_UNCERTAIN":
            return cause.details?.causeCode === "SMART_REMAKE_GEMINI_OUTPUT_TRUNCATED"
                ? "Kết quả AI bị cắt trước khi hoàn tất. Tư liệu và các nhận định đã có vẫn được giữ; kiểm tra trạng thái lượt vừa gửi trước khi tạo yêu cầu mới."
                : "Chưa nhận được kết quả AI hợp lệ để tiếp tục. Tư liệu và các nhận định đã có vẫn được giữ; kiểm tra trạng thái lượt vừa gửi trước khi tạo yêu cầu mới.";
        case "SMART_REMAKE_GEMINI_OUTPUT_TRUNCATED":
            return "Kết quả AI bị cắt trước khi hoàn tất. Tư liệu vẫn được giữ; kiểm tra trạng thái lượt vừa gửi trước khi phân tích lại.";
        case "SMART_REMAKE_ATTEMPT_RECONCILIATION_REQUIRED":
            return "Cần kiểm tra trạng thái lượt AI trước. Các dữ liệu đã có vẫn được giữ; hệ thống chưa gửi lượt mới để tránh gọi trùng.";
        case "SMART_REMAKE_BASE_VERSION_REQUIRED":
            return "Cảnh này chưa có clip để sửa. Tiếp tục tạo video trước.";
        case "SMART_REMAKE_BASE_VERSION_CONFLICT":
        case "SMART_REMAKE_CANDIDATE_STALE":
        case "SMART_REMAKE_IDEMPOTENCY_CONFLICT":
            return "Phiên bản đã thay đổi. Kiểm tra lại dự án và chọn phiên bản mới nhất trước khi tiếp tục nhé.";
        case "SMART_REMAKE_RETENTION_UNAVAILABLE":
            return "Kho lưu video đang chưa sẵn sàng. Tư liệu của bạn vẫn còn; nhờ quản trị viên kiểm tra lưu trữ rồi thử lại nhé.";
        case "SMART_REMAKE_SOURCE_RANGE_INVALID":
            return "Đoạn đã chọn vượt độ dài video mẫu. Dời điểm bắt đầu hoặc chọn thời lượng phù hợp nhé.";
        case "SMART_REMAKE_SOURCE_REUPLOAD_REQUIRED":
            return "Tư liệu cũ chưa được lưu đầy đủ. Thêm lại video mẫu và ảnh sản phẩm để cập nhật kịch bản nhé.";
        case "SMART_REMAKE_SOURCE_ANALYSIS_INCOMPLETE":
            return "Chưa đọc đủ các cảnh trong đoạn mẫu. Bạn thử phân tích lại hoặc chọn đoạn khác nhé.";
        case "SMART_REMAKE_EXPECTATIONS_REQUIRED":
        case "SMART_REMAKE_EXPECTATIONS_INVALID":
            return "Cập nhật kịch bản để đồng bộ sản phẩm, tư liệu và yêu cầu cảnh trước khi tạo video nhé.";
        case "SMART_REMAKE_PROVIDER_PLAN_UPDATE_REQUIRED":
            return "Cập nhật kịch bản để tạo đúng 1 clip cho đầu ra 8 giây hoặc 2 clip cho 16 giây. Các clip và tác vụ đã gửi vẫn được giữ.";
        case "SMART_REMAKE_ASSEMBLY_EXPECTATIONS_REQUIRED":
            return "Ghép lại bản xem trước để kiểm tra theo yêu cầu hiện tại. Các clip đã có vẫn được giữ.";
        case "SMART_REMAKE_PRODUCT_ANALYSIS_INCOMPLETE":
            return "Chưa nhận diện đủ chi tiết từ ảnh sản phẩm. Chọn ảnh rõ hơn rồi cập nhật kịch bản nhé.";
        case "SMART_REMAKE_SOURCE_UNSUPPORTED":
        case "SMART_REMAKE_SOURCE_ANALYSIS_UNSUPPORTED":
            return "Cách thể hiện của video mẫu chưa được hỗ trợ đầy đủ. Chọn đoạn khác hoặc video mẫu khác nhé.";
        case "COMPILER_OUTPUT_INVALID":
        case "SMART_REMAKE_COMPILER_OUTPUT_INVALID":
            return "Thông tin sản phẩm và yêu cầu cảnh chưa nhất quán. Cập nhật kịch bản để phân tích lại tư liệu nhé.";
        case "SMART_REMAKE_CONDITIONING_BLOCKED":
            return "Ảnh cảnh chưa khớp sản phẩm hoặc trạng thái mở đầu. Kiểm tra tư liệu và cập nhật kịch bản trước khi tạo tiếp nhé.";
        case "SMART_REMAKE_SOURCE_INVALID":
        case "SMART_REMAKE_SOURCE_FRAME_FAILED":
        case "SMART_REMAKE_SOURCE_FRAME_INVALID":
            return "Chưa đọc được video mẫu. Thử video MP4, MOV hoặc WebM phát được đầy đủ nhé.";
        case "SMART_REMAKE_TIMELINE_SCENE_TOO_LONG":
            return "Có cảnh dài hơn 8 giây. Thêm mốc cắt ở bên dưới rồi cập nhật kịch bản nhé.";
        case "SMART_REMAKE_TIMELINE_SCENE_LIMIT":
            return "Kịch bản cũ chưa hỗ trợ đủ cảnh. Cập nhật kịch bản để phân tích toàn bộ video mẫu nhé.";
        case "SMART_REMAKE_TIMELINE_DENSITY_UNSUPPORTED":
        case "SMART_REMAKE_OUTPUT_DENSITY_UNSUPPORTED":
            return "Không đủ khung hình trong thời lượng đã chọn để giữ đủ các cảnh. Chọn 16 giây hoặc xem lại các mốc cắt nhé.";
        case "SMART_REMAKE_PROVIDER_PROMPT_TOO_LARGE":
            return "Chưa đóng gói được đầy đủ hướng dẫn cho KIE. Rút gọn yêu cầu bổ sung rồi cập nhật kịch bản nhé.";
        case "SMART_REMAKE_TIMELINE_CUTS_INVALID":
            return "Mốc cắt cần tăng dần và phủ đủ đoạn mẫu. Chỉnh lại các mốc rồi thử nhé.";
        case "SMART_REMAKE_TIMELINE_PROVIDER_REQUIRED":
            return "Timeline cần kết nối KIE Veo để tạo các clip theo nhóm cảnh. Nhờ quản trị viên kiểm tra nhé.";
        case "SMART_REMAKE_RENDER_GROUPS_INVALID":
            return "Nhóm cảnh chưa hợp lệ. Mỗi nhóm cần gồm các cảnh liền nhau và tối đa 8 giây; cập nhật lại kịch bản nhé.";
        case "OPENAI_IMAGE_NOT_CONFIGURED":
        case "OPENAI_IMAGES_NOT_CONFIGURED":
        case "OPENAI_IMAGE_AUTH_FAILED":
        case "OPENAI_IMAGE_PERMISSION_DENIED":
            return "Dịch vụ tạo ảnh OpenAI chưa được kết nối. Nhờ quản trị viên kiểm tra trước khi tạo video nhé.";
        case "OPENAI_IMAGE_NOT_LIVE":
            return "Đang ở chế độ kiểm thử nên chưa tạo ảnh thật. Bạn có thể xem và chỉnh kịch bản trước nhé.";
        case "OPENAI_IMAGE_RATE_LIMITED":
            return ["rate_limit_exceeded", "slow_down"].includes(
                String(cause.details?.providerErrorCode ?? ""),
            )
                ? "OpenAI đang giới hạn tần suất tạo ảnh. Chờ một lúc rồi thử lại."
                : "OpenAI từ chối tạo ảnh (429). Kiểm tra credit/hạn mức trước khi thử lại.";
        case "OPENAI_IMAGE_CREDITS_EXHAUSTED":
            if (cause.details?.providerErrorCode === "credit_balance_exhausted")
                return "OpenAI báo đã hết số dư credit. Nạp thêm credit cho tài khoản OpenAI trước khi thử lại.";
            return [
                "project_spend_limit_exceeded",
                "organization_spend_limit_exceeded",
                "organization_usage_limit_exceeded",
            ].includes(String(cause.details?.providerErrorCode ?? ""))
                ? "OpenAI báo đã chạm hạn mức chi tiêu hoặc sử dụng. Kiểm tra hạn mức của project/tổ chức OpenAI trước khi thử lại."
                : "OpenAI từ chối tạo ảnh do quota hoặc hạn mức thanh toán. Kiểm tra giới hạn chi tiêu, quota và tín dụng của project/tổ chức OpenAI trước khi thử lại.";
        case "OPENAI_IMAGE_VALIDATION_FAILED":
        case "OPENAI_IMAGE_REQUEST_REJECTED":
            return "Yêu cầu tạo ảnh chưa phù hợp. Kiểm tra ảnh sản phẩm, bố cục và prompt rồi thử lại nhé.";
        case "SMART_REMAKE_IMAGE_ASSET_INVALID":
            return "Chưa xác minh được ảnh tham chiếu đã lưu. Giữ dự án và nhờ kiểm tra kho tư liệu trước khi tạo tiếp nhé.";
        case "OPENAI_IMAGE_SUBMISSION_UNRESOLVED":
            return "Chưa xác định được kết quả tạo ảnh. Giữ dự án và kiểm tra lại trước khi gửi yêu cầu mới để tránh tính phí trùng.";
        case "SMART_REMAKE_TIMELINE_UNREVIEWED":
        case "SMART_REMAKE_CANDIDATE_NOT_ACCEPTED":
            return "Chọn phiên bản và duyệt đoạn sẽ dùng của từng cảnh trước khi ghép nhé.";
        case "SMART_REMAKE_TIMELINE_SAVE_FAILED":
            return "Chưa lưu được đoạn cắt. Lựa chọn vẫn còn trên màn hình; kiểm tra lại dự án trước khi thử lưu nhé.";
        case "SMART_REMAKE_RENDER_ALREADY_STARTED":
            return "Dự án này đã bắt đầu tạo clip. Mở phần Xem & ghép để kiểm tra hoặc tạo lại từng cảnh nhé.";
        case "SMART_REMAKE_MEDIA_CHANGED":
        case "SMART_REMAKE_MEDIA_UNREADABLE":
        case "SMART_REMAKE_TECHNICAL_CHECK_FAILED":
            return "Chưa kiểm tra được clip đang chọn. Tải lại dự án và chọn phiên bản hợp lệ trước khi ghép nhé.";
        case "SMART_REMAKE_ASSEMBLY_CHECK_FAILED":
        case "SMART_REMAKE_PUBLISH_INVALID":
        case "SMART_REMAKE_COMPOSE_FAILED":
            return "Chưa ghép được video. Bản nháp và video đã xuất vẫn được giữ; bạn có thể thử ghép lại.";
        case "SMART_REMAKE_TIMELINE_INVALID":
        case "SMART_REMAKE_TRIM_INVALID":
            return "Đoạn cắt chưa hợp lệ. Kiểm tra clip, độ dài và duyệt lại từng đoạn nhé.";
        case "KIE_NOT_CONFIGURED":
        case "KIE_AUTH_FAILED":
        case "KIE_DURABLE_JOB_REQUIRED":
            return "KIE: Dịch vụ tạo video chưa sẵn sàng. Nhờ quản trị viên kiểm tra kết nối để tiếp tục.";
        case "KIE_CREDITS_EXHAUSTED":
            return "KIE: Dịch vụ tạo video đã hết lượt sử dụng. Nhờ quản trị viên bổ sung để tiếp tục.";
        case "KIE_RATE_LIMITED":
            return "KIE: Dịch vụ tạo video đang bận. Đợi ít phút rồi kiểm tra lại yêu cầu đã gửi nhé.";
        case "KIE_SUBMISSION_UNCERTAIN":
        case "KIE_POLL_TIMEOUT":
        case "SMART_REMAKE_SUBMISSION_UNRESOLVED":
            return "Chưa xác định được kết quả từ kie.ai. Kiểm tra lại yêu cầu trước khi tạo tiếp để tránh gửi trùng.";
        case "KIE_TASK_FAILED": {
            const message = String(
                (cause.details?.providerError as SmartRemakeProviderError | undefined)
                    ?.providerMessage ?? "",
            ).toLowerCase();
            if (message.includes("public figure"))
                return "Lỗi từ nhà cung cấp kie.ai: bộ lọc từ chối tạo video vì cho rằng tư liệu liên quan đến nhân vật công chúng. Kiểm tra ảnh và nội dung trước khi thử lại.";
            if (/internal error|server exception/.test(message))
                return "Lỗi từ nhà cung cấp kie.ai: hệ thống tạo video báo lỗi nội bộ. Các clip đã hoàn tất vẫn được giữ; xem phản hồi và kiểm tra trạng thái.";
            return "Lỗi từ nhà cung cấp kie.ai. Chưa tạo được video. Các cảnh hoàn tất vẫn được giữ; hãy mở dự án để kiểm tra.";
        }
        case "KIE_UPLOAD_FAILED":
            return "Lỗi kết nối khi tải ảnh tham chiếu lên KIE. Ảnh đã tạo vẫn được giữ trong dự án; hãy thử lại khi kết nối ổn định.";
        case "KIE_UNSAFE_MEDIA_URL":
            return "Chưa gửi được ảnh sản phẩm tới KIE. Kiểm tra ảnh JPG, PNG hoặc WebP và thử lại nhé.";
        case "KIE_VALIDATION_FAILED":
            return "KIE: Yêu cầu tạo video chưa hợp lệ. Kiểm tra ảnh sản phẩm và prompt từng cảnh nhé.";
        case "KIE_OUTPUT_DOWNLOAD_FAILED":
            return "Video từ KIE đã tạo nhưng chưa tải về được. Giữ dự án và kiểm tra lại, chưa cần tạo cảnh mới.";
        case "SMART_REMAKE_OPERATION_UNRESOLVED":
            return "Yêu cầu trước có thể vẫn đang xử lý. Bấm Kiểm tra lại để cập nhật trước khi tạo tiếp.";
        default:
            return cause.code.startsWith("OPENAI_IMAGE_")
                ? "Chưa hoàn tất bước tạo ảnh. Các tư liệu đã lưu vẫn được giữ; kiểm tra lại dự án trước khi thử tiếp."
                : cause.code.startsWith("KIE_")
                  ? "Chưa hoàn tất yêu cầu tạo video với KIE. Các cảnh đã có vẫn được giữ; kiểm tra lại dự án trước khi tạo tiếp."
                  : cause.code.startsWith("SMART_REMAKE_")
                    ? "Chưa hoàn tất yêu cầu Smart Remake. Kiểm tra lại dự án hoặc tư liệu rồi thử lại nhé."
                    : cause.message;
    }
}

export function getRemakeProjectError(project: SmartRemakeProject | null): string | null {
    if (project?.pendingOperation || project?.lastOperation?.status !== "failed") return null;
    return getRemakeErrorMessage(
        new ApiError(
            project.lastOperation.errorCode || "SMART_REMAKE_OPERATION_FAILED",
            "Chưa hoàn tất yêu cầu. Các cảnh đã có vẫn được giữ; kiểm tra lại dự án trước khi tạo tiếp.",
            project.lastOperation.providerError?.httpStatus ??
                project.generationRecovery?.httpStatus ??
                503,
            {
                providerErrorCode: project.generationRecovery?.providerErrorCode,
                providerError: project.lastOperation.providerError,
            },
        ),
    );
}

export type SmartRemakeRenderAttempt = {
    compileSnapshot: string;
    productImage?: File;
    productUrl?: string;
    idempotencyKey: string;
};

export function prepareRemakeRenderAttempt(
    current: SmartRemakeRenderAttempt | null,
    input: { compileResult: SmartRemakeCompileResult; productImage?: File; productUrl?: string },
): SmartRemakeRenderAttempt {
    const compileSnapshot = JSON.stringify(input.compileResult);
    const productUrl = input.productUrl?.trim() || undefined;
    if (
        current?.compileSnapshot === compileSnapshot &&
        current.productImage === input.productImage &&
        current.productUrl === productUrl
    )
        return current;
    return {
        compileSnapshot,
        productImage: input.productImage,
        productUrl,
        idempotencyKey: crypto.randomUUID(),
    };
}

export function prepareRemakeRenderRetry(
    current: SmartRemakeRenderAttempt | null,
    input: { compileResult: SmartRemakeCompileResult; productImage?: File; productUrl?: string },
    recovery?: SmartRemakeGenerationRecovery,
): SmartRemakeRenderAttempt {
    const confirmed =
        current &&
        recovery?.kind === "retry_initial_render" &&
        recovery.requestKey === current.idempotencyKey;
    if (current && !confirmed) {
        if (
            current.compileSnapshot !== JSON.stringify(input.compileResult) ||
            current.productImage !== input.productImage ||
            current.productUrl !== (input.productUrl?.trim() || undefined)
        )
            throw new ApiError(
                "SMART_REMAKE_OPERATION_UNRESOLVED",
                "Chưa xác định được kết quả lượt tạo trước. Kiểm tra trạng thái trước khi gửi yêu cầu mới.",
                409,
            );
        return current;
    }
    return prepareRemakeRenderAttempt(null, input);
}

export function hasRemakeRepairClip(
    scene: SmartRemakeProject["scenes"][number] | undefined,
): boolean {
    return Boolean(
        scene?.activeVersionId &&
        scene.versions.find((version) => version.id === scene.activeVersionId)?.videoUrl?.trim(),
    );
}

export function getRemakeProjectPollInterval(project: SmartRemakeProject | null): 5000 | false {
    return project?.pendingOperation &&
        (project.provider === "kie" ||
            project.phase !== undefined ||
            ["inspection", "analysis", "compose"].includes(project.pendingOperation.kind ?? "")) &&
        !project.pendingOperation.needsReconciliation
        ? 5000
        : false;
}

export function getRemakeGenerationSetupError(
    compileResult: SmartRemakeCompileResult | null,
    health: SmartRemakeHealth | undefined,
): string | null {
    const groupingError = getRemakeProviderGroupingError(compileResult);
    if (groupingError) return groupingError;
    if (
        compileResult?.renderPlan?.imageModel &&
        health?.mode === "live" &&
        !health.openaiImagesConfigured
    )
        return "Dịch vụ tạo ảnh OpenAI chưa được kết nối. Nhờ quản trị viên kiểm tra trước khi tạo video nhé.";
    if (
        compileResult?.schemaVersion === 2 &&
        (compileResult.expectationsVersion !== 1 ||
            !/^[a-f0-9]{64}$/.test(compileResult.expectationsHash ?? ""))
    )
        return getRemakeErrorMessage(new ApiError("SMART_REMAKE_EXPECTATIONS_REQUIRED", "", 409));
    return null;
}

export function getRemakeProviderGroupingError(
    plan: Pick<SmartRemakeCompileResult, "schemaVersion" | "renderPlan"> | null,
): string | null {
    return plan?.schemaVersion === 2 && plan.renderPlan?.groupingPolicy !== "fixed_provider_windows"
        ? getRemakeErrorMessage(new ApiError("SMART_REMAKE_PROVIDER_PLAN_UPDATE_REQUIRED", "", 409))
        : null;
}

export async function renderSmartRemakeVideo(
    workspaceId: string,
    input: {
        compileResult: SmartRemakeCompileResult;
        productImage?: File;
        productUrl?: string;
        health?: SmartRemakeHealth;
        demo?: boolean;
        idempotencyKey?: string;
    },
): Promise<SmartRemakeRenderState> {
    if (input.demo === true) {
        if (!(await isDemoVideoAvailable(DEMO_OUTPUT_VIDEO))) {
            throw new Error(
                "Video mẫu chưa có trên máy này. Hãy chọn chế độ tạo video để tiếp tục.",
            );
        }
        return { finalVideoUrl: DEMO_OUTPUT_VIDEO, status: "completed", isDemo: true };
    }

    const health = input.health;
    const provider = health?.enabled
        ? health.mode === "fixture"
            ? "fixture"
            : health.kieConfigured
              ? "kie"
              : health.unificallyConfigured
                ? "unifically"
                : health.flowkitUrlSet
                  ? "flowkit"
                  : null
        : null;
    if (!provider) {
        throw new Error("Hãy cấu hình dịch vụ tạo video để tiếp tục.");
    }
    const isTimeline = input.compileResult.schemaVersion === 2;
    if (isTimeline && provider === "fixture")
        throw new Error(
            "Đang ở chế độ kiểm thử nên chưa tạo clip AI. Bạn có thể xem kịch bản hoặc video ví dụ.",
        );
    if (
        isTimeline &&
        (!input.compileResult.projectId || !Number.isInteger(input.compileResult.revision))
    )
        throw new Error("Kịch bản chưa được lưu đầy đủ. Cập nhật kịch bản trước khi tạo nhé.");
    if (isTimeline && provider !== "kie" && provider !== "fixture")
        throw new Error(
            "Timeline cần kết nối KIE Veo để tạo các clip theo nhóm cảnh. Nhờ quản trị viên kiểm tra nhé.",
        );
    const setupError = getRemakeGenerationSetupError(input.compileResult, health);
    if (setupError) throw new Error(setupError);
    const productUrl = input.productUrl?.trim();
    if (!isTimeline && provider !== "fixture" && !input.productImage && !productUrl) {
        throw new Error("Hãy thêm ảnh hoặc liên kết sản phẩm để tạo video.");
    }
    return renderSmartRemake(workspaceId, {
        compileResult: input.compileResult,
        ...(!isTimeline && input.productImage ? { productImage: input.productImage } : {}),
        ...(!isTimeline && productUrl ? { productUrl } : {}),
        ...(isTimeline
            ? {
                  projectId: input.compileResult.projectId,
                  expectedRevision: input.compileResult.revision,
              }
            : {}),
        provider,
        projectName: "Smart Remake",
        ...(input.idempotencyKey ? { idempotencyKey: input.idempotencyKey } : {}),
    });
}
