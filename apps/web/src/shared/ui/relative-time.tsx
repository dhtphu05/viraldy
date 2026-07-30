import { formatDistanceToNow } from "date-fns";
import { useEffect, useState } from "react";
import { formatUtcDateTime, toValidDate } from "@/shared/lib/date-format";

export function RelativeTime({
    value,
    addSuffix = true,
    className,
}: {
    value?: string | Date | null;
    addSuffix?: boolean;
    className?: string;
}) {
    const date = value ? toValidDate(value) : null;
    const iso = date?.toISOString() ?? "";
    const [label, setLabel] = useState(() => (date ? formatUtcDateTime(date) : "—"));

    useEffect(() => {
        if (!iso) {
            setLabel("—");
            return;
        }
        setLabel(formatDistanceToNow(new Date(iso), { addSuffix }));
    }, [addSuffix, iso]);

    if (!date) return <span className={className}>—</span>;

    return (
        <time className={className} dateTime={iso} title={formatUtcDateTime(date)}>
            {label}
        </time>
    );
}
