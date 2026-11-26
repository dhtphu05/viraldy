import { useId } from "react";
import { ExternalLink, ShieldCheck } from "lucide-react";
import { MEDIA_RIGHTS_POLICY_PATH } from "@/features/policies/media-rights-policy";
import { Button } from "@/shared/ui/button";
import type {
    SmartRemakeRequirements,
    SmartRemakeRights,
    SmartRemakeBudgetPolicy,
    SmartRemakeRightsDeclaration,
} from "@/shared/api/smart-remake";
import { Input } from "@/shared/ui/input";
import { Textarea } from "@/shared/ui/textarea";
import { DEFAULT_REMAKE_INTENT, hasCurrentRemakeRightsAttestation } from "../lib/remake-intake";

export interface RemakeProjectInputsProps {
    requirements: SmartRemakeRequirements;
    rights: SmartRemakeRights;
    budget?: SmartRemakeBudgetPolicy;
    onRequirementsChange(value: SmartRemakeRequirements): void;
    onRightsChange(value: SmartRemakeRights): void;
    onBudgetChange?(value: SmartRemakeBudgetPolicy): void;
    characterFile?: File | null;
    characterUrl?: string | null;
    onCharacterChange(file: File | null): void;
    disabled?: boolean;
    rightsSectionId?: string;
    onRightsConfirmationOpen(): void;
    presentation?: "full" | "details";
}

