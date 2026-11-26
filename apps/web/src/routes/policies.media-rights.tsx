import { createFileRoute } from "@tanstack/react-router";

import { MediaRightsPage } from "@/features/policies/media-rights-page";

export const Route = createFileRoute("/policies/media-rights")({
    head: () => ({
        meta: [
            { title: "Chính sách sử dụng tư liệu — Viraldy" },
            {
                name: "description",
                content:
                    "Quyền sử dụng video, ảnh sản phẩm và xử lý tư liệu bằng AI trong Smart Remake.",
            },
        ],
    }),
    component: MediaRightsPage,
});
