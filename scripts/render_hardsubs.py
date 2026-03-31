#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path

try:
    from scripts.ffmpeg_locator import ffmpeg_exe
    from scripts.render_overlay_text import render_text_overlay
    from scripts.parse_subtitles import parse_srt
except ModuleNotFoundError:
    from ffmpeg_locator import ffmpeg_exe
    from render_overlay_text import render_text_overlay
    from parse_subtitles import parse_srt


def fmt_time(value: float) -> str:
    return f"{value:.3f}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_video")
    parser.add_argument("input_srt")
    parser.add_argument("output_video")
    parser.add_argument("--title", default="")
    parser.add_argument("--fontfile", default="")
    args = parser.parse_args()

    src = Path(args.input_video)
    srt = Path(args.input_srt)
    dst = Path(args.output_video)
    dst.parent.mkdir(parents=True, exist_ok=True)

    cues = parse_srt(srt.read_text(encoding="utf-8", errors="ignore"))
    if not cues and not args.title:
        print("no subtitles or title to burn", file=sys.stderr)
        return 1

    work_dir = dst.parent / "_overlay_assets"
    work_dir.mkdir(parents=True, exist_ok=True)

    input_cmd = ["-i", str(src)]
    filter_parts = []
    current_label = "[0:v]"
    input_index = 1

    if args.title:
        title_png = work_dir / "title.png"
        # Render the first-second title as a transparent full-frame PNG so we
        # only rely on ffmpeg's basic overlay filter, not optional text filters.
        render_text_overlay(title_png, args.title, position="center", fontsize=30, fontfile=args.fontfile)
        input_cmd.extend(["-loop", "1", "-i", str(title_png)])
        next_label = f"[v{input_index}]"
        filter_parts.append(f"{current_label}[{input_index}:v]overlay=0:0:enable='between(t,0,1)'{next_label}")
        current_label = next_label
        input_index += 1

    for idx, cue in enumerate(cues, start=1):
        png = work_dir / f"sub-{idx:02d}.png"
        # Pre-render every cue to an RGBA image so subtitle burning still works
        # on ffmpeg builds that do not include libass or drawtext support.
        render_text_overlay(png, cue["text"], position="bottom", fontsize=24, fontfile=args.fontfile)
        input_cmd.extend(["-loop", "1", "-i", str(png)])
        next_label = f"[v{input_index}]"
        filter_parts.append(
            f"{current_label}[{input_index}:v]overlay=0:0:enable='between(t,{fmt_time(cue['start_seconds'])},{fmt_time(cue['end_seconds'])})'{next_label}"
        )
        current_label = next_label
        input_index += 1

    cmd = [
        ffmpeg_exe(),
        "-y",
        *input_cmd,
        "-filter_complex",
        ";".join(filter_parts),
        "-map",
        current_label,
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        # The overlay PNG inputs are looped forever, so -shortest keeps the
        # exported clip aligned with the real video duration.
        "-shortest",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(dst),
    ]
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    raise SystemExit(main())
