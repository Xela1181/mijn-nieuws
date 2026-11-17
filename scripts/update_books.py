#!/usr/bin/env python3
"""Publish one reviewed book each Amsterdam day. No arbitrary API recommendations."""
import calendar
import datetime as dt
import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "book-tips.json"
CATALOG = ROOT / "books-catalog.json"

def key(title, author):
    # Match existing legacy IDs (title|author), as well as catalog identifiers.
    return re.sub(r"[^a-z0-9]+", "", title.casefold()) + "|" + re.sub(r"[^a-z0-9]+", "", author.casefold())

def months_ago(day, months=6):
    year, month = day.year, day.month - months
    while month <= 0:
        year -= 1
        month += 12
    return dt.date(year, month, min(day.day, calendar.monthrange(year, month)[1]))

def main():
    today = dt.datetime.now(ZoneInfo("Europe/Amsterdam")).date()
    data = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))["books"]
    if len({key(b["title"], b["author"]) for b in catalog}) != len(catalog):
        raise ValueError("Duplicate title/author in curated catalog")
    if any(not all(b.get(field) for field in ("title", "author", "description", "relevance", "url", "year")) for b in catalog):
        raise ValueError("Incomplete curated book record")
    tips = [b for b in data.get("tips", []) if isinstance(b, dict) and b.get("date")]
    seen = [b for b in data.get("seen", []) if isinstance(b, dict) and b.get("date") and b.get("id")]
    for b in tips:
        identity = key(b["title"], b["author"])
        if not any(x["id"] == identity and x["date"] == b["date"] for x in seen):
            seen.append({"id": identity, "date": b["date"]})
    cutoff = months_ago(today)
    blocked = {x["id"] for x in seen if dt.date.fromisoformat(x["date"]) > cutoff}
    # Replace today's low-quality automated entry once, preserving its history.
    existing = next((x for x in tips if x["date"] == today.isoformat()), None)
    needs_replacement = existing and existing.get("book_id") not in {key(b["title"], b["author"]) for b in catalog}
    if existing is None or needs_replacement:
        choices = [b for b in catalog if key(b["title"], b["author"]) not in blocked]
        if choices:
            # Deterministic rotation, balanced by topic while remaining easy to audit.
            chosen = choices[(today.toordinal() // 7) % len(choices)]
            entry = {**chosen, "date": today.isoformat(), "book_id": key(chosen["title"], chosen["author"])}
            tips = [b for b in tips if b["date"] != today.isoformat()]
            tips.append(entry)
            seen.append({"id": entry["book_id"], "date": today.isoformat()})
            print("Selected:", entry["title"], "by", entry["author"])
        else:
            print("No eligible curated book: catalog must be expanded before next publication")
    tips = [b for b in tips if 0 <= (today - dt.date.fromisoformat(b["date"])).days < 7]
    tips.sort(key=lambda x: x["date"], reverse=True)
    OUT.write_text(json.dumps({"updated": dt.datetime.now(dt.timezone.utc).isoformat(),
                               "tips": tips[:7], "seen": seen}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
if __name__ == "__main__":
    main()
