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
selected = []
seen = set()
for category, limit in quotas.items():
    count = 0
    for item in source.get("articles", []):
        url = item.get("url", "")
        if item.get("category") != category or not url.startswith("https://") or url in seen:
            continue
        if not item.get("title") or not item.get("summary"):
            continue
        if category == "Sport" and re.search(r"ijshockey|ice hockey|\bnhl\b", (item["title"] + " " + item["summary"]).lower()):
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
    "item_ids": [],
    "narration": "",
    "warning": "Automatische RSS-voorselectie; niet gecontroleerd of gesynchroniseerd met ChatGPT."
}
(root / "daily-selection.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Created {len(selected)} RSS shortlist articles for {today}")
