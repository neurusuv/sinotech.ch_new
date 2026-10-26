import pathlib,json
ROOT=pathlib.Path(__file__).resolve().parents[1]
audit={x['url']:x for x in json.loads((ROOT/'archive/reports/teasers.json').read_text(encoding='utf-8'))}
for f in (ROOT/'content/posts').glob('*.md'):
 text=f.read_text(encoding='utf-8');meta,end=json.JSONDecoder().raw_decode(text)
 if meta.get('url') not in audit:continue
 item=audit[meta['url']];meta['teaser']=item['teaser'];meta['teaser_kind']=item['kind'];meta['display_title']=item.get('display_title',meta['title'])
 f.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n\n'+text[end:].strip(),encoding='utf-8')
