#!/usr/bin/env python3
import shutil
import subprocess
import sys
from pathlib import Path


def ffmpeg_exe() -> str:
    direct = shutil.which("ffmpeg")
    if direct:
        return direct

    try:
        # Fall back to imageio-ffmpeg so the helper scripts still work in
        # environments where ffmpeg was installed only as a Python package.
        out = subprocess.check_output(
            [sys.executable, "-c", "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"],
            text=True,
        ).strip()
    except Exception as exc:
        raise RuntimeError("ffmpeg not available; install imageio-ffmpeg or system ffmpeg") from exc

    if not out or not Path(out).exists():
        raise RuntimeError("ffmpeg executable path not found")
    return out
