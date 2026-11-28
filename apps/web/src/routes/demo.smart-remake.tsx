import { lazy, Suspense } from "react";
import { createFileRoute, notFound } from "@tanstack/react-router";

const DemoPage = import.meta.env.DEV
    ? lazy(() =>
          import("@/features/smart-remake/demo/smart-remake-demo-page").then((module) => ({
              default: module.SmartRemakeDemoPage,
          })),
      )
    : null;

export const Route = createFileRoute("/demo/smart-remake")({
    beforeLoad: () => {
        if (!import.meta.env.DEV) throw notFound();
    },
    component: SmartRemakeDemoRoute,
});

function SmartRemakeDemoRoute() {
    if (!DemoPage) throw notFound();
    return (
        <Suspense fallback={<p role="status">Đang mở bản demo Smart Remake…</p>}>
            <DemoPage />
        </Suspense>
    );
}
