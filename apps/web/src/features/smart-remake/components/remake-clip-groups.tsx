import { useEffect, useRef, useState } from "react";
import type { RepairIntent, SmartRemakeProject } from "@/shared/api/smart-remake";
import type { RemakeRepairCandidate } from "../lib/remake-action";
import {
    getRemakeClipCandidate,
    getRemakeClipGroups,
    type RemakeClipGroup,
} from "../lib/remake-clip-groups";
import { Button } from "@/shared/ui/button";
import { RemakeRepairForm } from "./remake-repair-form";
import { RemakePlayer } from "./remake-player";

type Navigation = {
    requestId: string;
    sceneId: string;
    view: "watch" | "repair" | "compare";
    versionId?: string;
};
interface Props {
    workspaceId: string;
    project: SmartRemakeProject;
    busy: boolean;
    repairCandidate?: RemakeRepairCandidate | null;
    navigation?: Navigation | null;
    onRepairGroup?(groupId: string, intent: RepairIntent): Promise<string | null>;
    onAccept(sceneId: string, candidateVersionId: string): Promise<boolean>;
    onRefresh?(): void;
}
const primaryButton = "min-h-11 bg-[#e00b41] text-white hover:bg-[#c90a3a]";

export function RemakeClipGroups(props: Props) {
    const groups = getRemakeClipGroups(props.project);
    if (!groups.length) return null;
    return (
        <section aria-label="Các clip trong video" className="space-y-3">
            <div>
                <h3 className="font-semibold text-text-primary">Muốn sửa phần nào?</h3>
                <p className="mt-1 text-sm text-text-secondary">
                    Xem từng clip đầy đủ rồi chọn clip cần sửa. Những clip còn lại được giữ nguyên.
                </p>
            </div>
            <div className="grid min-w-0 gap-4 md:grid-cols-2">
                {groups.map((group) => (
                    <ClipGroupCard
                        key={`${group.id}:${group.baseFingerprint}`}
                        {...props}
                        group={group}
                    />
                ))}
            </div>
        </section>
    );
}

