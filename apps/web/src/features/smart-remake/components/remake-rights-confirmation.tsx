import { useRef, useState } from "react";
import { ExternalLink, ShieldCheck } from "lucide-react";
import type { SmartRemakeRights } from "@/shared/api/smart-remake";
import { Button } from "@/shared/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/shared/ui/dialog";
import {
    MEDIA_RIGHTS_ATTESTATION_TEXT,
    MEDIA_RIGHTS_POLICY_PATH,
    MEDIA_RIGHTS_POLICY_SUMMARY,
} from "@/features/policies/media-rights-policy";
import { confirmRemakeMediaRights } from "../lib/remake-intake";

interface Props {
    open: boolean;
    onOpenChange(open: boolean): void;
    rights: SmartRemakeRights;
    onConfirm(rights: SmartRemakeRights): void;
    disabled?: boolean;
}

export function RemakeRightsConfirmation(props: Props) {
    return (
        <Dialog open={props.open} onOpenChange={props.onOpenChange}>
            {props.open && <ConfirmationContent {...props} />}
        </Dialog>
    );
}

function ConfirmationContent({ rights, onConfirm, onOpenChange, disabled }: Props) {
    const trigger = useRef<HTMLElement | null>(null);
    const [accepted, setAccepted] = useState(false);
    const [disclosed, setDisclosed] = useState(false);
    return (
        <DialogContent
            className="max-w-xl gap-5 rounded-3xl p-5 sm:p-7"
            onOpenAutoFocus={() => {
                trigger.current =
                    document.activeElement instanceof HTMLElement ? document.activeElement : null;
            }}
            onCloseAutoFocus={(event) => {
                if (trigger.current?.isConnected) {
                    event.preventDefault();
                    trigger.current.focus();
                }
            }}
        >
            <div className="flex size-11 items-center justify-center rounded-2xl bg-primary-soft text-primary">
                <ShieldCheck className="size-6" aria-hidden="true" />
            </div>
            <div className="space-y-2 pr-5">
                <DialogTitle className="text-xl leading-snug">
                    Xác nhận quyền sử dụng tư liệu
                </DialogTitle>
                <DialogDescription className="leading-relaxed text-text-secondary">
                    Trước khi phân tích, hãy xác nhận quyền với video và ảnh bạn đã chọn.
                </DialogDescription>
            </div>
            <div className="space-y-3 rounded-2xl bg-surface-soft p-4 text-sm leading-relaxed">
                <ul className="list-disc space-y-2 pl-4 text-text-secondary">
                    {MEDIA_RIGHTS_POLICY_SUMMARY.map((item) => (
                        <li key={item}>{item}</li>
                    ))}
                </ul>
                <a
                    href={MEDIA_RIGHTS_POLICY_PATH}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex min-h-11 items-center gap-2 font-medium text-primary underline underline-offset-4"
                >
                    Đọc chính sách đầy đủ <ExternalLink className="size-4" aria-hidden="true" />
                </a>
            </div>
            <fieldset disabled={disabled} className="space-y-4 text-sm leading-relaxed">
                <legend className="sr-only">Xác nhận của bạn</legend>
                <label className="flex cursor-pointer items-start gap-3">
                    <input
                        type="checkbox"
                        checked={accepted}
                        onChange={(event) => setAccepted(event.target.checked)}
                        className="mt-1 size-5 shrink-0 accent-primary"
                    />
                    <span>{MEDIA_RIGHTS_ATTESTATION_TEXT}</span>
                </label>
                <label className="flex cursor-pointer items-start gap-3">
                    <input
                        type="checkbox"
                        checked={disclosed}
                        onChange={(event) => setDisclosed(event.target.checked)}
                        className="mt-1 size-5 shrink-0 accent-primary"
                    />
                    <span>
                        Tôi đồng ý để Viraldy gửi tư liệu tới Gemini, OpenAI và KIE để phân tích,
                        tạo và kiểm tra video AI.
                    </span>
                </label>
            </fieldset>
            <p className="text-xs leading-relaxed text-text-secondary">
                Lưu xác nhận chưa bắt đầu tạo video hoặc phát sinh lượt gọi AI. Ngân sách được chọn
                riêng cho dự án.
            </p>
            <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                <Button variant="ghost" className="min-h-11" onClick={() => onOpenChange(false)}>
                    Để sau
                </Button>
                <Button
                    className="min-h-11"
                    disabled={disabled || !accepted || !disclosed}
                    onClick={() => {
                        onConfirm(confirmRemakeMediaRights(rights));
                        onOpenChange(false);
                    }}
                >
                    Lưu xác nhận
                </Button>
            </div>
        </DialogContent>
    );
}
