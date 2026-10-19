import csv, html, json, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).parent
DB = ROOT / 'data' / 'jobs.csv'
XLSX = ROOT / 'AIAA_UH_Summer_2027_Internships.xlsx'
TODAY_DATE = date.today()
TODAY = TODAY_DATE.isoformat()
CLOSING_SOON_DAYS = 14

INTERN = re.compile(r'\b(intern|internship|co-?op|student)\b', re.I)
SEASON = re.compile(r'(summer\s*2027|2027\s*summer|may\s*2027|june\s*2027)', re.I)
ENGINEERING = re.compile(r'(mechanical|aerospace|manufactur|industrial|production|test|structures?|mechanisms?|propulsion|avionics|electrical|electronics|embedded|software|computer|systems?|integration|flight|materials?|quality|reliability|controls?|guidance|navigation|GNC|robotics?|autonomy|design|engineering)', re.I)
EARLY_TITLE = re.compile(r'\b(new\s*grad(?:uate)?|early\s*career|entry[- ]level|associate\s+(?:engineer|engineering)|engineer\s+i\b|engineering\s+i\b|junior\s+(?:engineer|engineering))\b', re.I)
EARLY_BODY = re.compile(r'(new\s*grad(?:uate)?|recent\s*graduate|early\s*career|entry[- ]level|0\s*[-–]\s*2\s+years|0\s*[-–]\s*1\s+years|less than\s*2\s+years|bachelor.{0,80}(?:no experience|0\s*[-–]\s*2\s+years))', re.I)
SENIOR = re.compile(r'\b(senior|sr\.?|staff|principal|lead|manager|director|chief)\b', re.I)

MONTHS = {m.lower(): i for i, m in enumerate([
    '', 'January','February','March','April','May','June','July','August','September','October','November','December'
])}
MONTHS.update({k[:3]:v for k,v in list(MONTHS.items()) if k})

def extract_deadline(text):
    """Best-effort extraction of an explicitly stated 2026/2027 application deadline."""
    t = clean(text)
    patterns = [
        r'(?:application(?:s)?\s+(?:close|closes|deadline)|apply\s+by|deadline)\D{0,35}((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s+\d{1,2}(?:st|nd|rd|th)?[,]?\s+20(?:26|27))',
        r'(?:application(?:s)?\s+(?:close|closes|deadline)|apply\s+by|deadline)\D{0,35}(\d{1,2}/\d{1,2}/20(?:26|27))',
    ]
    for pat in patterns:
        m=re.search(pat,t,re.I)
        if not m: continue
        raw=re.sub(r'(st|nd|rd|th)', '', m.group(1), flags=re.I).replace('.', '')
        for fmt in ('%B %d, %Y','%b %d, %Y','%B %d %Y','%b %d %Y','%m/%d/%Y'):
            try: return datetime.strptime(raw,fmt).date().isoformat()
            except ValueError: pass
    return ''

def parse_iso(s):
    try: return date.fromisoformat(s) if s else None
    except ValueError: return None

def is_texas(location):
    return bool(re.search(r'\b(TX|Texas|Houston|Dallas|Fort Worth|Austin|Arlington|McGregor|Brownsville|Bastrop|Cedar Park|Greenville)\b', location or '', re.I))

def clean(s):
    s = html.unescape(s or '')
    return re.sub(r'<[^>]+>', ' ', s).replace('\n',' ').strip()

def role_stage(title, text):
    """Return Internship, New Grad / Early Career, or None.

    Engineer I alone is intentionally insufficient: generic level-I titles need
    corroborating early-career language in the posting body.
    """
    full=' '.join([title or '', text or ''])
    if INTERN.search(full) and SEASON.search(full) and ENGINEERING.search(full):
        return 'Internship'
    if SENIOR.search(title or '') or not ENGINEERING.search(full):
        return None
    explicit=bool(re.search(r'\b(new\s*grad(?:uate)?|early\s*career|entry[- ]level|associate\s+(?:engineer|engineering)|junior\s+(?:engineer|engineering))\b', title or '', re.I))
    level_one=bool(re.search(r'\b(?:engineer|engineering)\s+i\b', title or '', re.I))
    if explicit or (level_one and EARLY_BODY.search(text or '')):
        return 'New Grad / Early Career'
    return None

