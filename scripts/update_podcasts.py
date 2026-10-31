#!/usr/bin/env python3
"""Select one fresh, relevant podcast episode daily and retain seven daily tips."""
import datetime as dt
import email.utils
import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "podcast-tips.json"
FEEDS = [
    ("FT News Briefing", "https://feeds.acast.com/public/shows/ft-news-briefing", 5),
    ("Hard Fork", "https://feeds.simplecast.com/l2i9YnTd", 5),
    ("HBR IdeaCast", "https://feeds.simplecast.com/1A1wHqNA", 4),
    ("The Indicator from Planet Money", "https://feeds.npr.org/510325/podcast.xml", 3),
    ("Planet Money", "https://feeds.npr.org/510289/podcast.xml", 3),
    ("Marketplace", "https://www.marketplace.org/feed/podcast/marketplace/", 3),
]
KEYWORDS = {
    "finance": 7, "cfo": 9, "accounting": 7, "earnings": 6, "cash": 5,
    "interest": 5, "bank": 4, "market": 5, "invest": 7, "stock": 5,
    "econom": 5, "inflation": 5, "business": 4, "leadership": 5,
    "artificial intelligence": 10, " ai ": 8, "technology": 5, "tech": 5,
    "cloud": 8, "cyber": 7, "software": 6, "automation": 7, "data": 4,
    "marathon": 5, "running": 3, "ice hockey": 3, "speed skating": 3,
}
def cleaned(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", s or ""))).strip()
def child_text(node, names):
    for name in names:
        child = node.find(name)
        if child is not None and child.text:
            return child.text.strip()
    return ""
def parse_date(s):
    try:
        return email.utils.parsedate_to_datetime(s).astimezone(dt.timezone.utc)
    except (ValueError, TypeError, IndexError):
        try:
            return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
        except (ValueError, TypeError):
            return None
def episodes(name, url, weight):
    req = urllib.request.Request(url, headers={"User-Agent": "MijnNieuwsPodcast/1.0", "Accept": "application/rss+xml, application/xml, text/xml"})
    with urllib.request.urlopen(req, timeout=18) as response:
        root = ET.fromstring(response.read(2_000_000))
    found = []
    for item in root.findall(".//item")[:35]:
        title = cleaned(child_text(item, ["title"]))
        desc = cleaned(child_text(item, ["description", "{http://www.itunes.com/dtds/podcast-1.0.dtd}summary"]))
        link = child_text(item, ["link"])
        published = parse_date(child_text(item, ["pubDate"]))
        guid = child_text(item, ["guid"])
        if not title or not published:
            continue
        if not link.startswith("https://"):
            link = url
        # Only call a link 'direct Spotify' when the feed actually supplies a Spotify episode URL.
        spotify = next((v for v in [link, guid] if v.startswith("https://open.spotify.com/episode/")), "")
        search = "https://open.spotify.com/search/" + urllib.parse.quote(name + " " + title)
        found.append({"podcast": name, "title": title[:220], "description": desc[:280],
                      "url": link, "spotify_url": spotify, "spotify_search": search,
                      "published": published.isoformat(), "weight": weight})
    return found
def main():
    today = dt.datetime.now(ZoneInfo("Europe/Amsterdam")).date()
    history = []
    if OUT.exists():
        try:
            history = json.loads(OUT.read_text(encoding="utf-8")).get("tips", [])
        except (ValueError, OSError, AttributeError):
            pass
    history = [x for x in history if isinstance(x, dict) and x.get("date") and
               0 <= (today - dt.date.fromisoformat(x["date"])).days < 7]
    if any(x["date"] == today.isoformat() for x in history):
        print("Today's recommendation already exists; preserving the daily choice.")
    else:
        candidates = []
        for name, url, weight in FEEDS:
            try:
                got = episodes(name, url, weight)
                candidates.extend(got)
                print(f"{name}: {len(got)} episodes")
            except Exception as exc:
                print(f"{name}: {type(exc).__name__}: {exc}")
        used = {x.get("episode_id") for x in history}
        now = dt.datetime.now(dt.timezone.utc)
        ranked = []
        for x in candidates:
            age = (now - dt.datetime.fromisoformat(x["published"])).total_seconds() / 86400
            if age < -1 or age > 14:
                continue
            episode_id = x["podcast"] + "|" + x["title"].casefold()
            if episode_id in used:
                continue
            blob = " " + (x["title"] + " " + x["description"][:160]).lower() + " "
            relevance = sum(points for term, points in KEYWORDS.items() if term in blob)
            score = relevance * 3 + x["weight"] * 4 - max(0, age) * 1.4
            ranked.append((score, x["published"], episode_id, x))
        ranked.sort(reverse=True, key=lambda row: (row[0], row[1]))
        if ranked:
            _, _, episode_id, selected = ranked[0]
            selected.pop("weight")
            selected["episode_id"] = episode_id
            selected["date"] = today.isoformat()
            history.append(selected)
            print("Selected:", selected["podcast"], selected["title"])
        else:
            print("No verified fresh episode available; no fabricated recommendation.")
    history.sort(key=lambda x: x["date"], reverse=True)
    OUT.write_text(json.dumps({"updated": dt.datetime.now(dt.timezone.utc).isoformat(),
                                "tips": history[:7]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
if __name__ == "__main__":
    main()
