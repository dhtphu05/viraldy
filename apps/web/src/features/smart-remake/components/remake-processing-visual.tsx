import storyboardIllustration from "@/assets/smart-remake/analysis-storyboard.webp";
import renderIllustration from "@/assets/smart-remake/render-studio.webp";
import "./remake-processing.css";

export function RemakeProcessingVisual({
    kind = "generate",
    compact = false,
    active = true,
}: {
    kind?: "analyze" | "generate";
    compact?: boolean;
    active?: boolean;
}) {
    return (
        <div
            className={`remake-processing-visual${compact ? " remake-processing-visual--compact" : ""}`}
            data-active={active}
            aria-hidden="true"
        >
            <div className="remake-processing-visual__art">
                <img
                    src={kind === "analyze" ? storyboardIllustration : renderIllustration}
                    alt=""
                    width={960}
                    height={kind === "analyze" ? 548 : 640}
                    decoding="async"
                />
                {active && <span className="remake-processing-visual__scan" />}
            </div>
            {active && (
                <div className="remake-processing-visual__rhythm">
                    {Array.from({ length: 15 }, (_, index) => (
                        <i key={index} style={{ animationDelay: `${index * -0.13}s` }} />
                    ))}
                </div>
            )}
        </div>
    );
}
