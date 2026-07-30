export function normalizeAspectRatio(value?: string, fallback = "4 / 5") {
    if (!value) return fallback;
    return value.includes(":") ? value.replace(":", " / ") : value;
}