def classify_industry(company, title, text):
    s=' '.join([company,title,text]).lower()
    rules=[
      ('Exploration',r'rover|lander|habitat|spacesuit|space suit|lunar|moon|surface system'),
      ('Spaceflight',r'rocket|launch|propulsion|engine|booster|reentry|re-entry'),
      ('Space Systems',r'spacecraft|satellite|space station|orbital|payload'),
      ('Defense & High-Speed Flight',r'hypersonic|missile|weapon|military|defense|defence'),
      ('Robotics & Autonomous Systems',r'robot|autonom|unmanned|uas\b|uav\b|drone'),
      ('Aviation',r'aircraft|aviation|airplane|aeronaut|rotorcraft|helicopter|evtol'),
      ('Government & Research',r'nasa|national lab|research center|research centre'),
      ('Manufacturing & Suppliers',r'manufactur|production|supplier|materials|machining|composite')]
    for label,pat in rules:
        if re.search(pat,s,re.I): return label
    return 'Space Systems'

def classify_disciplines(title, text):
    s=' '.join([title,text]).lower(); out=[]
    rules=[('Aerospace',r'aerospace|aerodynamics?'),('Mechanical',r'mechanical|mechanism|thermal|fluids?'),('Electrical / Electronics',r'electrical|electronics|pcb|circuit'),('Computer / Embedded',r'embedded|firmware|computer engineering'),('Software',r'software|developer|programmer'),('Systems',r'systems? engineer|systems? integration'),('GNC / Controls',r'guidance|navigation|controls?|gnc\b'),('Manufacturing / Industrial',r'manufactur|industrial|production|process engineer'),('Materials',r'materials?|metallurg|composite'),('Test / Integration',r'test|integration|verification|validation'),('Propulsion',r'propulsion|rocket engine|turbomach'),('Structures',r'structur|stress|loads'),('Quality / Reliability',r'quality|reliability')]
    for label,pat in rules:
        if re.search(pat,s,re.I): out.append(label)
    return out or ['Other Engineering']

def greenhouse(c):
    url=f"https://boards-api.greenhouse.io/v1/boards/{c['token']}/jobs?content=true"
    r=requests.get(url,timeout=12); r.raise_for_status()
    out=[]
    for j in r.json().get('jobs',[]): 
        text=' '.join([j.get('title',''), clean(j.get('content',''))])
        stage=role_stage(j.get('title',''), text)
        if stage:
            out.append({'key':f"gh:{c['token']}:{j['id']}",'company':c['company'],'title':j.get('title',''),'stage':stage,'text':text,
                        'location':(j.get('location') or {}).get('name',''),'deadline':extract_deadline(text),'url':j.get('absolute_url','')})
    return out

def lever(c):
    url=f"https://api.lever.co/v0/postings/{c['token']}?mode=json"
    r=requests.get(url,timeout=12); r.raise_for_status()
    out=[]
    for j in r.json():
        text=' '.join([j.get('text',''), clean(j.get('descriptionPlain','')), clean(j.get('additionalPlain',''))])
        stage=role_stage(j.get('text',''), text)
        if stage:
            cats=j.get('categories') or {}
            out.append({'key':f"lever:{c['token']}:{j['id']}",'company':c['company'],'title':j.get('text',''),'stage':stage,'text':text,
                        'location':cats.get('location',''),'deadline':extract_deadline(text),'url':j.get('hostedUrl','')})
    return out

def _job(company, key, title, text, location, url):
    stage=role_stage(title,text)
    if not stage: return None
    return {'key':key,'company':company,'title':title,'stage':stage,'text':text,
            'location':location or '','deadline':extract_deadline(text),'url':url or ''}

