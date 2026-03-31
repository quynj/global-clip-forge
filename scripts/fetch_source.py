#!/usr/bin/env python3
import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> int:
    print("Running:", " ".join(cmd))
    return subprocess.run(cmd).returncode


def download_subtitles(yt_dlp: str, url: str, output_tpl: str) -> int:
    # Prefer English for downstream analysis, then fall back to Simplified Chinese
    # when English is unavailable.
    base = [
        yt_dlp,
        "--no-playlist",
        "--cookies-from-browser",
        "chrome",
        "--write-auto-sub",
        "--write-sub",
        "--convert-subs",
        "srt",
        "--skip-download",
        "-o",
        output_tpl,
    ]
    for langs in ("en,en-US,en-orig", "zh-Hans,zh-CN,zh"):
        code = run(base + ["--sub-langs", langs, url])
        if code == 0:
            return 0
    return 1


def download_video(yt_dlp: str, url: str, output_tpl: str) -> int:
    # The Android client path is currently the most reliable way to fetch a
    # simple MP4 from YouTube without a separate merge step.
    cmd = [
        yt_dlp,
        "--extractor-args",
        "youtube:player_client=android",
        "-f",
        "18",
        "-o",
        output_tpl,
        url,
    ]
    return run(cmd)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download a YouTube video and subtitles.")
    parser.add_argument("url", help="YouTube URL")
    parser.add_argument("output_dir", help="Directory to save source assets")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Support both a PATH install and the common user-site install location.
    yt_dlp = shutil.which("yt-dlp") or str(Path.home() / "Library/Python/3.9/bin/yt-dlp")
    if not Path(yt_dlp).exists() and shutil.which(yt_dlp) is None:
        print("yt-dlp not found", file=sys.stderr)
        return 1

    output_tpl = str(output_dir / "%(title)s [%(id)s].%(ext)s")
    sub_code = download_subtitles(yt_dlp, args.url, output_tpl)
    if sub_code != 0:
        print("subtitle download failed", file=sys.stderr)
        return sub_code

    video_code = download_video(yt_dlp, args.url, output_tpl)
    if video_code != 0:
        print("video download failed", file=sys.stderr)
    return video_code


if __name__ == "__main__":
    raise SystemExit(main())
