import { useCallback, useRef, useState } from "react";
import type { RemakeActionSnapshot } from "./remake-action";
import { hashRemakeFile } from "./remake-media-binding";
import {
    createSmartRemakeProject,
    updateSmartRemakeContext,
    inspectSmartRemakeSubject,
    reviewSmartRemakeFinding,
    approveSmartRemakeAssembly,
    exportSmartRemakeAssembly,
    restoreSmartRemakeAssembly,
    deleteSmartRemakeProject,
    reviewSmartRemakeRights,
    getSmartRemakeProject,
    type SmartRemakeProject,
    type SmartRemakeRequirements,
    type SmartRemakeRights,
    type SmartRemakeBudgetPolicy,
    type SmartRemakeOperationResult,
    type SmartRemakeInspectSubject,
    type SmartRemakeProjectMutationResult,
} from "@/shared/api/smart-remake";
import {
    DEFAULT_REMAKE_INTENT,
    emptyRemakeRights,
    getRemakeRightsError,
    invalidateRemakeMediaRights,
    normalizeRemakeRequirements,
    remakeRightsInput,
    remakeBudgetInput,
} from "./remake-intake";

export type RemakeBusyStep =
    | "analyze"
    | "generate"
    | "repair"
    | "compose"
    | "restore"
    | "sample"
    | "link"
    | "timeline"
    | "context"
    | "inspect"
    | "review"
    | "approve"
    | "export"
    | "delete";
type Run = <T>(kind: RemakeBusyStep, operation: () => Promise<T>) => Promise<T | undefined>;
interface PolicyOptions {
    workspaceId: string;
    project: SmartRemakeProject | null;
    run: Run;
    rememberProject(project: SmartRemakeProject): void;
    operationKey(payload: unknown): string;
    performOperation(
        payload: unknown,
        request: (key: string) => Promise<SmartRemakeOperationResult>,
    ): Promise<SmartRemakeOperationResult>;
    validFile(file: File, kind: "video" | "image"): boolean;
    setNotice(message: string): void;
    isLocked(): boolean;
}

const sameProductAngles = (left: File[] = [], right: File[] = []) =>
    left.length === right.length && left.every((file, index) => file === right[index]);