function ClipGroupCard({ group, ...props }: Props & { group: RemakeClipGroup }) {
    const [view, setView] = useState<"watch" | "repair" | "compare">("watch");
    const [working, setWorking] = useState(false);
    const [draft, setDraft] = useState<RepairIntent>({
        schemaVersion: 1,
        issues: [],
        instruction: "",
    });
    const [error, setError] = useState<string | null>(null);
    const card = useRef<HTMLElement>(null);
    const consumed = useRef<string | null>(null);
    const candidate = getRemakeClipCandidate(props.project, group, props.repairCandidate);
    const busy = props.busy || working;
    useEffect(() => {
        const next = props.navigation;
        if (!next || next.requestId === consumed.current || !group.memberIds.includes(next.sceneId))
            return;
        consumed.current = next.requestId;
        setView(next.view);
        card.current?.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
        card.current?.focus({ preventScroll: true });
    }, [props.navigation, group.memberIds]);
    async function repair(intent: RepairIntent) {
        if (!props.onRepairGroup || busy || !group.ready) return;
        setWorking(true);
        setError(null);
        try {
            await props.onRepairGroup(group.id, intent);
        } catch {
            setError("Chưa gửi được yêu cầu sửa clip. Bản đang dùng vẫn được giữ.");
        } finally {
            setWorking(false);
        }
    }
    async function accept() {
        if (!candidate || busy) return;
        setWorking(true);
        setError(null);
        try {
            if (await props.onAccept(candidate.sceneId, candidate.version.id)) setView("watch");
            else setError("Chưa áp dụng được bản mới. Kiểm tra trạng thái rồi thử lại.");
        } catch {
            setError("Chưa áp dụng được bản mới. Bản đang dùng vẫn được giữ.");
        } finally {
            setWorking(false);
        }
    }
    return (
        <article
            ref={card}
            tabIndex={-1}
            aria-label={`Clip ${group.index}`}
            className="min-w-0 space-y-4 rounded-3xl bg-surface p-5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
            <div className="flex flex-wrap items-center justify-between gap-2">
                <h4 className="font-semibold text-text-primary">Clip {group.index}</h4>
                <span className="text-sm text-text-secondary">
                    {group.startSecond}–{group.endSecond} giây
                </span>
            </div>
            {view === "compare" && candidate && group.videoUrl ? (
                <>
                    <RemakePlayer
                        url={group.videoUrl}
                        compareUrl={candidate.version.videoUrl}
                        scope={null}
                        compareScope={null}
                        versionLabel={
                            group.usesDefaultRanges
                                ? `Clip ${group.index} đang dùng`
                                : `Clip gốc ${group.index}`
                        }
                        compareLabel={`Clip ${group.index} bản mới`}
                    />
                    <p className="text-sm text-text-secondary">
                        Đây là toàn bộ clip {group.durationSeconds} giây. Bản mới chỉ thay thế khi
                        bạn áp dụng.
                    </p>
                    <Button
                        type="button"
                        className={`${primaryButton} w-full`}
                        disabled={busy}
                        onClick={() => void accept()}
                    >
                        Dùng bản mới cho Clip {group.index}
                    </Button>
                </>
            ) : group.videoUrl ? (
                <video
                    src={group.videoUrl}
                    controls
                    playsInline
                    preload="metadata"
                    aria-label={`Xem toàn bộ Clip ${group.index} (${group.durationSeconds} giây)`}
                    className="h-52 w-full rounded-2xl bg-[#19171d] object-contain"
                />
            ) : (
                <p
                    role="status"
                    className="rounded-2xl bg-surface-soft p-5 text-sm text-text-secondary"
                >
                    {group.pending
                        ? "Clip đang được chuẩn bị. Kết quả sẽ xuất hiện tại đây khi sẵn sàng."
                        : "Clip chưa có bản đang dùng nhất quán để sửa. Kiểm tra trạng thái dự án để tiếp tục."}
                </p>
            )}
            {!group.usesDefaultRanges && (
                <p className="rounded-xl bg-warn-soft p-3 text-sm text-text-secondary">
                    Đây là clip gốc {group.durationSeconds} giây. Đoạn cắt đã thay đổi trong Nâng
                    cao; bản {props.project.targetDuration}s phía trên mới phản ánh đoạn cắt đang
                    dùng.
                </p>
            )}
            <div className="flex flex-wrap gap-2">
                <Button
                    type="button"
                    variant="ghost"
                    className="min-h-11"
                    aria-pressed={view === "watch"}
                    onClick={() => setView("watch")}
                >
                    Xem Clip {group.index}
                </Button>
                <Button
                    type="button"
                    variant="outline"
                    className="min-h-11"
                    aria-pressed={view === "repair"}
                    disabled={!group.ready || busy || !props.onRepairGroup}
                    onClick={() => setView("repair")}
                >
                    Sửa Clip {group.index}
                </Button>
                {candidate && (
                    <Button
                        type="button"
                        variant="outline"
                        className="min-h-11"
                        aria-pressed={view === "compare"}
                        onClick={() => setView("compare")}
                    >
                        Xem bản mới Clip {group.index}
                    </Button>
                )}
            </div>
            {view === "repair" &&
                props.onRepairGroup &&
                group.anchorScene &&
                group.anchorVersion && (
                    <RemakeRepairForm
                        key={group.baseFingerprint}
                        workspaceId={props.workspaceId}
                        projectId={props.project.id}
                        scene={group.anchorScene}
                        active={group.anchorVersion}
                        sceneLabel={`Clip ${group.index}`}
                        clip={{ index: group.index, durationSeconds: group.durationSeconds }}
                        busy={busy}
                        draft={draft}
                        onDraftChange={setDraft}
                        saveStatus="Yêu cầu sửa chỉ áp dụng cho clip này"
                        onRepair={repair}
                    />
                )}
            {error && (
                <p
                    role="alert"
                    className="rounded-xl bg-destructive-soft p-3 text-sm text-destructive"
                >
                    {error}
                </p>
            )}
            {!group.ready && props.onRefresh && (
                <Button
                    type="button"
                    variant="ghost"
                    className="min-h-11"
                    onClick={props.onRefresh}
                >
                    Kiểm tra trạng thái clip
                </Button>
            )}
        </article>
    );
}
