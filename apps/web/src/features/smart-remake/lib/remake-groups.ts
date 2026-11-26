import type { SmartRemakeRenderGroup, SmartRemakeRenderPlan } from "@/shared/api/smart-remake";

export function getRenderGroups(plan: SmartRemakeRenderPlan): SmartRemakeRenderGroup[] {
    return (
        plan.groups ??
        plan.units.map((unit) => ({
            id: unit.id,
            renderUnitIds: [unit.id],
            rawDurationFrames: unit.rawDurationFrames,
            targetDurationFrames: unit.targetDurationFrames,
            segments: [{ renderUnitId: unit.id, inFrame: 0, outFrame: unit.targetDurationFrames }],
        }))
    );
}

export function getRenderTaskCount(plan: SmartRemakeRenderPlan | undefined): number {
    return plan ? getRenderGroups(plan).length : 0;
}

export function getRenderGroupBreaks(plan: SmartRemakeRenderPlan | undefined): number[] {
    if (!plan) return [];
    if (plan.groupingPolicy === "fixed_provider_windows") return [];
    if (plan.renderGroupBreaks) return [...plan.renderGroupBreaks];
    const groups = getRenderGroups(plan);
    let count = 0;
    return groups.slice(0, -1).flatMap((group) => {
        count += group.renderUnitIds.length;
        const next = plan.units[count];
        return next && group.targetDurationFrames + next.targetDurationFrames <= 192 ? [count] : [];
    });
}

export function previewRenderGroups(
    plan: SmartRemakeRenderPlan,
    breaks: number[],
): SmartRemakeRenderGroup[] {
    if (plan.groupingPolicy === "fixed_provider_windows") return getRenderGroups(plan);
    return plan.units.reduce<SmartRemakeRenderGroup[]>((groups, unit, index) => {
        const previous = groups.at(-1);
        const combine =
            previous &&
            !breaks.includes(index) &&
            previous.targetDurationFrames + unit.targetDurationFrames <= 192;
        if (!combine)
            return [
                ...groups,
                {
                    id: `preview-${index}`,
                    renderUnitIds: [unit.id],
                    rawDurationFrames: 192,
                    targetDurationFrames: unit.targetDurationFrames,
                    segments: [
                        { renderUnitId: unit.id, inFrame: 0, outFrame: unit.targetDurationFrames },
                    ],
                },
            ];
        return [
            ...groups.slice(0, -1),
            {
                ...previous,
                renderUnitIds: [...previous.renderUnitIds, unit.id],
                targetDurationFrames: previous.targetDurationFrames + unit.targetDurationFrames,
                segments: [
                    ...previous.segments,
                    {
                        renderUnitId: unit.id,
                        inFrame: previous.targetDurationFrames,
                        outFrame: previous.targetDurationFrames + unit.targetDurationFrames,
                    },
                ],
            },
        ];
    }, []);
}