export function RemakeProjectInputs(props: RemakeProjectInputsProps) {
    const id = useId();
    const { requirements, rights, disabled } = props;
    const character = requirements.requiresCharacter;
    const full = props.presentation !== "details";
    const declaration = (
        role: "source" | "product" | "character",
        value: SmartRemakeRightsDeclaration,
    ) => props.onRightsChange({ ...rights, [role]: value });
    return (
        <section
            aria-label={full ? "Yêu cầu và quyền sử dụng tư liệu" : "Yêu cầu bổ sung cho video"}
            className="mx-auto max-w-4xl space-y-5 rounded-3xl bg-surface p-5 sm:p-6"
        >
            <fieldset disabled={disabled} className="min-w-0 space-y-4">
                <legend className="mb-3 font-semibold text-text-primary">
                    Yêu cầu cần giữ đúng
                </legend>
                <label className="block space-y-2 text-sm" htmlFor={`${id}-intent`}>
                    <span>Mục tiêu video</span>
                    <Textarea
                        id={`${id}-intent`}
                        value={requirements.intent}
                        maxLength={4000}
                        placeholder={DEFAULT_REMAKE_INTENT}
                        aria-describedby={`${id}-intent-help`}
                        onChange={(event) =>
                            props.onRequirementsChange({
                                ...requirements,
                                intent: event.target.value,
                            })
                        }
                    />
                </label>
                <p id={`${id}-intent-help`} className="text-xs text-text-secondary">
                    Không bắt buộc chỉnh. Nếu để trống, hệ thống làm theo video mẫu và dùng sản phẩm
                    của bạn.
                </p>
                <p id={`${id}-requirements-help`} className="text-xs text-text-secondary">
                    Nhập mỗi dòng một yêu cầu. Chỉ khai báo claims bạn có căn cứ.
                </p>
                <div className="grid gap-4 sm:grid-cols-2">
                    {(
                        [
                            ["keep", "Phải giữ"],
                            ["replace", "Cần thay"],
                            ["forbid", "Không được xuất hiện"],
                            ["claims", "Claims được phép"],
                        ] as const
                    ).map(([key, label]) => (
                        <label
                            key={key}
                            htmlFor={`${id}-${key}`}
                            className="block space-y-2 text-sm"
                        >
                            <span>{label}</span>
                            <Textarea
                                id={`${id}-${key}`}
                                aria-describedby={`${id}-requirements-help`}
                                value={requirements[key].join("\n")}
                                onChange={(event) =>
                                    props.onRequirementsChange({
                                        ...requirements,
                                        [key]: event.target.value.split("\n"),
                                    })
                                }
                            />
                        </label>
                    ))}
                </div>
                <label className="flex min-h-11 items-center gap-3 text-sm">
                    <input
                        type="checkbox"
                        checked={character}
                        onChange={(event) =>
                            props.onRequirementsChange({
                                ...requirements,
                                requiresCharacter: event.target.checked,
                            })
                        }
                        className="size-5 accent-primary"
                    />{" "}
                    Có nhân vật cần giữ giống ảnh gốc
                </label>
                {character && (
                    <div className="space-y-3 rounded-2xl bg-surface-soft p-4">
                        <label htmlFor={`${id}-character`} className="block space-y-2 text-sm">
                            <span>Ảnh nhân vật gốc</span>
                            <Input
                                id={`${id}-character`}
                                type="file"
                                accept="image/jpeg,image/png,image/webp"
                                onChange={(event) =>
                                    props.onCharacterChange(event.target.files?.[0] ?? null)
                                }
                            />
                        </label>
                        {props.characterFile && (
                            <p className="break-words text-xs text-text-secondary">
                                {props.characterFile.name}
                            </p>
                        )}
                        {props.characterUrl && (
                            <img
                                src={props.characterUrl}
                                alt="Ảnh nhân vật tham chiếu gốc"
                                className="size-24 rounded-xl object-contain"
                            />
                        )}
                        <fieldset className="space-y-3">
                            <legend className="text-sm font-medium">Đồng ý của nhân vật</legend>
                            <label className="flex min-h-11 items-center gap-3 text-sm">
                                <input
                                    type="checkbox"
                                    checked={rights.characterConsent?.consented ?? false}
                                    className="size-5 accent-primary"
                                    onChange={(event) =>
                                        props.onRightsChange({
                                            ...rights,
                                            characterConsent: {
                                                scope: "",
                                                evidenceNote: "",
                                                ...rights.characterConsent,
                                                consented: event.target.checked,
                                            },
                                        })
                                    }
                                />
                                Có consent cho việc dùng hình ảnh bằng AI
                            </label>
                            <label
                                className="block space-y-2 text-sm"
                                htmlFor={`${id}-consent-scope`}
                            >
                                <span>Phạm vi consent</span>
                                <Input
                                    id={`${id}-consent-scope`}
                                    value={rights.characterConsent?.scope ?? ""}
                                    maxLength={2000}
                                    onChange={(event) =>
                                        props.onRightsChange({
                                            ...rights,
                                            characterConsent: {
                                                consented: false,
                                                evidenceNote: "",
                                                ...rights.characterConsent,
                                                scope: event.target.value,
                                            },
                                        })
                                    }
                                />
                            </label>
                            <label
                                className="block space-y-2 text-sm"
                                htmlFor={`${id}-consent-evidence`}
                            >
                                <span>Căn cứ consent</span>
                                <Textarea
                                    id={`${id}-consent-evidence`}
                                    value={rights.characterConsent?.evidenceNote ?? ""}
                                    maxLength={4000}
                                    onChange={(event) =>
                                        props.onRightsChange({
                                            ...rights,
                                            characterConsent: {
                                                consented: false,
                                                scope: "",
                                                ...rights.characterConsent,
                                                evidenceNote: event.target.value,
                                            },
                                        })
                                    }
                                />
                            </label>
                        </fieldset>
                    </div>
                )}
            </fieldset>
            {full && (
                <fieldset
                    id={props.rightsSectionId}
                    tabIndex={props.rightsSectionId ? -1 : undefined}
                    disabled={disabled}
                    className="min-w-0 scroll-mt-24 space-y-4 focus-visible:outline-2 focus-visible:outline-ring"
                >
                    <legend className="mb-3 font-semibold">Quyền sử dụng tư liệu</legend>
                    <div className="flex flex-wrap items-start gap-3 rounded-2xl bg-surface-soft p-4">
                        <ShieldCheck
                            className="mt-0.5 size-5 shrink-0 text-primary"
                            aria-hidden="true"
                        />
                        <div className="min-w-0 flex-1 space-y-2 text-sm">
                            <p className="font-medium">
                                {hasCurrentRemakeRightsAttestation(rights)
                                    ? "Người dùng đã xác nhận quyền"
                                    : "Xác nhận quyền với video và ảnh của bạn"}
                            </p>
                            <p className="leading-relaxed text-text-secondary">
                                Đọc chính sách và xác nhận bạn có đủ quyền dùng tư liệu để tạo video
                                AI. Đây là cam kết của người dùng, không phải xác minh bản quyền.
                            </p>
                            <a
                                href={MEDIA_RIGHTS_POLICY_PATH}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex min-h-11 items-center gap-1.5 text-primary underline underline-offset-4"
                            >
                                Chính sách sử dụng tư liệu{" "}
                                <ExternalLink className="size-3.5" aria-hidden="true" />
                            </a>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {!hasCurrentRemakeRightsAttestation(rights) && (
                                <Button
                                    variant="outline"
                                    className="min-h-11"
                                    onClick={props.onRightsConfirmationOpen}
                                >
                                    Đọc và xác nhận
                                </Button>
                            )}
                            {hasCurrentRemakeRightsAttestation(rights) && (
                                <Button
                                    variant="ghost"
                                    className="min-h-11"
                                    onClick={() =>
                                        props.onRightsChange({
                                            ...rights,
                                            source: {
                                                ...rights.source,
                                                declared: false,
                                                revoked: true,
                                            },
                                            product: {
                                                ...rights.product,
                                                declared: false,
                                                revoked: true,
                                            },
                                            attestation: {
                                                ...rights.attestation!,
                                                accepted: false,
                                                revoked: true,
                                            },
                                            providerDisclosureAcknowledged: false,
                                        })
                                    }
                                >
                                    Thu hồi xác nhận
                                </Button>
                            )}
                        </div>
                    </div>
                    <details className="rounded-2xl bg-surface-soft p-4 text-sm">
                        <summary className="cursor-pointer py-1 font-medium">
                            Giấy phép, bằng chứng và ghi công (tuỳ chọn)
                        </summary>
                        <p className="my-3 text-xs text-text-secondary">
                            Bổ sung nếu tư liệu có điều kiện cấp phép hoặc cần ghi công.
                        </p>
                        <div className="space-y-3">
                            {(["source", "product"] as const).map((key) => (
                                <RightsFields
                                    key={key}
                                    id={`${id}-${key}`}
                                    optional
                                    label={key === "source" ? "video mẫu" : "ảnh sản phẩm"}
                                    value={rights[key]}
                                    onChange={(next) => declaration(key, next)}
                                />
                            ))}
                        </div>
                    </details>
                </fieldset>
            )}
            {character && (
                <fieldset disabled={disabled}>
                    <RightsFields
                        id={`${id}-character`}
                        label="ảnh nhân vật"
                        value={
                            rights.character ?? {
                                basis: "owned",
                                scope: "",
                                evidenceNote: "",
                                declared: false,
                            }
                        }
                        onChange={(next) => declaration("character", next)}
                    />
                </fieldset>
            )}
        </section>
    );
}

