#!/usr/bin/env python3
"""每日设计灵感页构建器。用法:
  python3 build.py 2026-11-01 [--allow-short] [--blocks DIR] [--out FILE] [--check]
  --allow-short  条数不足 8 时放行（blocks 里任一 meta 或 blocks/_short.json 必须写 short_reason）
  --blocks DIR   换 blocks 目录（测试用）；--out 输出文件；--check 构建后跑 tools/check.py 做 390/360 手机检查
规则：日期 >= 2026-11-01 用 8 条规则（Web 4 + App 4，focus 交互≥4 / 界面≥3）；更早日期按旧规则 2 Web + 2 App。
block 结构见 HOWTO.md。退出码 2 = 校验不通过（不生成页面）。"""
import sys,os,re,json,glob,base64,argparse,subprocess
sys.stdout.reconfigure(line_buffering=True)
from urllib.parse import urlparse
os.chdir(os.path.dirname(os.path.abspath(__file__)))
ap=argparse.ArgumentParser();ap.add_argument('date',nargs='?',default='2026-10-13')
ap.add_argument('--allow-short',action='store_true');ap.add_argument('--blocks',default='blocks')
ap.add_argument('--out');ap.add_argument('--check',action='store_true')
ap.add_argument('--recommended',default='/workspace/inspo/recommended.md')
A=ap.parse_args();date=A.date;NEW=date>='2026-11-01'
ERR=[];WARN=[]
def b64(p): return 'data:image/webp;base64,'+base64.b64encode(open(p,'rb').read()).decode()
def part(s,tag):
    m=re.search(r'<!--%s-->(.*?)<!--/%s-->'%(tag,tag),s,re.S); return m.group(1).strip() if m else ''
def site_of(name,url):
    if 'mobbin.com' in (url or ''): return name.split(' · ')[0].strip().lower()
    h=urlparse(url or '').netloc.lower(); return h[4:] if h.startswith('www.') else h or name.split(' · ')[0].strip().lower()
files=sorted(f for f in glob.glob(os.path.join(A.blocks,'*.html')))
blocks=[]
for f in files:
    s=open(f).read(); m=re.search(r'<!--meta (.*?)-->',s,re.S)
    if not m: sys.exit(f'[build] {f}: 缺 <!--meta {{...}}-->')
    try: meta=json.loads(m.group(1))
    except Exception as e: sys.exit(f'[build] {f}: meta 不是合法 JSON：{e}')
    blocks.append((f,s,meta))
def die():
    print('[build] 不生成页面，校验未通过：');[print('  ✗',e) for e in ERR];sys.exit(2)
kinds=[]
for f,s,m in blocks:
    k=m.get('kind')
    if k not in ('Web','App'): ERR.append(f'{f}: meta.kind 必须是 "Web" 或 "App"，现在是 {k!r}')
    kinds.append(k)
w,a=kinds.count('Web'),kinds.count('App')
if not NEW:
    if w<2 or a<2: ERR.append(f'本期 Web={w}、App={a}，旧规则需要 Web≥2 且 App≥2')
    if ERR: die()
    print(f'[build] 旧规则（<2026-11-01）kind 校验通过：Web={w} App={a}')
