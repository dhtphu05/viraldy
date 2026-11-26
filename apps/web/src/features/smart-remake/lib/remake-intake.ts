import { MEDIA_RIGHTS_POLICY_VERSION } from "@/features/policies/media-rights-policy";
import { getRemakeAnalysisRecovery } from "./remake-analysis-recovery";
import type {
    SmartRemakeBudgetPolicy,
    SmartRemakeProject,
    SmartRemakeRequirements,
    SmartRemakeRights,
    SmartRemakeRightsDeclaration,
} from "@/shared/api/smart-remake";

export const DEFAULT_REMAKE_INTENT =
    "Làm theo cách quay, hành động và nhịp của video mẫu, thay bằng sản phẩm trong ảnh tải lên.";

export function emptyRemakeRights(): SmartRemakeRights {
    const declaration = (): SmartRemakeRightsDeclaration => ({
        basis: "attested",
        scope: "",
        declared: false,
        evidenceNote: "",
    });
    return { source: declaration(), product: declaration(), providerDisclosureAcknowledged: false };
}

export function normalizeRemakeRequirements(
    value: SmartRemakeRequirements,
): SmartRemakeRequirements {
    const lines = (items: string[]) => items.map((item) => item.trim()).filter(Boolean);
    return {
        intent: value.intent.trim() || DEFAULT_REMAKE_INTENT,
        keep: lines(value.keep),
        replace: lines(value.replace),
        forbid: lines(value.forbid),
        claims: lines(value.claims),
        requiresCharacter: value.requiresCharacter,
        characterReferencePolicy: value.characterReferencePolicy ?? "product_and_character",
    };
}

export function remakeBudgetInput(value: SmartRemakeBudgetPolicy): SmartRemakeBudgetPolicy {
    if (value.mode === "unlimited") return { mode: "unlimited" };
    return {
        ...(value.mode ? { mode: value.mode } : {}),
        capUsd: value.capUsd,
        maxAttempts: value.maxAttempts,
        maxDurationSeconds: value.maxDurationSeconds,
    };
}

export function remakeRightsInput(value: SmartRemakeRights): SmartRemakeRights {
    const declaration = (item: SmartRemakeRightsDeclaration): SmartRemakeRightsDeclaration => ({
        basis: item.basis,
        scope: item.scope.trim(),
        declared: item.declared,
        evidenceNote: item.evidenceNote.trim(),
        attribution: item.attribution?.trim() || null,
        revoked: item.revoked ?? false,
    });
    return {
        source: declaration(value.source),
        product: declaration(value.product),
        ...(value.character ? { character: declaration(value.character) } : {}),
        ...(value.characterConsent
            ? {
                  characterConsent: {
                      consented: value.characterConsent.consented,
                      scope: value.characterConsent.scope.trim(),
                      evidenceNote: value.characterConsent.evidenceNote.trim(),
                      revoked: value.characterConsent.revoked ?? false,
                  },
              }
            : {}),
        providerDisclosureAcknowledged: value.providerDisclosureAcknowledged,
        ...(value.attestation
            ? {
                  attestation: {
                      policyVersion: value.attestation.policyVersion,
                      accepted: value.attestation.accepted,
                      ...(value.attestation.revoked ? { revoked: true } : {}),
                  },
              }
            : {}),
    };
}

export function hasCurrentRemakeRightsAttestation(rights: SmartRemakeRights): boolean {
    return Boolean(
        rights.attestation?.policyVersion === MEDIA_RIGHTS_POLICY_VERSION &&
        rights.attestation.accepted &&
        !rights.attestation.revoked &&
        rights.source.declared &&
        !rights.source.revoked &&
        rights.product.declared &&
        !rights.product.revoked &&
        rights.providerDisclosureAcknowledged,
    );
}

export function confirmRemakeMediaRights(rights: SmartRemakeRights): SmartRemakeRights {
    const confirm = (value: SmartRemakeRightsDeclaration): SmartRemakeRightsDeclaration => ({
        ...value,
        basis: "attested",
        declared: true,
        revoked: false,
    });
    return {
        ...rights,
        source: confirm(rights.source),
        product: confirm(rights.product),
        providerDisclosureAcknowledged: true,
        attestation: { policyVersion: MEDIA_RIGHTS_POLICY_VERSION, accepted: true },
    };
}

