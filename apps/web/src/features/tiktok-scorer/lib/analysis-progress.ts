export type AnalysisSignal = {
    label: string;
    detail: string;
};

export type AnalysisProgressView = {
    percent: number;
    title: string;
    description: string;
    coverageLabel: string;
    confirmed: AnalysisSignal[];
    active: AnalysisSignal[];
};

const STAGE_ORDER = [
    "queued",
    "loading_job",
    "extracting_media",
    "building_evidence",
    "building_scene_inventory",
    "scoring",
    "compiling_fixes",
    "enriching_direction",
    "validating_output",
    "persisting",
    "completed",
] as const;

const STAGE_COPY: Record<string, Pick<AnalysisProgressView, "title" | "description">> = {
    queued: {
        title: "Waiting to begin",
        description: "Your immutable video version is ready and queued for analysis.",
    },
    loading_job: {
        title: "Preparing the analysis",
        description: "Loading the selected video, score profile, and product context.",
    },
    extracting_media: {
        title: "Preparing video and audio",
        description: "Reading duration, format, audio availability, and frames for review.",
    },
    building_evidence: {
        title: "Reading visual, speech, and text evidence",
        description: "Reviewing what is actually shown, said, and overlaid across the video.",
    },
    building_scene_inventory: {
        title: "Mapping the scene sequence",
        description:
            "Organizing evidence into reusable scenes, demo steps, proof, and CTA moments.",
    },
    scoring: {
        title: "Evaluating creative structure",
        description: "Applying the selected deterministic rubric to the verified evidence.",
    },
    compiling_fixes: {
        title: "Building the fix plan",
        description: "Turning findings into edit, reshoot, and seller-confirmation actions.",
    },
    enriching_direction: {
        title: "Checking optional creative direction",
        description: "Adding non-scoring enhancements without changing the structural verdict.",
    },
    validating_output: {
        title: "Validating every evidence link",
        description: "Checking that scores, findings, and actions trace back to real evidence.",
    },
    persisting: {
        title: "Saving the result",
        description: "Persisting the immutable score, evidence, and revision-ready action plan.",
    },
    completed: {
        title: "Analysis ready",
        description: "The evidence-grounded result is ready to review.",
    },
};

export function buildAnalysisProgress(
    stage: string | null | undefined,
    serverProgress: number | null | undefined,
    durationMs: number | null,
): AnalysisProgressView {
    const normalizedStage = normalizeStage(stage);
    const currentIndex = Math.max(0, STAGE_ORDER.indexOf(normalizedStage));
    const isAfter = (target: (typeof STAGE_ORDER)[number]) =>
        currentIndex > STAGE_ORDER.indexOf(target);

    const confirmed: AnalysisSignal[] = [];
    if (isAfter("loading_job")) {
        confirmed.push({
            label: "Context locked",
            detail: "Video version, intended use, and score profile are fixed for this run.",
        });
    }
    if (isAfter("extracting_media")) {
        confirmed.push({
            label: "Media prepared",
            detail: durationMs
                ? `${formatMs(durationMs)} of video is ready to inspect.`
                : "Video and audio streams are ready to inspect.",
        });
    }
    if (isAfter("building_evidence")) {
        confirmed.push({
            label: "Evidence captured",
            detail: "Visuals, speech, on-screen text, and product moments have been reviewed.",
        });
    }
    if (isAfter("building_scene_inventory")) {
        confirmed.push({
            label: "Scene sequence mapped",
            detail: "Reusable shots, demo steps, proof, CTA, and disclosure ranges are organized.",
        });
    }

    return {
        percent: Math.min(100, Math.max(0, serverProgress ?? 0)),
        ...(STAGE_COPY[normalizedStage] ?? STAGE_COPY.loading_job),
        coverageLabel: durationMs
            ? `Reviewing the full 0:00–${formatMs(durationMs)} video`
            : "Full-video review in progress",
        confirmed,
        active: activeSignals(normalizedStage),
    };
}

function normalizeStage(stage: string | null | undefined): (typeof STAGE_ORDER)[number] {
    if (stage === "running" || stage === "processing") return "extracting_media";
    if (stage === "succeeded") return "completed";
    return STAGE_ORDER.includes(stage as (typeof STAGE_ORDER)[number])
        ? (stage as (typeof STAGE_ORDER)[number])
        : "loading_job";
}

function activeSignals(stage: (typeof STAGE_ORDER)[number]): AnalysisSignal[] {
    if (stage === "building_evidence") {
        return [
            { label: "Product visibility", detail: "Where and how clearly the product appears" },
            { label: "Spoken claims", detail: "Claims, voiceover, and creator speech" },
            { label: "On-screen text", detail: "OCR, overlays, CTA, and disclosures" },
            { label: "Demo actions", detail: "Physical steps, proof, and before/after moments" },
        ];
    }
    if (stage === "building_scene_inventory") {
        return [
            { label: "Scene boundaries", detail: "Where each usable shot starts and ends" },
            { label: "Narrative order", detail: "Hook, demonstration, proof, and CTA sequence" },
            { label: "Reusable footage", detail: "Moments that can be repaired in the edit" },
        ];
    }
    if (stage === "scoring") {
        return [
            { label: "Hook clarity", detail: "How quickly the viewer understands the premise" },
            { label: "Demo and proof", detail: "Whether the product mechanism is evidenced" },
            { label: "CTA readiness", detail: "Whether the next action is clear for this use" },
        ];
    }
    if (stage === "compiling_fixes") {
        return [
            { label: "Edit repairs", detail: "Changes possible with existing footage" },
            { label: "Reshoot needs", detail: "Missing physical evidence that must be filmed" },
            { label: "Completion checks", detail: "How each recommended change will be verified" },
        ];
    }
    return [];
}

function formatMs(value: number): string {
    const totalSeconds = Math.max(0, Math.round(value / 1_000));
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${String(seconds).padStart(2, "0")}`;
}
