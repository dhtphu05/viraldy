import type {
    Applicability,
    Confidence,
    CreativeDecision,
    EvidenceStatus,
    FixEventType,
    FixGroupKey,
    IntendedUse,
    ProfileSelectionMode,
    ScoreMode,
    ScoreProfileCode,
    TikTokComparisonFinding,
    TikTokCreativeUpgrade,
    TikTokDimension,
    TikTokEvidence,
    TikTokFinding,
    TikTokFixAction,
    TikTokSceneInventory,
    TikTokScoreComparison,
    TikTokScoreList,
    TikTokScoreProfile,
    TikTokScoreRun,
    TikTokStrength,
    TikTokVideoOperation,
} from "../types";

const PROFILE_LABELS: Record<ScoreProfileCode, string> = {
    general_tiktok_v1: "General TikTok",
    product_led_demo_v1: "Product-led demo",
    creator_review_v1: "Creator review",
    story_led_pov_v1: "Story-led POV",
    tutorial_howto_v1: "Tutorial / how-to",
    unboxing_reaction_v1: "Unboxing / reaction",
    comment_reply_faq_v1: "Comment reply / FAQ",
    offer_led_shop_v1: "Offer-led TikTok Shop",
};

const DIMENSION_LABELS: Record<string, string> = {
    hook_clarity: "Hook Clarity",
    product_visibility: "Product Visibility",
    demo_clarity: "Demo Clarity",
    proof_strength: "Proof Strength",
    creator_authenticity: "Creator Authenticity",
    offer_clarity: "Value & Offer Clarity",
    cta_readiness: "CTA Readiness",
    tiktok_native_fit: "TikTok-native Fit",
    claim_safety: "Claim Safety",
};

function record(value: unknown): Record<string, unknown> {
    return value !== null && typeof value === "object" && !Array.isArray(value)
        ? (value as Record<string, unknown>)
        : {};
}

function list(value: unknown): unknown[] {
    return Array.isArray(value) ? value : [];
}

function strings(value: unknown): string[] {
    return list(value).filter((item): item is string => typeof item === "string");
}

function text(value: unknown, fallback = ""): string {
    return typeof value === "string" ? value : fallback;
}

function nullableText(value: unknown): string | null {
    const result = text(value).trim();
    return result ? result : null;
}

function numberValue(value: unknown): number | null {
    if (typeof value === "number" && Number.isFinite(value)) return value;
    if (typeof value === "string" && value.trim() && Number.isFinite(Number(value))) {
        return Number(value);
    }
    return null;
}

function booleanValue(value: unknown): boolean | null {
    return typeof value === "boolean" ? value : null;
}

function range(value: unknown): [number, number] | null {
    if (!Array.isArray(value) || value.length < 2) return null;
    const start = numberValue(value[0]);
    const end = numberValue(value[1]);
    if (start === null || end === null || start < 0 || end < start) return null;
    return [start, end];
}

function ranges(value: unknown): Array<[number, number]> {
    return list(value)
        .map(range)
        .filter((item): item is [number, number] => item !== null);
}

function confidence(value: unknown): Confidence {
    return value === "high" || value === "medium" ? value : "low";
}

function applicability(value: unknown, fallback: Applicability = "unknown"): Applicability {
    return value === "applicable" || value === "not_applicable" || value === "unknown"
        ? value
        : fallback;
}

function evidenceStatus(value: unknown, fallback: EvidenceStatus = "insufficient"): EvidenceStatus {
    return value === "sufficient" || value === "partial" || value === "insufficient"
        ? value
        : fallback;
}

function scoreMode(value: unknown): ScoreMode {
    return value === "product_aware" || value === "usage_aware" ? value : "quick";
}

function intendedUse(value: unknown): IntendedUse {
    return value === "tiktok_shop_affiliate" ||
        value === "ugc_paid_candidate" ||
        value === "spark_candidate"
        ? value
        : "tiktok_organic";
}

function profileCode(value: unknown): ScoreProfileCode {
    return value && Object.hasOwn(PROFILE_LABELS, String(value))
        ? (value as ScoreProfileCode)
        : "general_tiktok_v1";
}