def workday(c):
    base=f"https://{c['host']}/wday/cxs/{c['tenant']}/{c['site']}"
    out=[]; seen=set()
    searches=c.get('search_texts') or ['2027','intern','early career','entry level','new grad','engineer I']
    for query in searches:
        offset=0; limit=int(c.get('limit',20)); max_pages=int(c.get('max_pages',3))
        for _ in range(max_pages):
            r=requests.post(base+'/jobs',json={'appliedFacets':{},'limit':limit,'offset':offset,'searchText':query},timeout=12)
            r.raise_for_status(); data=r.json(); posts=data.get('jobPostings',[])
            if not posts: break
            for j in posts:
                ext=j.get('externalPath',''); title=j.get('title','')
                if not ext or ext in seen: continue
                seen.add(ext)
                try: d=requests.get(base+ext,timeout=12).json().get('jobPostingInfo',{})
                except Exception: d={}
                text=' '.join([title,clean(d.get('jobDescription','')),str(d.get('additionalLocations',''))])
                x=_job(c['company'],f"wd:{c['tenant']}:{d.get('jobReqId') or ext}",title,text,
                       d.get('location') or j.get('locationsText',''),d.get('externalUrl') or ('https://'+c['host']+ext))
                if x: out.append(x)
            offset += limit
            if offset >= data.get('total',0): break
    return out

def sitemap_jobs(c):
    out=[]; seen=set(); headers={'User-Agent':'Mozilla/5.0 AIAA-UH-Opportunity-Finder/1.0'}
    patterns=[re.compile(p,re.I) for p in c.get('job_url_patterns',[])]
    for sm in c.get('sitemaps',[]):
        r=requests.get(sm,headers=headers,timeout=15); r.raise_for_status()
        soup=BeautifulSoup(r.text,'xml')
        urls=[x.get_text(strip=True) for x in soup.find_all('loc')]
        # Follow sitemap indexes one level.
        if any(u.lower().endswith('.xml') for u in urls[:20]):
            nested=[]
            for u in urls[:int(c.get('max_sitemaps',20))]:
                if not u.lower().endswith('.xml'): continue
                try:
                    rr=requests.get(u,headers=headers,timeout=12); rr.raise_for_status()
                    nested.extend(x.get_text(strip=True) for x in BeautifulSoup(rr.text,'xml').find_all('loc'))
                except Exception: pass
            urls=nested
        if patterns: urls=[u for u in urls if any(p.search(u) for p in patterns)]
        for url in urls[:int(c.get('detail_limit',60))]:
            if url in seen: continue
            seen.add(url)
            try:
                rr=requests.get(url+c.get('detail_url_suffix',''),headers=headers,timeout=12); rr.raise_for_status()
                page=BeautifulSoup(rr.text,'html.parser')
                title=(page.find('h1') or page.find('title'))
                title=clean(title.get_text(' ',strip=True) if title else '')
                text=clean(page.get_text(' ',strip=True))
                loc=''
                m=re.search(r'(?:Location|Locations?)\s*[:\-]?\s*([^|]{2,120})',text,re.I)
                if m: loc=m.group(1).strip()
                x=_job(c['company'],'sitemap:'+c['company']+':'+url,title,text,loc,url)
                if x: out.append(x)
            except Exception: continue
    return out

def rss_jobs(c):
    # Some career platforms expose XML sitemaps through what is effectively a feed.
    cc=dict(c); cc['sitemaps']=[c['url']]
    return sitemap_jobs(cc)

def phenom(c):
    # Phenom sites vary by tenant. Their server-rendered search results are still
    # useful when queried with several high-signal early-career terms.
    cc=dict(c); base=c['base_url'].rstrip('/')
    terms=c.get('search_texts') or ['2027','intern','early career','entry level','new grad']
    cc['urls']=[base+'/global/en/search-results?keywords='+requests.utils.quote(q) for q in terms]
    return careers_page(cc)