export function useRemakePolicy({
    workspaceId,
    project,
    run,
    rememberProject,
    operationKey,
    performOperation,
    validFile,
    setNotice,
    isLocked,
}: PolicyOptions) {
    const [requirements, setRequirements] = useState<SmartRemakeRequirements>({
        intent: DEFAULT_REMAKE_INTENT,
        keep: [],
        replace: [],
        forbid: [],
        claims: [],
        requiresCharacter: false,
    });
    const [rights, setRights] = useState<SmartRemakeRights>(emptyRemakeRights);
    const [budget, setBudget] = useState<SmartRemakeBudgetPolicy>({ mode: "unlimited" });
    const [characterFile, setCharacterFile] = useState<File | null>(null);
    const intakeAttempt = useRef<{
        source: File;
        product: File | undefined;
        additionalProducts?: File[];
        productUrl?: string;
        character: File | null;
        metadataHash: string;
        key: string;
        projectId?: string;
        mediaHashes?: SmartRemakeProject["inputMediaHashes"];
    } | null>(null);
    async function restoreIntakeBinding(
        saved: SmartRemakeProject,
        inputs: {
            video: File | null;
            product?: File;
            additionalProducts?: File[];
            productUrl?: string;
            character: File | null;
        },
        isCurrent: () => boolean = () => true,
    ): Promise<boolean> {
        const expected = saved.inputMediaHashes;
        if (!expected || !inputs.video || !inputs.product || (project && saved.id !== project.id))
            return false;
        const [source, product, character, additionalProducts] = await Promise.all([
            hashRemakeFile(inputs.video),
            hashRemakeFile(inputs.product),
            inputs.character ? hashRemakeFile(inputs.character) : null,
            Promise.all((inputs.additionalProducts ?? []).map(hashRemakeFile)),
        ]);
        if (!isCurrent()) return false;
        if (
            source !== expected.source ||
            product !== expected.product ||
            character !== (expected.character ?? null) ||
            JSON.stringify(additionalProducts) !== JSON.stringify(expected.additionalProducts ?? [])
        )
            return false;
        intakeAttempt.current = {
            source: inputs.video,
            product: inputs.product,
            additionalProducts: inputs.additionalProducts
                ? [...inputs.additionalProducts]
                : undefined,
            productUrl: inputs.productUrl,
            character: inputs.character,
            metadataHash: "",
            key: crypto.randomUUID(),
            projectId: saved.id,
            mediaHashes: expected,
        };
        setCharacterFile(inputs.character);
        return true;
    }
    async function prepareProject({
        video,
        product,
        additionalProducts = [],
        productUrl,
        productImageUrl,
        duration,
        snapshot = { requirements, rights, budget },
    }: {
        video: File | null;
        product?: File;
        additionalProducts?: File[];
        productUrl?: string;
        productImageUrl?: string;
        duration: 8 | 12 | 16;
        snapshot?: RemakeActionSnapshot;
    }): Promise<SmartRemakeProject> {
        if (additionalProducts.length > 13)
            throw new Error("Tối đa 14 ảnh sản phẩm. Xóa bớt ảnh rồi thử lại nhé.");
        if (!video && project && project.targetDuration !== duration)
            throw new Error(
                "Thêm lại video mẫu để tạo dự án với thời lượng mới. Dự án trước vẫn được giữ.",
            );
        if (!video && (product || additionalProducts.length || productUrl || characterFile))
            throw new Error(
                "Thêm lại video mẫu để lưu bộ tư liệu mới trước khi phân tích. Tư liệu cũ vẫn được giữ.",
            );
        let owned = project;
        const previous = intakeAttempt.current;
        const metadataHash = JSON.stringify({
            targetDuration: duration,
            requirements: normalizeRemakeRequirements(snapshot.requirements),
            rights: remakeRightsInput(snapshot.rights),
            budget: { mode: "unlimited" },
        });
        const reusesLocalInputs =
            previous?.projectId &&
            project &&
            previous.projectId === project.id &&
            project.targetDuration === duration &&
            previous.source === video &&
            previous.product === product &&
            sameProductAngles(previous.additionalProducts, additionalProducts) &&
            previous.productUrl === productUrl &&
            previous.character === characterFile;
        if (video && !reusesLocalInputs) {
            if (
                !previous ||
                previous.source !== video ||
                previous.product !== product ||
                !sameProductAngles(previous.additionalProducts, additionalProducts) ||
                previous.productUrl !== productUrl ||
                previous.character !== characterFile ||
                previous.metadataHash !== metadataHash
            )
                intakeAttempt.current = {
                    source: video,
                    product,
                    additionalProducts: [...additionalProducts],
                    productUrl: productUrl,
                    character: characterFile,
                    metadataHash,
                    key: crypto.randomUUID(),
                };
            let upload = product;
            if (!upload && productImageUrl) {
                const response = await fetch(productImageUrl);
                if (!response.ok)
                    throw new Error(
                        "Chưa tải được ảnh sản phẩm từ link. Thêm ảnh trực tiếp để lưu tư liệu có quyền.",
                    );
                const blob = await response.blob();
                upload = new File([blob], "product-reference", { type: blob.type });
                if (!validFile(upload, "image"))
                    throw new Error("Ảnh từ link chưa hợp lệ. Thêm ảnh sản phẩm trực tiếp nhé.");
            }
            if (!upload) throw new Error("Thêm ảnh sản phẩm trước khi lưu tư liệu.");
            const created = await createSmartRemakeProject(workspaceId, {
                metadata: {
                    idempotencyKey: intakeAttempt.current!.key,
                    projectName: "Smart Remake",
                    targetDuration: duration,
                    requirements: normalizeRemakeRequirements(snapshot.requirements),
                    rights: remakeRightsInput(snapshot.rights),
                    budget: { mode: "unlimited" },
                },
                referenceVideo: video,
                productImage: upload,
                ...(additionalProducts.length
                    ? { additionalProductImages: additionalProducts }
                    : {}),
                ...(characterFile ? { characterImage: characterFile } : {}),
            });
            owned = created.project;
            intakeAttempt.current!.projectId = owned.id;
            intakeAttempt.current!.mediaHashes = owned.inputMediaHashes;
            rememberProject(owned);
        }
        if (!owned) throw new Error("Lưu tư liệu trước khi phân tích.");
        return syncContext(owned, snapshot);
    }

    async function syncContext(
        owned: SmartRemakeProject,
        snapshot: RemakeActionSnapshot = { requirements, rights, budget },
    ): Promise<SmartRemakeProject> {
        let latest = owned;
        const requested = {
            requirements: normalizeRemakeRequirements(snapshot.requirements),
            rights: remakeRightsInput(snapshot.rights),
            budget: { mode: "unlimited" },
        };
        const saved = {
            requirements: owned.requirements && normalizeRemakeRequirements(owned.requirements),
            rights: owned.rights && remakeRightsInput(owned.rights),
            budget: owned.budget?.policy && remakeBudgetInput(owned.budget.policy),
        };
        for (const field of ["requirements", "rights", "budget"] as const) {
            if (JSON.stringify(requested[field]) === JSON.stringify(saved[field])) continue;
            const input = { expectedRevision: latest.revision, [field]: requested[field] };
            const next = await updateSmartRemakeContext(workspaceId, latest.id, field, {
                ...input,
                idempotencyKey: operationKey({ kind: field, projectId: latest.id, ...input }),
            });
            latest = next.project;
            rememberProject(latest);
        }
        return latest;
    }

    async function saveContext() {
        if (!project) return;
        await run("context", async () => {
            await syncContext(project);
            setNotice(
                "Đã lưu yêu cầu và quyền sử dụng tư liệu. Nội dung thay đổi cần kiểm tra và duyệt lại.",
            );
        });
    }

    async function projectOperation(
        kind: RemakeBusyStep,
        input: Record<string, unknown>,
        request: (identity: {
            expectedRevision: number;
            idempotencyKey: string;
        }) => Promise<SmartRemakeProjectMutationResult>,
    ) {
        if (!project) return;
        const completed = await run(kind, async () => {
            const snapshot = {
                kind,
                projectId: project.id,
                expectedRevision: project.revision,
                ...input,
            };
            const next = await performOperation(snapshot, async (key) => {
                const result = await request({
                    expectedRevision: project.revision,
                    idempotencyKey: key,
                });
                return {
                    project:
                        result.project ?? (await getSmartRemakeProject(workspaceId, project.id)),
                    operationId: result.operationId ?? key,
                    status:
                        result.status === "running"
                            ? "running"
                            : result.status === "failed"
                              ? "failed"
                              : "completed",
                };
            });
            rememberProject(next.project);
            if (next.status === "failed")
                throw new Error("Thao tác chưa hoàn tất. Kiểm tra trạng thái dự án rồi thử lại.");
            return true;
        });
        if (!completed) throw new Error("Chưa hoàn tất thao tác. Xem thông báo của dự án.");
    }

    async function inspect(subject: SmartRemakeInspectSubject, snapshot?: RemakeActionSnapshot) {
        if (!project) return false;
        if (!snapshot) {
            await projectOperation("inspect", { subject }, (identity) =>
                inspectSmartRemakeSubject(workspaceId, project.id, { ...identity, subject }),
            );
            return true;
        }
        return (
            (await run("inspect", async () => {
                const owned = await syncContext(project, snapshot);
                const input = { subject, expectedRevision: owned.revision };
                const next = await performOperation(
                    { kind: "inspect", projectId: owned.id, ...input },
                    async (key) => {
                        const response = await inspectSmartRemakeSubject(workspaceId, owned.id, {
                            ...input,
                            idempotencyKey: key,
                        });
                        return {
                            project:
                                response.project ??
                                (await getSmartRemakeProject(workspaceId, owned.id)),
                            operationId: response.operationId ?? key,
                            status:
                                response.status === "failed"
                                    ? "failed"
                                    : response.status === "running"
                                      ? "running"
                                      : "completed",
                        };
                    },
                );
                rememberProject(next.project);
                if (next.status === "failed")
                    throw new Error(
                        "Kiểm tra chưa hoàn tất. Kiểm tra trạng thái trước khi thử lại.",
                    );
                return true;
            })) ?? false
        );
    }

    async function review(
        reportId: string,
        findingId: string,
        decision: "accept" | "reject",
        reason: string,
    ) {
        if (!project) return;
        const input = { reportId, findingId, decision, reason };
        return projectOperation("review", input, (identity) =>
            reviewSmartRemakeFinding(workspaceId, project.id, { ...identity, ...input }),
        );
    }

    async function approve(assemblyId: string, reportId: string) {
        if (!project) return;
        return projectOperation("approve", { assemblyId, reportId }, (identity) =>
            approveSmartRemakeAssembly(workspaceId, project.id, {
                ...identity,
                assemblyId,
                reportId,
            }),
        );
    }

    async function rightsReview(evidenceNote: string) {
        if (!project) return;
        return projectOperation("review", { evidenceNote }, (identity) =>
            reviewSmartRemakeRights(workspaceId, project.id, { ...identity, evidenceNote }),
        );
    }

    async function restore(assemblyId: string) {
        if (!project) return;
        return projectOperation("restore", { assemblyId }, (identity) =>
            restoreSmartRemakeAssembly(workspaceId, project.id, { ...identity, assemblyId }),
        );
    }

    async function deleteProject(reason: string) {
        if (!project) return;
        return projectOperation("delete", { reason }, (identity) =>
            deleteSmartRemakeProject(workspaceId, project.id, { ...identity, reason }),
        );
    }

    async function exportAssembly(assemblyId: string) {
        const approvalId = project?.release?.activeApprovalId;
        if (!project || !approvalId) throw new Error("Duyệt đúng thành phẩm trước khi tải video.");
        const exported = await run("export", async () => {
            const input = { expectedRevision: project.revision, assemblyId, approvalId };
            const next = await exportSmartRemakeAssembly(workspaceId, project.id, {
                ...input,
                idempotencyKey: operationKey({ kind: "export", projectId: project.id, ...input }),
            });
            if (!next.downloadUrl) throw new Error("Backend chưa cấp bản xuất được duyệt.");
            rememberProject(next.project ?? (await getSmartRemakeProject(workspaceId, project.id)));
            const link = document.createElement("a");
            link.href = next.downloadUrl;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            link.download = "smart-remake.mp4";
            link.click();
            setNotice("Đã cấp bản xuất có nhãn AI của đúng thành phẩm được duyệt.");
            return true;
        });
        if (!exported)
            throw new Error("Chưa tải được video. Kiểm tra duyệt xuất và quyền hiện tại.");
    }

    const loadContext = useCallback((saved: SmartRemakeProject) => {
        if (saved.requirements) setRequirements(saved.requirements);
        if (saved.rights) setRights(remakeRightsInput(saved.rights));
        setBudget({ mode: "unlimited" });
    }, []);
    const intakeError = getRemakeRightsError(
        requirements,
        rights,
        Boolean(characterFile || project?.characterImageUrl),
    );
    const contextDirty = Boolean(
        project &&
        (JSON.stringify(normalizeRemakeRequirements(requirements)) !==
            JSON.stringify(
                project.requirements && normalizeRemakeRequirements(project.requirements),
            ) ||
            JSON.stringify(remakeRightsInput(rights)) !==
                JSON.stringify(project.rights && remakeRightsInput(project.rights)) ||
            JSON.stringify(remakeBudgetInput(budget)) !==
                JSON.stringify(project.budget?.policy && remakeBudgetInput(project.budget.policy))),
    );
    return {
        requirements,
        rights,
        budget,
        characterFile,
        intakeError,
        contextDirty,
        invalidateMediaRights: () => setRights(invalidateRemakeMediaRights),
        onRequirementsChange: (value: SmartRemakeRequirements) => {
            if (!isLocked()) setRequirements(value);
        },
        onRightsChange: (value: SmartRemakeRights) => {
            if (!isLocked()) setRights(value);
        },
        onBudgetChange: (_value: SmartRemakeBudgetPolicy) => {
            if (!isLocked()) setBudget({ mode: "unlimited" });
        },
        onCharacterChange: (file: File | null) => {
            if (!isLocked() && (!file || validFile(file, "image"))) {
                setCharacterFile(file);
                setRights((current) => ({
                    ...invalidateRemakeMediaRights(current),
                    ...(current.character
                        ? { character: { ...current.character, declared: false } }
                        : {}),
                    ...(current.characterConsent
                        ? { characterConsent: { ...current.characterConsent, consented: false } }
                        : {}),
                }));
            }
        },
        saveContext,
        inspect,
        review,
        rightsReview,
        approve,
        restore,
        exportAssembly,
        deleteProject,
        prepareProject,
        restoreIntakeBinding,
        getIntakeBinding: () =>
            intakeAttempt.current?.projectId && intakeAttempt.current.mediaHashes
                ? {
                      projectId: intakeAttempt.current.projectId,
                      mediaHashes: intakeAttempt.current.mediaHashes,
                  }
                : null,
        hasCurrentIntake: (
            video: File | null,
            product: File | undefined,
            productUrl: string | undefined,
            duration: 8 | 12 | 16,
            additionalProducts: File[] = [],
        ) =>
            !video ||
            Boolean(
                intakeAttempt.current?.projectId === project?.id &&
                project?.targetDuration === duration &&
                intakeAttempt.current?.source === video &&
                intakeAttempt.current?.product === product &&
                sameProductAngles(intakeAttempt.current?.additionalProducts, additionalProducts) &&
                intakeAttempt.current?.productUrl === productUrl &&
                intakeAttempt.current?.character === characterFile,
            ),
        syncContext,
        applySnapshot: (snapshot: RemakeActionSnapshot) => {
            setRequirements(snapshot.requirements);
            setRights(remakeRightsInput(snapshot.rights));
            setBudget({ mode: "unlimited" });
        },
        loadContext,
    };
}
