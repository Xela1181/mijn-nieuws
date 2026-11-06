#!/usr/bin/env python3
"""Generate a bilingual audio news briefing from the dashboard's daily selection.

Free dependencies: edge-tts and ffmpeg. Never silently drop selected articles.
"""
import asyncio
import datetime as dt
import json
import re
import subprocess
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

import edge_tts

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "audio"
VOICE_EN = "en-GB-SoniaNeural"
VOICE_NL = "nl-NL-ColetteNeural"
RATE = "-8%"
CATEGORIES = ["Finance & CFO", "IT & technologie", "Beleggen & economie", "Nederland & wereld", "Sport"]
LABELS = {
    "Finance & CFO": "Finance and CFO",
    "IT & technologie": "technology",
    "Beleggen & economie": "investing and the economy",
    "Nederland & wereld": "the Netherlands and world news",
    "Sport": "sport",
}


def clean(value):
    value = re.sub(r"https?://\S+", "", str(value or ""))
    return re.sub(r"\s+", " ", value).strip()


def article_text(item):
    """Read only source-provided text, without inventing additional detail."""
    title = clean(item.get("title"))
    summary = clean(item.get("summary"))
    if not title:
        raise ValueError("Selected article has no title")
    # Many Google News summaries repeat the headline with a publisher suffix.
    title_words = set(re.findall(r"\w+", title.casefold()))
    summary_words = set(re.findall(r"\w+", summary.casefold()))
    if summary and len(summary.split()) >= 12 and len(summary_words - title_words) >= 5:
        # Avoid abrupt trailing RSS excerpts; no unsupported completion.
        summary = re.sub(r"\s*(?:\[\.\.\.\]|…|\.\.\.)\s*$", "", summary)
        return title.rstrip(". ") + ". " + summary
    return title


def load_selection(now):
    path = ROOT / "daily-selection.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("date") != now.date().isoformat():
        raise ValueError("Daily selection is not dated today; refusing to publish stale audio")
    if data.get("selection_mode") not in ("rss_shortlist", "curated"):
        raise ValueError("Unknown selection mode")
    items = data.get("articles")
    if not isinstance(items, list) or not 1 <= len(items) <= 15:
        raise ValueError("Expected 1–15 selected articles; refusing invalid audio")
    ids = [a.get("id") or a.get("url") for a in items]
    if not all(ids) or len(ids) != len(set(ids)) or ids != data.get("item_ids"):
        raise ValueError("Selection identifiers are missing, duplicated or out of order")
    for a in items:
        if a.get("category") not in CATEGORIES or not a.get("title") or a.get("language") not in ("nl", "en"):
            raise ValueError("Article missing a supported category, title or language")
    return data, items, ids


def make_segments(items, now):
    """Each segment has a language, so Edge TTS uses the correct voice."""
    segments = [("en", f"Good morning. This is your news briefing for {now:%A, %d %B %Y}. Today's stories are read in their original language.")]
    current_category = None
    for i, item in enumerate(items, 1):
        category = item["category"]
        if category != current_category:
            segments.append(("en", f"Next, {LABELS[category]}."))
            current_category = category
        segments.append(("en", f"Story {i}."))
        segments.append((item["language"], article_text(item)))
    segments.append(("en", "That concludes today's news briefing. Have a good day."))
    return segments


async def main():
    now = dt.datetime.now(ZoneInfo("Europe/Amsterdam"))
    selection, items, ids = load_selection(now)
    segments = make_segments(items, now)
    transcript = "\n\n".join(text for _, text in segments) + "\n"
    metadata = {
        "date": now.date().isoformat(),
        "selection_mode": selection["selection_mode"],
        "voice": {"en": VOICE_EN, "nl": VOICE_NL},
        "word_count": len(transcript.split()),
        "news_count": len(items),
        "item_ids": ids,
        "sources": [{"title": a["title"], "url": a["url"], "category": a["category"]} for a in items],
    }
    OUT.mkdir(exist_ok=True)
    # Only replace published files after every TTS segment and ffmpeg succeeds.
    with tempfile.TemporaryDirectory() as temp:
        tmp = Path(temp)
        paths = []
        for i, (language, paragraph) in enumerate(segments):
            path = tmp / f"part_{i:03d}.mp3"
            voice = VOICE_NL if language == "nl" else VOICE_EN
            await edge_tts.Communicate(paragraph, voice, rate=RATE).save(str(path))
            paths.append(path)
        pause = tmp / "pause.mp3"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                        "anullsrc=r=24000:cl=mono", "-t", "1.2", "-c:a", "libmp3lame",
                        "-q:a", "5", str(pause)], check=True)
        playlist = tmp / "segments.txt"
        lines = []
        for i, path in enumerate(paths):
            if i:
                lines.append(f"file '{pause}'")
            lines.append(f"file '{path}'")
        playlist.write_text("\n".join(lines) + "\n", encoding="utf-8")
        output_mp3 = tmp / "briefing.mp3"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
                        "-i", str(playlist), "-c:a", "libmp3lame", "-q:a", "4", str(output_mp3)], check=True)
        if not output_mp3.exists() or output_mp3.stat().st_size < 1000:
            raise RuntimeError("Audio output is missing or empty")
        (OUT / "briefing.mp3").write_bytes(output_mp3.read_bytes())
    (OUT / "briefing.txt").write_text(transcript, encoding="utf-8")
    (OUT / "briefing.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated audio for {metadata['date']}: {metadata['word_count']} words, {len(items)} news items")


if __name__ == "__main__":
    asyncio.run(main())
