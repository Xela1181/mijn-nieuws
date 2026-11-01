#!/usr/bin/env python3
"""RSS updater using Python standard library; no API key or external dependency."""
import datetime as dt
import email.utils
import html
import json
import urllib.parse
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def google_news(query, lang='nl', country='NL'):
    return 'https://news.google.com/rss/search?q='+urllib.parse.quote(query)+'&hl='+lang+'&gl='+country+'&ceid='+country+':'+lang

FEEDS = [
    ('ITQ Nieuws','Google Nieuws · ITQ',google_news('"ITQ" (VMware OR Broadcom OR consultancy OR cloud OR Beverwijk OR Nederland) when:30d')),
    ('ITQ Nieuws','Google Nieuws · ITQ Consultancy',google_news('"ITQ Consultancy" when:30d')),
    ('Sport','Marathonnieuws',google_news('(marathon OR hardlopen) (wedstrijd OR training OR record OR atletiek) when:7d')),
    ('Sport','Langebaanschaatsen',google_news('(langebaanschaatsen OR schaatsen OR KNSB OR ISU) when:7d')),
    ('Sport','IJshockey',google_news('(ijshockey OR NHL OR ice hockey) when:7d')),
    ('Sport','Schaatsen nieuws',google_news('site:schaatsen.nl (world cup OR wckt OR schaatsen) when:7d')),
    ('Sport','Hardlopen nieuws',google_news('site:running.nl (marathon OR hardlopen) when:7d')),
    ('Finance & CFO','Nederlandse fiscaliteit',google_news('(belastingplan OR vennootschapsbelasting OR btw OR jaarrekening OR accountant) when:3d')),
    ('Finance & CFO','Europese CFO',google_news('(ECB OR DNB OR treasury OR liquiditeit OR fusie OR overname) when:3d')),
    ('Finance & CFO','CFO verslaggeving en audit',google_news('(IFRS OR accountancy OR jaarrekening OR audit OR financial reporting OR consolidatie) when:5d')),
    ('Finance & CFO','CFO treasury en forecasts',google_news('(cashflow OR werkkapitaal OR treasury OR liquiditeitsforecast OR CFO OR EBITDA) when:5d')),
    ('Finance & CFO','CFO internationaal',google_news('(CFO OR treasury OR accounting OR financial reporting OR corporate finance) when:5d','en','US')),
    ('Beleggen & economie','Nederlandse markten',google_news('(AEX OR ECB OR inflatie OR rente OR beleggers) when:3d')),
    # Proefbronnen: Google News site-filter totdat een betrouwbare directe RSS-feed is bevestigd.
    ('Finance & CFO','CFO.nl · proefbron',google_news('site:cfo.nl (CFO OR treasury OR governance OR audit OR forecast OR finance OR overname) when:7d')),
    ('Finance & CFO','CMweb · proefbron',google_news('site:cmweb.nl (controlling OR treasury OR jaarrekening OR AI OR risicomanagement OR werkkapitaal) when:7d')),
    ('Finance & CFO','NBA · proefbron',google_news('site:nba.nl (accountancy OR verslaggeving OR controle OR standaarden OR regelgeving OR jaarrekening) when:14d')),
    ('Finance & CFO','Harvard Business Review','https://feeds.hbr.org/harvardbusiness'),
    ('Finance & CFO','BBC Business','https://feeds.bbci.co.uk/news/business/rss.xml'),
    ('Finance & CFO','Financial Times','https://www.ft.com/?format=rss'),
    ('Finance & CFO','The Economist','https://www.economist.com/finance-and-economics/rss.xml'),
    ('IT & technologie','NOS Tech','https://feeds.nos.nl/nosnieuwstech'),
    ('IT & technologie','TechCrunch','https://techcrunch.com/feed/'),
    ('IT & technologie','MIT Technology Review','https://www.technologyreview.com/feed/'),
    ('IT & technologie','Ars Technica','https://feeds.arstechnica.com/arstechnica/index'),
    ('IT & technologie','BleepingComputer','https://www.bleepingcomputer.com/feed/'),
    ('Beleggen & economie','NOS Economie','https://feeds.nos.nl/nosnieuwseconomie'),
    ('Beleggen & economie','BBC Business','https://feeds.bbci.co.uk/news/business/rss.xml'),
    ('Beleggen & economie','MarketWatch','https://feeds.content.dowjones.io/public/rss/mw_topstories'),
    ('Beleggen & economie','WSJ Markets','https://feeds.content.dowjones.io/public/rss/RSSMarketsMain'),
    ('Nederland & wereld','NOS Nieuws','https://feeds.nos.nl/nosnieuwsalgemeen'),
    ('Nederland & wereld','BBC World','https://feeds.bbci.co.uk/news/world/rss.xml'),
    ('Sport','NOS Sport','https://feeds.nos.nl/nossportalgemeen'),
]
QUOTAS = {'Finance & CFO': 8, 'IT & technologie': 6, 'Beleggen & economie': 6, 'Nederland & wereld': 4, 'Sport': 8, 'ITQ Nieuws': 0}
KEYWORDS = {
 'Finance & CFO': ['cfo','finance director','financial reporting','financial statements','accounting','audit','treasury','liquidity','working capital','cash flow','cashflow','tax','belasting','btw','transfer pricing','consolidat','forecast','budget','ebitda','governance','compliance','ifrs','controller','financieel directeur','financiële verslaggeving','merger','acquisition','overname','m&a'],
 'IT & technologie': ['artificial intelligence','ai ',' ai','cloud','cyber','security','ransomware','broadcom','vmware','microsoft','data center','datacenter','automation','automatisering','enterprise','software','chip','semiconductor','llm','generative ai','it services'],
 'Beleggen & economie': ['stock','share','aandeel','etf','beurs','market','interest rate','rente','inflation','inflatie','economy','economie','central bank','ecb','fed ','earnings','dividend','bond','obligatie','invest','beleg','crypto','bitcoin','ethereum','index fund','s&p 500','nasdaq'],
 'Nederland & wereld': ['nederland','dutch','europe','eu ','verkiez','politiek','kabinet','regering','war','oorlog','geopolit','international','wereld','minister'],
 'Sport': ['marathon','running','hardlopen','schaatsen','langebaan','speed skating','knsb','isu','ijshockey','ice hockey','nhl','atletiek','wckt','world cup'],
 'ITQ Nieuws': ['itq','itq consultancy','itq.eu','broadcom','vmware'],
}
BLOCK = {'Beleggen & economie':['my father','my mother','caregiver','debit card','credit card debt','advice column','should i','relationship','retirement advice','inheritance dispute','personal finance question']}

