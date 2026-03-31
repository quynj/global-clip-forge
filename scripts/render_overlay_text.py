#!/usr/bin/env python3
import argparse
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont


SUBTITLE_FILL = (248, 244, 236, 255)
TITLE_FILL = (255, 224, 130, 255)
PANEL_FILL = (14, 16, 20, 190)
PANEL_STROKE = (255, 214, 102, 220)
SHADOW_FILL = (0, 0, 0, 110)


def load_font(size: int, fontfile: str = "") -> ImageFont.ImageFont:
    candidates = [fontfile] if fontfile else []
    candidates.extend(
        [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]
    )
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    # Wrap greedily at the character level so mixed Chinese and English text
    # still breaks cleanly without requiring external layout libraries.
    lines: list[str] = []
    current = ""
    for ch in text:
        trial = current + ch
        bbox = draw.textbbox((0, 0), trial, font=font, stroke_width=3)
        if current and (bbox[2] - bbox[0]) > max_width:
            lines.append(current)
            current = ch
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def draw_rounded_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    radius: int,
    fill: tuple[int, int, int, int],
    outline: Optional[tuple[int, int, int, int]] = None,
    width: int = 0,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def render_text_overlay(
    output: Path,
    text: str,
    *,
    width: int = 640,
    height: int = 360,
    fontsize: int = 24,
    position: str = "bottom",
    fontfile: str = "",
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font = load_font(fontsize, fontfile=fontfile)
    lines = wrap_text(draw, text, font, max_width=width - 60)

    line_gap = 10
    metrics = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font, stroke_width=3)
        metrics.append((bbox[2] - bbox[0], bbox[3] - bbox[1]))

    max_line_width = max((line_width for line_width, _ in metrics), default=0)
    text_block_height = sum(line_height for _, line_height in metrics) + line_gap * max(0, len(metrics) - 1)
    start_y = (height - text_block_height) // 2 if position == "center" else height - text_block_height - 24

    panel_padding_x = 24 if position == "center" else 18
    panel_padding_y = 16 if position == "center" else 14
    panel_width = max_line_width + panel_padding_x * 2
    panel_height = text_block_height + panel_padding_y * 2
    panel_x = (width - panel_width) // 2
    panel_y = start_y - panel_padding_y
    panel_box = (panel_x, panel_y, panel_x + panel_width, panel_y + panel_height)

    # The shadow keeps the panel readable on bright footage without making the
    # subtitle plate feel too heavy.
    shadow_box = (panel_box[0], panel_box[1] + 6, panel_box[2], panel_box[3] + 6)
    draw_rounded_panel(draw, shadow_box, radius=24, fill=SHADOW_FILL)
    draw_rounded_panel(
        draw,
        panel_box,
        radius=24,
        fill=PANEL_FILL,
        outline=PANEL_STROKE if position == "center" else None,
        width=2 if position == "center" else 0,
    )

    if position == "bottom":
        accent_y = panel_box[1] + 8
        draw.rounded_rectangle(
            (panel_box[0] + 18, accent_y, panel_box[2] - 18, accent_y + 4),
            radius=2,
            fill=PANEL_STROKE,
        )

    y = start_y
    for line, (line_width, line_height) in zip(lines, metrics):
        x = (width - line_width) // 2
        draw.text(
            (x, y),
            line,
            font=font,
            fill=TITLE_FILL if position == "center" else SUBTITLE_FILL,
            stroke_width=2 if position == "center" else 3,
            stroke_fill=(0, 0, 0, 170 if position == "center" else 220),
        )
        y += line_height + line_gap

    image.save(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("text")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=360)
    parser.add_argument("--fontsize", type=int, default=24)
    parser.add_argument("--position", choices=["bottom", "center"], default="bottom")
    parser.add_argument("--fontfile", default="")
    args = parser.parse_args()

    render_text_overlay(
        Path(args.output),
        args.text,
        width=args.width,
        height=args.height,
        fontsize=args.fontsize,
        position=args.position,
        fontfile=args.fontfile,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
