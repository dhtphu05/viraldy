import { ArrowRight } from "lucide-react";
import { Button } from "@/shared/ui/button";
import type { RemakeResultNextAction } from "../lib/remake-result-next-action";
import type { SmartRemakeProject } from "@/shared/api/smart-remake";
import { RemakeGenerationRecovery } from "./remake-generation-recovery";
import "./remake-result-next-step.css";

const workflowSteps = [
    "Xem toàn video",
    "Sửa cảnh khi cần",
    "Kiểm tra & duyệt",
    "Tải video",
] as const;
const actionStep: Partial<Record<RemakeResultNextAction["kind"], number>> = {
    update_plan: 0,
    candidate: 1,
    scene: 1,
    compose: 0,
    assembly_error: 0,
    inspect: 2,
    findings: 2,
    approve: 2,
    export: 3,
};

export interface RemakeResultNextStepProps {
    action: RemakeResultNextAction;
    busy?: boolean;
    onAction(action: RemakeResultNextAction): void;
    onDismissCandidate?(): void;
    onViewScript?(): void;
    budget?: SmartRemakeProject["budget"];
    technicalError?: string | null;
}
export function RemakeResultNextStep(props: RemakeResultNextStepProps) {
    if (props.action.kind === "retry_render") return <RemakeGenerationRecovery {...props} />;
    return (
        <section aria-label="Bước tiếp theo" className="remake-result-next-step">
            <ol className="sr-only" aria-label="Các bước hoàn thiện video">
                {workflowSteps.map((label, index) => (
                    <li
                        key={label}
                        aria-current={actionStep[props.action.kind] === index ? "step" : undefined}
                    >
                        {label}
                    </li>
                ))}
            </ol>
            <div className="remake-result-next-step__action">
                <div className="min-w-0 flex-1 basis-64">
                    <h2 className="sr-only">Bước tiếp theo</h2>
                    <p
                        role="status"
                        aria-live="polite"
                        className="text-sm leading-relaxed text-text-primary"
                    >
                        {props.action.reason}
                    </p>
                </div>
                <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
                    {props.action.kind === "candidate" && props.onDismissCandidate && (
                        <Button
                            type="button"
                            variant="ghost"
                            className="min-h-12"
                            disabled={props.busy}
                            onClick={props.onDismissCandidate}
                        >
                            Tiếp tục với bản đang dùng
                        </Button>
                    )}
                    <Button
                        type="button"
                        variant={props.action.kind === "scene" ? "ghost" : "default"}
                        className={`min-h-12 whitespace-normal focus-visible:ring-[#e00b41]/40 ${
                            props.action.kind === "scene"
                                ? "text-text-secondary"
                                : "bg-[#e00b41] text-white hover:bg-[#c90a3a]"
                        }`}
                        disabled={props.busy || props.action.kind === "blocked"}
                        onClick={() => props.onAction(props.action)}
                    >
                        {props.action.label} <ArrowRight aria-hidden="true" />
                    </Button>
                </div>
            </div>
        </section>
    );
}
