#!/usr/bin/env python3
"""Daily verified book suggestion from Open Library, with six-month no-repeat."""
import datetime as dt
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "book-tips.json"
QUERIES = [
    "artificial intelligence business", "financial management",
    "leadership strategy", "investing behavioral finance",
    "technology management", "business productivity",
    "corporate finance", "management innovation",
]
def norm(s):
    return re.sub(r"[^a-z0-9]+", "", s.casefold())
def months_ago(day, months=6):
    year, month = day.year, day.month - months
    while month <= 0:
        year -= 1
        month += 12
    import calendar
    return dt.date(year, month, min(day.day, calendar.monthrange(year, month)[1]))
def fetch(query):
    params = urllib.parse.urlencode({"q": query, "limit": 45, "fields": "key,title,author_name,first_publish_year,edition_count"})
    req = urllib.request.Request("https://openlibrary.org/search.json?" + params,
                                 headers={"User-Agent": "MijnNieuwsBookTips/1.0 (personal reading dashboard)"})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response).get("docs", [])
def main():
    today = dt.datetime.now(ZoneInfo("Europe/Amsterdam")).date()
    try:
        data = json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    history = [x for x in data.get("tips", []) if isinstance(x, dict) and x.get("date")]
    seen = [x for x in data.get("seen", []) if isinstance(x, dict) and x.get("id") and x.get("date")]
    for x in history:
        if x.get("book_id") and not any(z["id"] == x["book_id"] for z in seen):
            seen.append({"id": x["book_id"], "date": x["date"]})
    if not any(x["date"] == today.isoformat() for x in history):
        cutoff = months_ago(today)
        blocked = {x["id"] for x in seen if dt.date.fromisoformat(x["date"]) > cutoff}
        options = []
        for offset in range(len(QUERIES)):
            query = QUERIES[(today.toordinal() + offset) % len(QUERIES)]
            try:
                docs = fetch(query)
                print(query, len(docs))
            except Exception as exc:
                print(query, type(exc).__name__, str(exc)[:120])
                continue
            for doc in docs:
                title = str(doc.get("title", "")).strip()
                authors = doc.get("author_name") or []
                author = str(authors[0]).strip() if authors else ""
                key = doc.get("key", "")
                year = doc.get("first_publish_year")
                if not title or not author or not key.startswith("/works/") or not isinstance(year, int):
                    continue
                if year < 1990 or year > today.year or len(title) > 130:
                    continue
                identity = norm(title) + "|" + norm(author)
                if identity in blocked:
                    continue
                score = (min(year, today.year) - 1990) / 6 + min(int(doc.get("edition_count") or 0), 25) / 4
                options.append((score, identity, {
                    "date": today.isoformat(), "book_id": identity, "title": title,
                    "author": author, "year": year,
                    "topic": query, "description": "Een boek over " + query + ". Bekijk de bron voor een volledige beschrijving en recensies.",
                    "relevance": "Geselecteerd voor verdieping in Finance, technologie, strategie of persoonlijke ontwikkeling.",
                    "url": "https://openlibrary.org" + key,
                }))
            if len(options) >= 25:
                break
        options.sort(key=lambda x: (x[0], x[1]), reverse=True)
        if options:
            chosen = options[0][2]
            history.append(chosen)
            seen.append({"id": chosen["book_id"], "date": today.isoformat()})
            print("Selected", chosen["title"], chosen["author"])
        else:
            print("No verified book available; keeping existing recommendations.")
    history = [x for x in history if 0 <= (today - dt.date.fromisoformat(x["date"])).days < 7]
    history.sort(key=lambda x: x["date"], reverse=True)
    OUT.write_text(json.dumps({"updated": dt.datetime.now(dt.timezone.utc).isoformat(),
                               "tips": history[:7], "seen": seen}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
if __name__ == "__main__":
    main()
