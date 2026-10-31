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


def make_script(data, now):
    today = now.date()
    idx = today.toordinal() % 7
    pieces = [
        f"Good morning. This is your personal Business English news briefing for {today.strftime('%A, %d %B %Y')}.",
        "The briefing is written for upper-intermediate business English. News is based on public headlines and short summaries. Always consult the original articles for full context.",
    ]
    news = select_news(data, now)
    for category, _ in CATEGORIES:
        entries = [a for c, a in news if c == category]
        if not entries:
            continue
        label = {"IT & technologie": "Technology, AI and cloud", "Beleggen & economie": "Investing and markets",
                 "Nederland & wereld": "The Netherlands and the world", "Sport": "Sport"}.get(category, category)
        pieces.append(f"Now, {label}.")
        for item in entries:
            title = clean(item["title"], 140)
            summary = clean(item.get("summary", ""), 160)
            if summary and summary.casefold() not in title.casefold():
                pieces.append(f"{title}. {summary}.")
            else:
                pieces.append(f"{title}.")
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
    await edge_tts.Communicate(script, VOICE, rate=RATE).save(str(OUT / "briefing.mp3"))
    print(f"Generated audio for {metadata['date']}: {metadata['word_count']} words, {len(news)} news items")


if __name__ == "__main__":
    asyncio.run(main())
