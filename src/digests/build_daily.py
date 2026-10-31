#!/usr/bin/env python3
"""每日 X 日报页构建：python3 build_daily.py 2026-10-14
主题与元素组合写在 THEMES[date]；所有视觉统一走一套 token（:root 变量）。
输出 web/<date>.html，并把组合写入 used-combos.json（同日覆盖为单条）。"""
import json,os,sys,base64,re
from io import BytesIO
from PIL import Image
os.chdir(os.path.dirname(os.path.abspath(__file__)))
DATE=sys.argv[1] if len(sys.argv)>1 else '2026-10-14'

THEMES={
 '2026-10-14':{
  'theme':'办完一件事：白纸、黑胶囊、一抹 Cash 绿对勾，读完就勾选。',
  'elements':['cashapp-check-pop','cashapp-done-pill','ollama-pill-cta','ollama-proof-stats','dub-fan-out','dub-logo-flip','clerk-letter-reveal','things-soft-shadow','mintlify-digit-in','gpt888-ease','digvps-blur-enter','chatlab-scroll-reveal','chatlab-pills'],
  'notes':'chatlab-pills 改色为中性浅底 + 选中黑底绿点；things-soft-shadow 只取三层柔影；唯一强调色 #00D632。',
 }
}

# ===== 2026-10-25 起的去重/换骨架规则（DAILY.md「防撞车硬规则」）=====
EASING={'gpt888-ease'}  # 缓动类元素不受「前一期禁用 / 3 天 1 次」限制
SKEL_KEYS=('topbar','card','nav')
def _hue(hexs):
    import colorsys
    h=hexs.lstrip('#'); r,g,b_=(int(h[i:i+2],16)/255 for i in (0,2,4))
    hh,l,s=colorsys.rgb_to_hls(r,g,b_); return hh*360,s,l
def validate(date,cfg,uc):
    errs=[];prev=sorted([x for x in uc if x['date']<date],key=lambda x:x['date'])
    el=set(cfg['elements'])-EASING
    v2=date>=V2_FROM
    if v2: errs+=validate_v2(date,cfg,uc)
    if v2:
        if not cfg.get('bg'): errs.append('cfg 必须有 bg（主底色 hex）')
    elif date>='2026-10-26':
        sk=cfg.get('skeleton') or {}
        if not cfg.get('bg') or any(k not in sk for k in SKEL_KEYS): errs.append(f'cfg 必须有 bg 和 skeleton{{{",".join(SKEL_KEYS)}}}')
    if prev:
        p=prev[-1];pe=set(p['elements'])
        hit=el&pe
        if hit: errs.append(f'前一期({p["date"]})元素当天禁用（缓动除外）：{sorted(hit)}')
        j=len(set(cfg['elements'])&pe)/max(1,len(set(cfg['elements'])|pe))
        if j>0.2: errs.append(f'与 {p["date"]} 的 Jaccard={j:.2f} > 0.2')
        sk,psk=cfg.get('skeleton'),p.get('skeleton')
        if v2: pass
        elif sk and psk:
            ch=[k for k in SKEL_KEYS if sk.get(k)!=psk.get(k)]
            if len(ch)<2: errs.append(f'骨架只换了 {ch}，顶栏/说明卡形式/导航至少换 2 项')
        elif sk: print('[warn] 前一期没有 skeleton 字段，跳过骨架对比')
        if cfg.get('bg') and p.get('bg'):
            h1,s1,_=_hue(cfg['bg']);h2,s2,_=_hue(p['bg'])
            n1,n2=s1<0.08,s2<0.08
            d=min(abs(h1-h2),360-abs(h1-h2))
            if (n1 and n2) or (not n1 and not n2 and d<30): errs.append(f'背景色相没换：{cfg["bg"]} vs {p["bg"]}（色相差 {d:.0f}°，需 ≥30° 或一中性一有色）')
    from datetime import date as _d,timedelta
    D0=_d.fromisoformat(date);win={str(D0-timedelta(days=k)) for k in (1,2)}
    for x in uc:
        if x['date'] in win:
            rep=el&set(x['elements'])
            if rep: errs.append(f'3 天内同一元素最多 1 次：{sorted(rep)} 已在 {x["date"]} 用过')
    tok={t['id']:t for t in json.load(open('design-tokens.json'))['tokens']}
    bad=[i for i in cfg['elements'] if tok.get(i,{}).get('status')=='avoid' or (tok.get(i,{}).get('rating') or 5)<=2]
    if bad: errs.append(f'回避元素不得使用：{bad}')
    if errs:
        print('[build_daily] 规则校验失败，未写文件：');[print('  -',e) for e in dict.fromkeys(errs)];sys.exit(2)
    print('[build_daily] 规则校验通过')

# ===== 2026-11-01 起：版式原型 + 骨架 6 维 + 元素下限（DAILY.md「版式原型与防撞车硬规则 v2」）=====
V2_FROM='2026-11-01'
ARCHETYPES=['空间/地图型','时间/时刻表型','实物桌面/拼贴型','单列长卷型','索引/墙型','一次一条型','对话/终端/命令型','分栏对照/仪表盘型']
DIM_KEYS=('carrier','nav','axis','entrance','bg_hue','fonts')  # 信息载体/导航方式/浏览轴/进场方式/底色色相/字体组合
AXES={'纵','横','平面','翻页'}
def _arch(a):
    a=str(a or '').strip()
    if not a: return ''
    m=re.match(r'^\s*(\d+)\s*',a)
    if m and 1<=int(m.group(1))<=len(ARCHETYPES): return ARCHETYPES[int(m.group(1))-1]
    for x in ARCHETYPES:
        if x in a or a in x: return x
    return a
