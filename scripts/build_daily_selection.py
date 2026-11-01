#!/usr/bin/env python3
"""Create a reproducible, no-cost daily shortlist from existing RSS articles.
Not editorially verified and not synchronized with ChatGPT."""
import datetime as dt
import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo

root = Path(__file__).resolve().parents[1]
source = json.loads((root / "news.json").read_text(encoding="utf-8"))
today = dt.datetime.now(ZoneInfo("Europe/Amsterdam")).date().isoformat()
quotas = {"Finance & CFO": 4, "IT & technologie": 3, "Beleggen & economie": 3, "Nederland & wereld": 2, "Sport": 1}
priority = {
 "Finance & CFO": ("cfo", "treasury", "liquidity", "audit", "forecast", "ebitda", "tax", "ifrs", "governance", "belastingplan", "vennootschapsbelasting", "ecb", "dnb", "jaarrekening", "accountant"),
 "IT & technologie": ("vmware", "broadcom", "cloud", "cyber", "artificial intelligence", "microsoft", "data center"),
 "Beleggen & economie": ("etf", "stock", "aandeel", "beurs", "rente", "inflation", "ecb", "ethereum"),
 "Nederland & wereld": ("nederland", "europe", "kabinet", "economie", "minister"),
 "Sport": ("schaatsen", "langebaan", "marathon", "hardlopen", "ijshockey", "ice hockey", "nhl", "wckt", "thialf", "world cup"),
}
now = dt.datetime.now(dt.timezone.utc)
def rank(item):
 blob = (item.get("title", "") + " " + item.get("summary", "")).casefold()
 title = item.get("title", "").casefold()
 score = sum(5 if word in title else 2 for word in priority.get(item.get("category"), ()) if word in blob)
 try:
  moment = dt.datetime.fromisoformat(item.get("published", "").replace("Z", "+00:00"))
  if moment.tzinfo is None: moment = moment.replace(tzinfo=dt.timezone.utc)
  age = max(0, (now - moment).total_seconds() / 3600)
  score += 12 if age <= 24 else 7 if age <= 48 else 3 if age <= 72 else -15 if age > 168 else 0
 except (ValueError, TypeError, AttributeError):
  score -= 5
 return score
selected = []
seen = set()
for category, limit in quotas.items():
    count = 0
    for item in sorted((a for a in source.get("articles", []) if a.get("category") == category), key=rank, reverse=True):
        url = item.get("url", "")
        if item.get("category") != category or not url.startswith("https://") or url in seen:
            continue
        if not item.get("title") or not item.get("summary") or rank(item) < -5:
            continue
        seen.add(url)
        selected.append(item)
        count += 1
        if count == limit:
            break
# This file is a machine-selected shortlist only, not a curated final briefing.
output = {
    "date": today,
    "updated": dt.datetime.now(dt.timezone.utc).isoformat(),
    "selection_mode": "rss_shortlist",
    "articles": selected,
    "item_ids": [a.get("id") or a.get("url") for a in selected],
    "narration": "",
    "warning": "Automatische RSS-voorselectie; niet gecontroleerd of gesynchroniseerd met ChatGPT."
}
(root / "daily-selection.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Created {len(selected)} RSS shortlist articles for {today}")