function selectionMode(value: unknown): ProfileSelectionMode {
    return value === "model_suggested" ||
        value === "model_suggested_user_confirmed" ||
        value === "inherited" ||
        value === "user_overridden"
        ? value
        : "user_selected";
}

function decision(value: unknown): CreativeDecision {
    if (
        value === "request_better_media" ||
        value === "blocked" ||
        value === "revise" ||
        value === "usable_with_improvements" ||
        value === "structurally_ready"
    ) {
        return value;
    }
    if (value === "fix" || value === "needs_revision") return "revise";
    if (value === "proceed" || value === "ready") return "structurally_ready";
    return "pending";
}

function normalizeDimension(value: unknown, fallbackCode = "unknown"): TikTokDimension {
    const raw = record(value);
    const source: Record<string, unknown> = { ...raw, ...record(raw.result_json) };
    const code = text(source.code, fallbackCode);
    const evidenceIds = strings(source.evidence_ids ?? source.evidence_ids_json);
    const rawScore = numberValue(source.score);
    const legacyMissingProductCheck =
        ["offer_clarity", "claim_safety"].includes(code) && rawScore === 0 && !evidenceIds.length;
    const normalizedApplicability = applicability(
        source.applicability,
        legacyMissingProductCheck ? "not_applicable" : "applicable",
    );
    const normalizedEvidenceStatus = evidenceStatus(
        source.evidence_status,
        evidenceIds.length ? "sufficient" : "insufficient",
    );
    const responsiblyScoreable =
        normalizedApplicability === "applicable" && normalizedEvidenceStatus !== "insufficient";

    return {
        code,
        label: text(source.label, DIMENSION_LABELS[code] ?? humanize(code)),
        score: responsiblyScoreable ? rawScore : null,
        applicability: normalizedApplicability,
        evidenceStatus: normalizedEvidenceStatus,
        confidence: confidence(source.confidence),
        reason: text(source.reason, "This dimension has not been evaluated yet."),
        positiveSignals: strings(source.positive_signals ?? source.positive_signals_json),
        missingSignals: strings(source.missing_signals ?? source.missing_signals_json),
        uncertainty: strings(source.uncertainty ?? source.uncertainty_json),
        evidenceIds,
        ruleCodes: strings(source.contributing_rule_codes ?? source.contributing_rule_codes_json),
    };
}

function normalizeFinding(value: unknown, index: number): TikTokFinding {
    const raw = record(value);
    const source: Record<string, unknown> = { ...raw, ...record(raw.finding_json) };
    const code = text(source.code, `finding-${index + 1}`);
    return {
        id: text(source.id, code),
        code,
        ruleCode: nullableText(source.rule_code),
        ruleClass: nullableText(source.rule_class),
        sourceDimension: text(source.source_dimension, "general"),
        severity: ["hard", "high", "medium", "low", "info"].includes(text(source.severity))
            ? (source.severity as TikTokFinding["severity"])
            : "medium",
        priority: ["P0", "P1", "P2", "P3"].includes(text(source.priority))
            ? (source.priority as TikTokFinding["priority"])
            : "P2",
        applicability: applicability(source.applicability, "applicable"),
        evidenceStatus: evidenceStatus(
            source.evidence_status,
            strings(source.evidence_ids ?? source.evidence_ids_json).length
                ? "sufficient"
                : "insufficient",
        ),
        title: text(source.title, text(source.message, humanize(code))),
        reason: text(source.reason, text(source.why, "Review the linked evidence.")),
        expected: record(source.expected ?? source.expected_json),
        observed: record(source.observed ?? source.observed_json),
        targetTimeRangeMs: range(source.target_time_range_ms ?? source.target_time_range_ms_json),
        evidenceIds: strings(source.evidence_ids ?? source.evidence_ids_json),
        uncertainty: strings(source.uncertainty ?? source.uncertainty_json),
        requiresSellerTruth: source.requires_seller_truth === true,
        canBeResolvedByEdit: booleanValue(source.can_be_resolved_by_edit),
        requiresPhysicalReshoot: booleanValue(source.requires_physical_reshoot),
    };
}

