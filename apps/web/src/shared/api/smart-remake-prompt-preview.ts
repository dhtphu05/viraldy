import { apiPost, type ApiRequestOptions } from "./client";
import type { SmartRemakeRequirements } from "./smart-remake-project-types";

export type SmartRemakePromptPreviewInput = {
    expectedRevision: number;
    scenePrompts?: Array<{
        renderUnitId: string;
        prompt: string;
        imagePrompt: string;
        videoPrompt: string;
    }>;
    requirements?: SmartRemakeRequirements;
};

export type SmartRemakePromptPreview = {
    projectId: string;
    revision: number;
    groups: Array<{ groupId: string; model: string; prompt: string }>;
};

export function previewSmartRemakeKiePrompts(
    workspaceId: string,
    projectId: string,
    input: SmartRemakePromptPreviewInput,
    options: ApiRequestOptions = {},
) {
    return apiPost<SmartRemakePromptPreview>(
        `/workspaces/${encodeURIComponent(workspaceId)}/smart-remake/projects/${encodeURIComponent(projectId)}/generation/prompt-preview`,
        input,
        options,
    );
}