def eightfold(c):
    base=c['base_url'].rstrip('/')
    terms=c.get('search_texts') or ['2027','intern','early career','entry level','new grad']
    cc=dict(c); cc['urls']=[base+'/careers?query='+requests.utils.quote(q) for q in terms]
    return careers_page(cc)


def careers_page(c):
    """Scan one or more official, server-rendered career search pages.

    This is intentionally conservative: only links whose surrounding text itself
    looks like a Summer 2027 engineering internship are emitted. This makes it
    useful for Phenom/SuccessFactors/Taleo/custom career sites without pretending
    every site has a public JSON API.
    """
    out=[]
    headers={'User-Agent':'Mozilla/5.0 AIAA-UH-Internship-Finder/1.0'}
    for page_url in c.get('urls',[c.get('url')]):
        if not page_url: continue
        r=requests.get(page_url,headers=headers,timeout=12); r.raise_for_status()
        soup=BeautifulSoup(r.text,'html.parser')
        seen=set()
        for a in soup.find_all('a', href=True):
            href=urljoin(page_url,a.get('href',''))
            # Include parent text because many career sites put location/date beside the title.
            parent=a.parent.get_text(' ',strip=True) if a.parent else ''
            text=clean(' '.join([a.get_text(' ',strip=True), parent]))
            if not text or href in seen: continue
            stage=role_stage(a.get_text(' ',strip=True),text)
            if stage:
                seen.add(href)
                title=a.get_text(' ',strip=True) or text[:180]
                key='page:'+c['company']+':'+href
                out.append({'key':key,'company':c['company'],'title':title[:220],
                            'stage':stage,'text':text,'location':'','deadline':extract_deadline(text),'url':href})
    return out

def classify_error(exc):
    """Map fetch failures to a source-health state without treating them as zero jobs."""
    msg=str(exc)
    if any(code in msg for code in ('403 Client Error','429 Client Error')):
        return 'BLOCKED', msg[:300]
    return 'ERROR', msg[:300]

def health_record(c, state, count=0, message=''):
    return {
        'company': c['company'], 'source_type': c.get('type',''), 'health': state,
        'matches': count, 'last_checked': TODAY, 'message': message
    }

def load_old():
    if not DB.exists(): return {}
    with DB.open(newline='',encoding='utf-8') as f: return {r['key']:r for r in csv.DictReader(f)}

def save(rows):
    DB.parent.mkdir(exist_ok=True)
    fields=['key','company','title','location','status','first_seen','last_seen','deadline','url','stage','text']
    with DB.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def export_roles_json(rows):
    """Normalized feed consumed by GitHub Pages and, later, README generation."""
    live=[]
    for r in rows:
        if r.get('status') not in ('NEW','OPEN'): continue
        text=r.get('text','')
        stage=r.get('stage') or ('Internship' if INTERN.search(r.get('title','')) else 'New Grad / Early Career')
        live.append({
            'id':r['key'],'company':r['company'],'title':r['title'],
            'location':r.get('location',''),'stage':stage,
            'industry':classify_industry(r['company'],r['title'],text),
            'disciplines':classify_disciplines(r['title'],text),
            'posted_at':r.get('posted_at') or r.get('first_seen',''),
            'first_seen':r.get('first_seen',''),'deadline':r.get('deadline',''),
            'apply_url':r.get('url','')
        })
    path=ROOT/'data'/'roles.json'; path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({'updated_at':TODAY,'roles':live},indent=2),encoding='utf-8')

