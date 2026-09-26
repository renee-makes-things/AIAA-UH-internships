import csv, html, json, re
from datetime import date, datetime, timedelta
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
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
ENGINEERING = re.compile(r'(mechanical|aerospace|manufactur|production|test|structures?|mechanisms?|propulsion|avionics|electrical|systems?|integration|flight|materials?|quality|design|engineering)', re.I)

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

def greenhouse(c):
    url=f"https://boards-api.greenhouse.io/v1/boards/{c['token']}/jobs?content=true"
    r=requests.get(url,timeout=30); r.raise_for_status()
    out=[]
    for j in r.json().get('jobs',[]): 
        text=' '.join([j.get('title',''), clean(j.get('content',''))])
        if INTERN.search(text) and SEASON.search(text) and ENGINEERING.search(text):
            out.append({'key':f"gh:{c['token']}:{j['id']}",'company':c['company'],'title':j.get('title',''),
                        'location':(j.get('location') or {}).get('name',''),'deadline':extract_deadline(text),'url':j.get('absolute_url','')})
    return out

def lever(c):
    url=f"https://api.lever.co/v0/postings/{c['token']}?mode=json"
    r=requests.get(url,timeout=30); r.raise_for_status()
    out=[]
    for j in r.json():
        text=' '.join([j.get('text',''), clean(j.get('descriptionPlain','')), clean(j.get('additionalPlain',''))])
        if INTERN.search(text) and SEASON.search(text) and ENGINEERING.search(text):
            cats=j.get('categories') or {}
            out.append({'key':f"lever:{c['token']}:{j['id']}",'company':c['company'],'title':j.get('text',''),
                        'location':cats.get('location',''),'deadline':extract_deadline(text),'url':j.get('hostedUrl','')})
    return out

def workday(c):
    # Workday public CXS endpoint. Different employers expose different site names,
    # so host/tenant/site live in companies.json instead of being hard-coded.
    base=f"https://{c['host']}/wday/cxs/{c['tenant']}/{c['site']}"
    out=[]; offset=0; limit=20
    while offset < 200:
        r=requests.post(base+'/jobs',json={'appliedFacets':{},'limit':limit,'offset':offset,'searchText':'2027 internship'},timeout=30)
        r.raise_for_status(); data=r.json(); posts=data.get('jobPostings',[])
        if not posts: break
        for j in posts:
            title=j.get('title',''); ext=j.get('externalPath','')
            # Fetch detail because Workday search results often omit the full description.
            try:
                d=requests.get(base+ext,timeout=30).json().get('jobPostingInfo',{})
            except Exception:
                d={}
            text=' '.join([title, clean(d.get('jobDescription','')), str(d.get('additionalLocations',''))])
            if INTERN.search(text) and SEASON.search(text) and ENGINEERING.search(text):
                url=d.get('externalUrl') or ('https://'+c['host']+ext)
                loc=d.get('location') or j.get('locationsText','')
                jid=d.get('jobReqId') or ext
                out.append({'key':f"wd:{c['tenant']}:{jid}",'company':c['company'],'title':title,'location':loc,'deadline':extract_deadline(text),'url':url})
        offset += limit
        if offset >= data.get('total',0): break
    return out


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
        r=requests.get(page_url,headers=headers,timeout=30); r.raise_for_status()
        soup=BeautifulSoup(r.text,'html.parser')
        seen=set()
        for a in soup.find_all('a', href=True):
            href=urljoin(page_url,a.get('href',''))
            # Include parent text because many career sites put location/date beside the title.
            parent=a.parent.get_text(' ',strip=True) if a.parent else ''
            text=clean(' '.join([a.get_text(' ',strip=True), parent]))
            if not text or href in seen: continue
            if INTERN.search(text) and SEASON.search(text) and ENGINEERING.search(text):
                seen.add(href)
                title=a.get_text(' ',strip=True) or text[:180]
                key='page:'+c['company']+':'+href
                out.append({'key':key,'company':c['company'],'title':title[:220],
                            'location':'','deadline':extract_deadline(text),'url':href})
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
    fields=['key','company','title','location','status','first_seen','last_seen','deadline','url']
    with DB.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

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
    for c in companies:
        try:
            jobs=greenhouse(c) if c['type']=='greenhouse' else lever(c) if c['type']=='lever' else workday(c) if c['type']=='workday' else careers_page(c) if c['type']=='careers_page' else []
            # API-backed sources can reliably report zero. Generic HTML pages cannot: many
            # render jobs in JavaScript, so zero from them is UNKNOWN unless explicitly trusted.
            if c['type']=='careers_page' and len(jobs)==0 and not c.get('trust_zero',False):
                state='UNKNOWN'; msg='Page fetched, but no verifiable Summer 2027 engineering internships were parsed; zero is not treated as authoritative.'
            else:
                state='OK'; msg='Successful source check.'; successful_companies.add(c['company'])
            health.append(health_record(c,state,len(jobs),msg))
            for j in jobs: found[j['key']]=j
            print(f"{c['company']}: {state} - {len(jobs)} matches")
        except Exception as e:
            state,msg=classify_error(e); health.append(health_record(c,state,0,msg))
            print(f"WARNING {c['company']}: {state} - {msg}")

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

    save(rows); export_xlsx(rows, health)
    ok=sum(h['health']=='OK' for h in health); unknown=sum(h['health']=='UNKNOWN' for h in health)
    blocked=sum(h['health']=='BLOCKED' for h in health); errors=sum(h['health']=='ERROR' for h in health)
    print(f"Source health: {ok} OK, {unknown} UNKNOWN, {blocked} BLOCKED, {errors} ERROR")
    print(f"Found {len(found)} matching internships from today's successful/partial checks; {sum(r['status']=='NEW' for r in rows)} new in database.")

if __name__=='__main__': main()