function RightsFields({
    id,
    label,
    value,
    onChange,
    optional = false,
}: {
    id: string;
    label: string;
    value: SmartRemakeRightsDeclaration;
    onChange(value: SmartRemakeRightsDeclaration): void;
    optional?: boolean;
}) {
    return (
        <div className="space-y-3 rounded-2xl bg-surface-soft p-4">
            {!optional && (
                <label className="flex min-h-11 items-center gap-3 text-sm">
                    <input
                        type="checkbox"
                        className="size-5 accent-primary"
                        checked={value.declared && !value.revoked}
                        onChange={(event) =>
                            onChange({ ...value, declared: event.target.checked, revoked: false })
                        }
                    />
                    Tôi có quyền sử dụng {label}
                </label>
            )}
            <label htmlFor={`${id}-basis`} className="block space-y-2 text-sm">
                <span>Căn cứ quyền · {label}</span>
                <select
                    id={`${id}-basis`}
                    className="min-h-11 w-full rounded-xl bg-surface px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    value={value.basis}
                    onChange={(event) =>
                        onChange({
                            ...value,
                            basis: event.target.value as SmartRemakeRightsDeclaration["basis"],
                        })
                    }
                >
                    {optional && <option value="attested">Theo xác nhận quyền sử dụng</option>}
                    <option value="owned">Tôi sở hữu</option>
                    <option value="licensed">Có giấy phép</option>
                    <option value="permission">Được cho phép</option>
                    <option value="public_domain">Phạm vi công cộng</option>
                </select>
            </label>
            <label className="block space-y-2 text-sm" htmlFor={`${id}-scope`}>
                <span>Phạm vi được dùng</span>
                <Input
                    id={`${id}-scope`}
                    required={!optional}
                    value={value.scope}
                    maxLength={2000}
                    onChange={(event) => onChange({ ...value, scope: event.target.value })}
                />
            </label>
            <label className="block space-y-2 text-sm" htmlFor={`${id}-evidence`}>
                <span>Ghi chú bằng chứng quyền</span>
                <Textarea
                    id={`${id}-evidence`}
                    value={value.evidenceNote}
                    maxLength={4000}
                    onChange={(event) => onChange({ ...value, evidenceNote: event.target.value })}
                />
            </label>
            <label className="block space-y-2 text-sm" htmlFor={`${id}-attribution`}>
                <span>Ghi công nếu có</span>
                <Input
                    id={`${id}-attribution`}
                    value={value.attribution ?? ""}
                    maxLength={2000}
                    onChange={(event) =>
                        onChange({ ...value, attribution: event.target.value || null })
                    }
                />
            </label>
        </div>
    );
}
