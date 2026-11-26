import { describe, expect, it } from "vitest";
import { ApiError } from "@/shared/api/errors";
import { getRemakeErrorMessage } from "./smart-remake-render";

describe("analysis error guidance", () => {
    it("explains the uncertain analysis without exposing provider text", () => {
        const message = getRemakeErrorMessage(
            new ApiError("SMART_REMAKE_MODEL_ATTEMPT_UNCERTAIN", "PRIVATE_BODY", 409),
        );
        expect(message).toContain("kết quả AI hợp lệ");
        expect(message).toContain("kiểm tra trạng thái");
        expect(message).not.toContain("PRIVATE_BODY");
    });

    it.each([
        new ApiError("SMART_REMAKE_GEMINI_OUTPUT_TRUNCATED", "PRIVATE_BODY", 409),
        new ApiError("SMART_REMAKE_MODEL_ATTEMPT_UNCERTAIN", "PRIVATE_BODY", 409, {
            causeCode: "SMART_REMAKE_GEMINI_OUTPUT_TRUNCATED",
        }),
    ])("uses a specific explanation only for a known truncated response", (error) => {
        const message = getRemakeErrorMessage(error);
        expect(message).toContain("bị cắt");
        expect(message).not.toContain("PRIVATE_BODY");
    });

    it("does not infer truncation from untrusted diagnostics", () => {
        const message = getRemakeErrorMessage(
            new ApiError("SMART_REMAKE_MODEL_ATTEMPT_UNCERTAIN", "PRIVATE_BODY", 409, {
                causeCode: "private-model-detail",
            }),
        );
        expect(message).toContain("kết quả AI hợp lệ");
        expect(message).not.toContain("bị cắt");
    });
});
