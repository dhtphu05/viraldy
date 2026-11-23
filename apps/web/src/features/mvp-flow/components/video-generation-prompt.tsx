import { Clipboard, FileVideo } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/shared/ui/button";
import { StatusChip } from "@/shared/ui/status-chip";
import { Textarea } from "@/shared/ui/textarea";

export type VideoGenerationPrompt = {
    schema_version: "video_generation_prompt_v1";
    prompt_text: string;
    aspect_ratio: "9:16";
    duration_seconds: number;
    source_concept_id: string;
};

export function VideoGenerationPromptPanel({
    artifact,
}: {
    artifact: VideoGenerationPrompt;
}) {
    const copyPrompt = async () => {
        try {
            await navigator.clipboard.writeText(artifact.prompt_text);
            toast.success("AI video prompt copied");
        } catch {
            toast.error("AI video prompt could not be copied");
        }
    };

    return (
        <section className="border-t border-divider pt-5" aria-labelledby="video-prompt-title">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                    <div className="flex items-center gap-2 text-primary">
                        <FileVideo className="h-4 w-4" />
                        <p className="text-[10px] font-semibold uppercase tracking-[0.14em]">
                            Generation artifact
                        </p>
                    </div>
                    <h3
                        id="video-prompt-title"
                        className="mt-1 text-base font-semibold text-text-primary"
                    >
                        AI video generation prompt
                    </h3>
                    <p className="mt-1 max-w-3xl text-sm leading-6 text-text-secondary">
                        Product-grounded prompt generated from the confirmed concept and Campaign
                        Pack.
                    </p>
                </div>
                <div className="flex flex-wrap gap-2">
                    <StatusChip tone="info">{artifact.aspect_ratio}</StatusChip>
                    <StatusChip tone="neutral">{artifact.duration_seconds}s</StatusChip>
                </div>
            </div>

            <Textarea
                aria-label="AI video generation prompt"
                className="mt-4 min-h-[360px] resize-y font-mono text-xs leading-5"
                value={artifact.prompt_text}
                readOnly
            />

            <div className="mt-3 flex justify-end">
                <Button type="button" onClick={() => void copyPrompt()}>
                    <Clipboard className="h-4 w-4" />
                    Copy video prompt
                </Button>
            </div>
        </section>
    );
}
