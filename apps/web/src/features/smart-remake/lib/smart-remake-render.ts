import {
    renderSmartRemake,
    type SmartRemakeCompileResult,
    type SmartRemakeHealth,
    type SmartRemakeRenderResult,
} from "@/shared/api/smart-remake";
import { isDemoVideoAvailable } from "@/shared/lib/optional-demo-media";

export type SmartRemakeRenderState = Pick<SmartRemakeRenderResult, "finalVideoUrl" | "status">;

const DEMO_OUTPUT_VIDEO = "/smart-remake/02_After.mp4";

export async function renderSmartRemakeVideo(
    workspaceId: string,
    input: {
        compileResult: SmartRemakeCompileResult;
        productImage?: File;
        health?: SmartRemakeHealth;
    },
): Promise<SmartRemakeRenderState> {
    if (await isDemoVideoAvailable(DEMO_OUTPUT_VIDEO)) {
        await new Promise<void>((resolve) => setTimeout(resolve, 20_000));
        return { finalVideoUrl: DEMO_OUTPUT_VIDEO, status: "completed" };
    }

    const health = input.health;
    const provider =
        health?.enabled && health.mode === "live"
            ? health.unificallyConfigured
                ? "unifically"
                : health.flowkitUrlSet
                  ? "flowkit"
                  : null
            : null;
    if (!provider) {
        throw new Error(
            "Video mẫu chưa có trên máy này. Hãy cấu hình dịch vụ tạo video để tiếp tục.",
        );
    }
    if (!input.productImage) {
        throw new Error("Hãy tải ảnh sản phẩm lên để tạo video với dịch vụ đã cấu hình.");
    }
    return renderSmartRemake(workspaceId, {
        compileResult: input.compileResult,
        productImage: input.productImage,
        provider,
        projectName: "Smart Remake",
    });
}