def validate_v2(date,cfg,uc):
    from datetime import date as _d,timedelta
    errs=[];D0=_d.fromisoformat(date)
    HOW='（在 pages/DATE.py 的 cfg 里补，格式见 web/DAILY.md「版式原型与防撞车硬规则 v2」）'
    if not str(cfg.get('stance','')).strip(): errs.append('cfg.stance 设计立场为空：写一句「场景/隐喻 + 为什么这样组织 + 舍弃了什么」'+HOW)
    a=_arch(cfg.get('archetype'))
    if not a: errs.append('cfg.archetype 缺失：从原型池 1–8 选一个，或写新原型名并加 cfg.archetype_why'+HOW)
    elif a not in ARCHETYPES and not str(cfg.get('archetype_why','')).strip(): errs.append(f'新原型「{a}」需写 cfg.archetype_why：一句话说明浏览方式为何与池内 8 种都不同')
    if 'vertical_list' not in cfg: errs.append('cfg.vertical_list 缺失：本页是否「纵向滚动卡片列表」骨架（true/false）')
    dims=cfg.get('dims') or {}
    miss=[k for k in DIM_KEYS if not str(dims.get(k,'')).strip()]
    if miss: errs.append(f'cfg.dims 缺 {miss}；六维 = carrier 信息载体 / nav 导航方式 / axis 浏览轴(纵|横|平面|翻页) / entrance 进场方式 / bg_hue 底色色相 / fonts 字体组合'+HOW)
    elif dims['axis'] not in AXES: errs.append(f'dims.axis 只能是 {sorted(AXES)}，当前 {dims["axis"]!r}')
    prev=sorted([x for x in uc if x['date']<date],key=lambda x:x['date'])
    win7={str(D0-timedelta(days=k)) for k in range(1,8)}
    for x in prev:
        if x['date'] in win7 and a and _arch(x.get('archetype'))==a: errs.append(f'近 7 天原型不重复：「{a}」已在 {x["date"]} 用过')
    for x in prev:
        if a and _arch(x.get('archetype'))==a and x.get('score') is not None and x['score']<=2 and (D0-_d.fromisoformat(x['date'])).days<=30:
            errs.append(f'低分原型 30 天内不用：「{a}」{x["date"]} score={x["score"]}')
    y=[x for x in prev if x['date']==str(D0-timedelta(days=1))]
    if cfg.get('vertical_list') and y and y[0].get('vertical_list'): errs.append(f'「纵向滚动卡片列表」连续最多 1 天：{y[0]["date"]} 已是纵向卡片列表')
    if not miss:
        for x in prev[-3:]:
            pd=x.get('dims')
            if not pd: print(f'[warn] {x["date"]} 没有 dims，跳过六维对比'); continue
            diff=[k for k in DIM_KEYS if str(dims[k]).strip()!=str(pd.get(k,'')).strip()]
            if len(diff)<4: errs.append(f'与 {x["date"]} 骨架六维只差 {len(diff)} 维 {diff}，需 ≥4 维不同（相同：{[k for k in DIM_KEYS if k not in diff]}）')
    tok={t['id']:t for t in json.load(open('design-tokens.json'))['tokens']}
    fav=[i for i in dict.fromkeys(cfg['elements']) if i not in EASING]
    unk=[i for i in fav if i not in tok]
    if unk: errs.append(f'cfg.elements 里有 design-tokens.json 不存在的 id：{unk}（自创处理请写进 cfg.own）')
    own=cfg.get('own') or []
    if any(not (isinstance(o,dict) and o.get('name')) for o in own): errs.append('cfg.own 每项写成 {"name":..,"desc":..}')
    nf=len([i for i in fav if i in tok]); srcs={tok[i]['source'] for i in fav if i in tok}
    if nf+len(own)<8: errs.append(f'交互/视觉细节元素共 {nf+len(own)} 个（收藏 {nf} + 自创 {len(own)}），需 ≥8（缓动不计）')
    if nf<5: errs.append(f'收藏库元素 {nf} 个，需 ≥5')
    if len(own)>2: errs.append(f'自创处理 {len(own)} 个，最多 2 个计入')
    if len(srcs)<4: errs.append(f'收藏元素来源站点 {len(srcs)} 个 {sorted(srcs)}，需 ≥4')
    return errs
from news_signal import sig_attrs,embed_signal,check_signal,load_day_items,normalize_sig_id  # 页面模板写 {sig_attrs(it)}；分组用 load_day_items
if os.path.exists(f'pages/{DATE}.py'):  # 页面模板按日独立：pages/YYYY-MM-DD.py 产出 RESULT{html,cfg,used}
    exec(open(f'pages/{DATE}.py').read()); html=RESULT['html']; cfg=RESULT['cfg']; used=RESULT['used']
    html=embed_signal(html,DATE)
    _day=load_day_items(DATE); print(_day['log'])
    _n=len(_day['all']) or None
    _se=check_signal(html,_n)
    if _se and DATE>='2026-10-26' and '--no-check' not in sys.argv: print('[build_daily] news-signal 校验失败：',_se);sys.exit(2)
    elif _se: print('[warn] news-signal：',_se)
    from news_signal import check_zh_summaries
    _ze=check_zh_summaries(_day)
    if _ze and DATE>='2026-10-27' and '--no-check' not in sys.argv: print('[build_daily] 中文简介校验失败（需要中文简介）：',_ze);sys.exit(2)
    p='used-combos.json'
    try: uc=json.load(open(p))
    except Exception: uc=[]
    if '--no-check' not in sys.argv: validate(DATE,cfg,uc)
    open(f'web/{DATE}.html','w').write(html)
    uc=[x for x in uc if x.get('date')!=DATE]
    rec={'date':DATE,'theme':cfg['theme'],'elements':cfg['elements'],'sources':sorted({t['source'] for t in used}),'non_core_share':round(sum(1 for t in used if t['source'] not in ('gpt888.vip','ChatLab','DigVPS'))/len(used),2)}
    if cfg.get('form'): rec['form']=cfg['form']
    if DATE>=V2_FROM:
        rec.update(archetype=_arch(cfg.get('archetype')),dims=cfg.get('dims'),vertical_list=bool(cfg.get('vertical_list')),stance=cfg.get('stance'),own=cfg.get('own') or [],score=None)
        if cfg.get('archetype_why'): rec['archetype_why']=cfg['archetype_why']
    for k in ('skeleton','bg'):
        if cfg.get(k): rec[k]=cfg[k]
    if cfg.get('notes'): rec['notes']=cfg['notes']
    uc.append(rec); json.dump(sorted(uc,key=lambda x:x['date']),open(p,'w'),ensure_ascii=False,indent=2)
    print('wrote',f'web/{DATE}.html',len(html),'non-core share',rec['non_core_share']); sys.exit(0)