function fixGroup(fixType: string, owner: string, reshootRequired: boolean): FixGroupKey {
    if (fixType === "request_better_media") return "better_media";
    if (fixType === "confirm_seller_input" || fixType === "confirm_rights" || owner === "seller") {
        return "seller";
    }
    if (reshootRequired || fixType === "reshoot_scene" || fixType === "add_missing_scene") {
        return "reshoot";
    }
    return "edit";
}

function normalizeOperation(value: unknown): TikTokVideoOperation {
    const source = record(value);
    return {
        operation: text(source.operation, "editor_review"),
        sourceSceneId: nullableText(source.source_scene_id),
        sourceRangeMs: range(source.source_range_ms),
        targetStartMs: numberValue(source.target_start_ms),
        targetDurationMs: numberValue(source.target_duration_ms),
        textValue: nullableText(source.text_value),
        evidenceIds: strings(source.evidence_ids),
        feasibility: text(source.feasibility, "requires_editor_confirmation"),
    };
}

export function normalizeTikTokFix(value: unknown, index = 0): TikTokFixAction {
    const raw = record(value);
    const source: Record<string, unknown> = { ...raw, ...record(raw.action_json) };
    const code = text(source.code, `fix-${index + 1}`);
    const instruction = text(source.instruction);
    const title = text(source.title, instruction || humanize(code));
    const fixType = text(source.fix_type, "edit_existing_footage");
    const owner = ["seller", "creator", "editor", "compliance_reviewer"].includes(
        text(source.owner_role),
    )
        ? (source.owner_role as TikTokFixAction["ownerRole"])
        : "editor";
    const reshootRequired = source.reshoot_required === true;
    const latestEvent = text(
        source.latest_event_type,
        text(record(source.latest_event).event_type, text(source.current_action_state)),
    );
    return {
        id: text(source.id, code),
        code,
        sourceFindingId: text(source.source_finding_id),
        sourceFindingCode: text(source.source_finding_code, code),
        recommendationClass:
            source.recommendation_class === "high_priority_improvement"
                ? "high_priority_improvement"
                : "required_fix",
        basis: text(source.basis, "video_diagnosis"),
        priority: ["P0", "P1", "P2"].includes(text(source.priority))
            ? (source.priority as TikTokFixAction["priority"])
            : "P1",
        severity: ["hard", "high", "medium", "low"].includes(text(source.severity))
            ? (source.severity as TikTokFixAction["severity"])
            : "medium",
        sourceDimension: text(source.source_dimension, "general"),
        ownerRole: owner,
        fixType,
        group: fixGroup(fixType, owner, reshootRequired),
        title,
        whyItMatters: text(
            source.why_it_matters,
            text(source.why, "Apply this change, then verify it in the next revision."),
        ),
        expected: record(source.expected ?? source.expected_json),
        observed: record(source.observed ?? source.observed_json),
        evidenceIds: strings(source.evidence_ids ?? source.evidence_ids_json),
        targetTimeRangeMs: range(source.target_time_range_ms ?? source.target_time_range_ms_json),
        operations: list(source.video_operations ?? source.video_operations_json).map(
            normalizeOperation,
        ),
        instructions: strings(source.instructions ?? source.instructions_json).length
            ? strings(source.instructions ?? source.instructions_json)
            : instruction
              ? [instruction]
              : [],
        strengthsToPreserve: strings(
            source.strengths_to_preserve ?? source.strengths_to_preserve_json,
        ),
        requiredInputs: strings(source.required_inputs ?? source.required_inputs_json),
        effort: ["low", "medium", "high"].includes(text(source.estimated_effort))
            ? (source.estimated_effort as TikTokFixAction["effort"])
            : "medium",
        reshootRequired,
        completionCriteria: strings(source.completion_criteria ?? source.completion_criteria_json),
        verificationMethod: text(
            source.verification_method,
            "Review the corresponding evidence after uploading a revision.",
        ),
        latestEvent: [
            "viewed",
            "accepted",
            "rejected",
            "sent_to_creator",
            "sent_to_editor",
            "marked_completed",
            "verified_after_revision",
        ].includes(latestEvent)
            ? (latestEvent as FixEventType)
            : null,
    };
}

