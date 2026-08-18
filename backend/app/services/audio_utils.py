import os
import shutil


def resolve_ffmpeg_bin() -> str | None:
    """Return an ffmpeg executable path (system PATH, FFMPEG_BIN, or bundled)."""
    custom = os.environ.get("FFMPEG_BIN", "").strip()
    if custom:
        return custom

    system = shutil.which("ffmpeg")
    if system:
        return system

    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return None