else:
    # ---- 1) 数量：Web 4 + App 4 ----
    short=None
    for f,s,m in blocks:
        if m.get('short_reason'): short=m['short_reason']
    if os.path.exists(os.path.join(A.blocks,'_short.json')):
        short=json.load(open(os.path.join(A.blocks,'_short.json'))).get('short_reason') or short
    if w>4 or a>4: ERR.append(f'Web={w}、App={a}，每期固定 Web 4 + App 4，多出来的移走')
    if w<4 or a<4:
        msg=f'Web={w}、App={a}，需要 Web 4 + App 4：补 {max(0,4-w)} 个 Web、{max(0,4-a)} 个 App'
        if not A.allow_short: ERR.append(msg+'；确实不够且不想凑，就加 --allow-short 并写 short_reason')
        elif not short: ERR.append(msg+'；用了 --allow-short 但没写 short_reason（写在任一 meta 或 blocks/_short.json）')
        else: WARN.append(f'条数不足放行：{msg}；原因：{short}（页面顶部会显示，交付消息里也要写）')
    # ---- 2) focus ----
    FOC=('交互','界面','兼具');ix=ui=both=0
    for f,s,m in blocks:
        fo=m.get('focus')
        if fo not in FOC: ERR.append(f'{f}: meta.focus 必须是 交互/界面/兼具 之一，现在是 {fo!r}');continue
        if fo in('交互','兼具'):
            ix+=1
            for fld,lab in(('how','怎么操作'),('fresh','为什么新鲜')):
                if len((m.get(fld) or '').strip())<8: ERR.append(f'{f}: 交互类要写 meta.{fld}（「{lab}」一句话，≥8 字）')
        if fo in('界面','兼具'): ui+=1
        if fo=='兼具': both+=1
    if both>1: ERR.append(f'兼具 {both} 条，最多允许 1 条；把多余的改成 交互 或 界面')
    need=[]
    if ix<4: need.append(f'交互 {ix}/4（再换 {4-ix} 条以交互/动效为主的）')
    if ui<3: need.append(f'界面 {ui}/3（再换 {3-ui} 条以视觉/版面为主的）')
    if need and not (A.allow_short and short): ERR.append('focus 覆盖不够：'+'；'.join(need)+'（兼具可同时计入两边）')
    elif need: WARN.append('focus 不足但已 --allow-short 放行：'+'；'.join(need))
    # ---- 3) 素材 ----
    for f,s,m in blocks:
        d=part(s,'demo')
        if m.get('kind')=='Web':
            if len(d)<200 or not re.search(r'<script|:hover|:active|animation|transition|@keyframes',d):
                ERR.append(f'{f}: Web 条目要有可交互的 live demo（<!--demo--> 里需要 HTML+CSS 动效/JS，现在太短或没有交互）')
        else:
            refs=re.findall(r'(?:data-b64|src|poster)="(?:inline:)?([^"]+)"',d)
            local=[r for r in refs if not r.startswith(('http','data:','blob:'))]
            if not local: ERR.append(f'{f}: App 条目要有本地视频或图片素材（assets/{date}/…）')
            for r in local:
                if not os.path.exists(r): ERR.append(f'{f}: 素材文件不存在：{r}')
            for v in re.findall(r'<video[^>]*>',d):
                for att in('muted','loop','playsinline'):
                    if not re.search(r'\b%s\b'%att,v): ERR.append(f'{f}: <video> 缺 {att}')
                if 'preload="metadata"' not in v and 'preload="none"' not in v: ERR.append(f'{f}: <video> 要 preload="metadata"（懒加载）')
                if re.search(r'\ssrc="',v): WARN.append(f'{f}: <video> 直接写了 src，建议用 data-b64，由外壳 IntersectionObserver 进视口再加载')
    # ---- 4) 和上一期不重复站点/元素 ----
    prev_dates=[os.path.basename(p) for p in glob.glob('blocks/_archive/*') if os.path.basename(p)<date]
    rec=open(A.recommended).read() if os.path.exists(A.recommended) else ''
    rows=re.findall(r'^\|\s*(\d{4}-\d\d-\d\d)\s*\|\s*([^|]+?)\s*\|\s*(\S+)\s*\|',rec,re.M)
    prev_dates+= [d for d,_,_ in rows if d<date]
    if prev_dates:
        pd=max(prev_dates);psites=set();pel=set()
        for d,n,u in rows:
            if d==pd: psites.add(site_of(n,u))
        for pf in glob.glob(f'blocks/_archive/{pd}/*.html'):
            mm=re.search(r'<!--meta (.*?)-->',open(pf).read(),re.S)
            if mm:
                pm=json.loads(mm.group(1));psites.add(site_of(pm.get('name',''),pm.get('url','')))
                pel|=set(pm.get('elements',[]))|{pm.get('key')}
        for f,s,m in blocks:
            st=site_of(m.get('name',''),m.get('url',''))
            if st in psites: ERR.append(f'{f}: 站点/App「{st}」上一期（{pd}）刚用过，换一个')
            dup=(set(m.get('elements',[]))|{m.get('key')})&pel
            if dup: ERR.append(f'{f}: 元素 {sorted(dup)} 上一期（{pd}）用过')
        print(f'[build] 对照上一期 {pd}：站点 {sorted(psites)}')
    # 本期内部也不能重复站点
    ss=[site_of(m.get('name',''),m.get('url','')) for _,_,m in blocks]
    for x in set(ss):
        if ss.count(x)>1: ERR.append(f'本期站点「{x}」出现 {ss.count(x)} 次，每站只上 1 条')
    if ERR: die()
    print(f'[build] 8 条规则校验通过：Web={w} App={a}；交互={ix} 界面={ui}（兼具 {both}）')