function normalizeStrength(value: unknown): TikTokStrength {
    const source = record(value);
    const title = text(source.title, text(source.message, "Strength to preserve"));
    return {
        code: text(source.code, slug(title)),
        title,
        sourceDimension: text(source.source_dimension, "general"),
        evidenceIds: strings(source.evidence_ids),
    };
}

function normalizeEvidence(value: unknown): TikTokEvidence {
    const source = record(value);
    const timeRangeObject = record(source.time_range);
    const timeRange =
        range(source.time_range_ms) ?? range([timeRangeObject.start_ms, timeRangeObject.end_ms]);
    const summary = record(source.value_summary_json);
    const numericConfidence = numberValue(source.confidence);
    const sourceType = text(source.source_type, text(source.evidence_type, "evidence"));
    return {
        id: text(source.id),
        sourceType,
        startMs: numberValue(source.start_ms) ?? timeRange?.[0] ?? null,
        endMs: numberValue(source.end_ms) ?? timeRange?.[1] ?? null,
        summary: text(
            source.summary ??
                summary.summary ??
                summary.description ??
                summary.action ??
                summary.visual_description ??
                summary.text ??
                summary.proof_type,
            text(source.description, fallbackEvidenceSummary(sourceType)),
        ),
        transcript: nullableText(
            source.transcript ??
                source.transcript_text ??
                source.spoken_text ??
                summary.transcript ??
                summary.spoken_text,
        ),
        ocrText: nullableText(
            source.ocr_text ?? source.overlay_text ?? summary.ocr_text ?? summary.overlay_text,
        ),
        frameUrl: nullableText(source.frame_url ?? source.preview_url ?? source.thumbnail_url),
        confidence:
            source.confidence === "high" ||
            source.confidence === "medium" ||
            source.confidence === "low"
                ? source.confidence
                : numericConfidence === null
                  ? null
                  : numericConfidence >= 0.8
                    ? "high"
                    : numericConfidence >= 0.5
                      ? "medium"
                      : "low",
    };
}

function fallbackEvidenceSummary(sourceType: string): string {
    if (sourceType.includes("product_appearance")) return "Product appearance";
    if (sourceType.includes("product_visibility")) return "Product visibility summary";
    if (sourceType.includes("demo_step")) return "Demo step";
    if (sourceType.includes("demo_summary")) return "Demo summary";
    if (sourceType.includes("proof")) return "Proof moment";
    if (sourceType.includes("hook")) return "Opening hook";
    if (sourceType.includes("cta")) return "CTA cue";
    if (sourceType.includes("claim")) return "Claim safety cue";
    if (sourceType.includes("platform")) return "Platform/native cue";
    if (sourceType.includes("editing")) return "Editing cue";
    if (sourceType.includes("creator")) return "Creator delivery cue";
    if (sourceType.includes("transcript")) return "Transcript segment";
    if (sourceType.includes("on_screen_text")) return "On-screen text";
    return "Evidence item";
}

