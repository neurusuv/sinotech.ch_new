import pathlib,sys,json,hashlib,urllib.parse,re,collections,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.deps'))
from bs4 import BeautifulSoup
reports=ROOT/'archive/reports'
records=json.loads((reports/'pages.json').read_text(encoding='utf-8'))
crawl=json.loads((reports/'crawl.json').read_text(encoding='utf-8'))
byurl={r['source']:r for r in records}
(ROOT/'content/listings').mkdir(exist_ok=True)
for generated in (ROOT/'content/listings').glob('*.md'):generated.unlink()
listing_paths=set()
# Keep every reachable category, author and chronological archive at its source URL.
for url in crawl['visited']:
    if url=='https://www.sinotech.ch/' or url in byurl or re.search(r'/page/\d+/?$',url) and '/archives/' not in url and '/author/' not in url:continue
    f=ROOT/'archive/html'/(hashlib.sha256(url.encode()).hexdigest()[:20]+'.html')
    if not f.exists():continue
    soup=BeautifulSoup(f.read_bytes(),'html.parser')
    links=[]
    for a in soup.select('h2 a,.wp-block-post-title a'):
        u=urllib.parse.urljoin(url,a.get('href',''))
        if u in byurl and u not in links:links.append(u)
    if not links:continue
    path=urllib.parse.unquote(urllib.parse.urlsplit(url).path).rstrip('/')+'/'
    if path in listing_paths:continue
    listing_paths.add(path)
    meta={'title':soup.title.get_text().rsplit(' – ',1)[0],'url':path,'source':url,'type':'listings','items':links}
    (ROOT/'content/listings'/(hashlib.sha256(path.encode()).hexdigest()[:16]+'.md')).write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'layouts/listings').mkdir(exist_ok=True)
# Keep the hand-designed archive template unchanged.

subprocess.run(['hugo','--minify','--printPathWarnings','--cleanDestinationDir'],cwd=ROOT,check=True)
public=ROOT/'public';broken=[];remote=[];imagecount=0;htmlcount=0
def exists(path):
    p=public/urllib.parse.unquote(path).lstrip('/')
    return p.is_file() or (p/'index.html').is_file()
for f in public.rglob('*.html'):
    if not f.is_file():continue
    htmlcount+=1;s=BeautifulSoup(f.read_bytes(),'html.parser')
    for tag in s.find_all(['a','img','source','script','link','iframe']):
        attr='href' if tag.name in ['a','link'] else 'src';val=tag.get(attr,'')
        if not val or val.startswith(('data:','mailto:','tel:','#','javascript:')):continue
        p=urllib.parse.urlsplit(val)
        if tag.name=='img':imagecount+=1
        if p.netloc and p.hostname not in ['localhost','127.0.0.1']:
            if tag.name!='a':remote.append({'page':str(f.relative_to(public)),'tag':tag.name,'url':val})
            continue
        if p.path.startswith('/') and not exists(p.path):broken.append({'page':str(f.relative_to(public)),'tag':tag.name,'url':val})
posts=[r for r in records if r['type']=='posts'];pages=[r for r in records if r['type']=='pages']
index=json.loads((public/'index.json').read_text(encoding='utf-8'))
dates=sorted({r['date'][:10] for r in posts})
report={'content':len(records),'posts':len(posts),'pages':len(pages),'rendered_html':htmlcount,'search_records':len(index),'rendered_image_references':imagecount,'missing_local_references':broken,'remote_embeds':remote,'categories':dict(collections.Counter(c for r in posts for c in r['categories'])),'dates':[dates[0],dates[-1]]}
(reports/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['missing_local_references','remote_embeds']},ensure_ascii=False))
print('MISSING LOCAL',len(broken),'REMOTE EMBEDS',len(remote))
