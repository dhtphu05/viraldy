import { describe, expect, it } from "vitest";
import { getRemakeClipCandidate, getRemakeClipGroups } from "./remake-clip-groups";
import { clipProject, groupCandidate } from "./remake-clip-groups.fixture";

describe("saved provider clip groups", () => {
    it("preserves an eight-second historical window when its group raw count is absent", () => {
        const project = clipProject();
        const legacy = {
            ...project,
            renderPlan: {
                ...project.renderPlan!,
                units: project.renderPlan!.units.map((unit) => ({
                    ...unit,
                    rawDurationFrames: 192,
                })),
                groups: project.renderPlan!.groups!.map(
                    ({ rawDurationFrames: _omitted, ...group }) => group,
                ),
            },
        } as unknown as typeof project;
        expect(getRemakeClipGroups(legacy).map((group) => group.durationSeconds)).toEqual([8, 8]);
    });
    it("invalidates the group draft and candidate when the selected trim changes", () => {
        const { project, group, receipt } = groupCandidate();
        const changed = {
            ...project,
            draftTimeline: {
                ...project.draftTimeline!,
                items: project.draftTimeline!.items.map((item, index) =>
                    index
                        ? item
                        : { ...item, inFrame: item.inFrame + 1, outFrame: item.outFrame + 1 },
                ),
            },
        };
        const current = getRemakeClipGroups(changed)[0];
        expect(current.ready).toBe(true);
        expect(current.usesDefaultRanges).toBe(false);
        expect(current.baseFingerprint).not.toBe(group.baseFingerprint);
        expect(current.videoUrl).toBe(group.videoUrl);
        expect(getRemakeClipCandidate(changed, current, receipt)).toBeNull();
    });
    it("maps twenty-five source fragments to exactly two complete six-second clips", () => {
        const project = clipProject();
        const groups = getRemakeClipGroups(project);
        expect(groups).toHaveLength(2);
        expect(
            groups.map((group) => [group.startSecond, group.endSecond, group.durationSeconds]),
        ).toEqual([
            [0, 6, 6],
            [6, 12, 6],
        ]);
        expect(groups.every((group) => group.ready)).toBe(true);
        expect(groups.map((group) => group.memberIds.length)).toEqual([12, 13]);
        expect(
            getRemakeClipGroups({
                ...project,
                renderPlan: { ...project.renderPlan!, groupingPolicy: undefined },
            }),
        ).toEqual([]);
    });
    it("does not select a group's clip from mixed active media or failed technical checks", () => {
        const project = clipProject();
        const mixed = {
            ...project,
            scenes: project.scenes.map((scene, index) =>
                index !== 1
                    ? scene
                    : {
                          ...scene,
                          versions: scene.versions.map((version) => ({
                              ...version,
                              technicalCheck: {
                                  ...version.technicalCheck,
                                  mediaHash: "other-video",
                              },
                          })),
                      },
            ),
        };
        expect(getRemakeClipGroups(mixed)[0]).toMatchObject({ ready: false, videoUrl: undefined });
        expect(getRemakeClipGroups(mixed)[1].ready).toBe(true);
    });
    it("requires the authoritative anchor receipt and all exact candidate bindings", () => {
        const { project, group, receipt } = groupCandidate();
        expect(getRemakeClipCandidate(project, group, receipt)?.version.id).toBe("candidate-0");
        expect(
            getRemakeClipCandidate(project, group, {
                projectId: project.id,
                sceneId: receipt.sceneId,
                versionId: receipt.versionId,
            }),
        ).toBeNull();
        expect(
            getRemakeClipCandidate(project, group, {
                ...receipt,
                affectedVersions: receipt.affectedVersions.slice(1),
            }),
        ).toBeNull();
        expect(
            getRemakeClipCandidate(project, group, { ...receipt, operationId: "different-repair" }),
        ).toBeNull();
        expect(
            getRemakeClipCandidate(project, group, { ...receipt, projectId: "other" }),
        ).toBeNull();
        expect(
            getRemakeClipCandidate(project, group, {
                ...receipt,
                affectedVersions: receipt.affectedVersions.map((binding, index) =>
                    index !== 1 ? binding : { ...binding, candidateVersionId: null },
                ),
            }),
        ).toBeNull();
    });
    it("rejects an inconsistent member instead of guessing from the latest version", () => {
        const { project, group, receipt } = groupCandidate();
        const changed = {
            ...project,
            scenes: project.scenes.map((scene, index) =>
                index !== 1
                    ? scene
                    : {
                          ...scene,
                          versions: scene.versions.map((version) =>
                              version.id !== "candidate-1"
                                  ? version
                                  : {
                                        ...version,
                                        mediaHash: "different",
                                        technicalCheck: {
                                            ...version.technicalCheck,
                                            mediaHash: "different",
                                        },
                                    },
                          ),
                      },
            ),
        };
        expect(getRemakeClipCandidate(changed, group, receipt)).toBeNull();
        const advanced = {
            ...project,
            scenes: project.scenes.map((scene, index) =>
                index ? scene : { ...scene, activeVersionId: "another-active" },
            ),
        };
        expect(getRemakeClipCandidate(advanced, group, receipt)).toBeNull();
    });
    it.each(["parent", "request", "range", "missing"])(
        "rejects an inconsistent candidate %s binding",
        (kind) => {
            const { project, group, receipt } = groupCandidate();
            const changed = {
                ...project,
                scenes: project.scenes.map((scene, index) =>
                    index !== 1
                        ? scene
                        : {
                              ...scene,
                              versions: scene.versions.flatMap((version) => {
                                  if (version.id !== "candidate-1") return [version];
                                  if (kind === "missing") return [];
                                  if (kind === "parent")
                                      return [{ ...version, parentVersionId: "other-base" }];
                                  if (kind === "request")
                                      return [
                                          {
                                              ...version,
                                              providerMetadata: {
                                                  ...version.providerMetadata,
                                                  requestId: "other-task",
                                              },
                                          },
                                      ];
                                  return [
                                      {
                                          ...version,
                                          providerMetadata: {
                                              ...version.providerMetadata,
                                              repairBaseTimeline: [],
                                          },
                                      },
                                  ];
                              }),
                          },
                ),
            };
            expect(getRemakeClipCandidate(changed, group, receipt)).toBeNull();
        },
    );
});
