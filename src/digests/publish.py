#!/usr/bin/env python3
"""Build site/ for GitHub Pages: copies web/YYYY-MM-DD.html and writes index.html (往期列表)."""
import json,os,re,shutil,glob,html
os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.makedirs('site',exist_ok=True)
pages=sorted([os.path.basename(p) for p in glob.glob('web/*.html') if re.match(r'\d{4}-\d{2}-\d{2}\.html$',os.path.basename(p))],reverse=True)
rows=[]
for p in pages:
    shutil.copy('web/'+p,'site/'+p); d=p[:-5]; heads=''
    try:
        j=json.load(open(f'items-{d}.json')); its=j['items']
        heads=' · '.join(html.escape(i['title']) for i in its[:3]); n=len(its); iss=html.escape(j.get('issue',''))
    except Exception: n='';iss=''
    rows.append(f'<a class="row" href="{d}.html"><span class="d">{d}</span><span class="i">{iss}</span><span class="t">{heads}</span><span class="n">{n} 条 →</span></a>')
open('site/.nojekyll','w').close()
open('site/index.html','w').write(f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>叼报 · 往期</title><style>
body{{margin:0;background:#f5f1e8;color:#1a1a1a;font-family:"Noto Serif SC","Songti SC",serif}}
.w{{max-width:860px;margin:0 auto;padding:48px 20px}}h1{{font-size:clamp(32px,7vw,64px);font-weight:500;letter-spacing:.04em;margin:0;border-bottom:3px double #1a1a1a;padding-bottom:12px}}
.k{{font:12px/1 monospace;letter-spacing:.2em;color:#b23a2a;text-transform:uppercase;margin-bottom:14px}}
.row{{display:grid;grid-template-columns:120px 90px 1fr auto;gap:12px;padding:18px 0;border-bottom:1px solid #1a1a1a33;color:inherit;text-decoration:none;opacity:0;animation:f .6s forwards}}
.row:hover{{background:#fff8}}.d{{font-family:monospace}}.i{{color:#b23a2a;font-family:monospace}}.n{{color:#666}}
@keyframes f{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:none}}}}
@media(max-width:600px){{.row{{grid-template-columns:1fr auto}}.i,.t{{grid-column:1/-1}}}}
</style></head><body><div class="w"><div class="k">DiaoDaily · Archive</div><h1>叼报 · 往期</h1>
{"".join(rows)}<p style="color:#888;font-size:12px;margin-top:32px">每日更新 · 内容来自 X 与 GitHub/HF/HN 等公开来源</p></div>
<script>document.querySelectorAll('.row').forEach((r,i)=>r.style.animationDelay=i*80+'ms')</script></body></html>''')
print(pages)
