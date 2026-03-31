#!/usr/bin/env python3
import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


def run(cmd: list[str]) -> int:
    print("Running:", " ".join(cmd))
    return subprocess.run(cmd).returncode


def probe_duration_seconds(media_path: Path) -> Optional[float]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None

    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(media_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None

    try:
        duration = float(result.stdout.strip())
    except ValueError:
        return None
    return duration if duration > 0 else None


def choose_model(media_path: Path, requested_model: str) -> str:
    if requested_model and requested_model != "auto":
        return requested_model

    duration_seconds = probe_duration_seconds(media_path)
    if duration_seconds is not None and duration_seconds >= 3600:
        print("Auto-selected Whisper model: base (video is longer than 1 hour)")
        return "base"

    if duration_seconds is not None:
        print("Auto-selected Whisper model: small (video is 1 hour or shorter)")
    else:
        print("Auto-selected Whisper model: small (duration probe unavailable)")
    return "small"


def transcribe_with_whisper_cli(
    media_path: Path,
    output_dir: Path,
    model: str,
    language: str,
    task: str,
) -> int:
    whisper = shutil.which("whisper")
    if whisper:
        cmd = [
            whisper,
            str(media_path),
            "--model",
            model,
            "--output_dir",
            str(output_dir),
            "--output_format",
            "srt",
            "--task",
            task,
            "--fp16",
            "False",
        ]
        if language:
            cmd.extend(["--language", language])
        return run(cmd)

    cmd = [
        sys.executable,
        "-m",
        "whisper",
        str(media_path),
        "--model",
        model,
        "--output_dir",
        str(output_dir),
        "--output_format",
        "srt",
        "--task",
        task,
        "--fp16",
        "False",
    ]
    if language:
        cmd.extend(["--language", language])
    return run(cmd)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate SRT subtitles with an open-source Whisper transcription model. "
            "Use this to create source-language subtitles when the video has no platform subtitles."
        )
    )
    parser.add_argument("input_media")
    parser.add_argument("output_srt")
    parser.add_argument(
        "--model",
        default="auto",
        help=(
            "Whisper model name. Defaults to auto: use base for videos longer than "
            "1 hour, otherwise small."
        ),
    )
    parser.add_argument(
        "--language",
        default="",
        help="Optional source language hint such as en or zh. Leave empty for auto-detect.",
    )
    parser.add_argument(
        "--task",
        choices=["transcribe", "translate"],
        default="transcribe",
        help="Use translate to ask Whisper to emit English subtitles from non-English speech.",
    )
    args = parser.parse_args()

    media_path = Path(args.input_media).expanduser().resolve()
    output_srt = Path(args.output_srt).expanduser().resolve()
    output_dir = output_srt.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    model = choose_model(media_path, args.model)

    code = transcribe_with_whisper_cli(media_path, output_dir, model=model, language=args.language, task=args.task)
    if code != 0:
        print("whisper transcription failed", file=sys.stderr)
        return code

    generated = output_dir / f"{media_path.stem}.srt"
    if not generated.exists():
        print(f"expected Whisper output not found: {generated}", file=sys.stderr)
        return 1

    if generated != output_srt:
        generated.replace(output_srt)
    print(output_srt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
