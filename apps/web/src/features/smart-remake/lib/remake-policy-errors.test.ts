import { describe, expect, it } from "vitest";

import { ApiError } from "@/shared/api/errors";
import { getRemakeErrorMessage } from "./smart-remake-render";

describe("rights policy errors", () => {
    it.each(["SMART_REMAKE_RIGHTS_ATTESTATION_REQUIRED", "SMART_REMAKE_RIGHTS_POLICY_OUTDATED"])(
        "asks for a current policy confirmation without exposing %s internals",
        (code) => {
            const message = getRemakeErrorMessage(new ApiError(code, "PRIVATE_SNAPSHOT", 403));
            expect(message).toContain("chính sách");
            expect(message).toContain("xác nhận");
            expect(message).not.toContain("PRIVATE_SNAPSHOT");
        },
    );
});