# ---- 渲染 ----
cards=[];nav=[];total=0;seen=set()
for f,s,meta in blocks:
    code=part(s,'code'); assert '</textarea' not in code
    k=meta['key']; kind=meta.get('kind','Web'); fo=meta.get('focus')
    params=''.join(f'<li>{p}</li>' for p in meta.get('params',[]))
    tags=''.join(f'<span class="tag">{t}</span>' for t in meta.get('tags',[]))
    thumb=f'<img class="thumb" src="{b64(meta["thumb"])}" alt="{meta["name"]} 原站截图（对照）" loading="lazy">' if meta.get('thumb') else ''
    focus=f'<span class="focus f-{ {"交互":"ix","界面":"ui","兼具":"both"}[fo]}">{fo}</span>' if fo else ''
    howfresh=''
    if fo in('交互','兼具'):
        howfresh=f'<dl class="hf"><dt>怎么操作</dt><dd>{meta["how"]}</dd><dt>为什么新鲜</dt><dd>{meta["fresh"]}</dd></dl>'
    nav.append(f'<a href="#b-{k}" class="chip{" app" if kind=="App" else ""}">{meta["name"].split(" · ")[0]}</a>')
    cards.append(f'''<article class="block design in" id="b-{k}" data-site="{meta["name"]}" data-url="{meta["url"]}" data-focus="{fo or ''}">
<header class="bh"><span class="kind {kind.lower()}">{kind}</span>{focus}<h2>{meta["name"]}</h2><span class="sub">{meta.get("subtitle","")}</span></header>
<div class="demo d-{k}">{part(s,"demo")}</div>
<div class="bb">{howfresh}<p class="why">{meta["why"]}</p><div class="tags">{tags}</div>
<details><summary>关键参数</summary><ul class="params">{params}</ul></details>
{f'<details><summary>关键代码</summary><textarea class="code" readonly spellcheck="false" rows="{min(18,code.count(chr(10))+2)}">{code}</textarea></details>' if code else ''}
<div class="ref">{thumb}<div class="links"><a href="{meta["url"]}" target="_blank" rel="noopener">{meta.get("ref","原站")} ↗</a><span class="note">{meta.get("note","")}</span></div></div>
<div class="act"><span class="df-stars" aria-label="评分"></span><button class="df-fav" type="button"></button></div></div></article>''')
    for r in re.findall(r'(?:data-b64|src|poster)="(?:inline:)?([^"]+)"',part(s,'demo'))+([meta['thumb']] if meta.get('thumb') else []):
        if r not in seen and os.path.exists(r): seen.add(r); total+=os.path.getsize(r)
cards=[re.sub(r'poster="inline:([^"]+)"',lambda m:'poster="'+b64(m.group(1))+'"',c) for c in cards]
shortnote=''
if NEW and len(blocks)<8:
    rs=[m.get('short_reason') for _,_,m in blocks if m.get('short_reason')]
    if os.path.exists(os.path.join(A.blocks,'_short.json')): rs.append(json.load(open(os.path.join(A.blocks,'_short.json'))).get('short_reason'))
    shortnote=f'<p class="short in">本期 {len(blocks)} 条（目标 8 条）：{rs[-1]}</p>'
t=open('template.html').read().replace('{{DATE}}',date).replace('{{NAV}}',''.join(nav)).replace('{{BLOCKS}}',shortnote+'\n'.join(cards)).replace('{{COUNT}}',str(len(cards)))
bad=re.findall(r'&(?:amp|lt|gt|quot|apos|nbsp|#\d+|#x[0-9a-f]+);',t,re.I)
assert not bad, f'HTML 实体会被连接器还原: {set(bad)}'
out=A.out or f'{date}.html'
open(out,'w').write(t)
mb=(total+len(t.encode()))/1e6
print(f'[build] {out} {len(t)} bytes, {len(cards)} blocks；页面+素材合计约 {mb:.1f}MB')
if mb>8: WARN.append(f'单页素材约 {mb:.1f}MB > 8MB：视频压到 480px 宽/24–30fps/CRF 30 左右或截短')
for x in WARN: print('  ⚠',x)
if A.check:
    r=subprocess.run(['timeout','-k','5','120','python3','tools/check.py',out]);sys.exit(r.returncode)