cfg=THEMES[DATE]
tok={t['id']:t for t in json.load(open('design-tokens.json'))['tokens']}
used=[tok[i] for i in cfg['elements']]
banned=[t['id'] for t in used if t.get('status')=='avoid' or (t.get('rating') or 5)<=2]
assert not banned,('回避元素不得使用',banned)
items=json.load(open(f'items-{DATE}.json'))

def emb(p,w,q=56):
    if not p or not os.path.exists(p): return None
    im=Image.open(p).convert('RGB'); im.thumbnail((w,w)); b=BytesIO(); im.save(b,'WEBP',quality=q)
    return 'data:image/webp;base64,'+base64.b64encode(b.getvalue()).decode()
CAT={'教程':'学习札记','工具':'工具箱','行业':'行业观察','观点':'评论','实测':'实验室','研究':'前沿研究','AIGC':'AIGC','变现':'落地变现'}
its=[]
for i,it in enumerate(items['items']):
    its.append(dict(i=i,cat=CAT.get(it['cat'],it['cat']),title=it['title'],handle=it['handle'],likes=it['likes'],rts=it['rts'],
      summary=it.get('summary',''),quote=it.get('quote',''),url=f"https://x.com/{it['handle']}/status/{it['id']}",
      media=emb(it.get('media'),640),avatar=emb(it.get('avatar'),88,60),eng=it['likes']+2*it['rts']))
mx=max(x['eng'] for x in its)
for x in its: x['heat']=round(x['eng']/mx*100)
top=sorted([x for x in its if x['media']],key=lambda x:-x['eng'])[:3]
cats=[]
for x in its:
    if x['cat'] not in cats: cats.append(x['cat'])
E=lambda s:''.join('&#%d;'%ord(c) if c in '&<>"\'' else c for c in str(s))
TL=sum(x['likes'] for x in its); TR=sum(x['rts'] for x in its)

credit=''.join(f'<li><code>{E(t["id"])}</code> · {E(t["title"])} — {E(t["source"])}{"（收藏）" if t.get("favorite") else "（推荐）"}</li>' for t in used)
H1=f'今天读完这 {len(its)} 条'
title_chars=''.join((f'<span class="ch" style="--k:{k}">{E(c)}</span>' if c!=" " else '<span class="sp"></span>') for k,c in enumerate(H1))
def digits(n,delay):
    s=str(n); return ''.join(f'<span class="digit"><i style="animation-delay:{delay+k*0.05:.2f}s">{c}</i></span>' for k,c in enumerate(s))
CHK='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>'
fan=''.join(f'<a class="fan-card soft" href="{x["url"]}" target="_blank" rel="noopener" style="--fan-x:{dx}px;--fan-y:{dy}px;--fan-rotate:{r}deg;--z:{z}"><img src="{x["media"]}" alt=""><span>{E(x["title"])}</span></a>'
  for x,(dx,dy,r,z) in zip(top,[(-78,14,-9,1),(0,-6,0,3),(78,14,9,2)]))
chips='<button class="on" data-c="*" type="button" role="tab" aria-selected="true"><s></s>全部 <em>%d</em></button>'%len(its)+''.join(f'<button data-c="{E(c)}" type="button" role="tab" aria-selected="false"><s></s>{E(c)} <em>{sum(1 for x in its if x["cat"]==c)}</em></button>' for c in cats)
cards=''.join(f'''<article class="item soft reveal" data-c="{E(x["cat"])}" data-i="{x["i"]}" style="--d:{(k%4)*70}ms">
 <button class="tick" type="button" aria-label="标记已读" aria-pressed="false">{CHK}</button>
 <div class="body"><div class="meta">{f'<img class="av" src="{x["avatar"]}" alt="">' if x["avatar"] else '<span class="av"></span>'}<b>@{E(x["handle"])}</b><span class="cat">{E(x["cat"])}</span></div>
 <h3>{E(x["title"])}</h3><p>{E(x["summary"])}</p>
 {f'<div class="pic"><img src="{x["media"]}" alt="" loading="lazy"></div>' if x["media"] else ''}
 <div class="foot"><span class="heat" title="热度 {x["heat"]}"><i style="--h:{x["heat"]}%"></i></span><span>♥ {x["likes"]} · ↻ {x["rts"]}</span><a class="go" href="{x["url"]}" target="_blank" rel="noopener">原帖 ↗</a></div></div>
</article>''' for k,x in enumerate(its))

