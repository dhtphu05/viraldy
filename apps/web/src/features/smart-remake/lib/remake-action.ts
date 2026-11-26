import type {
    SmartRemakeBudgetPolicy,
    SmartRemakeInspectSubject,
    SmartRemakePreflight,
    SmartRemakePromptDraft,
    SmartRemakeRequirements,
    SmartRemakeRights,
    RepairIntent,
} from "@/shared/api/smart-remake";
import { getRemakeBudgetError } from "./remake-intake";

export type RemakeActionSnapshot = {
    requirements: SmartRemakeRequirements;
    rights: SmartRemakeRights;
    budget: SmartRemakeBudgetPolicy;
};
export type RemakeRepairCandidate = { projectId: string; sceneId: string; versionId: string };
type IntentIdentity = { fingerprint: string; startsNewProject?: boolean };
export type RemakeActionIntent = IntentIdentity &
    (
        | { action: "analyze" | "reanalyze" | "render" }
        | {
              action: "repair";
              sceneId: string;
              baseVersionId: string | null;
              draft?: SmartRemakePromptDraft;
              repairIntent?: RepairIntent;
          }
        | { action: "inspect"; subject: SmartRemakeInspectSubject }
    );
export type RemakeActionArgs = {
    sceneId?: string;
    repairIntent?: RepairIntent;
    draft?: SmartRemakePromptDraft;
    subject?: SmartRemakeInspectSubject;
};
function usdMicros(value: string): bigint | null {
    if (!/^(?:0|[1-9]\d{0,7})(?:\.\d{1,6})?$/.test(value)) return null;
    const [whole, fraction = ""] = value.split(".");
    return BigInt(whole) * 1_000_000n + BigInt(fraction.padEnd(6, "0"));
}
export function getRemakeActionBudgetError(
    budget: SmartRemakeBudgetPolicy,
    preflight: SmartRemakePreflight,
): string | null {
    if (budget.mode === "unlimited") return null;
    const invalid = getRemakeBudgetError(budget);
    if (invalid) return invalid;
    const required = preflight.budget;
    if (!required) return "Chưa có đề xuất ngân sách. Kết nối lại để kiểm tra.";
    if (
        required.minimumCapUsd === null ||
        required.minimumMaxAttempts === null ||
        required.minimumDurationSeconds === null
    )
        return "Chưa có đề xuất giới hạn cho yêu cầu cũ này.";
    const cap = usdMicros(budget.capUsd);
    const minimum = usdMicros(required.minimumCapUsd);
    if (cap === null || minimum === null || cap < minimum)
        return `Trần ngân sách cần ít nhất ${required.minimumCapUsd} USD cho hành động này.`;
    if (budget.maxAttempts < required.minimumMaxAttempts)
        return `Cần cấp ít nhất ${required.minimumMaxAttempts} lượt cho dự án.`;
    if (budget.maxDurationSeconds < required.minimumDurationSeconds)
        return `Giới hạn thời gian cần ít nhất ${required.minimumDurationSeconds} giây tính từ khi dự án bắt đầu.`;
    return null;
}
export function remakePreflightChanged(
    displayed: SmartRemakePreflight,
    fresh: SmartRemakePreflight,
    approved: SmartRemakeBudgetPolicy,
): boolean {
    return (
        displayed.contextHash !== fresh.contextHash ||
        displayed.action !== fresh.action ||
        displayed.mode !== fresh.mode ||
        JSON.stringify(displayed.scope) !== JSON.stringify(fresh.scope) ||
        JSON.stringify(displayed.calls) !== JSON.stringify(fresh.calls) ||
        Boolean(getRemakeActionBudgetError(approved, fresh))
    );
}
