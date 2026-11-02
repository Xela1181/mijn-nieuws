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
VOICE = "en-GB-SoniaNeural"
RATE = "-8%"
MAX_WORDS = 1250

CATEGORIES = [
    ("Finance & CFO", 3),
    ("IT & technologie", 3),
    ("Beleggen & economie", 2),
    ("Nederland & wereld", 1),
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


DUTCH_WORDS = set("de het een van voor met bij over naar zijn wordt worden deze nieuwe nederlandse nederland op uit niet door als aan en ook".split())
def likely_dutch(title):
    words = re.findall(r"[a-zà-ÿ]+", title.lower())
    return sum(word in DUTCH_WORDS for word in words) >= 2


def complete_sentences(value, max_chars=600):
    """Keep complete source sentences; never read a clipped RSS fragment."""
    value = re.sub(r"https?://\\S+", "", str(value or ""))
    value = re.sub(r"\\s+", " ", value).strip()
    value = re.sub(r"\\s*(\\[\\.\\.\\.\\]|…|\\.\\.\\.)\\s*$", "", value)
    value = value[:max_chars]
    sentences = re.findall(r"[^.!?]+[.!?](?=\\s|$)", value)
    if sentences:
        return " ".join(s.strip() for s in sentences).strip()
    return value.strip() if len(value) < max_chars and not value.endswith((",", ";", ":")) else ""


def story_text(item):
    """Use a source-backed summary only when it is informative and in English."""
    if item.get("language") != "en" or likely_dutch(item.get("title", "")):
        return ""
    title = clean(item["title"], 180).rstrip(" .!?:;")
    if item.get('category') == 'Finance & CFO' and any(w in title.lower() for w in ('stock unit award', 'appointed', 'appointment', 'interim cfo', 'federal funds', 'government grant', 'compensation package')):
        return ""
    raw = str(item.get("summary") or "").strip()
    if len(raw.split()) < 17:
        return ""
    summary = complete_sentences(raw)
    if summary.endswith('[...]') or summary.endswith(' [...]'):
        summary = summary.replace('[...]', '').strip()
    if len(summary.split()) < 15:
        return ""
    # Avoid reading the same sentence twice. A summary alone often reads best.
    core = re.split(r"\\s[-–—]\\s", title)[0]
    title_words = set(re.findall(r"[a-z]{4,}", core.lower()))
    summary_words = set(re.findall(r"[a-z]{4,}", summary.lower()))
    overlap = len(title_words & summary_words) / max(1, len(title_words))
    if overlap > 0.5 or core.casefold() in summary.casefold():
        return summary if len(summary.split()) >= 18 else ""
    return title + ". " + summary


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
            spoken = story_text(item)
            if spoken:
                options.append((item, spoken))
        selected.extend((category, item, spoken) for item, spoken in options[:limit])
    return selected


def make_script(data, now):
    today = now.date()
    idx = today.toordinal() % 7
    pieces = [
        f"Good morning. This is your personal Business English news briefing for {today.strftime('%A, %d %B %Y')}.",
        "Here is today's selection of news stories with enough verified detail to explain clearly.",
    ]
    news = select_news(data, now)
    section_labels = {
        "Finance & CFO": "Finance and CFO",
        "IT & technologie": "Technology, artificial intelligence and cloud",
        "Beleggen & economie": "Investing and the economy",
        "Nederland & wereld": "The Netherlands and world news",
        "Sport": "Sport",
    }
    active_sections = [(cat, [(item, spoken) for group, item, spoken in news if group == cat])
                       for cat, _ in CATEGORIES]
    active_sections = [(cat, items) for cat, items in active_sections if items]
    for section_index, (category, entries) in enumerate(active_sections):
        label = section_labels[category]
        if section_index == 0:
            pieces.append(f"Let's begin with {label}.")
        else:
            pieces.append(f"That brings us to our next section: {label}.")
        for item_index, (item, spoken) in enumerate(entries):
            introduction = f"Story {item_index + 1}. "
            pieces.append(introduction + spoken)
        pieces.append(f"That's the latest from {label}.")
    if not news:
        pieces.append("There are no sufficiently detailed English news summaries available in the current feed. We will not invent missing details.")
    pieces.append("That concludes the news. Now for your recommendations and English practice.")
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
                    for category, item, spoken in news],
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
                        "anullsrc=r=24000:cl=mono", "-t", "1.6",
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
