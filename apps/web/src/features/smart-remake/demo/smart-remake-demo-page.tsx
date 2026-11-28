import { useEffect, useRef, useState } from "react";
import { Check, ChevronRight, Clapperboard, Images, Sparkles } from "lucide-react";
import type {
    SmartRemakeProject,
    SmartRemakeInspectionEvidence,
    SmartRemakePreflight,
    RepairIntent,
} from "@/shared/api/smart-remake";
import { BrandLogo } from "@/shared/ui/brand-logo";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/shared/ui/dialog";
import { RemakeInputs } from "../components/remake-inputs";
import { RemakeStoryboard } from "../components/remake-storyboard";
import { RemakeOutput } from "../components/remake-output";
import { RemakePlayer } from "../components/remake-player";
import { RemakeInspector } from "../components/remake-inspector";
import { RemakeProjectControls } from "../components/remake-project-controls";
import { RemakeSourceAudio } from "../components/remake-source-audio";
import { RemakeActionConfirmation } from "../components/remake-action-confirmation";
import { DEFAULT_REMAKE_INTENT, emptyRemakeRights } from "../lib/remake-intake";
import { RemakeDemoComparison } from "./remake-demo-comparison";
import { RemakeDemoExport } from "./remake-demo-export";
import { resolveInspectionEvidence, type InspectionSeekTarget } from "../lib/remake-inspection";
import {
    DEMO_ASSETS,
    selectDemoRanges,
    applyDemoVersion,
    type RemakeDemoFixture,
} from "./remake-demo-state";
import { createRemakePreviewDemo, createRemakeClipRepairDemo } from "./remake-preview-demo";
import type { RemakeRepairCandidate, RemakeActionIntent } from "../lib/remake-action";
import "../components/remake-studio.css";
import "./smart-remake-demo.css";

const screens = {
    inputs: "Tư liệu",
    analysis: "AI sơ bộ",
    transcript: "Transcript AI",
    storyboard: "Kịch bản",
    output: "Xem & ghép",
    compare: "So sánh bản sửa",
    inspector: "Output Inspector",
    export: "Duyệt & xuất",
    deletion: "Yêu cầu xóa",
} as const;
type Screen = keyof typeof screens;
const isScreen = (value: string): value is Screen => Object.hasOwn(screens, value);

