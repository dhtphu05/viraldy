import { Activity, Loader2, Mic2, Music2 } from "lucide-react";
import { getRemakeSourceAudio } from "../lib/remake-source-audio";
import "./remake-source-audio.css";

interface Props {
    value?: unknown;
    pending?: boolean;
    preliminary?: boolean;
}

const speechLabels = {
    present: "Đã nhận diện lời thoại",
    not_detected: "Chưa nhận diện lời thoại",
    unclear: "Chưa nghe rõ lời thoại",
};
const musicLabels = {
    present: "Có nhạc nền",
    not_detected: "Chưa nhận diện nhạc nền",
    unclear: "Chưa nghe rõ nhạc nền",
};
const paceLabels = {
    slow: "Nhịp chậm",
    medium: "Nhịp vừa",
    fast: "Nhịp nhanh",
    unclear: "Chưa rõ nhịp",
};

export function RemakeSourceAudio({ value, pending = false, preliminary = false }: Props) {
    const audio = getRemakeSourceAudio(value);
    if (!audio && !pending) return null;
    return (
        <section className="remake-source-audio" aria-label="Âm thanh trong video mẫu">
            <header>
                <h3>Âm thanh trong video mẫu</h3>
                {audio && (
                    <span>
                        {preliminary ? "Nhận diện sơ bộ từ video mẫu" : "AI nhận diện từ video mẫu"}
                    </span>
                )}
            </header>
            {audio ? (
                <>
                    <dl className="remake-source-audio__facts">
                        <div>
                            <dt>
                                <Mic2 aria-hidden="true" /> Lời thoại
                            </dt>
                            <dd>{speechLabels[audio.speech]}</dd>
                            {audio.language && (
                                <dd className="remake-source-audio__detail">{audio.language}</dd>
                            )}
                        </div>
                        <div>
                            <dt>
                                <Music2 aria-hidden="true" /> Nhạc nền
                            </dt>
                            <dd>{musicLabels[audio.music]}</dd>
                            {audio.description && (
                                <dd className="remake-source-audio__detail">{audio.description}</dd>
                            )}
                        </div>
                        {audio.pace && (
                            <div>
                                <dt>
                                    <Activity aria-hidden="true" /> Nhịp âm thanh
                                </dt>
                                <dd>{paceLabels[audio.pace]}</dd>
                            </div>
                        )}
                    </dl>
                    {audio.transcript && (
                        <details className="remake-source-audio__transcript" open>
                            <summary tabIndex={0}>Trích lời thoại nghe được</summary>
                            <p tabIndex={0}>{audio.transcript}</p>
                        </details>
                    )}
                    <small>
                        Thông tin AI nhận diện có thể chưa đầy đủ; đối chiếu với video mẫu.
                    </small>
                </>
            ) : (
                <p className="remake-source-audio__pending">
                    <Loader2 aria-hidden="true" /> Đang đọc lời thoại, nhạc và nhịp từ video mẫu.
                </p>
            )}
        </section>
    );
}
