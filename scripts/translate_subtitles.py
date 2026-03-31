#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

try:
    from scripts.parse_subtitles import parse_srt
    from scripts.trim_subtitles import fmt_time
except ModuleNotFoundError:
    from parse_subtitles import parse_srt
    from trim_subtitles import fmt_time


DEFAULT_MODEL = "gpt-4.1-mini"


def chunked(items: list[dict], size: int) -> list[list[dict]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def normalize_lang(value: str) -> str:
    return value.strip().lower().replace("_", "-")


def language_candidates(value: str) -> list[str]:
    normalized = normalize_lang(value)
    candidates = [normalized]
    aliases = {
        "english": ["en"],
        "en-us": ["en"],
        "en-gb": ["en"],
        "chinese": ["zh", "zh-cn"],
        "simplified-chinese": ["zh", "zh-cn"],
        "mandarin": ["zh", "zh-cn"],
        "japanese": ["ja"],
        "korean": ["ko"],
        "french": ["fr"],
        "german": ["de"],
        "spanish": ["es"],
        "portuguese": ["pt"],
        "portuguese-br": ["pt", "pt-br"],
        "brazilian-portuguese": ["pt", "pt-br"],
        "russian": ["ru"],
        "arabic": ["ar"],
        "hindi": ["hi"],
        "indonesian": ["id"],
        "turkish": ["tr"],
        "vietnamese": ["vi"],
        "thai": ["th"],
    }
    candidates.extend(aliases.get(normalized, []))
    if "-" in normalized:
        candidates.append(normalized.split("-", 1)[0])
    deduped = []
    for item in candidates:
        if item and item not in deduped:
            deduped.append(item)
    return deduped


def try_argos_translate(
    texts: list[str],
    *,
    source_language: str,
    target_language: str,
) -> Optional[list[str]]:
    try:
        from argostranslate import translate as argos_translate
    except ModuleNotFoundError:
        return None

    installed_languages = argos_translate.get_installed_languages()
    source_candidates = language_candidates(source_language) if source_language else []
    target_candidates = language_candidates(target_language)

    def match_lang(candidates: list[str]):
        for candidate in candidates:
            for language in installed_languages:
                code = normalize_lang(getattr(language, "code", ""))
                if code == candidate:
                    return language
        return None

    source_lang = match_lang(source_candidates) if source_candidates else None
    target_lang = match_lang(target_candidates)
    if target_lang is None:
        raise RuntimeError(
            "Argos Translate is installed, but no local package was found for the target language. "
            "Install the needed Argos language package inside your task venv first."
        )

    translation = None
    if source_lang is not None:
        translation = source_lang.get_translation(target_lang)
    else:
        for candidate in installed_languages:
            try:
                translation = candidate.get_translation(target_lang)
                source_lang = candidate
                break
            except Exception:
                continue

    if translation is None:
        raise RuntimeError(
            "Argos Translate is installed, but no matching local translation pair was found. "
            "Install a source-to-target Argos package inside your task venv."
        )

    return [translation.translate(text) for text in texts]


def request_translations(
    texts: list[str],
    *,
    source_language: str,
    target_language: str,
    model: str,
    api_key: str,
    base_url: str,
) -> list[str]:
    prompt = (
        "Translate each subtitle line into the target language.\n"
        "Rules:\n"
        f"- Source language: {source_language or 'auto-detect from the text'}\n"
        f"- Target language: {target_language}\n"
        "- Preserve meaning, names, and numbers accurately.\n"
        "- Keep the output natural and spoken, suitable for short-video subtitles.\n"
        "- Return strict JSON with one key: translations.\n"
        "- translations must be an array with exactly the same length as the input.\n"
    )
    body = {
        "model": model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps({"texts": texts}, ensure_ascii=False)},
        ],
    }
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"translation API request failed: {exc.code} {details}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"translation API request failed: {exc.reason}") from exc

    content = payload["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    translations = parsed.get("translations")
    if not isinstance(translations, list) or len(translations) != len(texts):
        raise RuntimeError("translation API response did not return the expected translations array")
    return [str(item).strip() for item in translations]


def write_srt(cues: list[dict], output_path: Path) -> None:
    lines = []
    for idx, cue in enumerate(cues, start=1):
        lines.append(str(idx))
        lines.append(f"{fmt_time(cue['start_seconds'])} --> {fmt_time(cue['end_seconds'])}")
        lines.extend(cue["text"].splitlines() or [""])
        lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Translate an SRT file into a user-specified target language while preserving timestamps."
        )
    )
    parser.add_argument("input_srt")
    parser.add_argument("output_srt")
    parser.add_argument("--target-language", required=True, help="Audience language, for example Japanese or pt-BR.")
    parser.add_argument(
        "--source-language",
        default="",
        help="Optional source language hint, for example English or ko.",
    )
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL", DEFAULT_MODEL))
    parser.add_argument("--batch-size", type=int, default=40)
    parser.add_argument(
        "--provider",
        choices=["auto", "argos", "openai"],
        default="auto",
        help="Translation backend. auto prefers local Argos Translate, then OpenAI if configured.",
    )
    args = parser.parse_args()

    input_path = Path(args.input_srt).expanduser().resolve()
    output_path = Path(args.output_srt).expanduser().resolve()
    cues = parse_srt(input_path.read_text(encoding="utf-8", errors="ignore"))
    translated_cues = []
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

    for batch in chunked(cues, size=max(1, args.batch_size)):
        source_texts = [cue["text"] for cue in batch]
        translations = None

        if args.provider in {"auto", "argos"}:
            translations = try_argos_translate(
                source_texts,
                source_language=args.source_language,
                target_language=args.target_language,
            )
            if translations is None and args.provider == "argos":
                print(
                    "Argos Translate is not installed. Install it inside your task venv or switch provider.",
                    file=sys.stderr,
                )
                return 1

        if translations is None and args.provider in {"auto", "openai"}:
            if not api_key:
                if args.provider == "openai":
                    print("OPENAI_API_KEY is required when --provider openai is used", file=sys.stderr)
                    return 1
            else:
                translations = request_translations(
                    source_texts,
                    source_language=args.source_language,
                    target_language=args.target_language,
                    model=args.model,
                    api_key=api_key,
                    base_url=base_url,
                )

        if translations is None:
            print(
                "No translation backend is available. Install Argos Translate in the task venv, "
                "or provide OPENAI_API_KEY for the OpenAI fallback.",
                file=sys.stderr,
            )
            return 1

        for cue, translated_text in zip(batch, translations):
            translated_cues.append(
                {
                    "start_seconds": cue["start_seconds"],
                    "end_seconds": cue["end_seconds"],
                    "text": translated_text,
                }
            )

    write_srt(translated_cues, output_path)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