function normalizeSceneInventory(value: unknown): TikTokSceneInventory | null {
    const source = record(value);
    if (!Object.keys(source).length) return null;
    return {
        assetVersionId: text(source.asset_version_id),
        durationMs: numberValue(source.duration_ms),
        audioAvailable: booleanValue(source.audio_available),
        coverageStatus: evidenceStatus(source.coverage_status),
        confidence: confidence(source.overall_confidence),
        scenes: list(source.scenes).map((item, index) => {
            const scene = record(item);
            return {
                id: text(scene.scene_id, `scene-${index + 1}`),
                startMs: numberValue(scene.start_ms) ?? 0,
                endMs: numberValue(scene.end_ms) ?? 0,
                summary: text(scene.summary, "Observed scene"),
                shotType: nullableText(scene.shot_type),
                productVisible: booleanValue(scene.product_visible),
                productMatchConfidence: numberValue(scene.product_match_confidence),
                productVisibilityQuality: nullableText(scene.product_visibility_quality),
                spokenText: nullableText(scene.spoken_text),
                overlayTexts: strings(scene.overlay_texts),
                demoStep: nullableText(scene.demo_step),
                proofRole: nullableText(scene.proof_role),
                creatorPresent: booleanValue(scene.creator_present),
                visualQuality: text(scene.visual_quality, "unknown"),
                continuityGroupId: nullableText(scene.continuity_group_id),
                reusableForEdit: scene.reusable_for_edit === true,
                evidenceIds: strings(scene.evidence_ids),
            };
        }),
        productRanges: ranges(source.product_appearance_ranges),
        ctaRanges: ranges(source.cta_ranges),
        disclosureRanges: ranges(source.disclosure_ranges),
        safeZoneObservations: list(source.safe_zone_observations).flatMap((item) => {
            const observation = record(item);
            const observationRange = range(observation.time_range_ms);
            return observationRange
                ? [
                      {
                          range: observationRange,
                          status: text(observation.status, "unknown"),
                          reason: text(observation.reason),
                          evidenceIds: strings(observation.evidence_ids),
                      },
                  ]
                : [];
        }),
        evidenceIds: strings(source.evidence_ids),
    };
}

function normalizeUpgrade(value: unknown, index: number): TikTokCreativeUpgrade {
    const source = record(value);
    return {
        id: text(source.id, `upgrade-${index + 1}`),
        title: text(source.title, "Creative Direction upgrade"),
        whyItFits: text(source.why_it_fits),
        affectsScore: false,
        keep: strings(source.keep_from_current_video),
        change: strings(source.change_in_current_video),
        additionalFootage: strings(source.additional_footage_needed),
        claimGuardrails: strings(source.claim_guardrails),
        expectedLearning: nullableText(source.expected_learning),
    };
}

