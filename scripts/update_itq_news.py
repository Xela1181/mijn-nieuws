#!/usr/bin/env python3
"""Independent, free ITQ-only news monitor. Does not collect general news."""
import datetime as dt
import email.utils
import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "itq-news.json"
SEED_URL = "https://www.techzine.nl/nieuws/infrastructure/582743/itq-cloud-platform-biedt-europese-private-cloud-op-vcf/"
QUERIES = [
    '("ITQ" "cloud" OR "ITQ" "VMware" OR "ITQ" "Broadcom") when:90d',
    '"ITQ Consultancy" when:90d',
    'site:techzine.nl "ITQ" when:90d',
    'site:itq.eu (cloud OR VMware OR Broadcom) when:90d',
]
def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", s or ""))).strip()[:500]
def get(node, key):
    v=node.find(key)
    return (v.text or "").strip() if v is not None else ""
def parse_date(raw):
    try:
        return email.utils.parsedate_to_datetime(raw).astimezone(dt.timezone.utc)
    except Exception:
        try:
            d=dt.datetime.fromisoformat(raw.replace("Z","+00:00"))
            return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
        except Exception:
            return None
def main():
    now=dt.datetime.now(dt.timezone.utc)
    try:
        old=json.loads(OUT.read_text(encoding="utf-8")).get("articles",[])
    except (OSError,ValueError):
        old=[]
    items={a["url"]:a for a in old if a.get("url") and a.get("title")}
    items[SEED_URL]=dict(category="ITQ Nieuws",source="Techzine",title="ITQ Cloud Platform biedt Europese private cloud op VCF",url=SEED_URL,summary="Techzine bericht over het ITQ Cloud Platform, een Europese privatecloudoplossing op basis van VMware Cloud Foundation.",published="",date_unknown=True)
    errors=[]
    for query in QUERIES:
        url="https://news.google.com/rss/search?q="+urllib.parse.quote(query)+"&hl=nl&gl=NL&ceid=NL:nl"
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req,timeout=20) as response:
                root=ET.fromstring(response.read(1500000))
            for node in root.findall(".//item")[:60]:
                title=clean(get(node,"title"))
                link=get(node,"link")
                published=parse_date(get(node,"pubDate"))
                if not title or not link.startswith("https://") or published is None:continue
                age=(now-published).total_seconds()/86400
                if age < -1 or age > 90:continue
                headline=title.casefold()
                if not re.search(r"(?<![a-z])itq(?![a-z])",headline):continue
                if not any(word in headline for word in ("cloud","vmware","broadcom","consultancy","platform","it services","managed services","itq")):continue
                if any(word in headline for word in ("vacature","werken bij","job opening","contact","privacyverklaring")):continue
                if link in items:continue
                items[link]=dict(category="ITQ Nieuws",source="Google Nieuws",title=title,url=link,summary=clean(get(node,"description")) or title,published=published.isoformat())
        except Exception as exc:
            errors.append(type(exc).__name__+": "+str(exc)[:100])
    recent=[]
    for item in items.values():
        date=parse_date(item.get("published",""))
        if (date is not None and -1 <= (now-date).total_seconds()/86400 <= 90) or item.get("url")==SEED_URL:
            recent.append(item)
    recent.sort(key=lambda a:a["published"],reverse=True)
    OUT.write_text(json.dumps({"updated":now.isoformat(),"articles":recent[:60],"errors":errors},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("ITQ articles:",len(recent),"Feed errors:",len(errors))
if __name__=="__main__":main()
