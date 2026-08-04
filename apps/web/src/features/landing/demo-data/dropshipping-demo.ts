export interface DropshippingCheckItem {
    id: string;
    requirement: string;
    observed: string;
    status: string;
    evidence: string;
    action: string;
}

export const dropshippingChecks: DropshippingCheckItem[] = [
    {
        id: "drop-1",
        requirement: "Supported sealing mechanism only",
        observed: "Spoken line: 'This makes every bag completely airtight.'",
        status: "blocked / prohibited claim",
        evidence: "ASR detected 'completely airtight' at 0:08.9",
        action: "Edit required: Replace spoken line. Do not make universal airtight claims.",
    },
    {
        id: "drop-2",
        requirement: "Avoid instant food preservation claims",
        observed: "No claims about keeping food fresh forever",
        status: "passed",
        evidence: "Claims evaluation passed",
        action: "No action.",
    },
    {
        id: "drop-3",
        requirement: "One-handed operation demo",
        observed: "Creator performs clear one-handed sealer demonstration",
        status: "passed",
        evidence: "Video frame analysis confirmed one-handed use at 0:03.5",
        action: "Preserve scene.",
    },
];
