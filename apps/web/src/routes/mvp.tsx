import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/mvp")({
    beforeLoad: ({ search }) => {
        throw redirect({
            to: "/production",
            search,
        });
    },
});
