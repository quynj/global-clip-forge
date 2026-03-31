#!/usr/bin/env python3
import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> int:
    print("Running:", " ".join(cmd))
    return subprocess.run(cmd).returncode


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
    parser.add_argument("--model", default="small")
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

    code = transcribe_with_whisper_cli(media_path, output_dir, model=args.model, language=args.language, task=args.task)
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