export function invalidateRemakeMediaRights(rights: SmartRemakeRights): SmartRemakeRights {
    return {
        ...rights,
        source: { ...rights.source, declared: false },
        product: { ...rights.product, declared: false },
        providerDisclosureAcknowledged: false,
        attestation: undefined,
    };
}

export function getRemakeBudgetError(budget: SmartRemakeBudgetPolicy): string | null {
    if (budget.mode === "unlimited") return null;
    if (!/^(?:0|[1-9]\d{0,7})(?:\.\d{1,6})?$/.test(budget.capUsd) || Number(budget.capUsd) <= 0)
        return "Nhập trần USD lớn hơn 0; hệ thống không tự chọn ngân sách trả phí.";
    if (
        !Number.isInteger(budget.maxAttempts) ||
        budget.maxAttempts < 1 ||
        budget.maxAttempts > 1000 ||
        !Number.isInteger(budget.maxDurationSeconds) ||
        budget.maxDurationSeconds < 1 ||
        budget.maxDurationSeconds > 86400
    )
        return "Nhập giới hạn lượt và thời gian hợp lệ.";
    return null;
}

export function getRemakeIntakeError(
    requirements: SmartRemakeRequirements,
    rights: SmartRemakeRights,
    budget: SmartRemakeBudgetPolicy,
    hasCharacter: boolean,
): string | null {
    const budgetError = getRemakeBudgetError(budget);
    if (budgetError) return budgetError;
    return getRemakeRightsError(requirements, rights, hasCharacter);
}

export function getRemakeRightsError(
    requirements: SmartRemakeRequirements,
    rights: SmartRemakeRights,
    hasCharacter: boolean,
): string | null {
    const hasAttestation = hasCurrentRemakeRightsAttestation(rights);
    if (
        (rights.attestation ||
            rights.source.basis === "attested" ||
            rights.product.basis === "attested") &&
        !hasAttestation
    )
        return "Đọc chính sách và xác nhận quyền sử dụng tư liệu trước khi phân tích.";
    for (const role of [
        "source",
        "product",
        ...(hasCharacter ? ["character" as const] : []),
    ] as const) {
        const declaration = rights[role];
        if (
            !declaration?.declared ||
            declaration.revoked ||
            ((role === "character" || declaration.basis !== "attested" || !hasAttestation) &&
                (!declaration.scope.trim() || !declaration.evidenceNote.trim()))
        )
            return "Khai báo phạm vi và căn cứ quyền cho từng tư liệu trước khi phân tích.";
    }
    if (!rights.providerDisclosureAcknowledged)
        return "Xác nhận dữ liệu sẽ được gửi tới nhà cung cấp AI.";
    if (hasCharacter && !requirements.requiresCharacter)
        return "Xác nhận yêu cầu giữ nhân vật khi dự án có ảnh nhân vật gốc.";
    if (requirements.requiresCharacter && !hasCharacter)
        return "Thêm ảnh nhân vật có quyền sử dụng.";
    if (
        hasCharacter &&
        (!rights.characterConsent?.consented ||
            rights.characterConsent.revoked ||
            !rights.characterConsent.scope.trim() ||
            !rights.characterConsent.evidenceNote.trim())
    )
        return "Ghi căn cứ đồng ý và phạm vi sử dụng hình ảnh nhân vật.";
    return null;
}

export function getRemakeResumeStep(project: SmartRemakeProject): "prepare" | "plan" | "result" {
    if (getRemakeAnalysisRecovery(project)) return "prepare";
    if (project.phase === "intake") return "prepare";
    if (
        project.schemaVersion === 2 &&
        project.renderPlan &&
        !project.pendingOperation &&
        project.scenes.every((scene) => scene.versions.length === 0)
    )
        return "plan";
    return "result";
}
