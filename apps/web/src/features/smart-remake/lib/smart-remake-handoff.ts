export type SmartRemakeHandoff = {
    referenceVideo: File;
    productImages: File[];
};

let pendingHandoff: SmartRemakeHandoff | null = null;

export function setSmartRemakeHandoff(handoff: SmartRemakeHandoff) {
    pendingHandoff = handoff;
}

export function consumeSmartRemakeHandoff(): SmartRemakeHandoff | null {
    const handoff = pendingHandoff;
    pendingHandoff = null;
    return handoff;
}

export function clearSmartRemakeHandoff(handoff: SmartRemakeHandoff) {
    if (pendingHandoff === handoff) pendingHandoff = null;
}
