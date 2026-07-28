import type { CreativeBoard } from "@/features/creative-library/types/creative";

export const seedBoards: CreativeBoard[] = [
    { id: "b-all", name: "All creatives", icon: "layers", system: true, filter: "all" },
    { id: "b-recent", name: "Recently saved", icon: "clock", system: true, filter: "recent" },
    { id: "b-competitor", name: "Competitor references", icon: "target" },
    { id: "b-kitchen", name: "Kitchen Gadgets", icon: "utensils" },
    { id: "b-pod", name: "POD Gift Angles", icon: "gift" },
    { id: "b-beauty", name: "Beauty Creators", icon: "sparkles" },
    { id: "b-home", name: "Home Organization", icon: "package" },
    { id: "b-unassigned", name: "Unassigned", icon: "inbox", system: true, filter: "unassigned" },
];
