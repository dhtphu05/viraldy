export interface CreativeDirection {
    number: string;
    title: string;
    buyer: string;
    opening: string;
    demo: string;
    proof: string;
    creatorStyle: string;
    tests: string;
    tag: string;
    conceptId: string;
}

export interface StoryboardShot {
    time: string;
    action: string;
    type: "hook" | "product" | "demo" | "proof" | "reaction" | "cta";
    details?: string;
}

export interface TikTokFix {
    id: string;
    title: string;
    expected: string;
    observed: string;
    action: string;
    needsReshoot: boolean;
    type: "blocker" | "warn" | "info";
}

export const steamerDirections: CreativeDirection[] = [
    {
        number: "01",
        conceptId: "late_for_class",
        title: "Late for Class Rescue",
        buyer: "College student in a dorm",
        opening: "Ten minutes before class, wrinkled shirt out of a backpack",
        demo: "Steam applied to wrinkled fabric area",
        proof: "Same-fabric before/after comparison",
        creatorStyle: "US college lifestyle creator",
        tests: "Whether time pressure urgency drives higher purchase intent than generic features.",
        tag: "Best Fit",
    },
    {
        number: "02",
        conceptId: "carry_on_rescue",
        title: "Carry-On Clothing Rescue",
        buyer: "Frequent traveler using carry-on",
        opening: "Wrinkled clothes from unpacking in a hotel room",
        demo: "Compact travel iron/steamer demonstration",
        proof: "Wrinkle removal from travel garments",
        creatorStyle: "US travel creator",
        tests: "Whether traveler convenience and hotel iron avoidance resonate better.",
        tag: "Alt Angle",
    },
    {
        number: "03",
        conceptId: "small_space_alternative",
        title: "Small-Space Iron Alternative",
        buyer: "Apartment renter with limited storage",
        opening: "Bulky ironing board setup frustration",
        demo: "Desk drawer storage + handheld steamer setup",
        proof: "Space savings and rapid handheld result",
        creatorStyle: "Small-apartment lifestyle creator",
        tests: "Whether saving apartment storage space beats travel convenience.",
        tag: "Contrast",
    },
];

export const steamerStoryboard: StoryboardShot[] = [
    {
        time: "0:00 - 0:02",
        action: "Establish deadline pressure: student getting ready for class realizes their shirt is completely wrinkled from their backpack.",
        type: "hook",
        details: "Spoken: 'I had ten minutes before class and this shirt looked like it came straight out of my backpack.'",
    },
    {
        time: "0:02 - 0:05",
        action: "Fast reveal of the SwiftPress Mini Garment Steamer. Show its compact profile.",
        type: "product",
        details: "Visual: Handheld device turned on, steam starting to build.",
    },
    {
        time: "0:05 - 0:10",
        action: "Visual demonstration: Glide steamer over one clearly wrinkled sleeve section.",
        type: "demo",
        details: "Requirement: Single continuous shot showing the steam contact area.",
    },
    {
        time: "0:10 - 0:14",
        action: "Observable same-fabric proof showing treated vs untreated area.",
        type: "proof",
        details: "Requirement: Visible side-by-side comparison of the same garment area.",
    },
    {
        time: "0:14 - 0:18",
        action: "Creator reacts to how quickly it worked and packs it away in a small drawer.",
        type: "reaction",
        details: "Constraint: Disclosure 'Results vary by fabric type' must be visible.",
    },
    {
        time: "0:18 - 0:21",
        action: "Call to Action to check out the product in the TikTok Shop store.",
        type: "cta",
        details: "Spoken: 'Tap the product tag to see it.'",
    },
];

export const steamerFixes: TikTokFix[] = [
    {
        id: "fix-01",
        title: "Move product reveal earlier",
        expected: "Product first appearance before 2.0 seconds.",
        observed: "First clear appearance was at 4.2 seconds.",
        action: "Edit existing footage to move the steamer close-up to 1.2s.",
        needsReshoot: false,
        type: "blocker",
    },
    {
        id: "fix-02",
        title: "Add same-item before/after proof",
        expected: "Observable comparison showing treated vs untreated fabric area.",
        observed: "Steam is visible in use, but no comparable before/after is shown.",
        action: "Reshoot a continuous shot comparing wrinkled vs smoothed fabric on the same shirt.",
        needsReshoot: true,
        type: "blocker",
    },
    {
        id: "fix-03",
        title: "Add required fabric disclosure",
        expected: "Required text overlay: 'Results vary by fabric type.'",
        observed: "No fabric capability disclosure was observed in the video.",
        action: "Add text overlay 'Results vary by fabric type.' between 15.2s and 18.0s.",
        needsReshoot: false,
        type: "blocker",
    },
];

export const steamerRevisionCompare = [
    {
        id: "comp-1",
        metric: "Product Reveal",
        draft1: "First visible at 4.2s (Too late)",
        draft2: "First visible at 1.4s (Resolved)",
        status: "fixed" as const,
    },
    {
        id: "comp-2",
        metric: "Same-Item Proof",
        draft1: "Steam only, no visible comparison",
        draft2: "Clear side-by-side before/after (Resolved)",
        status: "fixed" as const,
    },
    {
        id: "comp-3",
        metric: "Required Disclosure",
        draft1: "No disclosure overlay text",
        draft2: "'Results vary by fabric type.' added (Resolved)",
        status: "fixed" as const,
    },
    {
        id: "comp-4",
        metric: "Prohibited Claims",
        draft1: "No prohibited claims flagged",
        draft2: "All checks passed (Preserved)",
        status: "unchanged" as const,
    },
];
