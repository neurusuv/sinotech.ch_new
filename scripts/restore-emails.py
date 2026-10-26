import pathlib,sys,json,re
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.deps'))
from bs4 import BeautifulSoup
def decode(value):
 data=bytes.fromhex(value);return bytes(c^data[0] for c in data[1:]).decode('utf-8')
restored=[]
for f in (ROOT/'content').rglob('*.md'):
 text=f.read_text(encoding='utf-8');meta,end=json.JSONDecoder().raw_decode(text);body=BeautifulSoup(text[end:],'html.parser');changes=[]
 for node in body.select('[data-cfemail]'):
  address=decode(node['data-cfemail']);changes.append(address)
  if node.name=='a':node['href']='mailto:'+address;node.clear();node.append(address)
  else:
   parent=node.find_parent('a')
   if parent and '/cdn-cgi/l/email-protection' in parent.get('href',''):parent['href']='mailto:'+address
   node.replace_with(address)
 for a in body.select('a[href]'):
  href=a.get('href','')
  if '/cdn-cgi/l/email-protection#' in href:
   try:
    address=decode(href.split('#',1)[1]);a['href']='mailto:'+address
    if 'protected' in a.get_text():a.clear();a.append(address)
   except ValueError:continue
 for node in body.select('[data-cfemail]'):
  del node['data-cfemail']
  node.attrs.pop('class',None)
 if changes:
  for field in ['description','teaser']:
   if meta.get(field):
    meta[field]=re.sub(r'\[email\s*protected\]',lambda _:changes[0],meta[field])
  f.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n\n'+str(body),encoding='utf-8');restored.append({'page':meta.get('url'),'emails':sorted(set(changes))})
(ROOT/'archive/reports/emails-restored.json').write_text(json.dumps(restored,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'pages':len(restored),'occurrences':sum(len(x['emails']) for x in restored),'contacts':next((x for x in restored if x['page']=='/contacts/'),None)},ensure_ascii=True))
