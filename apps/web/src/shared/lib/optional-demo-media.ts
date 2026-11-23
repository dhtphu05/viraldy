export async function isDemoVideoAvailable(url: string): Promise<boolean> {
    try {
        const response = await fetch(url, {
            method: "HEAD",
            signal: AbortSignal.timeout(3_000),
        });
        return response.ok && Boolean(response.headers.get("Content-Type")?.startsWith("video/"));
    } catch {
        return false;
    }
}
