import { useEffect, useState } from "react";
import { getFormattedMetrics } from "../demo-data/landing-proof-stats";
import { Activity, ShieldCheck, Eye, Compass, Video } from "lucide-react";

export function ScaleProofBand() {
    const [metrics, setMetrics] = useState(getFormattedMetrics());

    useEffect(() => {
        const interval = setInterval(() => {
            setMetrics(getFormattedMetrics());
        }, 30000); // update every 30 seconds for local time
        return () => clearInterval(interval);
    }, []);

    return (
        <section className="w-full bg-foreground text-white py-12 px-6 border-y border-divider relative overflow-hidden">
            {/* Soft decorative background shape */}
            <div className="absolute right-0 bottom-0 top-0 w-1/3 bg-gradient-to-l from-primary/5 to-transparent pointer-events-none" />

            <div className="mx-auto max-w-[1100px] relative z-10">
                <div className="flex items-center gap-2 mb-8 justify-center sm:justify-start">
                    <Activity className="h-4 w-4 text-primary animate-pulse" />
                    <span className="text-[10px] font-bold uppercase tracking-widest text-text-tertiary">
                        Creative Intelligence In Motion
                    </span>
                </div>

                <div className="grid gap-6 grid-cols-2 lg:grid-cols-5 text-center sm:text-left">
                    {/* Stat 1 */}
                    <div className="space-y-1">
                        <span className="text-2xl font-extrabold text-white tracking-tight block">
                            {metrics.creativeSignalsAnalyzed}
                        </span>
                        <span className="text-[10px] text-text-secondary uppercase font-bold tracking-wider block flex items-center justify-center sm:justify-start gap-1">
                            <ShieldCheck className="h-3 w-3 text-primary shrink-0" />
                            Signals Analyzed
                        </span>
                    </div>

                    {/* Stat 2 */}
                    <div className="space-y-1">
                        <span className="text-2xl font-extrabold text-white tracking-tight block">
                            {metrics.videosReviewed}
                        </span>
                        <span className="text-[10px] text-text-secondary uppercase font-bold tracking-wider block flex items-center justify-center sm:justify-start gap-1">
                            <Video className="h-3 w-3 text-primary shrink-0" />
                            Videos Reviewed
                        </span>
                    </div>

                    {/* Stat 3 */}
                    <div className="space-y-1">
                        <span className="text-2xl font-extrabold text-white tracking-tight block">
                            {metrics.productsAnalyzed}
                        </span>
                        <span className="text-[10px] text-text-secondary uppercase font-bold tracking-wider block flex items-center justify-center sm:justify-start gap-1">
                            <Compass className="h-3 w-3 text-primary shrink-0" />
                            Products Grounded
                        </span>
                    </div>

                    {/* Stat 4 */}
                    <div className="space-y-1">
                        <span className="text-2xl font-extrabold text-white tracking-tight block">
                            {metrics.creativeDirectionsGenerated}
                        </span>
                        <span className="text-[10px] text-text-secondary uppercase font-bold tracking-wider block flex items-center justify-center sm:justify-start gap-1">
                            <Eye className="h-3 w-3 text-primary shrink-0" />
                            Directions Born
                        </span>
                    </div>

                    {/* Stat 5 (Local metrics) */}
                    <div className="space-y-1 col-span-2 sm:col-span-1 border-t sm:border-t-0 sm:border-l border-white/10 pt-4 sm:pt-0 sm:pl-6">
                        <span className="text-xs text-text-tertiary block font-semibold">
                            Today ({metrics.currentTime})
                        </span>
                        <span className="text-base font-bold text-white block mt-0.5">
                            {metrics.videosAnalyzedToday} analyzed
                        </span>
                        <span className="text-[9px] text-text-tertiary uppercase font-medium block">
                            Active session tracking
                        </span>
                    </div>
                </div>
            </div>
        </section>
    );
}
