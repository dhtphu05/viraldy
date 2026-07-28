export function authHeaders(): HeadersInit {
    const token = import.meta.env.VITE_LOCAL_AUTH_TOKEN || "local-test";
    return { Authorization: `Bearer ${token}` };
}
