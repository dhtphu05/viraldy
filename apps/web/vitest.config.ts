import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
    resolve: {
        alias: {
            "@": fileURLToPath(new URL("./src", import.meta.url)),
        },
    },
    test: {
        environment: "node",
        include: ["src/**/*.test.ts"],
        environmentOptions: { jsdom: { url: "http://localhost" } },
        coverage: {
            provider: "v8",
            reporter: ["text", "json-summary"],
            reportsDirectory: "/tmp/viraldy-web-coverage",
        },
    },
});
