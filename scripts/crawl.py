import sys, subprocess, pathlib, json, urllib.request, urllib.parse, urllib.error, concurrent.futures, hashlib, time, re, html
ROOT=pathlib.Path(__file__).resolve().parents[1]
ROOT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'.deps'))
try: from bs4 import BeautifulSoup
except ImportError:
    subprocess.run([sys.executable,'-m','pip','install','--target',str(ROOT/'.deps'),'beautifulsoup4'],check=True)
    from bs4 import BeautifulSoup
BASE='https://www.sinotech.ch/'
for d in ['archive/html','archive/reports','content/posts','content/pages','static','layouts/_default','layouts/partials','scripts']:(ROOT/d).mkdir(parents=True,exist_ok=True)
def norm(url,base=BASE):
    u=urllib.parse.urljoin(base,html.unescape(url)); p=urllib.parse.urlsplit(u)
    if p.hostname in ['sinotech.ch','www.sinotech.ch']:
        return urllib.parse.urlunsplit(('https','www.sinotech.ch',p.path or '/',p.query,''))
    return urllib.parse.urlunsplit((p.scheme,p.netloc,p.path,p.query,''))
def request(url):
    for attempt in range(2):
        try:
            req=urllib.request.Request(urllib.parse.quote(url,safe=':/?&=%+;,@!~*\'()'),headers={'User-Agent':'SinotechArchive/1.0 (local preservation)'})
            with urllib.request.urlopen(req,timeout=14) as res:return res.read(),res.headers.get('Content-Type',''),res.geturl()
        except urllib.error.HTTPError as e:
            err=str(e)
            if e.code in [400,401,403,404,410]:break
        except Exception as e:
            err=str(e);time.sleep(attempt+1)
    return None,err,url
def fetch_page(url):
    key=hashlib.sha256(url.encode()).hexdigest()[:20]; dest=ROOT/'archive/html'/f'{key}.html'
    if dest.exists(): data=dest.read_bytes();ct='text/html';final=url
    else:
        data,ct,final=request(url)
        if data is not None and 'html' in ct:dest.write_bytes(data)
    return url,data,ct,final,str(dest.relative_to(ROOT))
