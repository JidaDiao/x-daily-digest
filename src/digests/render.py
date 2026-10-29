#!/usr/bin/env python3
"""X 每日 AI 推荐 · 杂志式多页出图
用法: python3 render.py <style> <items.json> [out_prefix]
  多页模板（含 {{PAGE}}）→ <out_prefix>-01.png 封面, -02.. 内容页（每页 3–4 条），1080x1440
  旧单页模板（含 {{ITEMS}}）→ 单张长图 <out_prefix>.png
默认 out_prefix = /workspace/digests/out/<style>/<date>"""
import json,sys,subprocess,html,os,math,re,collections
from PIL import Image
D=os.path.dirname(os.path.abspath(__file__)); e=html.escape
ICON={"教程":"📚","工具":"🛠","行业":"📰","观点":"💬","实测":"🧪","研究":"🔬","AIGC":"🎨","变现":"💰"}
COLNAME={"教程":"学习札记","工具":"工具箱","行业":"行业观察","观点":"评论","实测":"实验室","研究":"前沿研究","AIGC":"AIGC","变现":"落地变现"}
STOP=set("the and for with you your into from this that via one all are".split())
ZH=["智能体","大模型","Agent","MCP","Skill","Claude Code","Codex","课程","游戏","编码","文档","推理","微调","Prompt","API","iOS","Gemini","DeepSeek","豆包"]
def heat(x): return x["likes"]+2*x["rts"]
def img(x,cls,cap,i):
    p=x.get("media")
    if p and os.path.exists(os.path.join(D,p)):
        kind="原帖配图"
        inner=f'<img src="file://{os.path.join(D,p)}">'
    else:
        kind="插画"; inner=svgph(i,x["cat"],cls!="thumb")
    return f'<figure class="fig {cls}"><div class="well">{inner}</div>{f"<figcaption><b>图 {cap}</b> · {kind} · @{e(x["handle"])}</figcaption>" if cap else ""}</figure>'
def svgph(i,cat,txt=True):
    lines="".join(f'<line x1="{x}" y1="0" x2="{x-260}" y2="600" />' for x in range(0,1400,46))
    return f'<svg class="ph" viewBox="0 0 800 600" preserveAspectRatio="xMinYMid slice"><g class="hatch">{lines}</g><circle class="disc" cx="560" cy="250" r="190"/>{f'<text class="phn" x="60" y="520">{i:02d}</text><text class="phc" x="70" y="110">{e(cat)}</text>' if txt else ''}</svg>'
def kick(x):
    av=x.get("avatar"); a=f'<img class="av" src="file://{os.path.join(D,av)}">' if av and os.path.exists(os.path.join(D,av)) else ""
    return f'<div class="kick">{a}<span class="ic">{ICON.get(x["cat"],"✦")}</span><b>{e(x["cat"])}</b><span class="by">@{e(x["handle"])}</span></div>'
def meta(x,mx): return f'<div class="meta"><span class="lk">♥ {x["likes"]}</span><span class="rt">↻ {x["rts"]}</span><span class="hx">热度 {round(heat(x)/mx*100)}</span></div><div class="heat"><i style="width:{heat(x)/mx*100:.1f}%"></i></div>'
def keywords(items):
    c=collections.Counter()
    for x in items:
        txt=x["title"]+" "+x["summary"]; w=1+heat(x)/50
        for k in ZH:
            if k.lower() in txt.lower(): c[k]+=w
        for t in re.findall(r"[A-Za-z][A-Za-z0-9.\-]{2,}",txt):
            if t.lower() not in STOP and not any(t.lower() in k.lower() for k in ZH): c[t]+=w*.6
    return c.most_common(12)