export function SmartRemakeDemoPage() {
    const [previewStatus] = useState<"ready" | "processing" | null>(() => {
        if (typeof window === "undefined") return null;
        const scenario = new URLSearchParams(window.location.search).get("scenario");
        return scenario === "whole-preview-ready" || scenario === "whole-preview-candidate"
            ? "ready"
            : scenario === "whole-preview-pending"
              ? "processing"
              : null;
    });
    const [fixture, setFixture] = useState<RemakeDemoFixture | null>(null);
    const [project, setProject] = useState<SmartRemakeProject | null>(null);
    const [clipCandidate, setClipCandidate] = useState<RemakeRepairCandidate | null>(null);
    const [clipConfirmation, setClipConfirmation] = useState<{
        intent: RemakeActionIntent;
        preflight: SmartRemakePreflight;
        label: string;
    } | null>(null);
    const [screen, setScreen] = useState<Screen>("inputs");
    const [error, setError] = useState("");
    const [notice, setNotice] = useState("");
    const [evidence, setEvidence] = useState<InspectionSeekTarget | null>(null);
    const [images, setImages] = useState([`${DEMO_ASSETS}product.webp`]);
    const [primary, setPrimary] = useState(0);
    const importedImages = useRef<string[]>([]);
    const duration = project?.targetDuration ?? 16;
    useEffect(() => () => importedImages.current.forEach((url) => URL.revokeObjectURL(url)), []);
    useEffect(() => {
        const readHash = () => {
            const value = window.location.hash.slice(1);
            if (isScreen(value)) setScreen(value);
        };
        readHash();
        window.addEventListener("hashchange", readHash);
        const abort = new AbortController();
        void fetch(`${DEMO_ASSETS}fixture.json`, { signal: abort.signal })
            .then(async (response) => {
                if (!response.ok) throw new Error("Chưa có bộ dữ liệu demo trên máy này.");
                const data = (await response.json()) as RemakeDemoFixture;
                setFixture(data);
                const inspection = await fetch(`${DEMO_ASSETS}inspection.json`, {
                    signal: abort.signal,
                });
                const extra = inspection.ok ? await inspection.json() : {};
                const saved = { ...data.project, ...extra };
                if (
                    new URLSearchParams(window.location.search).get("scenario") ===
                    "whole-preview-candidate"
                ) {
                    const demo = createRemakeClipRepairDemo(saved);
                    setProject(demo.project);
                    setClipCandidate(demo.candidate);
                    return;
                }
                setProject(previewStatus ? createRemakePreviewDemo(saved, previewStatus) : saved);
            })
            .catch((reason: unknown) => {
                if (!abort.signal.aborted)
                    setError(
                        reason instanceof Error ? reason.message : "Chưa mở được dữ liệu demo.",
                    );
            });
        return () => {
            abort.abort();
            window.removeEventListener("hashchange", readHash);
        };
    }, [previewStatus]);
    useEffect(() => {
        window.scrollTo({ top: 0 });
        setNotice("");
    }, [screen]);
    const demoOnly = async () => {
        setNotice(
            "Bản demo dùng kết quả đã lưu. Thao tác này không gửi tác vụ AI hoặc thay đổi dự án thật.",
        );
    };
    async function confirmDemoClipRepair(groupId: string, intent: RepairIntent): Promise<null> {
        const group = project?.renderPlan?.groups?.find((value) => value.id === groupId);
        const index = project?.renderPlan?.groups?.findIndex((value) => value.id === groupId) ?? -1;
        const anchor = project?.scenes.find((scene) => scene.id === group?.renderUnitIds[0]);
        if (!project || !group || !anchor?.activeVersionId) return null;
        setClipConfirmation({
            label: `Clip ${index + 1}`,
            intent: {
                action: "repair",
                fingerprint: `fixture-confirm-${groupId}:${project.revision}:${JSON.stringify(intent)}`,
                sceneId: anchor.id,
                baseVersionId: anchor.activeVersionId,
                repairScope: "provider_group",
                repairIntent: intent,
            },
            preflight: {
                action: "repair",
                projectId: project.id,
                revision: project.revision,
                contextHash: `fixture-context-${groupId}`,
                mode: "fixture",
                scope: {
                    targetDuration: group.rawDurationFrames / 24,
                    sceneCount: group.renderUnitIds.length,
                    groupCount: 1,
                    imageCount: 2,
                    repairScope: "provider_group",
                    renderGroupId: groupId,
                },
                calls: { analysis: 1, image: 2, video: 1, inspection: 0, total: 4 },
                budget: null,
                blockers: [],
            },
        });
        return null;
    }
    function seekEvidence(value: SmartRemakeInspectionEvidence) {
        if (!project) return;
        const target = resolveInspectionEvidence(
            value,
            project.inspectionMedia ?? [],
            project.inspectionMappings ?? [],
            value.timebase === "scene_local" ? "raw_group" : undefined,
        );
        if (target) setEvidence(target);
        else setNotice("Bằng chứng này chưa có tệp tương ứng trong bộ demo.");
    }
    const titles: Record<Screen, [string, string]> = {
        inputs: [
            "Dùng cách quay của video mẫu cho sản phẩm của bạn",
            "Video mẫu và hình ảnh sản phẩm, sẵn sàng cho bước phân tích.",
        ],
        analysis: [
            "AI đã đọc được gì từ video mẫu?",
            "Nhận định sơ bộ và âm thanh được lưu từ lượt phân tích thật.",
        ],
        transcript: [
            "Lời thoại trong video mẫu",
            "Transcript AI nhận diện từ 20.mp4 · Tiếng Việt · 46,81 giây.",
        ],
        storyboard: [
            "Duyệt kịch bản từ video mẫu",
            "13 cảnh từ phân tích thật · Đầu ra 16 giây · Video dọc 9:16.",
        ],
        output: previewStatus
            ? [
                  "Xem toàn video 12 giây",
                  "Xem video 12 giây, rồi chọn Clip 1 hoặc Clip 2 nếu cần sửa.",
              ]
            : ["Video của bạn", "Xem từng cảnh, chọn đoạn phù hợp rồi ghép bản xem trước."],
        compare: [
            "So sánh trước và sau sửa",
            "Hai video trước/sau do bạn cung cấp. Bản sau sử dụng đoạn 0–8 giây.",
        ],
        inspector: [
            "Output Inspector",
            "Kết quả kiểm tra AI thật của bản trước sửa, kèm bằng chứng cần đối chiếu.",
        ],
        export: [
            "Duyệt và xuất video",
            "Xem bản có nhãn AI và trạng thái kiểm tra trước khi hoàn tất.",
        ],
        deletion: [
            "Quản lý tư liệu dự án",
            "Xem phạm vi và xác nhận yêu cầu ngừng dùng, xóa tư liệu.",
        ],
    };
    return (
        <div className="report-demo-shell w-full min-w-0">
            <aside className="report-demo-sidebar max-lg:hidden!" aria-label="Điều hướng minh họa">
                <BrandLogo />
                <small>CREATE & OPERATE</small>
                <span>
                    <Images size={18} /> Creative Library
                </span>
                <a href="#inputs" className="report-demo-sidebar__active">
                    <Sparkles size={18} /> Smart Remake
                </a>
                <span>
                    <Clapperboard size={18} /> Project
                </span>
            </aside>
            <div className="report-demo-body">
                <header className="report-demo-header min-w-0 gap-3 max-sm:px-4!">
                    <span className="min-w-0 flex-1">
                        <span className="truncate">Vali DELSEY</span>
                        <ChevronRight size={14} className="shrink-0" />
                        <span className="truncate">Smart Remake</span>
                    </span>
                    <span className="report-demo-label shrink-0 max-sm:hidden">
                        Bộ minh họa báo cáo
                    </span>
                </header>
                <main className="report-demo-main min-w-0">
                    <div className="remake-studio report-demo-content min-w-0 max-sm:mx-4! max-sm:my-4! max-sm:w-auto!">
                        <details className="report-demo-navigation">
                            <summary>Chuyển màn demo · {screens[screen]}</summary>
                            <nav aria-label="Các màn demo Smart Remake">
                                {Object.entries(screens).map(([key, label]) => (
                                    <a
                                        key={key}
                                        href={`#${key}`}
                                        aria-current={screen === key ? "page" : undefined}
                                    >
                                        {label}
                                    </a>
                                ))}
                            </nav>
                        </details>
                        <div className="report-demo-title min-w-0">
                            <p>SMART REMAKE</p>
                            <h1 className="max-sm:text-2xl!">{titles[screen][0]}</h1>
                            <p>{titles[screen][1]}</p>
                        </div>
                        {previewStatus && (
                            <p
                                role="note"
                                className="min-w-0 rounded-2xl bg-warn-soft p-4 text-sm leading-relaxed text-text-secondary max-sm:p-3"
                            >
                                Fixture UI · Trạng thái mô phỏng. Video 12 giây được cắt từ tư liệu
                                có sẵn, giữ âm thanh; không có lượt tạo AI mới hoặc thay đổi dự án
                                thật.
                            </p>
                        )}
                        {error && (
                            <p role="alert">
                                {error} Chạy script chuẩn bị tư liệu demo rồi tải lại trang.
                            </p>
                        )}
                        {!fixture || !project ? (
                            !error && <p role="status">Đang mở bộ minh họa…</p>
                        ) : (
                            <>
                                {screen === "inputs" && (
                                    <RemakeInputs
                                        sourceUrl={`${DEMO_ASSETS}reference.mp4`}
                                        sourceName="20.mp4"
                                        sourceDurationSeconds={46.809977}
                                        productUrls={images}
                                        primaryIndex={primary}
                                        onPrimaryChange={setPrimary}
                                        onVideo={() => void demoOnly()}
                                        onImages={(files) =>
                                            setImages((current) => [
                                                ...current,
                                                ...files.map((file) => {
                                                    const url = URL.createObjectURL(file);
                                                    importedImages.current.push(url);
                                                    return url;
                                                }),
                                            ])
                                        }
                                        onRemoveImage={(index) => {
                                            if (images[index]?.startsWith("blob:"))
                                                URL.revokeObjectURL(images[index]);
                                            setImages((current) =>
                                                current.filter((_, at) => at !== index),
                                            );
                                            setPrimary(0);
                                        }}
                                        link=""
                                        onLinkChange={() => {}}
                                        onLinkSubmit={() => void demoOnly()}
                                        isLinkLoading={false}
                                        duration={duration}
                                        onDuration={() =>
                                            setNotice(
                                                "Bộ demo đã chuẩn bị đầu ra 16 giây. Đổi thời lượng và phân tích lại tại Smart Remake khi làm dự án thật.",
                                            )
                                        }
                                        language="Tiếng Việt"
                                        onLanguage={() => {}}
                                        description=""
                                        onDescription={() => {}}
                                        brief=""
                                        onBrief={() => {}}
                                        disabled={false}
                                    />
                                )}
                                {(screen === "analysis" || screen === "transcript") && (
                                    <div className="report-demo-analysis">
                                        <section className="report-demo-reference">
                                            <video
                                                src={`${DEMO_ASSETS}reference.mp4`}
                                                controls
                                                playsInline
                                                preload="metadata"
                                            />
                                            <p>Video mẫu · 20.mp4 · 46,81 giây</p>
                                        </section>
                                        <section className="report-demo-analysis-copy">
                                            {screen === "analysis" && (
                                                <>
                                                    <span className="report-demo-status">
                                                        <Check size={15} /> Nhận định sơ bộ đã lưu
                                                    </span>
                                                    <h2>Nội dung AI nhận diện</h2>
                                                    <p>{fixture.quickSummary.summary}</p>
                                                    <div className="report-demo-observations">
                                                        {fixture.quickSummary.observations.map(
                                                            (item, index) => (
                                                                <article key={index}>
                                                                    <small>{item.label}</small>
                                                                    <p>{item.detail}</p>
                                                                </article>
                                                            ),
                                                        )}
                                                    </div>
                                                    <p className="text-xs text-text-secondary">
                                                        Đây là nhận định sơ bộ về video mẫu. Các
                                                        cảnh chi tiết được giữ ở bước Kịch bản.
                                                    </p>
                                                </>
                                            )}
                                            <RemakeSourceAudio
                                                value={fixture.quickSummary.sourceAudio}
                                                preliminary={screen === "analysis"}
                                            />
                                        </section>
                                    </div>
                                )}
                                {screen === "storyboard" && (
                                    <RemakeStoryboard
                                        compileResult={fixture.compiled}
                                        referenceUrl={`${DEMO_ASSETS}reference.mp4`}
                                        productUrl={images[primary]}
                                        onSceneChange={() => void demoOnly()}
                                    />
                                )}
                                {screen === "output" && (
                                    <RemakeOutput
                                        key={screen}
                                        workspaceId="report-demo"
                                        project={project}
                                        result={null}
                                        repairCandidate={clipCandidate}
                                        busy={false}
                                        productUrl={images[primary]}
                                        onRepair={async () => {
                                            await demoOnly();
                                            return null;
                                        }}
                                        onRepairGroup={confirmDemoClipRepair}
                                        onAccept={async (sceneId, versionId) => {
                                            if (
                                                clipCandidate?.sceneId === sceneId &&
                                                clipCandidate.versionId === versionId
                                            ) {
                                                const affected =
                                                    clipCandidate.affectedVersions ?? [];
                                                setProject(
                                                    (current) =>
                                                        current && {
                                                            ...current,
                                                            scenes: current.scenes.map((scene) => {
                                                                const binding = affected.find(
                                                                    (value) =>
                                                                        value.sceneId === scene.id,
                                                                );
                                                                return binding
                                                                    ? {
                                                                          ...scene,
                                                                          activeVersionId:
                                                                              binding.candidateVersionId,
                                                                      }
                                                                    : scene;
                                                            }),
                                                            draftTimeline:
                                                                current.draftTimeline && {
                                                                    ...current.draftTimeline,
                                                                    items: current.draftTimeline.items.map(
                                                                        (item) => {
                                                                            const binding =
                                                                                affected.find(
                                                                                    (value) =>
                                                                                        value.sceneId ===
                                                                                        item.renderUnitId,
                                                                                );
                                                                            return binding
                                                                                ? {
                                                                                      ...item,
                                                                                      versionId:
                                                                                          binding.candidateVersionId,
                                                                                      reviewed: false,
                                                                                  }
                                                                                : item;
                                                                        },
                                                                    ),
                                                                },
                                                            finalVideoUrl: "",
                                                            preview: {
                                                                schemaVersion: 1,
                                                                status: "processing",
                                                            },
                                                        },
                                                );
                                                setClipCandidate(null);
                                                setNotice(
                                                    "Đã áp dụng cả clip trong dữ liệu minh họa. Trạng thái ghép tiếp theo được mô phỏng, không gọi AI.",
                                                );
                                                return true;
                                            }
                                            setProject(
                                                (current) =>
                                                    current &&
                                                    applyDemoVersion(current, sceneId, versionId),
                                            );
                                            return true;
                                        }}
                                        onRefresh={() => void demoOnly()}
                                        onTimelineSave={async (items) =>
                                            setProject(
                                                (current) =>
                                                    current && selectDemoRanges(current, items),
                                            )
                                        }
                                        onPublish={async () => {
                                            if (previewStatus) {
                                                setProject(
                                                    (current) =>
                                                        current &&
                                                        createRemakePreviewDemo(current, "ready"),
                                                );
                                                setNotice(
                                                    "Đã chuyển bộ minh họa sang preview sẵn sàng. Không gửi tác vụ AI.",
                                                );
                                                return;
                                            }
                                            setProject(
                                                (current) =>
                                                    current && {
                                                        ...current,
                                                        finalVideoUrl: `${DEMO_ASSETS}preview.mp4`,
                                                    },
                                            );
                                            setNotice(
                                                "Đang xem bản ghép 16 giây đã chuẩn bị từ hai đoạn 8 giây; lựa chọn cắt mới chỉ lưu trong demo.",
                                            );
                                        }}
                                        guided
                                    />
                                )}
                                {screen === "compare" && (
                                    <RemakeDemoComparison
                                        project={project}
                                        comparison={fixture.comparison}
                                        onChoose={(versionId) => {
                                            setProject(
                                                (current) =>
                                                    current &&
                                                    applyDemoVersion(
                                                        current,
                                                        fixture.comparison.sceneId,
                                                        versionId,
                                                    ),
                                            );
                                            setNotice(
                                                "Đã lưu lựa chọn trong bản demo. Dữ liệu dự án thật được giữ nguyên.",
                                            );
                                        }}
                                    />
                                )}
                                {screen === "inspector" && (
                                    <RemakeInspector
                                        project={project}
                                        busy={false}
                                        onInspect={demoOnly}
                                        onReview={demoOnly}
                                        onSeek={seekEvidence}
                                    />
                                )}
                                {screen === "export" && <RemakeDemoExport project={project} />}
                                {screen === "deletion" && (
                                    <RemakeProjectControls
                                        project={project}
                                        busy={false}
                                        onApprove={demoOnly}
                                        onExport={demoOnly}
                                        onRestore={demoOnly}
                                        onDelete={demoOnly}
                                    />
                                )}
                                {(screen === "inputs" || screen === "storyboard") && (
                                    <details className="report-demo-generated">
                                        <summary>Ảnh OpenAI đã sinh · 2 ảnh</summary>
                                        <div>
                                            {["opening.png", "two-scenes.png"].map(
                                                (name, index) => (
                                                    <figure key={name}>
                                                        <img
                                                            src={`${DEMO_ASSETS}${name}`}
                                                            alt={`Ảnh OpenAI đã sinh ${index + 1}`}
                                                        />
                                                        <figcaption>
                                                            {index === 0
                                                                ? "Pink Delsey Luggage Travel Snapshot"
                                                                : "Blush Delsey Suitcase, Two Scenes"}
                                                        </figcaption>
                                                    </figure>
                                                ),
                                            )}
                                        </div>
                                    </details>
                                )}
                            </>
                        )}
                        {notice && (
                            <p role="status" className="report-demo-notice">
                                {notice}
                            </p>
                        )}
                        <Dialog
                            open={Boolean(evidence)}
                            onOpenChange={(open) => {
                                if (!open) setEvidence(null);
                            }}
                        >
                            <DialogContent className="max-w-3xl">
                                <DialogTitle>Bằng chứng kiểm tra</DialogTitle>
                                <DialogDescription>
                                    Media của báo cáo Inspector thật · {evidence?.timebase}
                                </DialogDescription>
                                {evidence?.kind === "image" ? (
                                    <img
                                        src={evidence.url}
                                        alt="Ảnh bằng chứng kiểm tra"
                                        className="mx-auto max-h-[65dvh] object-contain"
                                    />
                                ) : (
                                    evidence && (
                                        <RemakePlayer
                                            url={evidence.url}
                                            scope={{
                                                start: evidence.startSecond!,
                                                end: evidence.endSecond!,
                                            }}
                                            versionLabel="Bằng chứng"
                                        />
                                    )
                                )}
                            </DialogContent>
                        </Dialog>
                        <RemakeActionConfirmation
                            intent={clipConfirmation?.intent ?? null}
                            preflight={clipConfirmation?.preflight ?? null}
                            snapshot={{
                                requirements: project?.requirements ?? {
                                    intent: DEFAULT_REMAKE_INTENT,
                                    keep: [],
                                    replace: [],
                                    forbid: [],
                                    claims: [],
                                    requiresCharacter: false,
                                },
                                rights: project?.rights ?? emptyRemakeRights(),
                                budget: { mode: "unlimited" },
                            }}
                            loading={false}
                            submitting={false}
                            error={null}
                            sceneLabel={clipConfirmation?.label}
                            productUrl={images[primary]}
                            sourceUrl={project?.sourceVideoUrl}
                            hasCharacter={Boolean(project?.characterImageUrl)}
                            onCancel={() => setClipConfirmation(null)}
                            onRetry={() =>
                                setNotice(
                                    "Đây là đề xuất trong fixture UI; không gọi API để lấy đề xuất mới.",
                                )
                            }
                            onConfirm={async () => {
                                setClipConfirmation(null);
                                setNotice(
                                    "Đã xác nhận trong bộ minh họa. Không gọi AI hoặc tạo lượt trả phí.",
                                );
                            }}
                        />
                    </div>
                </main>
            </div>
        </div>
    );
}
