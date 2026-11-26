/** Byte identity survives browser reloads; File object identity does not. */
export async function hashRemakeFile(file: Blob): Promise<string> {
    const bytes =
        typeof file.arrayBuffer === "function"
            ? await file.arrayBuffer()
            : await new Promise<ArrayBuffer>((resolve, reject) => {
                  const reader = new FileReader();
                  reader.onerror = () =>
                      reject(reader.error ?? new Error("Chưa đọc được tư liệu."));
                  reader.onload = () => resolve(reader.result as ArrayBuffer);
                  reader.readAsArrayBuffer(file);
              });
    const hash = await crypto.subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(hash), (value) => value.toString(16).padStart(2, "0")).join(
        "",
    );
}
