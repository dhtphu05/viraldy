import type { Activity } from "@/shared/types";

const now = Date.now();
const mins = (m: number) => new Date(now - m * 60_000).toISOString();

export const activities: Activity[] = [
    {
        id: "a-1",
        kind: "analysis",
        title: "Creative DNA analysis completed",
        subject: "Kitchen Organizer — 6 references",
        at: mins(18),
    },
    {
        id: "a-2",
        kind: "message",
        title: "Revision message copied",
        subject: "@tidy.emma — hook rewrite v2",
        at: mins(52),
    },
    {
        id: "a-3",
        kind: "pack",
        title: "Campaign Pack updated",
        subject: "Dog Mom Holiday Gift Campaign",
        at: mins(120),
    },
    {
        id: "a-4",
        kind: "asset",
        title: "Spark-ready asset approved",
        subject: "@theresa_pets — asset 04",
        at: mins(240),
    },
    {
        id: "a-5",
        kind: "recommendation",
        title: "Recommendation accepted",
        subject: "Scale problem-solution angle",
        at: mins(360),
    },
    {
        id: "a-6",
        kind: "analysis",
        title: "Creative DNA analysis completed",
        subject: "Beauty Mirror — 4 references",
        at: mins(600),
    },
];
