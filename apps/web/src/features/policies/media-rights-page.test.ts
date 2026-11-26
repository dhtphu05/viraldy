import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { MediaRightsPage } from "./media-rights-page";
import { MEDIA_RIGHTS_ATTESTATION_TEXT, MEDIA_RIGHTS_POLICY_VERSION } from "./media-rights-policy";

describe("media rights policy", () => {
    it("publishes the versioned policy and exact attestation without accepting it", () => {
        const html = renderToStaticMarkup(createElement(MediaRightsPage));
        expect(html).toContain("Chính sách sử dụng tư liệu");
        expect(html).toContain(MEDIA_RIGHTS_POLICY_VERSION);
        expect(html).toContain(MEDIA_RIGHTS_ATTESTATION_TEXT);
        expect(html).toContain("Người dùng đã xác nhận quyền");
        expect(html).toContain("Gemini");
        expect(html).toContain("OpenAI");
        expect(html).toContain("KIE");
        expect(html).not.toContain('type="checkbox"');
        expect(html).not.toContain("Tôi đồng ý và tiếp tục");
    });
});
