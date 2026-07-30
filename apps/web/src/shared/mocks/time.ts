const MINUTE_MS = 60_000;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;

export const DEMO_NOW_ISO = "2026-07-29T16:00:00.000Z";
export const DEMO_NOW_MS = Date.parse(DEMO_NOW_ISO);

export function demoMinutesAgo(minutes: number) {
    return new Date(DEMO_NOW_MS - minutes * MINUTE_MS).toISOString();
}

export function demoHoursAgo(hours: number) {
    return new Date(DEMO_NOW_MS - hours * HOUR_MS).toISOString();
}

export function demoDaysAgo(days: number) {
    return new Date(DEMO_NOW_MS - days * DAY_MS).toISOString();
}

export function demoDaysFromNow(days: number) {
    return new Date(DEMO_NOW_MS + days * DAY_MS).toISOString();
}

export function isWithinDemoDays(iso: string, days: number) {
    const diff = DEMO_NOW_MS - new Date(iso).getTime();
    return diff >= 0 && diff < days * DAY_MS;
}