html=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>X 每日 AI 推荐 · {DATE}</title><style>
/* ===== 统一 token：纸白 + 墨黑 + 唯一强调 Cash 绿 / 14px 卡片 + 999px 胶囊 / 一条主缓动 ===== */
:root{{
 --paper:#ffffff;--wash:#f4f4f4;--ink:#242424;--fill:#171717;--muted:#898989;--line:#ececec;
 --accent:#00D632;            /* cashapp-check-pop：全页唯一强调色 */
 --soft:0 2px 4px rgba(0,0,0,.05),0 4px 16px rgba(0,0,0,.05),0 8px 32px rgba(0,0,0,.05); /* things-soft-shadow 三层柔影 */
 --r:14px;--r-s:10px;--r-pill:999px;
 --ease:cubic-bezier(.22,1,.36,1); /* gpt888-ease，全页唯一主缓动 */
 --fs-xs:12px;--fs-s:14px;--fs-m:16px;--fs-l:19px;--fs-xl:clamp(34px,9.4vw,58px);
 --font:-apple-system,BlinkMacSystemFont,"Inter","PingFang SC","Noto Sans SC",system-ui,sans-serif;
 color-scheme:light}}
*{{box-sizing:border-box;margin:0}}html{{-webkit-text-size-adjust:100%;scroll-behavior:smooth}}
body{{font-family:var(--font);background:var(--paper);color:var(--ink);font-size:var(--fs-m);line-height:1.55;overflow-x:hidden;-webkit-tap-highlight-color:transparent}}
a{{color:inherit;text-decoration:none}}button{{font:inherit;color:inherit}}
.wrap{{max-width:720px;margin:0 auto;padding:0 18px}}
.soft{{background:var(--paper);border-radius:var(--r);box-shadow:var(--soft)}}
/* 绿对勾（cashapp-check-pop） */
.chk{{display:grid;place-items:center;border-radius:50%;background:var(--accent);flex:none}}
.chk svg,.tick svg{{fill:none;stroke:#fff;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}}
@keyframes pop{{0%{{transform:scale(0)}}70%{{transform:scale(1.08)}}to{{transform:scale(1)}}}}
/* 顶栏 + 滚动进度 + 当前第 n/N（联动） */
.bar{{position:sticky;top:0;z-index:40;background:color-mix(in oklch,var(--paper) 88%,transparent);-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);border-bottom:1px solid transparent;transition:border-color .3s var(--ease)}}
.bar.scrolled{{border-color:var(--line)}}
.bar .in{{display:flex;align-items:center;justify-content:space-between;height:52px;font-size:var(--fs-s)}}
.logo{{display:flex;align-items:center;gap:8px;font-weight:600;cursor:pointer;user-select:none;min-height:44px}}
.logo i{{width:20px;height:20px;border-radius:50%;background:var(--fill);display:grid;place-items:center;transition:transform .5s var(--ease)}}
.logo i:after{{content:"";width:7px;height:7px;border-radius:50%;background:var(--accent)}}
.logo:active i{{transform:scale(.86)}}
.pos{{color:var(--muted);font-variant-numeric:tabular-nums;display:flex;align-items:center;gap:8px}}
.pos .ring{{width:18px;height:18px;transform:rotate(-90deg)}}.pos .ring circle{{fill:none;stroke-width:3}}
.pos .ring .bg{{stroke:var(--wash)}}.pos .ring .fg{{stroke:var(--accent);stroke-dasharray:44;stroke-dashoffset:calc(44 - 44 * var(--p,0));transition:stroke-dashoffset .2s linear}}
.prog{{height:2px;background:var(--accent);transform-origin:0 50%;transform:scaleX(var(--p,0))}}
/* 首屏分层进场：clerk-letter-reveal + digvps-blur-enter（错峰） */
.hero{{padding:34px 0 8px;text-align:center}}
.stamp{{width:52px;height:52px;margin:0 auto 14px;cursor:pointer;animation:pop .5s var(--ease) .1s both}}
.stamp svg{{width:28px;height:28px;stroke-dasharray:24;stroke-dashoffset:24;animation:draw .35s var(--ease) .45s forwards}}
.stamp.again{{animation:pop .5s var(--ease) both}}.stamp.again svg{{animation:draw .35s var(--ease) .2s both}}
.stamp:active{{transform:scale(.92)}}
@keyframes draw{{from{{stroke-dashoffset:24}}to{{stroke-dashoffset:0}}}}
.kicker{{font-size:var(--fs-xs);letter-spacing:.14em;color:var(--muted);text-transform:uppercase}}
h1{{font-size:var(--fs-xl);font-weight:650;letter-spacing:-.04em;line-height:1.08;margin:10px 0 12px}}
.sp{{display:inline-block;width:.22em}}.ch{{display:inline-block;animation:letter-reveal .3s ease-out both;animation-delay:calc(.25s + var(--k) * 45ms)}}
@keyframes letter-reveal{{0%{{opacity:0;filter:blur(2px)}}to{{opacity:1;filter:blur(0)}}}}
.lead{{color:var(--muted);font-size:var(--fs-m);max-width:30em;margin:0 auto}}
.up{{animation:blur-up .6s var(--ease) both;animation-delay:var(--d,0s)}}
@keyframes blur-up{{from{{opacity:0;transform:translateY(20px);filter:blur(10px)}}to{{opacity:1;transform:none;filter:blur(0)}}}}
/* ollama-pill-cta / cashapp-done-pill：同一颗黑胶囊 */
.pill{{display:inline-flex;align-items:center;justify-content:center;gap:6px;border:0;border-radius:var(--r-pill);background:var(--fill);color:#fff;padding:.6rem 1.5rem;font-size:var(--fs-m);font-weight:600;min-height:48px;cursor:pointer;transition:transform .2s var(--ease),background .2s}}
.pill:active{{transform:scale(.97)}}@media (hover:hover){{.pill:hover{{background:#000}}}}
.cta{{margin-top:18px}}
/* ollama-proof-stats + mintlify-digit-in */
.proof{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:26px auto 0;max-width:460px;cursor:pointer;border-radius:var(--r);padding:6px 0;transition:background .2s}}
.proof:active{{background:var(--wash)}}
.proof b{{display:block;font-size:26px;font-weight:550;letter-spacing:-.02em;font-variant-numeric:tabular-nums;line-height:1.2}}
.proof div>span{{font-size:var(--fs-xs);color:var(--muted)}}
.digit{{display:inline-block;overflow:hidden;vertical-align:bottom}}
.digit>i{{display:inline-block;font-style:normal;animation:digit-in .5s var(--ease) both}}
@keyframes digit-in{{0%{{opacity:0;transform:translateY(100%)}}to{{opacity:1;transform:translateY(0)}}}}
/* dub-fan-out 扇形卡 + 视差（联动） */
.fan{{position:relative;height:230px;margin:30px auto 6px;max-width:420px;display:grid;place-items:center;transform:translateY(var(--par,0px))}}
.fan-card{{grid-area:1/1;width:160px;height:190px;overflow:hidden;display:flex;flex-direction:column;z-index:var(--z);transform:translate(var(--fan-x),var(--fan-y)) rotate(var(--fan-rotate));transition:transform .5s var(--ease)}}
.fan.go .fan-card{{animation:fan-out 1s cubic-bezier(.16,1,.3,1) .7s backwards}}
@keyframes fan-out{{0%{{opacity:0;transform:translate(0) rotate(0deg) scale(.94)}}25%{{opacity:1}}to{{transform:translate(var(--fan-x,0),var(--fan-y,0)) rotate(var(--fan-rotate,0deg))}}}}
.fan-card img{{width:100%;height:120px;object-fit:cover;display:block}}
.fan-card span{{font-size:var(--fs-xs);font-weight:600;padding:8px 10px;line-height:1.35}}
.fan-card:active{{transform:translate(var(--fan-x),calc(var(--fan-y) - 8px)) rotate(var(--fan-rotate)) scale(1.03)}}
@media (hover:hover){{.fan-card:hover{{transform:translate(var(--fan-x),calc(var(--fan-y) - 8px)) rotate(var(--fan-rotate)) scale(1.03)}}}}
.fan.spin .fan-card{{animation:fan-out .9s cubic-bezier(.16,1,.3,1) backwards}}
.fan-hint{{text-align:center;font-size:var(--fs-xs);color:var(--muted)}}
/* 筛选条：chatlab-pills 改色 → 中性浅底，选中黑底 + 绿点（联动列表 + dub-logo-flip 标题） */
.filters{{position:sticky;top:52px;z-index:30;background:color-mix(in oklch,var(--paper) 88%,transparent);-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);padding:10px 0;margin:22px -18px 0}}
.chips{{display:flex;gap:6px;overflow-x:auto;padding:0 18px;scrollbar-width:none}}.chips::-webkit-scrollbar{{display:none}}
.chips button{{flex:none;display:inline-flex;align-items:center;gap:6px;border:0;background:var(--wash);border-radius:var(--r-pill);padding:7px 14px;font-size:var(--fs-s);min-height:38px;cursor:pointer;transition:background .3s var(--ease),color .3s,transform .2s var(--ease)}}
.chips button:active{{transform:scale(.95)}}
.chips button s{{width:0;height:7px;border-radius:50%;background:var(--accent);transition:width .3s var(--ease),margin .3s var(--ease);margin-right:-6px}}
.chips button em{{font-style:normal;color:var(--muted);font-size:var(--fs-xs)}}
.chips button.on{{background:var(--fill);color:#fff}}.chips button.on s{{width:7px;margin-right:0}}.chips button.on em{{color:#ffffffa8}}
.sechead{{display:flex;align-items:baseline;justify-content:space-between;margin:14px 0 12px;scroll-margin-top:120px}}
.flip{{display:grid}}.flip>span{{grid-area:1/1;font-size:var(--fs-l);font-weight:600}}
.flip .in{{animation:logo-flip-in .28s ease-out both}}.flip .out{{animation:logo-flip-out .18s ease-out both}}
@keyframes logo-flip-in{{0%{{filter:blur(2px);opacity:0;transform:scale(.96)}}to{{filter:blur(0);opacity:1;transform:scale(1)}}}}
@keyframes logo-flip-out{{0%{{filter:blur(0);opacity:1;transform:scale(1)}}to{{filter:blur(2px);opacity:0;transform:scale(.96)}}}}
.readc{{font-size:var(--fs-s);color:var(--muted);font-variant-numeric:tabular-nums}}
/* 卡片 + 滚动出现（chatlab-scroll-reveal） */
.list{{display:grid;gap:14px;padding-bottom:12px}}
.item{{display:flex;gap:12px;padding:16px;transition:opacity .35s var(--ease),transform .35s var(--ease),box-shadow .3s var(--ease)}}
.item.hide{{display:none}}
.reveal{{opacity:0;transform:translateY(24px)}}
.reveal.seen{{opacity:1;transform:none;transition:opacity .6s var(--ease) var(--d),transform .6s var(--ease) var(--d),box-shadow .3s var(--ease)}}
.item:active{{transform:scale(.99)}}
.item.cur{{box-shadow:var(--soft),0 0 0 1.5px var(--fill)}}
.tick{{flex:none;width:30px;height:30px;margin-top:1px;border-radius:50%;border:2px solid #d4d4d4;background:var(--paper);display:grid;place-items:center;cursor:pointer;transition:background .25s var(--ease),border-color .25s,transform .25s var(--ease)}}
.tick svg{{width:18px;height:18px;stroke-dasharray:24;stroke-dashoffset:24;transition:stroke-dashoffset .35s var(--ease) .05s}}
.tick:active{{transform:scale(.88)}}
.item.done .tick{{background:var(--accent);border-color:var(--accent);animation:pop .5s var(--ease)}}.item.done .tick svg{{stroke-dashoffset:0}}
.item.done h3{{color:var(--muted)}}
.body{{flex:1;min-width:0}}
.meta{{display:flex;align-items:center;gap:8px;font-size:var(--fs-xs);color:var(--muted)}}
.meta b{{color:var(--ink);font-weight:600;font-size:var(--fs-s)}}
.av{{width:26px;height:26px;border-radius:50%;object-fit:cover;background:var(--wash);flex:none;cursor:pointer;transition:transform .4s cubic-bezier(.34,1.56,.64,1)}}
.av.boing{{transform:scale(1.25) rotate(-8deg)}}
.cat{{margin-left:auto;padding:2px 9px;border-radius:var(--r-pill);background:var(--wash)}}
.item h3{{font-size:var(--fs-l);font-weight:600;letter-spacing:-.015em;line-height:1.3;margin:8px 0 4px;transition:color .3s}}
.item p{{font-size:var(--fs-s);color:#555}}
.pic{{margin-top:10px;border-radius:var(--r-s);overflow:hidden;aspect-ratio:16/9;background:var(--wash)}}
.pic img{{width:100%;height:100%;object-fit:cover;display:block}}
.foot{{display:flex;align-items:center;gap:10px;margin-top:10px;font-size:var(--fs-xs);color:var(--muted)}}
.heat{{width:56px;height:4px;border-radius:4px;background:var(--wash);overflow:hidden}}.heat i{{display:block;height:100%;width:var(--h);background:var(--ink);border-radius:4px;transform-origin:0 50%;transform:scaleX(0);transition:transform .8s var(--ease) .2s}}
.seen .heat i{{transform:scaleX(1)}}
.go{{margin-left:auto;color:var(--ink);font-weight:600;padding:6px 0}}
/* 彩蛋：toast + 全读完成功页（Cash App 结构：绿对勾 + 标题 + 黑胶囊 Done） */
.toast{{position:fixed;left:50%;bottom:24px;z-index:60;transform:translate(-50%,calc(100% + 40px));display:flex;align-items:center;gap:10px;padding:12px 18px;border-radius:var(--r-pill);background:var(--fill);color:#fff;font-size:var(--fs-s);box-shadow:0 10px 30px -10px rgba(0,0,0,.4);transition:transform .5s var(--ease);white-space:nowrap}}
.toast.show{{transform:translate(-50%,0)}}
.toast .chk{{width:22px;height:22px}}.toast .chk svg{{width:14px;height:14px}}
.dot-burst{{position:fixed;width:8px;height:8px;border-radius:50%;pointer-events:none;z-index:70;animation:burst .7s var(--ease) forwards}}
@keyframes burst{{to{{transform:translate(var(--bx),var(--by)) scale(.2);opacity:0}}}}
.done-page{{position:fixed;inset:0;z-index:80;background:var(--paper);display:flex;flex-direction:column;padding:16px 22px calc(24px + env(safe-area-inset-bottom));opacity:0;visibility:hidden;transform:scale(.98);transition:opacity .35s var(--ease),transform .45s var(--ease),visibility 0s .45s}}
.done-page.show{{opacity:1;visibility:visible;transform:none;transition:opacity .35s var(--ease),transform .45s var(--ease)}}
.done-page .x{{width:40px;height:40px;border:0;border-radius:50%;background:var(--wash);font-size:20px;cursor:pointer}}
.done-page .x:active{{transform:scale(.92)}}
.done-page .bd{{flex:1;max-width:460px;width:100%;margin:0 auto;padding-top:min(18vh,140px)}}
.done-page .chk{{width:64px;height:64px;transform:scale(0)}}.done-page .chk svg{{width:34px;height:34px}}
.done-page.show .chk{{animation:pop .5s var(--ease) .12s both}}
.done-page h2{{font-size:28px;font-weight:700;letter-spacing:-.03em;line-height:1.2;margin:18px 0 8px}}
.done-page p{{color:var(--muted)}}
.done-page .pill{{width:100%;max-width:460px;margin:0 auto;font-size:17px}}
footer{{margin:36px 0 40px;padding-top:18px;border-top:1px solid var(--line);font-size:var(--fs-xs);color:var(--muted)}}
footer b{{color:var(--ink)}}footer ul{{padding-left:18px;margin:6px 0 10px;display:grid;gap:3px}}footer code{{color:var(--ink)}}
.egg{{margin-top:8px}}
button:focus-visible,a:focus-visible{{outline:2px solid var(--fill);outline-offset:2px}}
@media (min-width:900px){{.wrap{{max-width:760px}}.fan{{height:260px}}.fan-card{{width:190px;height:220px}}.fan-card img{{height:145px}}}}
@media (prefers-reduced-motion:reduce){{*,*:before,*:after{{animation:none!important;transition:none!important}}.reveal{{opacity:1;transform:none}}.fan{{transform:none!important}}.heat i{{transform:none}}.stamp svg{{stroke-dashoffset:0}}.done-page .chk{{transform:none}}}}
</style></head><body>
<div class="bar" id="bar"><div class="wrap in"><span class="logo" id="logo" role="button" tabindex="0"><i></i>X 日报</span><span class="pos"><span id="pos">{E(items.get("issue",""))}</span><svg class="ring" viewBox="0 0 18 18" aria-hidden="true"><circle class="bg" cx="9" cy="9" r="7"/><circle class="fg" id="ring" cx="9" cy="9" r="7"/></svg></span></div><div class="prog" id="prog"></div></div>
<div class="wrap">
<section class="hero">
 <div class="chk stamp" id="stamp" role="button" tabindex="0" aria-label="绿对勾">{CHK}</div>
 <div class="kicker up" style="--d:.15s">{DATE} · {E(items.get("issue",""))}</div>
 <h1 aria-label="{E(H1)}">{title_chars}</h1>
 <p class="lead up" style="--d:.65s">从 X 公开帖子挑出 {len(its)} 条。读完一条，点左边的圆圈打个绿勾；全部勾完，有个小仪式。</p>
 <a class="pill cta up" style="--d:.8s" href="#list">开始阅读 <span aria-hidden="true">↓</span></a>
 <div class="proof up" style="--d:.9s" id="proof" title="点一下重滚数字">
  <div><b>{digits(len(its),1.0)}</b><span>条推荐</span></div>
  <div><b>{digits(TL,1.1)}</b><span>总点赞</span></div>
  <div><b>{digits(TR,1.2)}</b><span>总转发</span></div>
 </div>
 <div class="fan go" id="fan">{fan}</div>
 <p class="fan-hint up" style="--d:1.5s">热度前三 · 双击卡片重新展开</p>
</section>
<div class="filters" id="filters"><div class="chips" id="chips" role="tablist">{chips}</div></div>
<div class="sechead" id="list"><div class="flip" id="flip"><span>全部</span></div><span class="readc" id="readc">已读 0 / {len(its)}</span></div>
<section class="list">{cards}</section>
<footer>
 <p><b>今日主题</b>：{E(cfg["theme"])}</p>
 <p style="margin-top:10px"><b>灵感来源</b>（统一成一套 token：纸白 #fff / 洗灰 #f4f4f4 / 墨 #171717 · 唯一强调 Cash 绿 #00D632 · 卡片 14px / 胶囊 999px · cubic-bezier(.22,1,.36,1)）</p><ul>{credit}</ul>
 <p>改色说明：{E(cfg.get("notes",""))}</p>
 <p class="egg"><b>彩蛋</b>：全部勾完会弹出成功页 · 点三个数字会重滚 · 双击扇形卡重新展开 · 点顶部绿勾会再弹一次 · 点头像会弹一下 · 连点左上角 logo 五次</p>
 <p style="margin-top:8px">互动量 = 点赞 + 2×转发 · 数据 items-{DATE}.json</p>
</footer>
</div>
<div class="toast" id="toast" role="status"><span class="chk">{CHK}</span><span id="toastt">今天读完了</span></div>
<div class="done-page" id="donep" role="dialog" aria-modal="true" aria-hidden="true" aria-labelledby="doneh">
 <div><button class="x" id="donex" type="button" aria-label="关闭">×</button></div>
 <div class="bd"><div class="chk">{CHK}</div><h2 id="doneh">今天 {len(its)} 条，全部读完</h2><p>这件事办完了。明天 12:30 见。</p></div>
 <button class="pill" id="doneb" type="button">Done</button>
</div>
<script>
(()=>{{
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches,N={len(its)},KEY='xdaily-read-{DATE}';
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const bar=$('#bar'),prog=$('#prog'),ring=$('#ring'),pos=$('#pos'),fan=$('#fan'),items=$$('.item');
// 滚动进度 + 视差 + 当前条（联动）
let ticking=false;function onScroll(){{if(ticking)return;ticking=true;requestAnimationFrame(()=>{{
 const h=document.documentElement,p=(h.scrollTop/(h.scrollHeight-h.clientHeight||1)).toFixed(4);prog.style.setProperty('--p',p);ring.style.setProperty('--p',p);bar.classList.toggle('scrolled',h.scrollTop>8);
 if(!RM)fan.style.setProperty('--par',Math.min(60,h.scrollTop*.18)+'px');ticking=false}})}}
addEventListener('scroll',onScroll,{{passive:true}});onScroll();
const vis=()=>items.filter(x=>!x.classList.contains('hide'));
const spy=new IntersectionObserver(es=>{{es.forEach(e=>{{if(e.isIntersecting){{items.forEach(x=>x.classList.remove('cur'));e.target.classList.add('cur');const v=vis();pos.textContent=`第 ${{v.indexOf(e.target)+1}} / ${{v.length}} 条`}}}})}},{{rootMargin:'-45% 0px -50% 0px'}});
items.forEach(x=>spy.observe(x));
// 滚动出现
const rv=new IntersectionObserver(es=>es.forEach(e=>{{if(e.isIntersecting){{e.target.classList.add('seen');rv.unobserve(e.target)}}}}),{{threshold:.15}});
$$('.reveal').forEach(x=>rv.observe(x));
// 已读勾选（联动计数）+ 全读完成功页
let read=new Set();try{{read=new Set(JSON.parse(localStorage.getItem(KEY))||[])}}catch(e){{}}
const readc=$('#readc');function sync(){{items.forEach(x=>{{const d=read.has(x.dataset.i);x.classList.toggle('done',d);x.querySelector('.tick').setAttribute('aria-pressed',d)}});readc.textContent=`已读 ${{read.size}} / ${{N}}`;try{{localStorage.setItem(KEY,JSON.stringify([...read]))}}catch(e){{}}}}
function toast(t){{$('#toastt').textContent=t;const el=$('#toast');el.classList.add('show');clearTimeout(el._t);el._t=setTimeout(()=>el.classList.remove('show'),2600)}}
function burst(x,y){{if(RM)return;const c=['#00D632','#171717','#898989','#00D632'];for(let k=0;k<14;k++){{const d=document.createElement('i');d.className='dot-burst';const a=k/14*Math.PI*2,r=40+Math.random()*50;d.style.cssText=`left:${{x}}px;top:${{y}}px;background:${{c[k%4]}};--bx:${{Math.cos(a)*r}}px;--by:${{Math.sin(a)*r}}px`;document.body.appendChild(d);setTimeout(()=>d.remove(),800)}}}}
const dp=$('#donep');function donePage(o){{dp.classList.toggle('show',o);dp.setAttribute('aria-hidden',!o);document.body.style.overflow=o?'hidden':'';if(o)setTimeout(()=>$('#doneb').focus({{preventScroll:true}}),300)}}
$('#doneb').addEventListener('click',()=>{{donePage(false);toast('明天见')}});$('#donex').addEventListener('click',()=>donePage(false));
addEventListener('keydown',e=>{{if(e.key==='Escape')donePage(false)}});
items.forEach(x=>x.querySelector('.tick').addEventListener('click',e=>{{const i=x.dataset.i;read.has(i)?read.delete(i):read.add(i);sync();
 if(read.has(i)){{const r=e.currentTarget.getBoundingClientRect();burst(r.left+15,r.top+15);if(read.size===N)setTimeout(()=>donePage(true),RM?0:450);else toast(`已读 ${{read.size}} / ${{N}}`)}}}}));
sync();
// 筛选 chips → 列表 + 标题 flip（联动）
const flip=$('#flip');function setTitle(t){{const old=flip.querySelector('span:not(.out)');if(old.textContent===t)return;old.classList.remove('in');old.classList.add('out');setTimeout(()=>old.remove(),180);const n=document.createElement('span');n.className='in';n.textContent=t;flip.appendChild(n)}}
$$('#chips button').forEach(b=>b.addEventListener('click',()=>{{ $$('#chips button').forEach(x=>{{x.classList.toggle('on',x===b);x.setAttribute('aria-selected',x===b)}});
 const c=b.dataset.c;items.forEach(x=>x.classList.toggle('hide',c!=='*'&&x.dataset.c!==c));setTitle(c==='*'?'全部':c);
 const v=vis();v.forEach((x,k)=>{{x.classList.remove('seen');x.style.setProperty('--d',(k%6)*60+'ms');void x.offsetWidth;rv.observe(x)}});pos.textContent=`第 1 / ${{v.length}} 条`;
 b.scrollIntoView({{inline:'center',block:'nearest',behavior:RM?'auto':'smooth'}});
 const top=$('#list').getBoundingClientRect().top+scrollY-120;if(scrollY>top)scrollTo({{top,behavior:RM?'auto':'smooth'}})}}));
// 彩蛋：点数字重滚
$('#proof').addEventListener('click',()=>$$('#proof .digit>i').forEach((d,k)=>{{d.style.animation='none';void d.offsetWidth;d.style.animation='';d.style.animationDelay=(k*.04)+'s'}}));
// 彩蛋：双击扇形卡重新展开
let lastTap=0;fan.addEventListener('click',e=>{{const t=Date.now();if(t-lastTap<320){{e.preventDefault();const cs=[...fan.children],z=cs.map(c=>c.style.getPropertyValue('--z'));z.unshift(z.pop());cs.forEach((c,k)=>c.style.setProperty('--z',z[k]));fan.classList.remove('spin','go');void fan.offsetWidth;fan.classList.add('spin')}}lastTap=t}});
fan.addEventListener('dblclick',e=>e.preventDefault());
// 彩蛋：点顶部绿勾再弹一次
const st=$('#stamp');st.addEventListener('click',()=>{{st.classList.remove('again');void st.offsetWidth;st.classList.add('again');const r=st.getBoundingClientRect();burst(r.left+r.width/2,r.top+r.height/2)}});
// 彩蛋：点头像弹一下
$$('.av').forEach(a=>a.addEventListener('click',()=>{{a.classList.add('boing');setTimeout(()=>a.classList.remove('boing'),380)}}));
// 彩蛋：连点 logo 五次
let lc=0,lt;$('#logo').addEventListener('click',e=>{{lc++;clearTimeout(lt);lt=setTimeout(()=>lc=0,900);const i=e.currentTarget.querySelector('i');i.style.transform=`rotate(${{lc*72}}deg)`;if(lc>=5){{lc=0;toast('你发现了日报的小秘密');const r=i.getBoundingClientRect();burst(r.left+10,r.top+10)}}}});
}})();
</script></body></html>'''
bad=re.findall(r'&(?:amp|lt|gt|quot|apos|nbsp);',html); assert not bad,bad
for w in ('Cal.com','cal-duration','Cal 胶囊','3c84f3','Things 蓝'): assert w.lower() not in html.lower(),('禁用词',w)
open(f'web/{DATE}.html','w').write(html)
# used-combos：同日只保留一条（覆盖）
p='used-combos.json'
try: uc=json.load(open(p))
except Exception: uc=[]
uc=[x for x in uc if x.get('date')!=DATE]
rec={'date':DATE,'theme':cfg['theme'],'elements':cfg['elements'],'sources':sorted({t['source'] for t in used}),
  'non_core_share':round(sum(1 for t in used if t['source'] not in ('gpt888.vip','ChatLab','DigVPS'))/len(used),2)}
if cfg.get('notes'): rec['notes']=cfg['notes']
uc.append(rec)
json.dump(sorted(uc,key=lambda x:x['date']),open(p,'w'),ensure_ascii=False,indent=2)
print('wrote',f'web/{DATE}.html',len(html),'non-core share',rec['non_core_share'])