def style_sheet(ws):
    fill=PatternFill('solid',fgColor='16324F')
    for cell in ws[1]:
        cell.fill=fill; cell.font=Font(color='FFFFFF',bold=True); cell.alignment=Alignment(wrap_text=True)
    widths=[24,48,32,14,14,14,16,55]
    for i,w in enumerate(widths,1): ws.column_dimensions[get_column_letter(i)].width=w
    ws.freeze_panes='A2'; ws.auto_filter.ref=ws.dimensions
    for row in ws.iter_rows(min_row=2):
        for c in row: c.alignment=Alignment(vertical='top',wrap_text=True)
        if row[3].value=='NEW': row[3].fill=PatternFill('solid',fgColor='FFF2CC')
        elif row[3].value=='OPEN': row[3].fill=PatternFill('solid',fgColor='D9EAD3')
        elif row[3].value=='CLOSED': row[3].fill=PatternFill('solid',fgColor='F4CCCC')

def add_view(wb, title, rows):
    ws=wb.create_sheet(title)
    ws.append(['Company','Role','Location','Status','First Seen','Last Seen','Deadline','Application URL'])
    for r in rows:
        ws.append([r['company'],r['title'],r['location'],r['status'],r['first_seen'],r['last_seen'],r.get('deadline',''),r['url']])
    style_sheet(ws)
    return ws

def add_source_health(wb, health):
    ws=wb.create_sheet('SOURCE HEALTH')
    ws.append(['Company','Source Type','Health','Matches','Last Checked','Notes'])
    for h in sorted(health,key=lambda x:(x['health']!='OK',x['health'],x['company'])):
        ws.append([h['company'],h['source_type'],h['health'],h['matches'],h['last_checked'],h['message']])
    fill=PatternFill('solid',fgColor='16324F')
    for cell in ws[1]:
        cell.fill=fill; cell.font=Font(color='FFFFFF',bold=True); cell.alignment=Alignment(wrap_text=True)
    widths=[34,18,14,12,16,70]
    for i,w in enumerate(widths,1): ws.column_dimensions[get_column_letter(i)].width=w
    ws.freeze_panes='A2'; ws.auto_filter.ref=ws.dimensions
    health_fills={'OK':'D9EAD3','UNKNOWN':'FFF2CC','BLOCKED':'FCE5CD','ERROR':'F4CCCC'}
    for row in ws.iter_rows(min_row=2):
        row[2].fill=PatternFill('solid',fgColor=health_fills.get(row[2].value,'FFFFFF'))
        for c in row: c.alignment=Alignment(vertical='top',wrap_text=True)
    return ws

def export_xlsx(rows, health):
    wb=Workbook(); wb.remove(wb.active)
    live=[r for r in rows if r['status'] in ('NEW','OPEN')]
    ordered=sorted(rows,key=lambda x:(x['status']!='NEW',x['status']!='OPEN',x['company'],x['title']))
    add_view(wb,'ALL INTERNSHIPS',ordered)

    add_view(wb,'NEW TODAY', sorted(
        [r for r in live if r.get('first_seen')==TODAY], key=lambda x:(x['company'],x['title'])))

    week_start=TODAY_DATE-timedelta(days=6)
    add_view(wb,'NEW THIS WEEK', sorted(
        [r for r in live if parse_iso(r.get('first_seen')) and parse_iso(r.get('first_seen'))>=week_start],
        key=lambda x:(x['first_seen'],x['company'],x['title']), reverse=True))

    add_view(wb,'TEXAS - HOUSTON', sorted(
        [r for r in live if is_texas(r.get('location',''))], key=lambda x:(('houston' not in x.get('location','').lower()),x['company'],x['title'])))

    soon=[]
    for r in live:
        d=parse_iso(r.get('deadline',''))
        if d and TODAY_DATE <= d <= TODAY_DATE+timedelta(days=CLOSING_SOON_DAYS): soon.append(r)
    add_view(wb,'CLOSING SOON', sorted(soon,key=lambda x:(x.get('deadline',''),x['company'],x['title'])))

    # Lightweight dashboard for chapter officers.
    ws=wb.create_sheet('DASHBOARD',0)
    ws['A1']='AIAA UH — SUMMER 2027 INTERNSHIP FINDER'; ws['A1'].font=Font(bold=True,size=16,color='FFFFFF'); ws['A1'].fill=PatternFill('solid',fgColor='16324F')
    ws.merge_cells('A1:D1')
    metrics=[('Live internships',len(live)),('New today',sum(r.get('first_seen')==TODAY for r in live)),
             ('New this week',sum(parse_iso(r.get('first_seen')) and parse_iso(r.get('first_seen'))>=week_start for r in live)),
             ('Texas / Houston',sum(is_texas(r.get('location','')) for r in live)),('Closing in 14 days',len(soon))]
    ws.append([]); ws.append(['View','Count'])
    for k,v in metrics: ws.append([k,v])
    ws['A3'].font=ws['B3'].font=Font(bold=True); ws.column_dimensions['A'].width=28; ws.column_dimensions['B'].width=14
    ws['A10']='Updated'; ws['B10']=TODAY
    ws['A12']='SOURCE HEALTH'; ws['A12'].font=Font(bold=True)
    for i,(label,state) in enumerate([('Sources OK','OK'),('Unknown / unverified','UNKNOWN'),('Blocked','BLOCKED'),('Errors','ERROR')],13):
        ws.cell(i,1,label); ws.cell(i,2,sum(h['health']==state for h in health))
    add_source_health(wb, health)
    wb.save(XLSX)