TAG = re.compile(r'<[^>]+>')
def clean(s):
    return re.sub(r'\s+',' ',html.unescape(TAG.sub(' ',s or ''))).strip()[:240]
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
        language = ('en' if 'ceid=US:en' in url else 'nl') if 'news.google.com' in url else ('nl' if source.startswith('NOS') else 'en')
        out.append(dict(category=cat,source=source,title=title,url=link,summary=desc,published=date,language=language))
    return out

def main():
    now=dt.datetime.now(dt.timezone.utc)
    items=[];errors=[];google_errors=[]
    for cat,source,url in FEEDS:
        try:
            got=fetch(cat,source,url)
            print(f'{source}: {len(got)} items')
            items+=got
        except Exception as exc:
            errors.append(f'{source}: {type(exc).__name__}')
            if 'news.google.com' in url:google_errors.append(source)
            print(f'Feed error {source}: {exc}')
    # Prefer relevant, recent articles and distribute results by the requested category weights.
    unique={}
    for item in items:
        key=re.sub(r'[^a-z0-9]+','',item['title'].casefold())[:110]
        if key not in unique: unique[key]=item
    ranked={cat:[] for cat in QUOTAS}
    for item in unique.values():
        cat=item['category']; blob=(item['title']+' '+item['summary']).lower()
        # A Google News site search can return old evergreen pages despite when:7d.
        # Only dated, genuinely recent articles belong in a daily briefing.
        try:
            published=dt.datetime.fromisoformat(item['published'].replace('Z','+00:00'))
            age_hours=(now-published).total_seconds()/3600
            if age_hours < -2 or age_hours > (336 if cat=='ITQ Nieuws' else 168):continue
        except (ValueError, TypeError, KeyError, AttributeError):
            continue
        if cat=='ITQ Nieuws' and not ('itq' in blob and any(w in blob for w in ['vmware','broadcom','consultancy','cloud','beverwijk','netherlands','nederland','itq.eu','managed services','it services'])):continue
        if cat=='Sport' and not any(w in blob for w in KEYWORDS['Sport']):continue
        if cat=='Finance & CFO':
            title=item['title'].casefold()
            if 'proefbron' in item['source']:
                # Google site-search sometimes indexes biographies, glossaries and evergreen landing pages.
                headline=title.split(' - ')[0].strip()
                if len(headline.split()) < 5 or any(w in headline for w in
                    ('over ons','wie zijn wij','compliance-verklaring','contact','redactie',
                     'abonnement','privacyverklaring','algemene voorwaarden','auteurs',
                     'werken bij','onze mensen','kennisbank','begrippenlijst')):
                    continue
            # Recruiting, awards and event promotion are not daily CFO developments.
            low_value=('zoekt een ', 'vacature', 'hiring ', 'we are hiring',
                       'solliciteer', 'job opening', 'career opportunity',
                       'jury m&a awards', 'genomineerden voor best deal',
                       'meld je aan', 'schrijf je in voor')
            if any(word in title for word in low_value):continue
        if cat=='Finance & CFO' and any(w in item['title'].lower() for w in ('f1-commentator','formule 1-commentator','voetbaltrainer','transfernieuws')):continue
        # A generic local-government merger is not corporate finance or M&A.
        if cat=='Finance & CFO' and any(w in blob for w in ('gemeentelijke fusie','gemeentefusie','fusie van gemeenten','gemeenten fuseren','gemeentelijke herindeling')):continue
        if any(b in blob for b in BLOCK.get(cat,[])):continue
        score=sum(4 if word in item['title'].lower() else 1 for word in KEYWORDS[cat] if word in blob)
        if cat in ('Finance & CFO','IT & technologie','Beleggen & economie') and score==0:continue
        item['score']=score
        ranked[cat].append(item)
    for cat in ranked:
        ranked[cat].sort(key=lambda x:(x['score'],x['published']),reverse=True)
    # Diagnostic: expose why trial sources do or do not survive the first ranking.
    for trial in ('CFO.nl · proefbron','CMweb · proefbron','NBA · proefbron'):
        fetched=[a for a in items if a['source']==trial]
        eligible=[a for a in ranked['Finance & CFO'] if a['source']==trial]
        print(f'TRIAL {trial}: fetched={len(fetched)} eligible={len(eligible)}')
        for candidate in eligible[:3]:
            print(f"TRIAL candidate {trial}: score={candidate['score']} title={candidate['title'][:100]}")
    # Fixed daily targets: 25 general news items, plus separate ITQ coverage.
    # Limit single-source domination in Finance so specialist sources can compete.
    articles=[]
    for cat,quota in QUOTAS.items():
        picked=[];source_counts={}
        for item in ranked[cat]:
            src=item['source']
            if cat=='Finance & CFO' and source_counts.get(src,0)>=3:continue
            picked.append(item)
            source_counts[src]=source_counts.get(src,0)+1
            if len(picked)>=quota:break
        articles+=picked
    articles+=ranked['ITQ Nieuws'][:30]
    articles.sort(key=lambda x:(x['score'],x['published']),reverse=True)
    for item in articles:item.pop('score',None)
    path=ROOT/'news.json'
    if not articles and path.exists():
        try:
            old=json.loads(path.read_text(encoding='utf-8'))
            articles=[]  # Never republish stale cached headlines as freshly fetched news.
        except Exception:pass
    warning=('Er konden geen actuele RSS-artikelen worden opgehaald.' if not articles else
             f'Google Nieuws tijdelijk niet bereikbaar voor {len(google_errors)} bronnen; de selectie is mogelijk onvolledig.' if google_errors else
             'Niet alle nieuwsbronnen konden worden bijgewerkt.' if errors else '')
    result={'updated':now.isoformat(),'articles':articles,'warning':warning,'failed_sources':errors,'google_news_failures':len(google_errors)}
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Saved {len(articles)} articles; feed errors: {len(errors)}')
if __name__=='__main__':main()
