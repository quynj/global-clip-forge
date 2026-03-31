# zh-clip-forge

Codex skill for turning one long YouTube interview, talk, or podcast into 5 to 8 Chinese-subbed short clips.

## Overview

`zh-clip-forge` is a review-first clipping skill for long-form video.
It helps you download a source video, parse subtitles or transcript data, select self-contained moments, cut short clips, generate Chinese packaging copy, and export hard-subbed MP4s that are ready to review or post.

The current implementation is designed to work in environments where `ffmpeg` may not include `libass` or `drawtext`.
Instead of relying on optional text filters, the hard-sub pipeline renders transparent PNG text overlays and composites them with `ffmpeg overlay`.

## What It Does

- Downloads the source video and available subtitles from YouTube
- Prefers English subtitles for analysis, then falls back to Simplified Chinese when available
- Parses subtitle files into structured JSON for clip selection
- Helps select strong, self-contained moments for short-form distribution
- Cuts sub-3-minute clips from the source video
- Windows local subtitle timelines for each clip
- Burns Chinese subtitles and a first-second title into each exported video
- Writes per-clip metadata plus combined packaging notes for review

## Skill Trigger

Mention:

```text
$zh-clip-forge
```

Example:

```text
Use $zh-clip-forge to turn this YouTube interview URL into 5 to 8 Chinese-subbed short clips.
```

## Typical Workflow

1. Check `yt-dlp` and `ffmpeg`.
2. Create a work folder under `work/<video-slug>/`.
3. Download the source video and any available subtitle tracks.
4. Parse subtitles into `analysis/transcript.json`.
5. Pick 5 to 8 candidate clips with clear openings and endings.
6. Cut each clip to its own folder.
7. Translate or clean the local subtitle file into Chinese as needed.
8. Burn the subtitle track and a first-second title into `clip.hardsub.mp4`.
9. Write packaging copy and review notes.

## Repository Layout

```text
.
├── SKILL.md
├── README.md
├── agents/openai.yaml
├── references/
└── scripts/
```

## Scripts

- [scripts/fetch_source.py](./scripts/fetch_source.py)
  Downloads source assets with `yt-dlp`. It prefers browser cookies, tries English subtitles first, and uses the Android client path for MP4 download.
- [scripts/parse_subtitles.py](./scripts/parse_subtitles.py)
  Parses SRT files into structured JSON cues with both timestamp strings and numeric seconds.
- [scripts/trim_subtitles.py](./scripts/trim_subtitles.py)
  Slices a source subtitle file down to a clip-local timeline.
- [scripts/cut_clip.py](./scripts/cut_clip.py)
  Cuts one MP4 clip from the source video.
- [scripts/render_overlay_text.py](./scripts/render_overlay_text.py)
  Renders styled transparent PNG text overlays for subtitles and title cards.
- [scripts/render_hardsubs.py](./scripts/render_hardsubs.py)
  Builds hard-subbed exports by compositing rendered PNG overlays with `ffmpeg overlay`.
- [scripts/ffmpeg_locator.py](./scripts/ffmpeg_locator.py)
  Resolves a usable `ffmpeg` binary from either the system path or `imageio-ffmpeg`.

## Current Subtitle Rendering

The current subtitle renderer uses:

- A rounded translucent subtitle panel near the bottom of the frame
- Warm off-white subtitle text for better visual softness
- A first-second title card with a darker panel and highlighted title text
- Transparent PNG overlays so the pipeline works even when `ffmpeg` lacks subtitle and text filters

This means the plugin currently does not depend on:

- `libass`
- `ffmpeg subtitles`
- `ffmpeg drawtext`

As long as `ffmpeg overlay` works, hard-sub export should work.

## Install Into Codex

Copy this repository folder into:

```text
~/.codex/skills/zh-clip-forge
```

Or install it with your preferred Codex skill import flow from GitHub.

## Runtime Requirements

- `yt-dlp` available in the environment
- `ffmpeg` available in the environment, or resolvable through `imageio-ffmpeg`
- Python with `Pillow` available for text overlay rendering

## Runtime Notes

- The downloader prefers Chrome cookies and may need refreshed browser login state if YouTube blocks downloads.
- When English subtitles are unavailable, the workflow can fall back to `zh-Hans`.
- If a video has no usable subtitles, you may still need an external transcript or a separate speech-to-text fallback.
- The plugin is optimized for reviewable clip production, not exact word-for-word transcript reconstruction.

## Output Structure

Typical output lives under:

```text
work/<video-slug>/
  source/
  analysis/
  clips/
```

Each selected clip usually contains:

```text
clips/
  01-<slug>/
    clip.mp4
    clip.zh.srt
    clip.hardsub.mp4
    metadata.txt
```

## Related Files

- [SKILL.md](./SKILL.md)
- [agents/openai.yaml](./agents/openai.yaml)
- [references/clip-schema.md](./references/clip-schema.md)
- [references/analysis-prompt.md](./references/analysis-prompt.md)

## License

MIT
