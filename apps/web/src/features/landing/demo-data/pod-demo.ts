export interface ExpectedObservedItem {
    id: string;
    requirement: string;
    observed: string;
    status: string;
    confidence: string;
    evidence: string;
    action: string;
}

export const podChecks: ExpectedObservedItem[] = [
    {
        id: "pod-1",
        requirement: "Approved personalization: 'Milo'",
        observed: "Video shows crewneck printed with 'Miles'",
        status: "missing / fail",
        confidence: "high",
        evidence: "OCR detected 'Miles' text on apparel chest at 0:07.2",
        action: "Reshoot required: Creator must show correct personalization on crewneck.",
    },
    {
        id: "pod-2",
        requirement: "Dog mom identity hook (strategic fit)",
        observed: "Creator spoken hook: 'Tell me you are a dog mom without telling me.'",
        status: "passed / met",
        confidence: "high",
        evidence: "ASR matching hook at 0:00.5",
        action: "No action. Deliver remains natural.",
    },
    {
        id: "pod-3",
        requirement: "Emotional gifting payoff scene",
        observed: "Video shows friend's reaction opening the box",
        status: "passed / met",
        confidence: "medium",
        evidence: "Face sentiment analysis indicates high positive reaction at 0:11.4",
        action: "No action. Preserve emotional delivery.",
    },
    {
        id: "pod-4",
        requirement: "Prohibited claim check",
        observed: "No claims about 'guaranteed delivery date' or 'perfect gift for everyone'",
        status: "passed / met",
        confidence: "high",
        evidence: "Fulfillment claims evaluation passed",
        action: "No action.",
    },
];