def main():
    companies=json.loads((ROOT/'companies.json').read_text())
    found={}; health=[]; successful_companies=set()
    adapters={'greenhouse':greenhouse,'lever':lever,'workday':workday,'careers_page':careers_page,
              'sitemap_jobs':sitemap_jobs,'rss_jobs':rss_jobs,'phenom':phenom,'eightfold':eightfold}
    def scan_company(c):
        if c['type'] not in adapters: raise ValueError(f"Unsupported source type: {c['type']}")
        return adapters[c['type']](c)
    # Network-bound sources are independent; a bounded pool prevents slow/blocked
    # employers from making a 90+ company scan take hours.
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures={pool.submit(scan_company,c):c for c in companies}
        for future in as_completed(futures):
            c=futures[future]
            try:
                jobs=future.result()
                if c['type'] in ('careers_page','phenom','eightfold') and len(jobs)==0 and not c.get('trust_zero',False):
                    state='UNKNOWN'; msg='Source fetched, but no verifiable matching early-career engineering roles were parsed; zero is not authoritative.'
                else:
                    state='OK'; msg='Successful source check.'; successful_companies.add(c['company'])
                health.append(health_record(c,state,len(jobs),msg))
                for j in jobs: found[j['key']]=j
                print(f"{c['company']}: {state} - {len(jobs)} matches",flush=True)
            except Exception as e:
                state,msg=classify_error(e); health.append(health_record(c,state,0,msg))
                print(f"WARNING {c['company']}: {state} - {msg}",flush=True)

    old=load_old(); rows=[]
    for key,j in found.items():
        prev=old.get(key); j['first_seen']=prev['first_seen'] if prev else TODAY
        j['last_seen']=TODAY; j['status']='OPEN' if prev else 'NEW'; rows.append(j)

    # Only close a missing job if its company was successfully checked today.
    # If the source is UNKNOWN/BLOCKED/ERROR, preserve its last known status/data.
    for key,prev in old.items():
        if key not in found:
            if prev.get('company') in successful_companies:
                prev['status']='CLOSED'
            rows.append(prev)

    save(rows); export_xlsx(rows, health); export_roles_json(rows)
    ok=sum(h['health']=='OK' for h in health); unknown=sum(h['health']=='UNKNOWN' for h in health)
    blocked=sum(h['health']=='BLOCKED' for h in health); errors=sum(h['health']=='ERROR' for h in health)
    print(f"Source health: {ok} OK, {unknown} UNKNOWN, {blocked} BLOCKED, {errors} ERROR")
    print(f"Found {len(found)} matching internships from today's successful/partial checks; {sum(r['status']=='NEW' for r in rows)} new in database.")

if __name__=='__main__': main()
