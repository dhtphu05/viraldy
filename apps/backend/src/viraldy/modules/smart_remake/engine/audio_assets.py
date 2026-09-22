import subprocess
import tempfile
import uuid
from pathlib import Path

from viraldy.modules.smart_remake.runtime_paths import OUTPUTS_DIR

from .errors import SmartRemakeError
from .media_binaries import ffmpeg_path
from .schemas import UploadedMedia


AUDIO_ASSET_DIR = OUTPUTS_DIR / "smart-remake-assets" / "audio"


def extract_reference_music(media: UploadedMedia) -> dict[str, str]:
    if not media.bytes:
        raise SmartRemakeError("Reference video is empty.", "INVALID_ANALYZE_INPUT")
    AUDIO_ASSET_DIR.mkdir(parents=True, exist_ok=True)
    asset_id = str(uuid.uuid4())
    output_path = AUDIO_ASSET_DIR / f"{asset_id}.m4a"
    ffmpeg = ffmpeg_path()
    with tempfile.TemporaryDirectory(prefix="smart-remake-ref-audio-") as tmp:
        input_path = Path(tmp) / f"reference{_extension(media)}"
        input_path.write_bytes(media.bytes)
        subprocess.run(
            [ffmpeg, "-y", "-i", str(input_path), "-vn", "-acodec", "aac", "-b:a", "192k", str(output_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    if not output_path.exists():
        raise SmartRemakeError(
            "Reference music extraction produced no audio file.",
            "SMART_REMAKE_AUDIO_EXTRACTION_FAILED",
        )
    return {"assetId": asset_id, "filePath": str(output_path)}


def mux_reference_music(video_bytes: bytes, music_asset_id: str, video_has_audio: bool) -> bytes:
    music_path = AUDIO_ASSET_DIR / f"{_safe_asset_id(music_asset_id)}.m4a"
    if not music_path.exists():
        raise SmartRemakeError(
            "Reference music asset is missing.",
            "SMART_REMAKE_REFERENCE_MUSIC_MISSING",
            {"assetId": music_asset_id},
        )
    ffmpeg = ffmpeg_path()
    with tempfile.TemporaryDirectory(prefix="smart-remake-mux-") as tmp:
        input_path = Path(tmp) / "input.mp4"
        output_path = Path(tmp) / "output.mp4"
        input_path.write_bytes(video_bytes)
        if video_has_audio:
            args = [
                ffmpeg, "-y", "-i", str(input_path), "-stream_loop", "-1", "-i", str(music_path),
                "-filter_complex", "[1:a]volume=0.22[music];[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[a]",
                "-map", "0:v:0", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(output_path),
            ]
        else:
            args = [
                ffmpeg, "-y", "-i", str(input_path), "-stream_loop", "-1", "-i", str(music_path),
                "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(output_path),
            ]
        subprocess.run(args, check=True, capture_output=True, text=True)
        return output_path.read_bytes()


def _extension(media: UploadedMedia) -> str:
    if media.file_name and "." in media.file_name:
        suffix = Path(media.file_name).suffix
        if 2 <= len(suffix) <= 6:
            return suffix
    if media.mime_type == "video/webm":
        return ".webm"
    if media.mime_type == "video/quicktime":
        return ".mov"
    return ".mp4"


def _safe_asset_id(asset_id: str) -> str:
    if not asset_id.replace("-", "").replace("_", "").isalnum():
        raise SmartRemakeError("Invalid Smart Remake audio asset id.", "INVALID_SMART_REMAKE_INPUT")
    return asset_id
