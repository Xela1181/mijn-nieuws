#!/usr/bin/env python3
"""Build a short, source-grounded English audio briefing from the public news.json.
Uses edge-tts (unofficial free online speech service); no paid API key.
"""
import asyncio
import datetime as dt
import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo

import edge_tts

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "audio"
VOICE = "en-GB-RyanNeural"
RATE = "-8%"
MAX_WORDS = 1550

CATEGORIES = [
    ("Finance & CFO", 5),
    ("IT & technologie", 4),
    ("Beleggen & economie", 3),
    ("Nederland & wereld", 2),
    ("Sport", 1),
]
BOOKS = [
    ("The Goal", "Eliyahu M. Goldratt", "identify bottlenecks before optimising individual departments"),
    ("The Phoenix Project", "Gene Kim and colleagues", "connect IT operations to business outcomes"),
    ("Thinking, Fast and Slow", "Daniel Kahneman", "question overconfidence in financial decisions"),
    ("Good Strategy Bad Strategy", "Richard Rumelt", "focus resources on a clear diagnosis and coherent action"),
    ("Measure What Matters", "John Doerr", "connect strategic priorities with measurable outcomes"),
    ("The Psychology of Money", "Morgan Housel", "understand how behaviour influences investment decisions"),
    ("Financial Intelligence", "Karen Berman and Joe Knight", "explain financial performance in plain language"),
]
ENGLISH = [
    ("forecast confidence", "Achieving our full-year target depends on improving utilisation and securing new contracts.", "Explain a downside scenario using the phrase depends on."),
    ("board communication", "We have revised our outlook downwards, while implementing measures to protect profitability.", "Give a 30-second Board update about a forecast revision."),
    ("working capital", "Reducing overdue receivables could strengthen our short-term liquidity position.", "Explain one action to improve working capital."),
    ("profitability", "Revenue growth does not necessarily translate into higher operating margins.", "Explain the difference between growth and profitability."),
    ("risk management", "Provided that our mitigation measures take effect, we expect the downside risk to decrease.", "Use provided that to describe a financial risk."),
    ("budget variance", "The variance is primarily attributable to higher personnel costs.", "Explain a cost variance without inventing a cause."),
    ("executive summary", "Our results are below plan, mainly due to lower utilisation; management is taking corrective action.", "Summarise a challenging quarter in three sentences."),
]
AI_TIPS = [
    "Use AI to draft a variance commentary, but separate verified figures from hypotheses.",
    "Ask AI to review a finance policy for inconsistent responsibilities and missing controls.",
    "Use AI to structure upside and downside liquidity scenarios, with explicit assumptions.",
    "Ask AI to turn a verified KPI table into a concise Board narrative without inventing causes.",
    "Use AI to explain a complex spreadsheet formula and generate test cases.",
    "Use AI to compare anonymised intercompany service descriptions for inconsistencies.",
    "Before adopting a finance AI tool, assess data protection, auditability and human oversight.",
]


def clean(value, max_chars=190):
    value = re.sub(r"https?://\S+", "", str(value or ""))
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"[<>]", "", value)
    return value[:max_chars].rsplit(" ", 1)[0] if len(value) > max_chars else value


def select_news(data, now):
    selected = []
    cutoff = now.astimezone(dt.timezone.utc) - dt.timedelta(days=4)
    for category, limit in CATEGORIES:
        options = []
        for item in data.get("articles", []):
            if item.get("category") != category or not item.get("title"):
                continue
            try:
                published = dt.datetime.fromisoformat(item.get("published", ""))
                if published.tzinfo is None or published < cutoff:
                    continue
            except ValueError:
                continue
            options.append(item)
        selected.extend((category, item) for item in options[:limit])
    return selected


def spoken_item(item):
    """Make one natural spoken item; avoid repeating a headline in its summary."""
    title = clean(item["title"], 145).rstrip(" .!?:;")
    summary = clean(item.get("summary", ""), 210).rstrip(" .!?:;")
    if not summary:
        return title + "."
    # RSS descriptions often repeat the full headline verbatim.
    if title.casefold() in summary.casefold():
        remainder = re.sub(re.escape(title), "", summary, flags=re.IGNORECASE).strip(" .!?:;-")
        if remainder and len(remainder.split()) >= 5:
            return title + ". " + remainder[0].upper() + remainder[1:] + "."
        return title + "."
    # Also remove repeated leading fragments and descriptions with heavy word overlap.
    title_words = set(re.findall(r"[a-z]{4,}", title.lower()))
    summary_words = set(re.findall(r"[a-z]{4,}", summary.lower()))
    overlap = len(title_words & summary_words) / max(1, min(len(title_words), len(summary_words)))
    if overlap > 0.78:
        return summary[0].upper() + summary[1:] + "."
    return title + ". " + summary[0].upper() + summary[1:] + "."