export function normalizeTikTokScoreRun(value: unknown): TikTokScoreRun {
    const outer = record(value);
    const base = record(outer.score_run ?? outer.run ?? outer);
    const result = record(base.result ?? base.result_json ?? base.score_result_json);
    const source: Record<string, unknown> = {
        ...base,
        ...result,
        dimensions: outer.dimensions ?? result.dimensions,
        findings: outer.findings ?? result.findings,
        fix_actions: outer.fix_actions ?? result.fix_actions ?? result.required_fixes,
        evidence: outer.evidence ?? result.evidence,
        job_id: record(outer.job).id ?? outer.job_id ?? base.processing_job_id,
        asset_name: outer.asset_name ?? outer.asset_filename ?? base.asset_name,
        product_name: outer.product_name ?? base.product_name,
    };
    const rawProfile = record(source.profile_selection);
    const code = profileCode(rawProfile.profile_code ?? source.score_profile);
    const dimensionSource = source.dimensions ?? source.dimension_scores_json;
    const dimensions = Array.isArray(dimensionSource)
        ? dimensionSource.map((item) => normalizeDimension(item))
        : Object.entries(record(dimensionSource)).map(([key, item]) =>
              normalizeDimension(item, key),
          );
    const findingSource = source.findings ?? source.findings_json ?? source.blockers_json;
    const fixSource =
        source.fix_actions ?? source.required_fixes ?? source.fixes ?? source.fixes_json ?? [];
    const inventory = normalizeSceneInventory(
        source.scene_inventory ?? source.scene_inventory_json,
    );
    const status = text(source.status, text(source.run_status, "queued"));
    const media = record(source.playback);
    const mediaUrl = nullableText(media.video_url ?? source.video_url ?? source.media_url);
    const normalizedDecision = decision(
        source.creative_structure_decision ?? source.decision ?? source.action_label,
    );

    return {
        id: text(source.id, text(outer.run_id)),
        workspaceId: nullableText(source.workspace_id),
        assetId: nullableText(source.asset_id),
        assetVersionId: text(source.asset_version_id),
        assetName: text(
            source.asset_name ?? source.original_filename ?? record(source.asset).name,
            "Untitled video",
        ),
        productId: nullableText(source.product_id),
        productName: nullableText(source.product_name ?? record(source.product).name),
        status,
        currentStage: text(source.current_stage, status),
        jobId: nullableText(source.processing_job_id ?? source.job_id ?? record(outer.job).id),
        score: numberValue(source.overall_score ?? source.structural_score),
        confidence: confidence(source.overall_confidence ?? source.confidence),
        decision: normalizedDecision,
        paidUseRightsStatus: text(source.paid_use_rights_status, "not_evaluated"),
        finalPaidReadiness: text(source.final_paid_readiness, "not_applicable"),
        scoreMode: scoreMode(source.score_mode),
        intendedUse: intendedUse(source.intended_use),
        profile: {
            code,
            label: text(rawProfile.label, PROFILE_LABELS[code]),
            selectionMode: selectionMode(
                rawProfile.selection_mode ?? source.profile_selection_mode,
            ),
            confidence: numberValue(rawProfile.confidence ?? source.profile_selection_confidence),
            reason: nullableText(rawProfile.reason ?? source.profile_selection_reason),
            alternatives: strings(
                rawProfile.alternative_profiles ?? source.alternative_profiles_json,
            ).map(profileCode),
            evidenceIds: strings(rawProfile.evidence_ids ?? source.profile_evidence_ids_json),
        },
        dimensions,
        findings: list(findingSource).map(normalizeFinding),
        fixes: list(fixSource).map(normalizeTikTokFix),
        strengths: list(source.strengths ?? source.strengths_json).map(normalizeStrength),
        evidence: list(source.evidence ?? source.evidence_items ?? source.evidence_json)
            .map(normalizeEvidence)
            .filter((item) => item.id),
        sceneInventory: inventory,
        optionalUpgrades: list(source.optional_upgrades ?? source.creative_upgrades_json).map(
            normalizeUpgrade,
        ),
        uncertainty: strings(source.uncertainty),
        mediaUrl,
        mediaExpiresAt: nullableText(media.expires_at ?? source.media_expires_at),
        partialEvidence:
            status === "partial_evidence" ||
            inventory?.coverageStatus === "partial" ||
            inventory?.coverageStatus === "insufficient",
        revisionCount: numberValue(source.revision_count) ?? 0,
        comparisonIds: strings(source.comparison_ids),
        parentScoreRunId: nullableText(source.parent_score_run_id),
        failureCode: nullableText(source.failure_code ?? source.error_code),
        failureMessage: nullableText(source.failure_message ?? source.error_message),
        createdAt: nullableText(source.created_at),
        updatedAt: nullableText(source.updated_at ?? source.completed_at ?? source.created_at),
        completedAt: nullableText(source.completed_at),
    };
}

export function normalizeTikTokScoreList(value: unknown): TikTokScoreList {
    const source = record(value);
    const rawItems = Array.isArray(value) ? value : list(source.items ?? source.results);
    return {
        items: rawItems.map(normalizeTikTokScoreRun),
        total: numberValue(source.total) ?? rawItems.length,
        limit: numberValue(source.limit) ?? rawItems.length,
        offset: numberValue(source.offset) ?? 0,
    };
}

export function normalizeTikTokFixList(value: unknown): TikTokFixAction[] {
    const source = record(value);
    return list(Array.isArray(value) ? value : (source.items ?? source.fixes)).map(
        normalizeTikTokFix,
    );
}

export function normalizeTikTokScoreProfiles(value: unknown): TikTokScoreProfile[] {
    const source = record(value);
    return list(Array.isArray(value) ? value : source.items).map((item) => {
        const profile = record(item);
        const code = profileCode(profile.code ?? profile.profile_code);
        return {
            code,
            label: text(profile.label, PROFILE_LABELS[code]),
            version: numberValue(profile.version ?? profile.profile_version) ?? 1,
            description: text(profile.description),
            isDefault: profile.is_default === true || code === "general_tiktok_v1",
            suggested: profile.suggested === true || profile.is_suggested === true,
            suggestionConfidence: numberValue(profile.suggestion_confidence ?? profile.confidence),
            suggestionReason: nullableText(profile.suggestion_reason ?? profile.reason),
        };
    });
}

