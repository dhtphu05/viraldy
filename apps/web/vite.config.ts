import tailwindcss from "@tailwindcss/vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import react from "@vitejs/plugin-react";
import { nitro } from "nitro/vite";
import { defineConfig, type PluginOption } from "vite";

const srcPath = new URL("./src", import.meta.url).pathname;

export default defineConfig(({ command }) => {
    const isBuild = command === "build";
    const plugins: PluginOption[] = [
        tailwindcss(),
        tanstackStart({
            importProtection: {
                behavior: "error",
                client: {
                    files: ["**/server/**"],
                    specifiers: ["server-only"],
                },
            },
            server: { entry: "server" },
        }),
        react(),
    ];

    if (isBuild) {
        plugins.push(
            nitro({
                preset: "cloudflare-module",
                cloudflare: {
                    nodeCompat: true,
                    deployConfig: true,
                },
            }),
        );
    }

    return {
        css: { transformer: "lightningcss" },
        plugins,
        resolve: {
            alias: {
                "@": srcPath,
            },
            dedupe: [
                "react",
                "react-dom",
                "react/jsx-runtime",
                "react/jsx-dev-runtime",
                "@tanstack/react-query",
                "@tanstack/query-core",
            ],
            tsconfigPaths: true,
        },
        optimizeDeps: {
            include: [
                "react",
                "react-dom",
                "react-dom/client",
                "react/jsx-runtime",
                "react/jsx-dev-runtime",
            ],
            ignoreOutdatedRequests: true,
        },
        server: {
            host: "0.0.0.0",
            port: 8080,
        },
    };
});
