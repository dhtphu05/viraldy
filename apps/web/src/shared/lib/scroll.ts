export function scrollElementIntoView(
    element: Element | null | undefined,
    options: ScrollIntoViewOptions = {},
) {
    if (!element) return;

    const reducedMotion =
        typeof window !== "undefined" &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    element.scrollIntoView({
        ...options,
        behavior: reducedMotion ? "auto" : (options.behavior ?? "smooth"),
    });
}