def make_script(data, now):
    today = now.date()
    idx = today.toordinal() % 7
    pieces = [
        f"Good morning. This is your personal Business English news briefing for {today.strftime('%A, %d %B %Y')}.",
        "The briefing is written for upper-intermediate business English. News is based on public headlines and short summaries. Always consult the original articles for full context.",
    ]
    news = select_news(data, now)
    section_labels = {
        "Finance & CFO": "Finance and CFO",
        "IT & technologie": "Technology, artificial intelligence and cloud",
        "Beleggen & economie": "Investing and the economy",
        "Nederland & wereld": "The Netherlands and world news",
        "Sport": "Sport",
    }
    active_sections = [(cat, [item for group, item in news if group == cat])
                       for cat, _ in CATEGORIES]
    active_sections = [(cat, items) for cat, items in active_sections if items]
    for section_index, (category, entries) in enumerate(active_sections):
        label = section_labels[category]
        if section_index == 0:
            pieces.append(f"Let's begin with {label}.")
        else:
            pieces.append(f"That brings us to our next section: {label}.")
        for item_index, item in enumerate(entries):
            introduction = ("Our first story: " if item_index == 0 else
                            "In another development: " if item_index % 3 == 1 else
                            "Next, " if item_index % 3 == 2 else
                            "Also worth noting: ")
            pieces.append(introduction + spoken_item(item))
        pieces.append(f"That's the latest from {label}.")
    if not news:
        pieces.append("There are no sufficiently recent verified news headlines available in the current feed.")
    title, author, idea = BOOKS[idx]
    pieces.append(f"Today's book recommendation is {title}, by {author}. One idea to explore is to {idea}.")
    pieces.append("Podcast recommendation: check the Books and Podcasts tab for a verified episode link. No episode is announced without a confirmed link.")
    topic, example, task = ENGLISH[idx]
    pieces.append(f"Business English practice. Today's topic is {topic}. Listen to this model sentence. {example} Now your speaking task: {task} Pause the recording if you want more time to answer.")
    pieces.append(f"And finally, your AI for Finance tip. {AI_TIPS[idx]} Never enter confidential company information into an unapproved AI service.")
    pieces.append("That concludes today's briefing. Have a productive day.")
    text = "\n\n".join(pieces)
    words = text.split()
    if len(words) > MAX_WORDS:
        # Keep closing sections even when news volume is unusually high.
        tail = pieces[-5:]
        head = pieces[:2]
        budget = MAX_WORDS - len(" ".join(head + tail).split())
        middle = " ".join(pieces[2:-5]).split()[:max(0, budget)]
        text = "\n\n".join(head + [" ".join(middle)] + tail)
    return text, news


async def main():
    now = dt.datetime.now(ZoneInfo("Europe/Amsterdam"))
    data = json.loads((ROOT / "news.json").read_text(encoding="utf-8"))
    script, news = make_script(data, now)
    OUT.mkdir(exist_ok=True)
    (OUT / "briefing.txt").write_text(script + "\n", encoding="utf-8")
    metadata = {
        "date": now.date().isoformat(), "voice": VOICE, "level": "B2+",
        "word_count": len(script.split()), "news_count": len(news),
        "sources": [{"title": item["title"], "url": item.get("url", ""), "category": category}
                    for category, item in news],
    }
    (OUT / "briefing.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Generate sections individually to make transitions audible.
    # MP3 segments can be joined by ffmpeg with short silences.
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        segment_paths = []
        for i, paragraph in enumerate(script.split("\n\n")):
            if not paragraph.strip():
                continue
            path = Path(tmp) / f"part_{i:03d}.mp3"
            await edge_tts.Communicate(paragraph, VOICE, rate=RATE).save(str(path))
            segment_paths.append(path)
        if not segment_paths:
            raise RuntimeError("No audio segments generated")
        # A short pause between stories, rather than uninterrupted reading.
        concat_file = Path(tmp) / "segments.txt"
        silence = Path(tmp) / "pause.mp3"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i",
                        "anullsrc=r=24000:cl=mono", "-t", "0.7",
                        "-c:a", "libmp3lame", "-q:a", "5", str(silence)],
                       check=True)
        lines = []
        for i, path in enumerate(segment_paths):
            if i:
                lines.append(f"file '{silence}'")
            lines.append(f"file '{path}'")
        concat_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat",
                        "-safe", "0", "-i", str(concat_file), "-c", "copy",
                        str(OUT / "briefing.mp3")], check=True)
    print(f"Generated audio for {metadata['date']}: {metadata['word_count']} words, {len(news)} news items")


if __name__ == "__main__":
    asyncio.run(main())
