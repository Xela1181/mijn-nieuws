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
quotas = {"Finance & CFO": 4, "IT & technologie": 3, "Beleggen & economie": 3, "Nederland & wereld": 2, "Sport": 3}
priority = {
 "Finance & CFO": ("cfo", "treasury", "liquidity", "audit", "forecast", "ebitda", "tax", "ifrs", "governance", "belastingplan", "vennootschapsbelasting", "ecb", "dnb", "jaarrekening", "accountant", "cash flow", "transfer pricing", "financial reporting", "merger", "acquisition"),
 "IT & technologie": ("vmware", "broadcom", "cloud", "cyber", "artificial intelligence", "microsoft", "data center"),
 "Beleggen & economie": ("etf", "stock", "aandeel", "beurs", "rente", "inflation", "ecb", "ethereum"),
 "Nederland & wereld": ("nederland", "europe", "kabinet", "economie", "minister"),
 "Sport": ("schaatsen", "langebaan", "marathon", "hardlopen", "ijshockey", "ice hockey", "nhl", "wckt", "thialf", "world cup"),
}
now = dt.datetime.now(dt.timezone.utc)
MAX_ARTICLE_AGE_HOURS = 36
SPORT_LOW_VALUE = ('nu kijken', 'of gemist', 'tvgids', 'tv-gids', 'livestream', 'loting/startlijsten', 'startlijsten', 'programma schaatsen', 'programma world cup')
def substantial(item):
    title = item.get('title', '').casefold()
    summary = (item.get('summary') or '').strip()
    if item.get('category') == 'Sport' and any(term in title for term in SPORT_LOW_VALUE):
        return False
    # RSS summaries that merely repeat the headline are not substantive news.
    if len(summary.split()) < 18:
        return False
    return True

def rank(item):
 blob = (item.get("title", "") + " " + item.get("summary", "")).casefold()
 title = item.get("title", "").casefold()
 score = sum(5 if word in title else 2 for word in priority.get(item.get("category"), ()) if word in blob)
 try:
  moment = dt.datetime.fromisoformat(item.get("published", "").replace("Z", "+00:00"))
  if moment.tzinfo is None: moment = moment.replace(tzinfo=dt.timezone.utc)
  age = max(0, (now - moment).total_seconds() / 3600)
  score += 35 if age <= 24 else 18 if age <= 48 else 4 if age <= 72 else -12
 except (ValueError, TypeError, AttributeError):
  score -= 5
 return score
selected = []
seen = set()
for category, limit in quotas.items():
    count = 0
    tax_politics_count = 0
    candidates = sorted((a for a in source.get("articles", []) if a.get("category") == category), key=rank, reverse=True)
    if category == "Sport":
        # Reserve one candidate per interest before filling remaining slots.
        sports = (
            ("schaats", "langebaan", "knsb", "isu", "thialf", "speed skating", "wckt"),
            ("ijshockey", "ice hockey", "nhl"),
            ("hardlopen", "marathon", "running", "atletiek"),
        )
        preferred = []
        used_urls = set()
        for terms in sports:
            match = next((a for a in candidates
                          if a.get("url") not in used_urls
                          and any(t in (a.get("title", "") + " " + a.get("summary", "")).casefold() for t in terms)), None)
            if match:
                preferred.append(match)
                used_urls.add(match.get("url"))
        candidates = preferred + [a for a in candidates if a.get("url") not in used_urls]
    for item in candidates:
        url = item.get("url", "")
        if item.get("category") != category or not url.startswith("https://") or url in seen:
            continue
        # Recheck freshness even if news.json was produced by an older fetcher.
        try:
            published = dt.datetime.fromisoformat(item['published'].replace('Z', '+00:00'))
            if published.tzinfo is None: published = published.replace(tzinfo=dt.timezone.utc)
            age_hours = (now - published).total_seconds() / 3600
            if age_hours < -2 or age_hours > MAX_ARTICLE_AGE_HOURS:
                continue
        except (KeyError, ValueError, TypeError, AttributeError):
            continue
        if not item.get("title") or not substantial(item) or rank(item) < -5:
            continue
        if category == 'Finance & CFO' and any(w in (item.get('title','')+' '+item.get('summary','')).casefold() for w in ('gemeentelijke fusie','gemeentefusie','fusie van gemeenten','gemeenten fuseren','gemeentelijke herindeling')):
            continue
        title = item.get('title', '').casefold()
        if category == 'Finance & CFO' and any(w in title for w in ('zoekt een ', 'vacature', 'hiring ', 'we are hiring', 'solliciteer', 'job opening', 'career opportunity', 'jury m&a awards', 'genomineerden voor best deal', 'meld je aan', 'schrijf je in voor')):
            continue
        if category == 'Finance & CFO' and any(w in title for w in ('f1-commentator', 'formule 1-commentator', 'voetbaltrainer', 'transfernieuws')):
            continue
        tax_politics = category == 'Finance & CFO' and any(w in title for w in ('belastingplan', 'btw-verhoging', 'belastingakkoord', 'btw', 'belasting', 'tax deal'))
        if tax_politics and tax_politics_count >= 2:
            continue
        if tax_politics:
            tax_politics_count += 1
        seen.add(url)
        selected.append(item)
        count += 1
        if count == limit:
            break
# Older articles are a fallback when the daily feed lacks enough relevant fresh stories.
older_count = sum(
    (now - dt.datetime.fromisoformat(a["published"].replace("Z", "+00:00"))).total_seconds() > 48 * 3600
    for a in selected
)
freshness_warning = (f" {older_count} van de {len(selected)} artikelen zijn ouder dan 48 uur; "
                     "deze zijn als aanvulling opgenomen omdat er onvoldoende recente geschikte berichten waren."
                     if older_count else "")
# This file is a machine-selected shortlist only, not a curated final briefing.
output = {
    "date": today,
    "updated": dt.datetime.now(dt.timezone.utc).isoformat(),
    "selection_mode": "rss_shortlist",
    "articles": selected,
    "item_ids": [a.get("id") or a.get("url") for a in selected],
    "narration": "",
    "warning": "Automatische RSS-voorselectie; niet gecontroleerd of gesynchroniseerd met ChatGPT." + freshness_warning + (" " + source["warning"] if source.get("warning") else ""),
    "source_failures": source.get("failed_sources", []),
    "google_news_failures": source.get("google_news_failures", 0)
}
(root / "daily-selection.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Created {len(selected)} RSS shortlist articles for {today}")
