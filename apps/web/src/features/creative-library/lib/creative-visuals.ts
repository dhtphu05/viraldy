// Deterministic gradient placeholders for creative thumbnails.
// Frontend-only — no image assets required.

const palettes: Record<string, [string, string, string]> = {
    sunset: ["#ffb199", "#ff6b8b", "#ff385c"],
    peach: ["#ffd6a5", "#ffb385", "#f7876a"],
    blush: ["#ffe0ec", "#ffc6d9", "#ff96b8"],
    mint: ["#d6f7e3", "#94e8b4", "#3fb87a"],
    sage: ["#e3ecd8", "#b6c99b", "#7a9061"],
    lavender: ["#e6dcff", "#c3b1f0", "#8a75d1"],
    coral: ["#ffe0d6", "#ffb199", "#ff7a59"],
    amber: ["#fff2c2", "#ffd873", "#f5a623"],
    rose: ["#ffd6e0", "#ff9db0", "#e75f7c"],
    sky: ["#d6f0ff", "#a6d8ff", "#5aa9ea"],
    lilac: ["#f0dcff", "#d0a6f0", "#a26ed4"],
    stone: ["#e8e8ec", "#c8c8d0", "#8a8a94"],
};

export function thumbnailGradient(seed: string): string {
    const p = palettes[seed] ?? palettes.stone;
    return `linear-gradient(140deg, ${p[0]} 0%, ${p[1]} 45%, ${p[2]} 100%)`;
}

export function thumbnailAccent(seed: string): string {
    const p = palettes[seed] ?? palettes.stone;
    return p[2];
}

export function formatDuration(sec: number): string {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60)
        .toString()
        .padStart(2, "0");
    return `${m}:${s}`;
}
