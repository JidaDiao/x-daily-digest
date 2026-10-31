#!/usr/bin/env python3
"""手机检查：python3 tools/check.py design/<date>.html  → 390×844、360×740 两档
检查横向溢出（scrollWidth==视口宽，.marquee/.track/[data-scroll-x] 内部除外）、pageerror、视频属性；
截全页长图到 /tmp/design-check-<w>.png。外面请套 timeout -k 5 120。退出码 0 过、2 不过。"""
import sys,asyncio,os
from playwright.async_api import async_playwright
f=os.path.abspath(sys.argv[1]);bad=[]
JS='''w=>{const o=[];document.querySelectorAll('body *').forEach(e=>{if(e.closest('.marquee,.track,[data-scroll-x],.nav'))return;const r=e.getBoundingClientRect();if(r.width&&(r.right>w+1||r.left<-1)&&getComputedStyle(e).position!=='fixed')o.push((e.className||e.tagName)+'@'+Math.round(r.right))});
return {sw:document.documentElement.scrollWidth,over:o.slice(0,8),vids:[...document.querySelectorAll('video')].map(v=>[v.muted,v.loop,v.playsInline,v.preload])}}'''
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox','--disable-gpu'])
        for w,h in((390,844),(360,740)):
            pg=await b.new_page(viewport={'width':w,'height':h},has_touch=True,is_mobile=True)
            errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
            await pg.goto('file://'+f,wait_until='load',timeout=30000)
            hh=await pg.evaluate('document.body.scrollHeight')
            for y in range(0,hh,600): await pg.evaluate(f'scrollTo(0,{y})');await pg.wait_for_timeout(60)
            await pg.wait_for_timeout(500);r=await pg.evaluate(JS,w)
            await pg.screenshot(path=f'/tmp/design-check-{w}.png',full_page=True,timeout=30000)
            ok=r['sw']==w and not r['over'] and not errs and all(v[0] and v[1] and v[2] for v in r['vids'])
            print(f'[check] {w}px scrollWidth={r["sw"]} 溢出={r["over"]} 错误={errs[:3]} 视频={len(r["vids"])} → {"过" if ok else "不过"}')
            if not ok: bad.append(w)
        await b.close()
asyncio.run(main());sys.exit(2 if bad else 0)
