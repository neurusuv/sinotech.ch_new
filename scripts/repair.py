import pathlib,sys,json,urllib.parse,urllib.request,concurrent.futures,hashlib,re,collections
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.deps'))
from bs4 import BeautifulSoup
R=ROOT/'archive/reports';records=json.loads((R/'pages.json').read_text(encoding='utf-8'));assets=json.loads((R/'assets.json').read_text(encoding='utf-8'));fails=json.loads((R/'failures.json').read_text(encoding='utf-8'));am={x['source']:x['local'] for x in assets};recoveries=[]
def canonical(u):
 p=urllib.parse.urlsplit(u);host=p.hostname
 if host in ['sinotech.ch','www.sinotech.ch']:return urllib.parse.urlunsplit(('https','www.sinotech.ch',p.path,p.query,''))
 return u
def local(u):return am.get(canonical(u)) or am.get(u)
def alt(u):return re.sub(r'-\d+x\d+(?=\.[^.]+$)','',u)
def recover(x):
 u=x['url'];p=urllib.parse.urlsplit(u)
 if not re.search(r'\.(jpe?g|png|gif|pdf|docx?|xlsx?)$',p.path,re.I):return None
 a=alt(u)
 if a!=u and local(a):return u,local(a),'existing full-size version',None,None
 candidates=[]
 if a!=u:candidates.append(a)
 if u.startswith('http:'):candidates.append('https:'+u[5:])
 for candidate in candidates:
  try:
   req=urllib.request.Request(urllib.parse.quote(candidate,safe=':/?&=%+;,@!~*\'()'),headers={'User-Agent':'SinotechArchive/1.0 (local preservation)'})
   with urllib.request.urlopen(req,timeout=8) as res:data=res.read();ct=res.headers.get('Content-Type','')
   if 'html' in ct:continue
   cp=urllib.parse.urlsplit(candidate)
   loc=urllib.parse.unquote(cp.path) if cp.hostname=='www.sinotech.ch' and not cp.query else '/media/'+hashlib.sha256(candidate.encode()).hexdigest()[:24]+pathlib.PurePosixPath(cp.path).suffix
   dest=ROOT/'static'/loc.lstrip('/');dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
   return u,loc,candidate,data,candidate
  except Exception:pass
 return None
with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
 for result in ex.map(recover,fails):
  if result:
   u,loc,method,data,src=result;am[u]=loc;recoveries.append({'source':u,'local':loc,'recovered_via':method})
   if data is not None:assets.append({'source':src,'local':loc,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
print('RECOVERED',len(recoveries),flush=True)
# Read metadata from each individual listing card, rather than unrelated recommendations.
cardmeta={}
for f in (ROOT/'archive/html').glob('*.html'):
 soup=BeautifulSoup(f.read_bytes(),'html.parser')
 for card in soup.select('li.wp-block-post'):
  title=card.select_one('.wp-block-post-title a')
  if not title:continue
  url=canonical(urllib.parse.urljoin('https://www.sinotech.ch/',title.get('href','')))
  img=card.select_one('.wp-block-post-featured-image img')
  cardmeta[url]={'categories':list(dict.fromkeys(a.get_text(' ',strip=True) for a in card.select('.taxonomy-category a'))),'featured':local(urllib.parse.urljoin(url,img['src'])) if img else ''}
missingimgs=[];comments=0
for record in records:
 f=ROOT/record['file'];text=f.read_text(encoding='utf-8');dec=json.JSONDecoder();meta,end=dec.raw_decode(text);body=BeautifulSoup(text[end:].strip(),'html.parser')
 if record['source'] in cardmeta:
  meta.update(cardmeta[record['source']]);record.update(cardmeta[record['source']])
 raw=BeautifulSoup((ROOT/record['raw']).read_bytes(),'html.parser')
 # Preserve publicly visible comments as static history where present.
 area=raw.select_one('.comment-list, .wp-block-comment-template')
 if area:
  for unwanted in area.select('script,form,.comment-reply-link'):unwanted.decompose()
  heading=body.new_tag('h2');heading.string='历史留言';body.append(heading);body.append(area);comments+=1
 for tag in body.find_all(True):
  for attr in ['href','src','poster','data-src','data-original']:
   v=tag.get(attr)
   if v:
    u=canonical(urllib.parse.urljoin(record['source'],v))
    if local(u):tag[attr]=local(u)
  if tag.get('srcset'):
   parts=[]
   for v in tag['srcset'].split(','):
    bits=v.strip().split()
    if not bits:continue
    u=canonical(urllib.parse.urljoin(record['source'],bits[0]))
    if local(u):parts.append(' '.join([local(u)]+bits[1:]))
   if parts:tag['srcset']=', '.join(parts)
   else:del tag['srcset']
  if tag.name=='img':
   src=tag.get('src','');url=canonical(urllib.parse.urljoin(record['source'],src))
   if local(url):tag['src']=local(url);src=tag['src']
   if src.startswith(('http:','https:','//')):
    missingimgs.append({'page':record['url'],'image':url,'alt':tag.get('alt','')})
    tag.decompose()
 f.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n\n'+str(body),encoding='utf-8')
# Preserve the four title-only source sections without inventing their content.
known={r['url'] for r in records}
for path in ['/women/','/cafps/','/youth/','/camsts/']:
 if path in known:continue
 url='https://www.sinotech.ch'+path;raw='archive/html/'+hashlib.sha256(url.encode()).hexdigest()[:20]+'.html';s=BeautifulSoup((ROOT/raw).read_bytes(),'html.parser');h=s.select_one('h1');title=h.get_text(' ',strip=True) if h else s.title.get_text().split(' – ')[0]
 meta={'title':title,'url':path,'source':url,'type':'pages','description':'','date':'2000-01-01T00:00:00+00:00'};file='content/pages/'+hashlib.sha256(url.encode()).hexdigest()[:16]+'.md'
 (ROOT/file).write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n\n\n',encoding='utf-8');records.append({**meta,'file':file,'raw':raw})
known_sources={r['source'] for r in records}
for url in json.loads((R/'crawl.json').read_text(encoding='utf-8'))['visited']:
 if url in known_sources or not re.fullmatch(r'https://www.sinotech.ch/archives/\d+\.html',url):continue
 raw='archive/html/'+hashlib.sha256(url.encode()).hexdigest()[:20]+'.html'
 if not (ROOT/raw).exists():continue
 s=BeautifulSoup((ROOT/raw).read_bytes(),'html.parser');h=s.select_one('h1');t=s.select_one('time[datetime]')
 if not h:continue
 meta={'title':h.get_text(' ',strip=True),'date':t.get('datetime') if t else '2000-01-01T00:00:00+00:00','url':urllib.parse.urlsplit(url).path,'source':url,'type':'posts','categories':cardmeta.get(url,{}).get('categories',[]),'description':''}
 file='content/posts/'+hashlib.sha256(url.encode()).hexdigest()[:16]+'.md';(ROOT/file).write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n\n\n',encoding='utf-8');records.append({**meta,'file':file,'raw':raw})
for name,obj in [('pages',records),('assets',assets),('recoveries',recoveries),('missing-images',missingimgs),('unresolved', [x for x in fails if not local(x['url'])])]:
 (R/(name+'.json')).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
print('METADATA',len(cardmeta),'MISSING IMAGE REFERENCES',len(missingimgs),'COMMENT PAGES',comments,flush=True)
