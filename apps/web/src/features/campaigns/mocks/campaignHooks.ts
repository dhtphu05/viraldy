import type { Hook, HookType } from "@/features/campaigns/types/campaign";

// Hook templates. {product} and {problem} are simple frontend placeholders
// replaced by the mock AI. No network involved.

type Template = Omit<Hook, "id" | "sourceAngleId"> & { text: string };

export const hookTemplates: Record<HookType, Template[]> = {
    "Problem-first": [
        {
            text: "My {environment} looked clean until I opened this {problem_area}.",
            type: "Problem-first",
            creatorStyle: "Handheld POV",
            fit: "Strong fit",
        },
        {
            text: "I stopped trying to fix {problem} — until this.",
            type: "Problem-first",
            creatorStyle: "Talking head",
            fit: "Good test",
        },
    ],
    Curiosity: [
        {
            text: "I didn't know {product} could do this until I tried it in {environment}.",
            type: "Curiosity",
            creatorStyle: "POV",
            fit: "Good test",
        },
        {
            text: "This one thing changed my whole {routine}.",
            type: "Curiosity",
            creatorStyle: "Voiceover b-roll",
            fit: "Good test",
        },
    ],
    "Product reveal": [
        {
            text: "Watch what happens when I use {product} in {environment}.",
            type: "Product reveal",
            creatorStyle: "Demo",
            fit: "Strong fit",
        },
        {
            text: "I set up {product} in under a minute — here's the result.",
            type: "Product reveal",
            creatorStyle: "Timelapse",
            fit: "Strong fit",
        },
    ],
    "Social proof": [
        {
            text: "Everyone kept asking where I got {product}.",
            type: "Social proof",
            creatorStyle: "Vlog",
            fit: "Good test",
        },
        {
            text: "3 months in, this is the only {category} thing I still use.",
            type: "Social proof",
            creatorStyle: "Talking head",
            fit: "Good test",
        },
    ],
    Comparison: [
        {
            text: "I bought 4 viral {category} products so you don't have to.",
            type: "Comparison",
            creatorStyle: "Reviewer",
            fit: "Experimental",
            riskFlag: "Comparison claims should be demonstrable on camera",
        },
    ],
    "Emotional identity": [
        {
            text: "If you're the person who {identity_moment}, this is for you.",
            type: "Emotional identity",
            creatorStyle: "Talking head",
            fit: "Good test",
        },
    ],
    "Gift reaction": [
        {
            text: "My {gift_recipient} actually cried when she opened this.",
            type: "Gift reaction",
            creatorStyle: "Real reaction",
            fit: "Strong fit",
        },
        {
            text: "I finally found the {occasion} gift that isn't generic.",
            type: "Gift reaction",
            creatorStyle: "Reveal",
            fit: "Good test",
        },
    ],
};
