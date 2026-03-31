#!/usr/bin/env python3
import argparse
from pathlib import Path
from typing import Optional

try:
    from scripts.parse_subtitles import parse_srt
    from scripts.trim_subtitles import fmt_time
except ModuleNotFoundError:
    from parse_subtitles import parse_srt
    from trim_subtitles import fmt_time


def overlap_seconds(a: dict, b: dict) -> float:
    return max(0.0, min(a["end_seconds"], b["end_seconds"]) - max(a["start_seconds"], b["start_seconds"]))


def find_best_match(cue: dict, candidates: list[dict], tolerance: float) -> Optional[dict]:
    best = None
    best_overlap = 0.0
    for candidate in candidates:
        overlap = overlap_seconds(cue, candidate)
        start_delta = abs(cue["start_seconds"] - candidate["start_seconds"])
        end_delta = abs(cue["end_seconds"] - candidate["end_seconds"])
        if overlap <= 0 and (start_delta > tolerance or end_delta > tolerance):
            continue
        if overlap > best_overlap:
            best = candidate
            best_overlap = overlap
    return best


def merge_cues(primary: list[dict], secondary: list[dict], primary_first: bool, tolerance: float) -> list[dict]:
    merged = []
    for cue in primary:
        match = find_best_match(cue, secondary, tolerance=tolerance)
        lines = [cue["text"].strip()]
        if match and match["text"].strip() and match["text"].strip() != cue["text"].strip():
            if primary_first:
                lines = [cue["text"].strip(), match["text"].strip()]
            else:
                lines = [match["text"].strip(), cue["text"].strip()]
        merged.append(
            {
                "start_seconds": cue["start_seconds"],
                "end_seconds": cue["end_seconds"],
                "text": "\n".join(line for line in lines if line),
            }
        )
    return merged


def write_srt(cues: list[dict], output_path: Path) -> None:
    lines = []
    for idx, cue in enumerate(cues, start=1):
        lines.append(str(idx))
        lines.append(f"{fmt_time(cue['start_seconds'])} --> {fmt_time(cue['end_seconds'])}")
        lines.extend(cue["text"].splitlines())
        lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge two SRT files into stacked bilingual subtitles.")
    parser.add_argument("primary_srt")
    parser.add_argument("secondary_srt")
    parser.add_argument("output_srt")
    parser.add_argument(
        "--primary-first",
        action="store_true",
        help="Place the primary subtitle on the first line and the secondary subtitle on the second line.",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.35,
        help="Maximum start/end timing difference to consider non-overlapping cues a match.",
    )
    args = parser.parse_args()

    primary = parse_srt(Path(args.primary_srt).read_text(encoding="utf-8", errors="ignore"))
    secondary = parse_srt(Path(args.secondary_srt).read_text(encoding="utf-8", errors="ignore"))
    merged = merge_cues(primary, secondary, primary_first=args.primary_first, tolerance=args.tolerance)
    output_path = Path(args.output_srt)
    write_srt(merged, output_path)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
