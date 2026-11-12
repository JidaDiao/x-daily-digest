#!/usr/bin/env python3
"""每日设计灵感页构建器。用法:
  python3 build.py 2026-11-01 [--allow-short] [--blocks DIR] [--out FILE] [--check]
  --allow-short  条数不足 8 时放行（blocks 里任一 meta 或 blocks/_short.json 必须写 short_reason）
  --blocks DIR   换 blocks 目录（测试用）；--out 输出文件；--check 构建后跑 tools/check.py 做 390/360 手机检查
规则：日期 >= 2026-11-01 用 8 条规则（Web 4 + App 4，focus 交互≥4 / 界面≥3）；更早日期按旧规则 2 Web + 2 App。
blocks/_layout.json 可选（多版式工具）；缺省用 list 壳。用户 2026-11-03 更正：设计页不强制每日换 layout。
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
LAYOUTS=('magazine','workbench','wall','timeline','deck','index')
# 开场轮换（2026-11-12 起）：「今日拼接」每天换一种展示方式，避免开头总是一个样。
# collage=整块拼贴（现版）/ strip=横条 chips / fold=折叠（默认收起，点开看拼贴）。按日期序数轮换，同一天固定。
OPENINGS=('collage','fold','strip')
DIM_KEYS=('carrier','nav','axis','chrome')
DIFF_KEYS=('style','motion','ui','ux','card')
CARD_LIKE=frozenset(('wall','magazine'))
USED_PATH='design-used-layouts.json'
def load_used():
    if not os.path.exists(USED_PATH): return {'entries':[]}
    try: return json.load(open(USED_PATH))
    except Exception: return {'entries':[]}
def save_used(data):
    open(USED_PATH,'w').write(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def append_used(entry):
    data=load_used(); ents=data.setdefault('entries',[])
    ents=[e for e in ents if e.get('date')!=entry.get('date')]
    ents.append(entry); ents.sort(key=lambda e:e.get('date') or '')
    data['entries']=ents; save_used(data)
def load_layout(blocks_dir, date):
    """可选：有 blocks/_layout.json 则套用多版式；没有则默认 list 壳。设计页不强制每日换 layout（2026-11-03 用户更正）。"""
    lp=os.path.join(blocks_dir,'_layout.json')
    if not os.path.exists(lp):
        return None
    try: L=json.load(open(lp))
    except Exception as e:
        ERR.append(f'{lp}: JSON 无效：{e}'); return None
    lay=L.get('layout')
    if lay not in LAYOUTS:
        ERR.append(f'{lp}: layout 若填写必须是 {list(LAYOUTS)} 之一，现在是 {lay!r}')
        return None
    dims=L.get('dims') or {}
    for k in DIM_KEYS:
        if not str(dims.get(k) or '').strip():
            WARN.append(f'{lp}: dims.{k} 空（可选版式建议补全）')
    diffs=L.get('diffs') or {}
    for k in DIFF_KEYS:
        if not str(diffs.get(k) or '').strip():
            WARN.append(f'{lp}: diffs.{k} 空（设计页非强制；叼报五维在资讯页强制）')
    return L
def _date_add(date, days):
    import datetime as _dt
    d=_dt.date.fromisoformat(date)+_dt.timedelta(days=days)
    return d.isoformat()
def b64(p): return 'data:image/webp;base64,'+base64.b64encode(open(p,'rb').read()).decode()
def part(s,tag):
    m=re.search(r'<!--%s-->(.*?)<!--/%s-->'%(tag,tag),s,re.S); return m.group(1).strip() if m else ''
def site_of(name,url):
    if 'mobbin.com' in (url or ''): return name.split(' · ')[0].strip().lower()
    p=urlparse(url or ''); h=p.netloc.lower(); h=h[4:] if h.startswith('www.') else h
    # 同站多元素（如 Lthero 专场）：用 path 首段区分，避免一期只能上 1 条
    seg=(p.path or '/').strip('/').split('/')[0]
    if h and seg: return f'{h}/{seg}'
    return h or name.split(' · ')[0].strip().lower()
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
LAYOUT=load_layout(A.blocks, date)
# 开场按日期轮换（collage/strip/fold），同一天固定
import datetime as _dt
try:
    opening=OPENINGS[_dt.date.fromisoformat(date).toordinal()%len(OPENINGS)]
except Exception:
    opening='collage'
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
def esc_txt(x):
    return (str(x) if x is not None else '').replace('<','‹').replace('>','›').replace('"','″')
def render_knobs(meta):
    knobs=meta.get('knobs') or []
    if not knobs: return ''
    bits=[]
    for k in knobs:
        var=k.get('var') or k.get('name'); 
        if not var: continue
        if not var.startswith('--'): var='--'+var
        label=esc_txt(k.get('label') or var)
        typ=k.get('type','range'); unit=k.get('unit',''); val=k.get('value',k.get('default',''))
        if typ=='range':
            bits.append(f'<label><strong>{label}</strong><input type="range" data-var="{var}" data-unit="{unit}" min="{k.get("min",0)}" max="{k.get("max",100)}" step="{k.get("step",1)}" value="{val}"><span class="kv">{val}{unit}</span></label>')
        elif typ=='color':
            bits.append(f'<label><strong>{label}</strong><input type="color" data-var="{var}" value="{val or "#888888"}"><span class="kv">{val}</span></label>')
        elif typ=='select':
            opts=''.join(f'<option value="{esc_txt(o)}"{" selected" if str(o)==str(val) else ""}>{esc_txt(o)}</option>' for o in k.get('options',[]))
            bits.append(f'<label><strong>{label}</strong><select data-var="{var}" data-unit="{unit}">{opts}</select><span class="kv">{val}{unit}</span></label>')
        else:
            bits.append(f'<label><strong>{label}</strong><input data-var="{var}" data-unit="{unit}" value="{esc_txt(val)}"><span class="kv">{val}{unit}</span></label>')
    return f'<details><summary>可调参数</summary><div class="knobs" aria-label="可调参数">{''.join(bits)}</div></details>' if bits else ''
def render_collage(path, variant='collage'):
    if not os.path.exists(path): return ''
    c=json.load(open(path))
    stance=esc_txt(c.get('stance') or '')
    why=esc_txt(c.get('why') or '')
    bg=c.get('bg') or '#0c0c0b'; fg=c.get('fg') or '#f3f1ea'
    bits=[]
    for i,b in enumerate(c.get('bits') or []):
        cls='bit'
        if b.get('kind')=='favorite' or b.get('favorite'): cls+=' fav'
        if b.get('kind')=='own' or b.get('own'): cls+=' own'
        r=b.get('rotate', ((i%5)-2)*3)
        title=esc_txt(b.get('title') or b.get('id') or '元素')
        src=esc_txt(b.get('source') or b.get('from') or '')
        note=esc_txt(b.get('note') or '')
        bits.append({'cls':cls,'r':r,'title':title,'src':src,'note':note})
    tags=''.join(f'<span>{esc_txt(t)}</span>' for t in (c.get('tags') or []))
    note=esc_txt(c.get('note') or '收藏元素虚线绿框 · 自创虚线橙框 · 不是卡片墙，是当天立场的拼贴')
    if not stance or not bits:
        return ''
    bits_html=''.join(f'<div class="{b["cls"]}" style="--r:{b["r"]}deg"><b>{b["title"]}</b><span class="src">{b["src"]}</span>{("<div>"+b["note"]+"</div>") if b["note"] else ""}</div>' for b in bits)
    tags_html=f'<div class="c-tags">{tags}</div>' if tags else ''
    if variant=='strip':
        chip_list=[]
        for b in bits:
            extra=(' fav' if ' fav' in b['cls'] else '')+(' own' if ' own' in b['cls'] else '')
            s2=f'<span class="src">{b["src"]}</span>' if b['src'] else ''
            chip_list.append(f'<span class="c-chip{extra}"><b>{b["title"]}</b>{s2}</span>')
        chips=''.join(chip_list)
        return f'''<section class="collage strip in" style="animation-delay:.18s" aria-label="今日拼接">
<div class="c-eye">今日拼接</div>
<p class="c-stance">{stance}</p>
<div class="c-strip">{chips}</div>
{tags_html}
<p class="c-why">{why}</p>
</section>'''
    if variant=='fold':
        return f'''<details class="collage fold in" style="animation-delay:.18s" aria-label="今日拼接">
<summary><span class="c-eye">今日拼接</span><span class="c-stance">{stance}</span></summary>
<div class="c-body"><p class="c-why">{why}</p>
<div class="c-stage" style="--c-bg:{bg};--c-fg:{fg}"><div class="c-bits">{bits_html}</div></div>
{tags_html}
<p class="c-note">{note}</p></div>
</details>'''
    return f'''<section class="collage in" style="animation-delay:.18s" aria-label="今日拼接">
<div class="c-eye">今日拼接</div>
<p class="c-stance">{stance}</p>
<p class="c-why">{why}</p>
<div class="c-stage" style="--c-bg:{bg};--c-fg:{fg}"><div class="c-bits">{bits_html}</div></div>
{tags_html}
<p class="c-note">{note}</p>
</section>'''
# 校验：2026-11-02 起 Web 应有 code 与（建议）knobs；缺 code 警告，缺 collage 文件警告
if date>='2026-11-02':
    for f,s,m in blocks:
        if m.get('kind')=='Web' and not part(s,'code'):
            WARN.append(f'{f}: Web 建议提供 <!--code--> 片段（可复制给 AI）；11-02 起强烈建议')
        if m.get('kind')=='Web' and not (m.get('knobs') or []):
            WARN.append(f'{f}: Web 建议写 meta.knobs（可调关键参数）')
    cp=os.path.join(A.blocks,'_collage.json')
    if not os.path.exists(cp):
        WARN.append(f'缺 {cp}：11-02 起应有「今日拼接」；今晚先出壳，明早例程必须写')
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
        howfresh=f'<details><summary>怎么操作 · 为什么新鲜</summary><dl class="hf"><dt>怎么操作</dt><dd>{meta["how"]}</dd><dt>为什么新鲜</dt><dd>{meta["fresh"]}</dd></dl></details>'
    knobs=render_knobs(meta) if kind=='Web' else ''
    code_block=''
    if code:
        rows=min(18,code.count(chr(10))+2)
        code_block=f'''<details><summary>关键代码 · 可复制给 AI</summary>
<textarea class="code" id="code-{k}" readonly spellcheck="false" rows="{rows}">{code}</textarea>
<div class="code-bar"><button type="button" class="pri" data-copy="#code-{k}">复制代码</button><button type="button" data-copy="#code-{k}" data-mode="ai">复制给 AI</button></div>
</details>'''
    nav.append(f'<a href="#b-{k}" class="chip{" app" if kind=="App" else ""}">{meta["name"].split(" · ")[0]}</a>')
    cards.append(f'''<article class="block design in" id="b-{k}" data-site="{meta["name"]}" data-url="{meta["url"]}" data-focus="{fo or ''}">
<header class="bh"><span class="kind {kind.lower()}">{kind}</span>{focus}<h2>{meta["name"]}</h2><span class="sub">{meta.get("subtitle","")}</span></header>
<div class="demo d-{k}">{part(s,"demo")}</div>
<div class="bb"><p class="why">{meta["why"]}</p><div class="tags">{tags}</div>
<div class="ref">{thumb}<div class="links"><a href="{meta["url"]}" target="_blank" rel="noopener">{meta.get("ref","原站")} ↗</a><span class="note">{meta.get("note","")}</span></div></div>
<div class="act"><span class="df-stars" aria-label="评分"></span><button class="df-fav" type="button"></button></div>
{howfresh}
<details><summary>关键参数</summary><ul class="params">{params}</ul></details>
{knobs}
{code_block}
</div></article>''')
    for r in re.findall(r'(?:data-b64|src|poster)="(?:inline:)?([^"]+)"',part(s,'demo'))+([meta['thumb']] if meta.get('thumb') else []):
        if r not in seen and os.path.exists(r): seen.add(r); total+=os.path.getsize(r)
cards=[re.sub(r'poster="inline:([^"]+)"',lambda m:'poster="'+b64(m.group(1))+'"',c) for c in cards]
shortnote=''
if NEW and len(blocks)<8:
    rs=[m.get('short_reason') for _,_,m in blocks if m.get('short_reason')]
    if os.path.exists(os.path.join(A.blocks,'_short.json')): rs.append(json.load(open(os.path.join(A.blocks,'_short.json'))).get('short_reason'))
    shortnote=f'<p class="short in">本期 {len(blocks)} 条（目标 8 条）：{rs[-1]}</p>'
collage=render_collage(os.path.join(A.blocks,'_collage.json'), opening)
lay=(LAYOUT or {}).get('layout') or 'list'
dims=(LAYOUT or {}).get('dims') or {}
diffs=(LAYOUT or {}).get('diffs') or {}
# chrome 维：deck / slim chrome → collage.slim
if lay=='deck' or str(dims.get('chrome') or '').find('slim')>=0 or str(dims.get('chrome') or '') in ('collage-slim','narrow','tool-strip'):
    collage=collage.replace('class="collage ','class="collage slim ',1) if collage else collage
# timeline: number blocks
if lay=='timeline':
    numbered=[]
    for i,c in enumerate(cards,1):
        numbered.append(c.replace('<article ','<article data-i="%02d" '%i,1))
    cards=numbered
# workbench: insert zone labels before first Web and first App
if lay=='workbench':
    out_cards=[]; seen_web=seen_app=False
    for c in cards:
        if (not seen_web) and 'class="kind web"' in c:
            out_cards.append('<div class="wb-zone" role="presentation">Web</div>'); seen_web=True
        if (not seen_app) and 'class="kind app"' in c:
            out_cards.append('<div class="wb-zone" role="presentation">App</div>'); seen_app=True
        out_cards.append(c)
    cards=out_cards
# index wall from nav/blocks meta
index_wall=''
if lay=='index':
    bits=[]
    for f,s,m in blocks:
        k=m['key']; kind=m.get('kind','Web'); name=esc_txt(m.get('name') or k)
        short=name.split(' · ')[0]
        fo=esc_txt(m.get('focus') or '')
        bits.append(f'<a href="#b-{k}" class="{"app" if kind=="App" else "web"}"><strong>{short}</strong><span>{kind} · {fo}</span></a>')
    index_wall=f'<nav class="layout-index-wall" aria-label="索引墙">{"".join(bits)}</nav>'
# deck dots
deck_dots=''
if lay=='deck':
    n=sum(1 for c in cards if '<article ' in c)
    parts=[]
    for i in range(1, n+1):
        on=' class="on"' if i==1 else ''
        parts.append(f'<button type="button" aria-label="第 {i} 条"{on}></button>')
    deck_dots='<div class="deck-dots" aria-label="幻灯页码">'+''.join(parts)+'</div>'
blocks_html=shortnote+chr(10).join(cards)
diffs_attr='|'.join(f'{k}:{esc_txt(diffs.get(k,""))}' for k in DIFF_KEYS)
t=open('template.html').read()
t=t.replace('{{DATE}}',date).replace('{{NAV}}',''.join(nav)).replace('{{BLOCKS}}',blocks_html).replace('{{COUNT}}',str(len([c for c in cards if "<article" in c]) or len(blocks))).replace('{{COLLAGE}}',collage)
t=t.replace('{{LAYOUT}}',lay).replace('{{INDEX_WALL}}',index_wall).replace('{{DECK_DOTS}}',deck_dots).replace('{{DIFFS_ATTR}}',diffs_attr).replace('{{OPENING}}',opening)
bad=re.findall(r'&(?:amp|lt|gt|quot|apos|nbsp|#\d+|#x[0-9a-f]+);',t,re.I)
assert not bad, f'HTML 实体会被连接器还原: {set(bad)}'
# layout must have been valid; if >=11-04 and ERR still pending somehow
if date>='2026-11-04' and ERR: die()
out=A.out or f'{date}.html'
open(out,'w').write(t)
mb=(total+len(t.encode()))/1e6
print(f'[build] {out} {len(t)} bytes, {len(blocks)} blocks；layout={lay}；页面+素材合计约 {mb:.1f}MB')
if LAYOUT:
    print(f'[build] dims={dims}')
    print(f'[build] diffs={diffs}')
if mb>8: WARN.append(f'单页素材约 {mb:.1f}MB > 8MB：视频压到 480px 宽/24–30fps/CRF 30 左右或截短')
for x in WARN: print('  ⚠',x)
# append used-layouts（正式 out 名像日期才记；测试 --out 带 layout-test 也记但用 date）
if LAYOUT and lay in LAYOUTS and not ERR:
    note=(LAYOUT.get('why') or LAYOUT.get('note') or '')
    # 仅当输出是正式日页或明确要求时记录；测试 html 用 --out *layout-test* 仍可记便于演练——按 date 去重
    if A.out is None or os.path.abspath(A.out)==os.path.abspath(f'{date}.html'):
        append_used({'date':date,'layout':lay,'dims':dims,'diffs':diffs,'stance':LAYOUT.get('stance') or '','note':note,'opening':opening})
        print(f'[build] 已记入 {USED_PATH}: {date} → {lay}')
    else:
        print(f'[build] 非正式输出（--out）跳过写入 {USED_PATH}')
if A.check:
    r=subprocess.run(['timeout','-k','5','120','python3','tools/check.py',out]);sys.exit(r.returncode)