queue={BASE}; seen=set(); pages={}; failures=[]; assets=set()
for n in range(2,48):queue.add(BASE+f'page/{n}')
while queue:
    batch=sorted(queue-seen);queue=set()
    if not batch:break
    print('PAGE BATCH',len(batch),'done',len(seen),flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for url,data,ct,final,saved in pool.map(fetch_page,batch):
            seen.add(url)
            if data is None: failures.append({'url':url,'error':ct});continue
            if 'html' not in ct:assets.add(url);continue
            soup=BeautifulSoup(data,'html.parser');pages[url]=(soup,saved)
            for tag in soup.find_all(['a','img','source','video','audio','iframe','link','script']):
                for attr in ['href','src','poster','data-src','data-original']:
                    val=tag.get(attr)
                    if not val or val.startswith(('data:','mailto:','tel:','javascript:','#')):continue
                    target=norm(val,url);p=urllib.parse.urlsplit(target)
                    if p.scheme not in ['https','http']:continue
                    internal=p.hostname=='www.sinotech.ch'
                    isasset=bool(re.search(r'\.(?:jpe?g|png|gif|webp|svg|ico|pdf|docx?|xlsx?|pptx?|zip|mp4|mp3|css|js|woff2?|ttf)(?:$|\?)',p.path,re.I)) or '/wp-content/uploads/' in p.path
                    if isasset:assets.add(target)
                    elif internal and tag.name=='a' and not p.query and not any(x in p.path for x in ['/feed','/wp-json','/wp-admin','/wp-login','/comment-page-']):
                        if target not in seen:queue.add(target)
                for item in tag.get('srcset','').split(','):
                    if item.strip():assets.add(norm(item.strip().split()[0],url))
    (ROOT/'archive/reports/progress.json').write_text(json.dumps({'pages':len(pages),'queued':len(queue),'assets':len(assets),'failed':failures},ensure_ascii=False,indent=2),encoding='utf-8')
    if len(seen)>12000:raise RuntimeError('Unexpected crawl expansion; inspect progress')
print('PAGES COMPLETE',len(pages),'ASSETS',len(assets),flush=True)
assetmap={};assetrecords=[]
def asset_path(url):
    p=urllib.parse.urlsplit(url)
    path=urllib.parse.unquote(p.path)
    if p.hostname=='www.sinotech.ch' and not p.query and '..' not in pathlib.PurePosixPath(path).parts:return path
    suffix=pathlib.PurePosixPath(path).suffix
    return '/media/'+hashlib.sha256(url.encode()).hexdigest()[:24]+suffix
def fetch_asset(url):
    local=asset_path(url);dest=ROOT/'static'/local.lstrip('/')
    if dest.exists():data=dest.read_bytes();ct='cached'
    else:
        data,ct,_=request(url)
        if data is not None:
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    return url,local,data,ct
pending=assets.copy();done=set()
while pending:
    batch=sorted(pending-done);pending=set()
    if not batch:break
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        for i,(url,local,data,ct) in enumerate(pool.map(fetch_asset,batch)):
            done.add(url)
            if data is None:failures.append({'url':url,'error':ct});continue
            assetmap[url]=local
            assetrecords.append({'source':url,'local':local,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
            if '.css' in urllib.parse.urlsplit(url).path:
                for val in re.findall(r'url\([\s\'"]*([^\)\'"\s]+)',data.decode('utf-8','replace')):
                    if not val.startswith('data:'):pending.add(norm(val,url))
            if i%100==0:print('ASSETS',len(done),'/',len(assets),flush=True)
    assets|=pending
def page_local(url):
    p=urllib.parse.urlsplit(url)
    if p.hostname=='www.sinotech.ch' and url in pages:return p.path or '/'
    return url
records=[]
for url,(soup,saved) in pages.items():
    body=soup.select_one('.entry-content, .wp-block-post-content')
    if not body:continue
    title=soup.select_one('h1.wp-block-post-title, h1.entry-title, h1')
    title=title.get_text(' ',strip=True) if title else soup.title.get_text().split(' – ')[0]
    p=urllib.parse.urlsplit(url);post=bool(re.fullmatch(r'/archives/\d+\.html/?',p.path))
    kind='posts' if post else 'pages'
    stamp=soup.select_one('time[datetime]');date=stamp.get('datetime') if stamp else '2000-01-01T00:00:00+00:00'
    cats=list(dict.fromkeys(x.get_text(' ',strip=True) for x in soup.select('a[rel~=category], .taxonomy-category a')))
    featured=soup.select_one('.wp-block-post-featured-image img, img.wp-post-image')
    image=norm(featured.get('src'),url) if featured and featured.get('src') else ''
    for tag in body.find_all(['script','style']):tag.decompose()
    for tag in body.find_all(True):
        for attr in list(tag.attrs):
            if attr.startswith('on'):del tag[attr]
        for attr in ['src','href','poster','data-src','data-original']:
            if tag.get(attr):
                val=tag[attr]
                if val.startswith(('data:','mailto:','tel:','#')):continue
                target=norm(val,url);tag[attr]=assetmap.get(target,page_local(target))
        if tag.get('srcset'):
            tag['srcset']=', '.join(' '.join([assetmap.get(norm(x.strip().split()[0],url),norm(x.strip().split()[0],url))]+x.strip().split()[1:]) for x in tag['srcset'].split(',') if x.strip())
        if tag.name=='img':
            tag['loading']='lazy';tag['decoding']='async'
            if tag.get('data-src'):tag['src']=tag['data-src']
    excerpt=body.get_text(' ',strip=True)[:180]
    meta={'title':title,'date':date,'url':p.path,'source':url,'categories':cats,'featured':assetmap.get(image,''),'description':excerpt,'type':kind}
    key=hashlib.sha256(url.encode()).hexdigest()[:16]
    (ROOT/f'content/{kind}/{key}.md').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n\n'+body.decode_contents(),encoding='utf-8')
    records.append({**meta,'file':f'content/{kind}/{key}.md','raw':saved})
for url,local in assetmap.items():
    if '.css' in urllib.parse.urlsplit(url).path:
        dest=ROOT/'static'/local.lstrip('/');txt=dest.read_text(encoding='utf-8',errors='replace')
        txt=re.sub(r'url\(([\s\'"]*)([^\)\'"\s]+)([\s\'"]*)\)',lambda m:'url('+m[1]+assetmap.get(norm(m[2],url),norm(m[2],url))+m[3]+')',txt)
        dest.write_text(txt,encoding='utf-8')
for name,obj in [('pages',records),('assets',assetrecords),('failures',failures),('crawl',{'visited':sorted(seen),'content_count':len(records),'html_count':len(pages),'asset_count':len(assetrecords),'captured':'2026-10-26','scope':'Public reachable same-host HTML, 47 main pagination pages, referenced media and CSS dependencies. External linked websites are not recursively crawled.'})]:
    (ROOT/f'archive/reports/{name}.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
print('COMPLETE',len(records),'content',len(assetrecords),'assets',len(failures),'failures',flush=True)
