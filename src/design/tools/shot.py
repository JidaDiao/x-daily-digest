#!/usr/bin/env python3
"""稳定截图：python3 tools/shot.py URL OUT.png [--w 390 --h 844] [--full] [--wait 2500]
用 playwright + /usr/bin/google-chrome；导航 20s 超时，只等 domcontentloaded，再固定等 wait ms；
外层务必再套 `timeout -k 5 45`，防止浏览器本身挂死。退出码 0 成功、1 失败（会打印原因，不要重试超过 1 次）。"""
import sys,asyncio,argparse
from playwright.async_api import async_playwright
ap=argparse.ArgumentParser();ap.add_argument('url');ap.add_argument('out')
ap.add_argument('--w',type=int,default=390);ap.add_argument('--h',type=int,default=844)
ap.add_argument('--full',action='store_true');ap.add_argument('--wait',type=int,default=2500)
a=ap.parse_args()
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox','--disable-gpu'])
        try:
            m=a.w<800
            pg=await b.new_page(viewport={'width':a.w,'height':a.h},has_touch=m,is_mobile=m,device_scale_factor=2 if m else 1)
            pg.set_default_timeout(20000)
            try: await pg.goto(a.url,wait_until='domcontentloaded',timeout=20000)
            except Exception as e: print('[shot] goto 未完成，按当前状态截图:',type(e).__name__)
            await pg.wait_for_timeout(a.wait)
            await pg.screenshot(path=a.out,full_page=a.full,timeout=15000)
            print('[shot] ok',a.out)
        finally: await b.close()
try: asyncio.run(main())
except Exception as e: print('[shot] FAIL',e); sys.exit(1)
