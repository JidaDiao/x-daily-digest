#!/usr/bin/env python3
"""从 guizang-social-card-skill 的 theme-presets / components 规范生成 template-<style>.html。改设计请改这里再重跑。"""
import json,os
D=os.path.dirname(os.path.abspath(__file__))
ED={ # Editorial Magazine x E-ink（theme-presets.md 原值）
"ink-classic":("#f3f0e8","#ebe6da","#0a0a0b","#68625a","rgba(10,10,11,.22)","#111111","#d8d2c6","10,10,11"),
"indigo-porcelain":("#f2f4f5","#e5ebef","#0a1f3d","#5f6d78","rgba(10,31,61,.20)","#315d93","#d7e1ec","10,31,61"),
"forest-ink":("#f5f1e8","#e8dfcf","#16251b","#5d665d","rgba(22,37,27,.22)","#2e6b4f","#d4dfd2","22,37,27"),
"kraft-paper":("#eedfc7","#dfc9a8","#2a1e13","#755f49","rgba(42,30,19,.24)","#9b5a2e","#d5b58f","42,30,19"),
"dune":("#f0e6d2","#ded0b7","#1f1a14","#6f6557","rgba(31,26,20,.22)","#8f7650","#d4c2a4","31,26,20"),
"midnight-ink":("#0e0d0c","#1a1714","#ece2cf","#9a8c75","rgba(236,226,207,.22)","#d4a04a","#3a2a14","236,226,207"),
}
SW={ # Swiss International（accent 原值；黄/绿上的字用 #0a0a0a）
"ikb-blue":("#002FA7","#ffffff"),"lemon-yellow":("#FFD500","#0a0a0a"),
"lemon-green":("#C5E803","#0a0a0a"),"safety-orange":("#FF6B35","#0a0a0a"),
}
COMMON="""*{box-sizing:border-box;margin:0}body{width:1080px;background:var(--paper)}
.page{position:relative;width:1080px;height:1440px;overflow:hidden;background:var(--paper);color:var(--ink);display:flex;flex-direction:column}
.cloud span{display:inline-block;margin:0 22px 10px 0;line-height:1.2}
.legend{list-style:none;padding:0}.legend li{display:flex;align-items:center;gap:12px}
.dot{width:14px;height:14px;display:inline-block}
.bar{display:grid;grid-template-columns:230px 1fr 64px;align-items:center;gap:16px}
.bar .tr{height:12px;position:relative}.bar .tr i{position:absolute;left:0;top:0;bottom:0}
.item .heat{height:4px;position:relative;margin-top:16px}.item .heat i{position:absolute;left:0;top:0;bottom:0}
.fill{flex:1}"""+"""
/* —— 杂志版式（结构，两套共用） —— */
.fig{margin:0}.well{position:relative;overflow:hidden;width:100%;height:100%}.well img{width:100%;height:100%;object-fit:cover;display:block}
.ph{width:100%;height:100%;display:block}.ph .hatch line{stroke:var(--accent);stroke-opacity:.18;stroke-width:2}.ph .disc{fill:var(--accent);fill-opacity:.14}
.ph .phn{font-size:300px;fill:var(--ink);fill-opacity:.88}.ph .phc{font-size:44px;fill:var(--accent);letter-spacing:.2em}
figcaption{font-size:17px;margin-top:10px;letter-spacing:.06em}
.mast{text-align:center;padding:14px 0 12px}.mast-title{font-size:124px;line-height:1.05;letter-spacing:.06em}
.mast-sub{display:flex;justify-content:center;gap:34px;padding:12px 0;margin-top:14px}
.lead-story{display:grid;grid-template-columns:480px 1fr;gap:40px;padding:24px 0 22px}.hero-fig .well{height:260px}
.col-name{display:inline-block;font-size:19px;letter-spacing:.2em;padding:4px 0;margin-bottom:12px}
.t-lead{font-size:42px;line-height:1.3;margin:6px 0 14px}.lead-story .s{font-size:24px;line-height:1.7}
.viz{display:grid;grid-template-columns:400px 1fr;gap:44px;padding:20px 0 4px}.chart{margin:0}
.dn{font-size:76px;fill:var(--ink)}.seg{stroke:var(--accent)}.dot{background:var(--accent)}
.lower{display:grid;grid-template-columns:1fr 360px;gap:44px;padding-top:22px}
.toc ol{list-style:none;padding:0;columns:1}.toc li{display:flex;gap:14px;font-size:20px;line-height:1.5}.toc li span{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.toc li em{font-style:normal}
.cloud .words{line-height:1.1}
.sec{display:flex;align-items:flex-end;gap:22px;padding:26px 0 16px;margin-bottom:28px}.sec-title{flex:1;font-size:54px;line-height:1.1}.sec-no{font-size:22px;letter-spacing:.16em}
.feature{display:grid;grid-template-columns:470px 1fr;gap:40px}.feat-fig .well{height:430px}
.feature .no{font-size:72px;line-height:1;margin-bottom:6px}.feature .t{font-size:42px;line-height:1.32;margin:4px 0 12px}.feature .s{font-size:24px;line-height:1.7}
.pq{margin:18px 0 6px;padding:14px 0 14px 22px;font-size:27px;line-height:1.5}.pq cite{display:block;font-size:17px;font-style:normal;margin-top:8px;letter-spacing:.1em}
.grid{display:grid;gap:36px;margin-top:26px;padding-top:24px}.g1{grid-template-columns:1fr}.g2{grid-template-columns:1fr 1fr}.g3{grid-template-columns:1fr 1fr 1fr}
.grid .item{display:block;padding:0;border:none;position:relative}.grid .thumb .well{height:150px}.g3 .thumb .well{height:120px}
.grid .item .no{position:absolute;top:10px;left:12px;font-size:44px;line-height:1;padding:2px 10px}
.grid .item .kick{margin-top:16px}.grid .t{font-size:32px;line-height:1.35;margin:6px 0 10px}.g3 .t{font-size:27px}.grid .s{font-size:21px;line-height:1.65}
.av{width:30px;height:30px;border-radius:50%;object-fit:cover;vertical-align:middle;margin-right:10px}
.meta .hx{opacity:.85}
"""
EDCSS="""
:root{--serif-zh:"Noto Serif CJK SC","Noto Serif SC","Songti SC",serif;--serif-en:"Playfair Display",serif;--sans-zh:"Noto Sans CJK SC","PingFang SC",sans-serif;--mono:"IBM Plex Mono",monospace}
.page{font-family:var(--serif-zh);padding:72px 80px 60px}
.grain{position:absolute;inset:0;pointer-events:none;opacity:.35;mix-blend-mode:multiply;background-image:radial-gradient(rgba(var(--ink-rgb),.07) 1px,transparent 1px);background-size:5px 5px}
.paper-wash{position:absolute;inset:0;pointer-events:none;background:linear-gradient(180deg,rgba(var(--ink-rgb),.02),rgba(var(--ink-rgb),.05) 60%,rgba(var(--ink-rgb),.08))}
.page>*:not(.grain):not(.paper-wash){position:relative;z-index:2}
.strip{display:flex;justify-content:space-between;font:500 18px var(--mono);letter-spacing:.2em;color:var(--muted);text-transform:uppercase;border-bottom:1px solid var(--ink);padding-bottom:16px}
.kicker{font:500 21px var(--mono);letter-spacing:.22em;color:var(--accent);margin:56px 0 18px;text-transform:uppercase}
.display{font-weight:500;font-size:112px;letter-spacing:.04em;line-height:1.12}
.display em{font-family:var(--serif-en);font-style:italic;color:var(--accent);font-weight:500}
.h-sub{font:italic 400 34px var(--serif-en);color:var(--muted);margin-top:18px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin:44px 0 36px}
.stats div{padding:22px 0 20px;border-right:1px solid var(--line);padding-left:20px}.stats div:first-child{padding-left:0}.stats div:last-child{border:none}
.stats b{display:block;font:500 56px/1 var(--serif-en);color:var(--ink)}.stats span{font:500 18px var(--mono);letter-spacing:.2em;color:var(--muted)}
.label{font:500 18px var(--mono);letter-spacing:.2em;color:var(--muted);margin-bottom:18px;text-transform:uppercase}
.viz{display:grid;grid-template-columns:360px 1fr;gap:48px}
.donut-wrap{display:flex;gap:24px;align-items:center}.legend li{font:400 22px var(--serif-zh);margin-bottom:8px}.legend em{font:500 18px var(--mono);color:var(--muted);font-style:normal;margin-left:auto}
.bars .bar{font:400 22px var(--serif-zh);margin-bottom:14px}.bar .tr{background:var(--paper-2)}.bar .tr i{background:var(--accent)}.bar b{font:500 19px var(--mono);text-align:right}
.bar .nm{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cloud{margin-top:34px;border-top:1px solid var(--line);padding-top:24px}.cloud span{font-family:var(--serif-zh);color:var(--ink)}.cloud span.k0{color:var(--accent);font-style:italic;font-family:var(--serif-en),var(--serif-zh)}
.foot{display:flex;justify-content:space-between;border-top:1px solid var(--ink);padding-top:18px;font:500 18px var(--mono);letter-spacing:.2em;color:var(--muted)}
.list{margin-top:30px}
.item{display:grid;grid-template-columns:110px 1fr;column-gap:24px;padding:34px 0;border-top:1px solid var(--line)}.item:first-child{border-top:none}
.no{font:400 76px/1 var(--serif-en);color:var(--accent);font-style:italic}
.kick{font:500 18px var(--mono);letter-spacing:.2em;color:var(--muted);margin-bottom:14px}.kick b{color:var(--accent);font-weight:500;margin:0 16px 0 8px}
.t{font-weight:500;font-size:46px;line-height:1.36;letter-spacing:.03em;margin-bottom:14px}
.s{font:400 27px/1.75 var(--serif-zh);color:rgba(var(--ink-rgb),.78)}
.meta{font:500 19px var(--mono);letter-spacing:.12em;color:var(--muted);margin-top:14px}.meta span{margin-right:28px}
.item .heat{background:var(--paper-2)}.item .heat i{background:var(--accent)}
.sec-title{font-weight:500;font-size:64px;letter-spacing:.03em;margin-top:44px}.sec-title em{font:italic 500 64px var(--serif-en);color:var(--accent)}
"""
EDCSS+="""
.page{padding:56px 72px 48px}
.mast{border-bottom:1px solid var(--ink)}.mast-title{font-weight:600;letter-spacing:.08em}.mast-title em{font:italic 500 124px var(--serif-en);color:var(--accent);margin:0 10px}
.mast-sub{border-top:3px double var(--ink);font:500 18px var(--mono);letter-spacing:.2em;color:var(--muted)}
.lead-story{border-bottom:1px solid var(--line)}figcaption{font-family:var(--mono);color:var(--muted)}figcaption b{color:var(--accent);font-weight:500}
.col-name{font-family:var(--mono);color:var(--accent);border-bottom:1px solid var(--accent)}.t-lead{font-weight:500;letter-spacing:.03em}
.viz{border-bottom:1px solid var(--line);padding-bottom:20px}.label{margin-bottom:12px}.bars .bar{font-size:20px}
.toc li{font-family:var(--serif-zh);border-bottom:1px dotted var(--line)}.toc li em{font:italic 500 20px var(--serif-en);color:var(--accent)}
.cloud{margin:0;border:none;padding:0}
.sec{border-bottom:3px double var(--ink)}.sec-dot{display:none}.sec-title{font-weight:500;letter-spacing:.04em}.sec-no{font:italic 500 28px var(--serif-en);color:var(--accent)}
.pq{border-left:3px solid var(--accent);font-family:var(--serif-zh);font-weight:500;color:var(--ink)}.pq cite{font-family:var(--mono);color:var(--muted)}
.grid{border-top:1px solid var(--ink)}.g2 .item+.item,.g3 .item+.item{border-left:1px solid var(--line);padding-left:36px;margin-left:-18px}
.grid .item .no{background:var(--paper);color:var(--accent)}.grid .item .no{left:auto}.grid .item+.item .no{left:48px}.grid .item:first-child .no{left:12px}
.list{display:none}
"""
MID="""
.grain{opacity:.26;mix-blend-mode:screen;background-image:radial-gradient(rgba(255,244,214,.10) 1px,transparent 1px)}
.paper-wash{background:radial-gradient(80% 50% at 28% 16%,rgba(212,160,74,.12),transparent 64%),radial-gradient(70% 60% at 80% 86%,rgba(60,40,20,.20),transparent 72%),linear-gradient(180deg,rgba(236,226,207,.02),rgba(0,0,0,.32))}
"""
SWCSS="""
:root{--paper:#fafaf8;--ink:#0a0a0a;--grey-1:#f0f0ee;--grey-2:#d4d4d2;--grey-3:#737373;--sans:"Inter","Helvetica Neue",Helvetica,sans-serif;--sans-zh:"Noto Sans CJK SC","PingFang SC",sans-serif;--mono:"IBM Plex Mono",monospace}
.page{font-family:var(--sans),var(--sans-zh);padding:0}
.grain,.paper-wash{display:none}
.strip{display:flex;justify-content:space-between;font:500 20px var(--mono);letter-spacing:.14em;text-transform:uppercase;padding:44px 72px 0}
.cover .strip{color:var(--accent-on)}
.hero{background:var(--accent);color:var(--accent-on);margin:-80px 0 0;padding:150px 72px 56px}
.kicker{font:600 22px var(--sans);letter-spacing:.06em;text-transform:uppercase}
.display{font-weight:200;font-size:168px;line-height:.96;letter-spacing:-.03em;margin-top:34px}.display em{font-style:normal}
.h-sub{font:300 34px var(--sans),var(--sans-zh);margin-top:26px}
.body{padding:0 72px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);border-bottom:2px solid var(--ink)}
.stats div{padding:26px 0 22px}.stats b{display:block;font:200 72px/1 var(--sans);letter-spacing:-.02em}.stats span{font:500 19px var(--mono);color:var(--grey-3);letter-spacing:.1em}
.label{font:600 20px var(--sans),var(--sans-zh);letter-spacing:.06em;text-transform:uppercase;margin:34px 0 18px}
.viz{display:grid;grid-template-columns:360px 1fr;gap:48px}
.donut-wrap{display:flex;gap:24px;align-items:center}.legend li{font:400 22px var(--sans-zh);margin-bottom:8px}.legend em{font:500 18px var(--mono);color:var(--grey-3);font-style:normal;margin-left:auto}
.bars .bar{font:400 22px var(--sans-zh);margin-bottom:14px}.bar .tr{background:var(--grey-1)}.bar .tr i{background:var(--ink)}.bar:first-child .tr i{background:var(--accent)}.bar b{font:500 19px var(--mono);text-align:right}
.bar .nm{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cloud{border-top:2px solid var(--ink);margin-top:30px}.cloud span{font-family:var(--sans),var(--sans-zh);font-weight:300}.cloud span.k0{font-weight:500}
.foot{display:flex;justify-content:space-between;margin:0 72px 44px;border-top:2px solid var(--ink);padding-top:18px;font:500 18px var(--mono);letter-spacing:.14em;color:var(--grey-3)}
.content .strip{color:var(--ink)}
.sec{margin:36px 72px 0;display:flex;align-items:flex-end;gap:28px;border-bottom:2px solid var(--ink);padding-bottom:20px}
.sec-title{font:200 104px/1 var(--sans);letter-spacing:-.03em}.sec-title em{font-style:normal}.sec-dot{width:56px;height:56px;background:var(--accent);margin-bottom:8px}
.list{padding:0 72px}
.item{display:grid;grid-template-columns:170px 1fr;padding:32px 0;border-bottom:1px solid var(--grey-2)}.item:last-child{border-bottom:none}
.no{font:200 104px/.9 var(--sans);letter-spacing:-.04em}
.kick{font:500 18px var(--mono);letter-spacing:.12em;color:var(--grey-3);margin-bottom:12px}.kick .ic{display:none}.kick b{background:var(--accent);color:var(--accent-on);padding:3px 12px;font:600 18px var(--sans-zh);letter-spacing:.04em;margin-right:16px}
.t{font:400 44px/1.32 var(--sans),var(--sans-zh);letter-spacing:-.005em;margin-bottom:12px}
.s{font:400 26px/1.7 var(--sans-zh);color:#333}
.meta{font:500 19px var(--mono);color:var(--grey-3);margin-top:12px}.meta span{margin-right:28px}
.item .heat{background:var(--grey-1)}.item .heat i{background:var(--accent)}
"""
SWCSS+="""
.page{padding:0 0 0}
.cover>.strip,.content>.strip{background:var(--ink);color:var(--paper);padding:18px 64px}
.mast,.lead-story,.viz,.lower{margin:0 64px}.sec,.feature,.grid{margin-left:64px;margin-right:64px}
.mast{text-align:left;border-bottom:2px solid var(--ink)}.mast-title{font:200 156px/1 var(--sans),var(--sans-zh);letter-spacing:-.03em}.mast-title em{font-style:normal;background:var(--accent);color:var(--accent-on);padding:0 14px;margin:0 12px}
.mast-sub{justify-content:flex-start;font:500 19px var(--mono);color:var(--grey-3)}
.lead-story{border-bottom:2px solid var(--ink)}figcaption{font-family:var(--mono);color:var(--grey-3)}figcaption b{color:var(--ink)}
.col-name{background:var(--accent);color:var(--accent-on);padding:4px 12px;font:600 19px var(--sans-zh)}.t-lead{font-weight:400;letter-spacing:-.01em}
.viz{border-bottom:2px solid var(--ink);padding-bottom:20px}.label{margin:0 0 12px}.bars .bar{font-size:20px}
.toc li{border-bottom:1px solid var(--grey-2);font-family:var(--sans-zh)}.toc li em{font:500 19px var(--mono)}
.cloud{margin:0;border:none}
.sec{border-bottom:2px solid var(--ink);margin-top:30px}.sec-title{font:200 76px/1 var(--sans),var(--sans-zh);letter-spacing:-.02em}.sec-no{font:500 22px var(--mono)}
.feature .no{font:200 96px/1 var(--sans);letter-spacing:-.04em}.feature .t{font-weight:400}
.pq{border-left:10px solid var(--accent);font:300 30px/1.45 var(--sans),var(--sans-zh)}.pq cite{font-family:var(--mono);color:var(--grey-3)}
.grid{border-top:2px solid var(--ink)}.grid .item .no{background:var(--accent);color:var(--accent-on);font-weight:300}.grid .t{font-weight:400}
.ph .phn{font-family:var(--sans);font-weight:200}.foot{margin:0 64px 40px}
"""
def wrap(css,name): return f'<!doctype html><html><head><meta charset="utf-8"><!-- style: {name}; ported from op7418/guizang-social-card-skill --><style>{COMMON}{css}</style></head><body>{{{{PAGE}}}}</body></html>'
styles=[]
for k,(p,p2,ink,mu,ln,ac,acs,rgb) in ED.items():
    v=f":root{{--paper:{p};--paper-2:{p2};--ink:{ink};--muted:{mu};--line:{ln};--accent:{ac};--accent-soft:{acs};--ink-rgb:{rgb}}}"
    open(f"{D}/template-editorial-{k}.html","w").write(wrap(EDCSS+v+(MID if k=="midnight-ink" else ""),f"editorial-{k}")); styles.append(f"editorial-{k}")
for k,(ac,on) in SW.items():
    open(f"{D}/template-swiss-{k}.html","w").write(wrap(SWCSS+f":root{{--accent:{ac};--accent-on:{on}}}",f"swiss-{k}")); styles.append(f"swiss-{k}")
# 轮换：编辑风与瑞士风交替
ed=[s for s in styles if s.startswith("editorial")];sw=[s for s in styles if s.startswith("swiss")]
rot=[];[rot.extend(x for x in pair if x) for pair in __import__("itertools").zip_longest(ed,sw)]
json.dump({"source":"https://github.com/op7418/guizang-social-card-skill","rotation":rot,"legacy_not_in_rotation":["v2","terminal","cute","swiss","newspaper"]},open(f"{D}/styles.json","w"),ensure_ascii=False,indent=1)
print(rot)
