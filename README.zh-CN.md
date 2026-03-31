# global-clip-forge

一个用于把YouTube播客、演讲等长视频自动拆成 5 到 8 条短视频的 Codex 技能，支持用户指定目标语言，并导出带硬字幕的成片。

## 简介

`global-clip-forge` 是一个面向长视频内容的“先分析、再剪辑”技能。
它可以帮助你下载源视频、处理已有字幕或转录无字幕视频、让调用技能的 AI 生成目标语言字幕、筛选适合传播的精彩片段、裁剪短视频，并最终输出带硬字幕的 MP4 成片。

当前实现刻意避免依赖 `ffmpeg` 的 `libass` 或 `drawtext`。
字幕和标题会先渲染成透明 PNG，再通过 `ffmpeg overlay` 叠加到视频上，因此兼容性更高。

## 核心能力

- 下载 YouTube 视频及可用字幕
- 当平台没有字幕时，使用开源 Whisper 生成视频原语言字幕
- 支持按用户指定的目标语言做本地化剪辑
- 目标语言字幕默认由调用技能的 AI 生成
- 可按需输出双语字幕
- 自动筛选适合短视频传播的 20 秒到 3 分钟片段
- 裁剪片段并输出 `clip.hardsub.mp4`
- 标题卡只使用目标语言，不使用双语标题
- 一旦字幕文件准备完成，应直接继续烧录最终视频，不需要再次确认

## 适用场景

适合以下任务：

- 把一条长访谈、播客、演讲、圆桌讨论拆成多条短视频
- 原视频可能没有现成字幕
- 需要面向某个目标语言市场输出短视频
- 需要双语字幕或目标语言字幕
- 希望先得到候选片段，再决定是否批量导出

## 触发方式

在 Codex 中提到：

```text
$global-clip-forge
```

示例：

```text
Use $global-clip-forge to turn this YouTube interview URL into 5 to 8 short clips for a Japanese audience, with bilingual subtitles.
```

## 典型工作流

1. 检查环境依赖。
  确认 `yt-dlp`、`ffmpeg`、Python 和 `Pillow` 可用。
2. 建立任务目录。
  推荐使用：

```text
work/<video-slug>/
  source/
  transcripts/
  analysis/
  clips/
```

1. 确定本次任务的语言策略。
  包括：

- 视频原语言
- 用户指定的目标语言
- 是否需要双语字幕
- 是否需要标题卡

1. 下载源视频和可用字幕。
  使用 [scripts/fetch_source.py](./scripts/fetch_source.py)。
   如果用户对字幕语言有优先级要求，可以通过 `--subtitle-langs` 指定顺序。
2. 如果视频没有可用字幕，生成原语言字幕。
  使用 [scripts/transcribe_subtitles.py](./scripts/transcribe_subtitles.py) 把字幕统一输出到 `work/<video-slug>/transcripts/`。
3. 生成目标语言字幕。
  默认由调用技能的 AI 按时间轴翻译生成 `source.<target>.srt` 或 `clip.<target>.srt`。
   如果你明确想走脚本方案，也可以使用 [scripts/translate_subtitles.py](./scripts/translate_subtitles.py) 作为可选辅助。
4. 解析字幕为结构化 JSON。
  使用 [scripts/parse_subtitles.py](./scripts/parse_subtitles.py) 输出到 `analysis/transcript.json`。
5. 分析全文并筛选候选片段。
  结合：

- [references/clip-schema.md](./references/clip-schema.md)
- [references/analysis-prompt.md](./references/analysis-prompt.md)

1. 导出候选片段。
  每条候选通常控制在 20 到 180 秒之间，并写入：

- `analysis/selected_clips.json`
- `analysis/candidate-review.txt`
- `analysis/clip-packaging.txt`

1. 为每条片段生成本地字幕。
  包括：

- `clip.<source-lang>.srt`
- `clip.<target-lang>.srt`
- 如需双语，再合成 `clip.bilingual.srt`

1. 生成最终成片。
  使用 [scripts/render_hardsubs.py](./scripts/render_hardsubs.py) 直接输出 `clip.hardsub.mp4`。
    只要字幕文件已经准备好，就应直接继续这一步，不需要额外确认。

## 目录结构

典型输出结构如下：

```text
work/<video-slug>/
  source/
    original.mp4
    original.<lang>.srt
  transcripts/
    source.<source-lang>.srt
    source.<target-lang>.srt
    source.bilingual.srt
  analysis/
    transcript.json
    selected_clips.json
    candidate-review.txt
    clip-packaging.txt
  clips/
    01-<slug>/
      clip.mp4
      clip.<source-lang>.srt
      clip.<target-lang>.srt
      clip.bilingual.srt
      clip.hardsub.mp4
      metadata.txt
```

## 主要脚本

- [scripts/fetch_source.py](./scripts/fetch_source.py)
下载视频与字幕，支持字幕语言优先级。
- [scripts/parse_subtitles.py](./scripts/parse_subtitles.py)
把 SRT 解析成结构化 JSON。
- [scripts/transcribe_subtitles.py](./scripts/transcribe_subtitles.py)
用 Whisper 为无字幕视频生成原语言字幕。
- [scripts/translate_subtitles.py](./scripts/translate_subtitles.py)
可选的字幕翻译辅助脚本，不是默认主路径。
- [scripts/trim_subtitles.py](./scripts/trim_subtitles.py)
将整段字幕裁剪为片段字幕。
- [scripts/merge_bilingual_subtitles.py](./scripts/merge_bilingual_subtitles.py)
将原语言和目标语言字幕合成为双语字幕。
- [scripts/cut_clip.py](./scripts/cut_clip.py)
裁剪视频片段。
- [scripts/render_overlay_text.py](./scripts/render_overlay_text.py)
将字幕或标题渲染为透明 PNG。
- [scripts/render_hardsubs.py](./scripts/render_hardsubs.py)
将字幕或标题烧录到视频里，输出最终 MP4。
- [scripts/ffmpeg_locator.py](./scripts/ffmpeg_locator.py)
负责定位系统 `ffmpeg` 或 `imageio-ffmpeg`。

## 字幕与标题约定

- 标题卡如果启用，只使用目标语言
- 双语字幕通常建议“目标语言在上，原语言在下”或按实际策略调整
- 字幕字号默认偏克制，不做过大设计
- 如果 `clip.<target-lang>.srt` 或 `clip.bilingual.srt` 已经生成，就应直接烧录成 `clip.hardsub.mp4`

## 运行要求

- `yt-dlp`
- `ffmpeg` 或可替代的 `imageio-ffmpeg`
- Python
- `Pillow`
- 当视频没有字幕时，需要可用的 Whisper 运行环境

## 安装到 Codex

推荐安装到：

```text
~/.codex/skills/global-clip-forge
```

## 输出约定

技能完成后，通常应返回：

- 源视频与字幕所在目录
- 候选片段清单及时间范围
- 包装文案文件路径
- 每条最终成片的 `clip.hardsub.mp4` 路径

如果流程失败，应明确指出阻塞原因，例如：

- YouTube 下载失败
- 平台无字幕且 Whisper 不可用
- `ffmpeg` 不可用
- 转录质量过差，无法可靠切片

## 相关文件

- [SKILL.md](./SKILL.md)
- [README.md](./README.md)
- [agents/openai.yaml](./agents/openai.yaml)
- [references/clip-schema.md](./references/clip-schema.md)
- [references/analysis-prompt.md](./references/analysis-prompt.md)