function normalizeComparisonFinding(value: unknown): TikTokComparisonFinding {
    const source = record(value);
    const code = text(source.code, text(source.finding_code, "finding"));
    return {
        code,
        title: text(source.title, humanize(code)),
        beforeEvidenceIds: strings(source.before_evidence_ids),
        afterEvidenceIds: strings(source.after_evidence_ids),
    };
}

export function normalizeTikTokScoreComparison(value: unknown): TikTokScoreComparison {
    const outer = record(value);
    const nested = record(outer.comparison_json ?? outer.comparison);
    const source: Record<string, unknown> = { ...outer, ...nested };
    const beforeScore = numberValue(source.before_score);
    const afterScore = numberValue(source.after_score);
    const resolved = source.resolved_blockers ?? source.resolved_blockers_json;
    const unresolved = source.unresolved_blockers ?? source.unresolved_blockers_json;
    const regressions = source.new_regressions ?? source.new_regressions_json;
    const dimensionChanges = source.dimension_changes ?? source.dimension_changes_json;
    const evidence = source.evidence_before_after ?? source.evidence_before_after_json;
    const strengths = source.strengths_preserved ?? source.strengths_preserved_json;
    const actions = source.actions_verified ?? source.actions_verified_json;
    return {
        id: text(source.id, text(source.comparison_id)),
        beforeScoreRunId: nullableText(source.before_score_run_id),
        afterScoreRunId: nullableText(source.after_score_run_id),
        beforeAssetVersionId: text(source.before_asset_version_id),
        afterAssetVersionId: text(source.after_asset_version_id),
        beforeScore,
        afterScore,
        scoreDelta: beforeScore !== null && afterScore !== null ? afterScore - beforeScore : null,
        status: text(source.status, "completed"),
        resolved: list(resolved).map(normalizeComparisonFinding),
        unresolved: list(unresolved).map(normalizeComparisonFinding),
        regressions: list(regressions).map(normalizeComparisonFinding),
        dimensions: list(dimensionChanges).map((item) => {
            const change = record(item);
            return {
                code: text(change.code),
                beforeScore: numberValue(change.before_score),
                afterScore: numberValue(change.after_score),
                beforeApplicability: change.before_applicability
                    ? applicability(change.before_applicability)
                    : null,
                afterApplicability: change.after_applicability
                    ? applicability(change.after_applicability)
                    : null,
            };
        }),
        evidence: list(evidence).map((item) => {
            const comparison = record(item);
            return {
                subjectCode: text(comparison.subject_code),
                beforeEvidenceIds: strings(comparison.before_evidence_ids),
                afterEvidenceIds: strings(comparison.after_evidence_ids),
            };
        }),
        strengths: list(strengths).map(normalizeStrength),
        actions: list(actions).map((item) => {
            const action = record(item);
            return {
                actionId: text(action.action_id),
                actionCode: text(action.action_code),
                sourceFindingCode: text(action.source_finding_code),
                status:
                    action.status === "verified" || action.status === "not_verified"
                        ? action.status
                        : "not_evaluated",
                before: record(action.before),
                after: record(action.after),
                beforeEvidenceIds: strings(action.evidence_before_ids),
                afterEvidenceIds: strings(action.evidence_after_ids),
                reason: text(action.reason),
            };
        }),
        finalNextAction: text(source.final_next_action, "review_unresolved_blockers"),
        likeForLike: source.like_for_like !== false,
        warning: nullableText(source.comparison_warning),
    };
}

function humanize(value: string): string {
    return value
        .replace(/_v\d+$/, "")
        .replace(/[_-]+/g, " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function slug(value: string): string {
    return value
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/(^-|-$)/g, "");
}
