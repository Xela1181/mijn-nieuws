#!/usr/bin/env python3
"""RSS updater using Python standard library; no API key or external dependency."""
import datetime as dt
import email.utils
import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEEDS = [
    ('Finance & CFO','BBC Business','https://feeds.bbci.co.uk/news/business/rss.xml'),
    ('Finance & CFO','Harvard Business Review','https://feeds.hbr.org/harvardbusiness'),
    ('IT & technologie','NOS Tech','https://feeds.nos.nl/nosnieuwstech'),
    ('IT & technologie','TechCrunch','https://techcrunch.com/feed/'),
    ('IT & technologie','BBC Technology','https://feeds.bbci.co.uk/news/technology/rss.xml'),
    ('Beleggen & economie','NOS Economie','https://feeds.nos.nl/nosnieuwseconomie'),
    ('Beleggen & economie','BBC Business','https://feeds.bbci.co.uk/news/business/rss.xml'),
    ('Beleggen & economie','MarketWatch','https://feeds.content.dowjones.io/public/rss/mw_topstories'),
    ('Nederland & wereld','NOS Nieuws','https://feeds.nos.nl/nosnieuwsalgemeen'),
    ('Nederland & wereld','BBC World','https://feeds.bbci.co.uk/news/world/rss.xml'),
    ('Sport','NOS Sport','https://feeds.nos.nl/nossportalgemeen'),
]
TAG = re.compile(r'<[^>]+>')
def clean(s):
    return re.sub(r'\s+',' ',html.unescape(TAG.sub(' ',s or ''))).strip()[:420]
def value(node, names):
    for name in names:
        x=node.find(name)
        if x is not None and x.text: return x.text.strip()
    return ''
def parse_date(raw):
    try:
        d=email.utils.parsedate_to_datetime(raw)
        if d: return d.astimezone(dt.timezone.utc).isoformat()
    except Exception: pass
    try: return dt.datetime.fromisoformat(raw.replace('Z','+00:00')).astimezone(dt.timezone.utc).isoformat()
    except Exception: return ''
def fetch(cat, source, url):
    req=urllib.request.Request(url,headers={'User-Agent':'MijnNieuwsPersonalRSS/2.0 (+https://github.com/)' ,'Accept':'application/rss+xml, application/atom+xml, application/xml, text/xml'})
    with urllib.request.urlopen(req,timeout=18) as r: data=r.read(2_000_000)
    root=ET.fromstring(data)
    items=root.findall('.//item') or root.findall('{http://www.w3.org/2005/Atom}entry')
    out=[]
    for node in items[:35]:
        title=clean(value(node,['title','{http://www.w3.org/2005/Atom}title']))
        link=value(node,['link'])
        if not link:
            for el in node.findall('{http://www.w3.org/2005/Atom}link'):
                if el.attrib.get('rel','alternate')=='alternate':link=el.attrib.get('href','');break
        if not link.startswith(('https://','http://')) or not title:continue
        date=parse_date(value(node,['pubDate','{http://www.w3.org/2005/Atom}updated','{http://www.w3.org/2005/Atom}published','{http://purl.org/dc/elements/1.1/}date']))
        desc=clean(value(node,['description','{http://www.w3.org/2005/Atom}summary','{http://www.w3.org/2005/Atom}content']))
        out.append(dict(category=cat,source=source,title=title,url=link,summary=desc,published=date))
    return out

def main():
    now=dt.datetime.now(dt.timezone.utc)
    items=[];errors=[]
    for cat,source,url in FEEDS:
        try:
            got=fetch(cat,source,url)
            print(f'{source}: {len(got)} items')
            items+=got
        except Exception as exc:
            errors.append(f'{source}: {type(exc).__name__}')
            print(f'Feed error {source}: {exc}')
    unique={}
    for item in items:
        if item['url'] not in unique:unique[item['url']]=item
    articles=sorted(unique.values(),key=lambda a:a['published'],reverse=True)[:150]
    path=ROOT/'news.json'
    if not articles and path.exists():
        try:
            old=json.loads(path.read_text(encoding='utf-8'))
            articles=old.get('articles',[])
        except Exception:pass
    result={'updated':now.isoformat(),'articles':articles,'warning':('Niet alle nieuwsbronnen konden worden bijgewerkt.' if errors and articles else 'Er konden nog geen RSS-artikelen worden opgehaald.' if not articles else '')}
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Saved {len(articles)} articles; feed errors: {len(errors)}')
if __name__=='__main__':main()