def donut(items):
    c=collections.Counter(x["cat"] for x in items); n=len(items); r=110; C=2*math.pi*r; off=0; segs=[]; leg=[]
    for j,(k,v) in enumerate(c.most_common()):
        op=1-j*0.16; L=v/n*C
        segs.append(f'<circle r="{r}" cx="150" cy="150" fill="none" stroke-width="44" class="seg" style="stroke-opacity:{op:.2f}" stroke-dasharray="{L-4:.1f} {C:.1f}" stroke-dashoffset="{-off:.1f}" transform="rotate(-90 150 150)"/>'); off+=L
        leg.append(f'<li><i class="dot" style="opacity:{op:.2f}"></i>{e(k)}<em>{v/n*100:.0f}%</em></li>')
    return f'<div class="donut-wrap"><svg width="210" height="210" viewBox="0 0 300 300">{"".join(segs)}<text x="150" y="168" text-anchor="middle" class="dn">{n}</text></svg><ul class="legend">{"".join(leg)}</ul></div>'
def strip(d,right): return f'<div class="strip"><span>X DAILY · AI DIGEST</span><span>{e(d["date"])}</span><span>{right}</span></div>'
def cover(d,mx,np_):
    it=d["items"]; L=it[0]; tl=sum(x["likes"] for x in it); tr=sum(x["rts"] for x in it); H=sum(heat(x) for x in it)
    bars="".join(f'<div class="bar"><span class="nm">{i+1:02d} {e(x["title"])}</span><span class="tr"><i style="width:{heat(x)/mx*100:.1f}%"></i></span><b>{heat(x)}</b></div>' for i,x in sorted(enumerate(it),key=lambda p:-heat(p[1]))[:5])
    kw=keywords(it); km=kw[0][1] if kw else 1; kw=kw[:7]
    cloud="".join(f'<span class="k{0 if j<3 else 1}" style="font-size:{22+int(26*w/km)}px">{e(k)}</span>' for j,(k,w) in enumerate(kw))
    per=pages(it); toc=[]; pg=2
    for chunk in per:
        for x in chunk: toc.append(f'<li><span>{e(x["title"])}</span><em>P{pg:02d}</em></li>')
        pg+=1
    return f'''<section class="page cover"><div class="grain"></div><div class="paper-wash"></div>
{strip(d,f"{e(d.get('issue',''))} · 共 {np_} 版")}
<header class="mast"><div class="mast-title">X 每日<em>AI</em>报</div><div class="mast-sub"><span>{len(it)} 条精选</span><span>♥ {tl}</span><span>↻ {tr}</span><span>热度指数 {H}</span></div></header>
<div class="lead-story">{img(L,"hero-fig","1",1)}<div class="ls-text"><div class="col-name">头条 · {COLNAME.get(L["cat"],L["cat"])}</div>{kick(L)}<h2 class="t-lead">{e(L["title"])}</h2><p class="s">{e(L["summary"])}</p></div></div>
<div class="viz"><figure class="chart"><div class="label">分类占比</div>{donut(it)}<figcaption><b>图 2</b> · 本期 {len(it)} 条按栏目分布</figcaption></figure>
<figure class="chart"><div class="label">互动量 Top 5</div><div class="bars">{bars}</div><figcaption><b>图 3</b> · 互动量 = 点赞 + 2×转发</figcaption></figure></div>
{'<style>.toc li{line-height:1.28!important;font-size:19px!important}.toc li em{font-size:19px!important}</style>' if len(it)>7 else ''}<div class="lower"><div class="toc"><div class="label">本期目录</div><ol>{"".join(toc)}</ol></div><div class="cloud"><div class="label">关键词</div><div class="words">{cloud}</div></div></div>
<div class="fill"></div><div class="foot"><span>原帖链接附于图下</span><span>CURATED BY GROK BOT</span></div></section>'''
def pages(it):
    n=len(it); k=max(1,math.ceil(n/4)); 
    if n/k<3 and k>1: k-=1
    sz=[n//k+(1 if i<n%k else 0) for i in range(k)]; out=[];s=0
    for z in sz: out.append(it[s:s+z]); s+=z
    return out
def content(d,chunk,start,pno,np_,mx):
    F=chunk[0]; rest=chunk[1:]; cats=" · ".join(list(dict.fromkeys(COLNAME.get(x["cat"],x["cat"]) for x in chunk))[:2])
    q=F.get("quote") or F["summary"]
    feat=f'''<article class="feature">{img(F,"feat-fig",f"{pno}-1",start)}<div class="f-body"><div class="no">{start:02d}</div>{kick(F)}<h2 class="t">{e(F["title"])}</h2><p class="s">{e(F["summary"])}</p><blockquote class="pq">“{e(q)}”<cite>— @{e(F["handle"])}</cite></blockquote>{meta(F,mx)}</div></article>'''
    gs="".join(f'<article class="item">{img(x,"thumb","",start+j+1)}<div class="no">{start+j+1:02d}</div>{kick(x)}<h3 class="t">{e(x["title"])}</h3><p class="s">{e(x["summary"])}</p>{meta(x,mx)}</article>' for j,x in enumerate(rest))
    return f'''<section class="page content"><div class="grain"></div><div class="paper-wash"></div>{strip(d,f"第 {pno:02d} 版 / 共 {np_} 版")}
<div class="sec"><div class="sec-dot"></div><div class="sec-title">{e(cats)}</div><div class="sec-no">P{pno:02d}</div></div>
{feat}<div class="grid g{len(rest)}">{gs}</div><div class="fill"></div><div class="foot"><span>X 每日 AI 报 · {e(d["date"])}</span><span>{pno:02d}</span></div></section>'''
def shot(htmlstr,out,h):
    tmp=out+".html"; open(tmp,"w").write(htmlstr)
    subprocess.run(["google-chrome","--headless=new","--no-sandbox","--hide-scrollbars","--allow-file-access-from-files",f"--screenshot={out}",f"--window-size=1080,{h}","--virtual-time-budget=3000",f"file://{tmp}"],check=True,capture_output=True); os.remove(tmp)
def main():
    style,src=sys.argv[1],sys.argv[2]; d=json.load(open(src)); tpl=open(f"{D}/template-{style}.html").read()
    pre=sys.argv[3] if len(sys.argv)>3 else f"{D}/out/{style}/{d['date']}"; os.makedirs(os.path.dirname(pre),exist_ok=True)
    if "{{PAGE}}" not in tpl:  # 旧单页长图模板
        it="".join(f'<article class="item"><div class="no">{i+1:02d}</div><div class="bd">{kick(x)}<h2 class="t">{e(x["title"])}</h2><p class="s">{e(x["summary"])}</p><div class="meta"><span class="lk">♥ {x["likes"]}</span><span class="rt">↻ {x["rts"]}</span></div></div></article>' for i,x in enumerate(d["items"]))
        t=tpl
        for k,v in {"ITEMS":it,"DATE":d["date"],"ISSUE":d.get("issue",""),"N":str(len(d["items"]))}.items(): t=t.replace("{{"+k+"}}",v)
        out=pre+".png"; shot(t,out,5000); im=Image.open(out).convert("RGB"); w,H=im.size; p=im.load(); bg=p[w//2,H-1]
        y=next(y for y in range(H-1,0,-1) if any(sum(abs(a-b) for a,b in zip(p[x,y],bg))>40 for x in range(0,w,3)))
        im.crop((0,0,w,min(H,y+90))).save(out); print(out); return
    mx=max(heat(x) for x in d["items"]) or 1; ch=pages(d["items"]); np_=len(ch)+1
    outs=[f"{pre}-01.png"]; shot(tpl.replace("{{PAGE}}",cover(d,mx,np_)),outs[0],1440); s=1
    for i,c in enumerate(ch):
        o=f"{pre}-{i+2:02d}.png"; shot(tpl.replace("{{PAGE}}",content(d,c,s,i+2,np_,mx)),o,1440); outs.append(o); s+=len(c)
    print("\n".join(outs))
if __name__=="__main__": main()
