import { apiGet, apiPostForm } from "./client";

export type SmartRemakeHealth = {
    enabled: boolean;
    mode: "fixture" | "live";
    providers: string[];
    flowkitUrlSet: boolean;
    unificallyConfigured: boolean;
    limits: { referenceVideoBytes: number; productImageBytes: number };
};

export type SmartRemakeCompileResult = {
    success: true;
    mode: "smart_remake" | "montage";
    renderSubmitted: false;
    inputSummary: { targetDuration: 8 | 16; aspectRatio: "9:16"; language: string | null };
    referenceAnalysis: Record<string, unknown>;
    analyzeOutput: Record<string, unknown>;
    productLock: Record<string, unknown>;
    sceneMap: {
        targetDuration: 8 | 16;
        sceneCount: 1 | 2;
        scenes: Array<Record<string, unknown>>;
    };
    compiledPrompts: Array<Record<string, unknown>>;
    compilerDiagnostics: Record<string, unknown>;
    diagnostics: Record<string, unknown>;
    versions: Record<string, unknown>;
    warnings: string[];
};

export type SmartRemakeRenderResult = {
    success: true;
    mode: "smart_remake";
    provider: string;
    finalVideoUrl: string;
    targetDuration: 8 | 16;
    sceneCount: number;
    renderSubmitted: boolean;
    status: "completed" | "submitted";
    warnings: string[];
    projectId?: string;
    videoId?: string;
    sceneIds?: string[];
};

export function getSmartRemakeHealth(workspaceId: string) {
    return apiGet<SmartRemakeHealth>(`/workspaces/${workspaceId}/smart-remake/health`);
}

export function compileSmartRemake(
    workspaceId: string,
    input: {
        targetDuration: 8 | 16;
        language: string;
        prompt: string;
        description: string;
        referenceVideo: File;
        productImage?: File;
        productUrl?: string;
        productTitle?: string;
        productDescription?: string;
    },
) {
    const body = new FormData();
    body.set("mode", "smart_remake");
    body.set("targetDuration", String(input.targetDuration));
    body.set("aspectRatio", "9:16");
    body.set("language", input.language);
    body.set("prompt", input.prompt);
    body.set("description", input.description);
    body.set("referenceVideo", input.referenceVideo);
    if (input.productImage) body.set("productImage", input.productImage);
    if (input.productUrl) body.set("productUrl", input.productUrl);
    if (input.productTitle) body.set("productTitle", input.productTitle);
    if (input.productDescription) body.set("productDescription", input.productDescription);
    return apiPostForm<SmartRemakeCompileResult>(
        `/workspaces/${workspaceId}/smart-remake/compile`,
        body,
    );
}

export function renderSmartRemake(
    workspaceId: string,
    input: {
        compileResult: SmartRemakeCompileResult;
        productImage: File;
        provider: "fixture" | "flowkit" | "unifically";
        projectName: string;
    },
) {
    const body = new FormData();
    body.set("compileResult", JSON.stringify(input.compileResult));
    body.set("productImage", input.productImage);
    body.set("provider", input.provider);
    body.set("projectName", input.projectName);
    body.set("audioRequired", "false");
    return apiPostForm<SmartRemakeRenderResult>(
        `/workspaces/${workspaceId}/smart-remake/render`,
        body,
    );
}
