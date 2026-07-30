import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/production")({
    beforeLoad: ({ search }) => {
        throw redirect({
            to: "/mvp",
            search,
        });
    },
});
