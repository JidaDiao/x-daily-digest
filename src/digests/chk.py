import asyncio,sys,os
from playwright.async_api import async_playwright
D=sys.argv[1] if len(sys.argv)>1 else '2026-10-14';V=sys.argv[2] if len(sys.argv)>2 else 'v1'
SRC=sys.argv[3] if len(sys.argv)>3 else f'/workspace/digests/web/{D}.html'
U='file://'+os.path.abspath(SRC);O=f'/workspace/digests/shots/{D}-{V}/';os.makedirs(O,exist_ok=True)
if D=='2026-10-15':
  exec(open('/workspace/digests/chk_1015.py').read())
  sys.exit(0)

AUDIT_JS=r"""()=>{const r={sw:document.documentElement.scrollWidth,iw:innerWidth,big:[],tap:[],font:0,fontEx:[],vh:[]};
for(const e of document.querySelectorAll('body *')){const cs=getComputedStyle(e),b=e.getBoundingClientRect();if(cs.display==='none'||cs.visibility==='hidden')continue;
 const nm=e.tagName.toLowerCase()+(e.id?'#'+e.id:'')+(e.classList.length?'.'+[...e.classList].join('.'):'');
 if(cs.touchAction==='none'&&b.width*b.height>20000)r.big.push(nm+' '+Math.round(b.width)+'x'+Math.round(b.height));
 if(e.matches('a,button,input,select,textarea,[role=button],[role=tab],[onclick]')&&b.width>0&&(b.width<44||b.height<44))r.tap.push(nm+' '+Math.round(b.width)+'x'+Math.round(b.height));
 if(parseFloat(cs.fontSize)<12&&[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())){r.font++;if(r.fontEx.length<5)r.fontEx.push(nm+' '+cs.fontSize)}}
for(const sh of document.styleSheets){try{for(const ru of sh.cssRules){const t=ru.cssText;if(/\b100vh\b/.test(t))r.vh.push(t.slice(0,90))}}catch(e){}}
return r}"""
async def audit(b):
  bad=0
  for w,h in((390,844),(360,740)):
    c=await b.new_context(viewport={'width':w,'height':h},has_touch=True,is_mobile=True,device_scale_factor=2);pg=await c.new_page()
    errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
    await pg.goto(U);await pg.wait_for_timeout(200);await pg.evaluate("document.getAnimations().forEach(a=>{try{a.finish()}catch(e){}})");await pg.wait_for_timeout(300)
    await pg.screenshot(path=f'{O}m{w}-top.png');await pg.screenshot(path=f'{O}m{w}-full.png',full_page=True)
    r=await pg.evaluate(AUDIT_JS);tag=f'[{w}x{h}]'
    if r['sw']!=r['iw'] or r['iw']!=w:bad+=1;print(tag,'ERROR 横向溢出 scrollWidth',r['sw'],'innerWidth',r['iw'],'viewport',w)
    else:print(tag,'OK scrollWidth==innerWidth',r['iw'])
    for x in r['big']:bad+=1;print(tag,'ERROR touch-action:none 大面积',x)
    print(tag,'WARN 点击目标<44px:',len(r['tap']),r['tap'][:6])
    print(tag,'WARN 字号<12px 文本节点:',r['font'],r['fontEx'])
    for x in r['vh'][:4]:print(tag,'WARN 100vh:',x)
    sg=await pg.evaluate("""()=>{
      const els=[...document.querySelectorAll('[data-sig-id]')];
      const idOk=id=>/^(?:x|gh|hf|hn|ld|reddit):[A-Za-z0-9._:\\/\\-@#+]{1,199}$/.test(id);
      const txt=(document.body.innerText||'')+(document.title||'');
      const badName=/X\\s*日报/.test(txt) && !/不要再写/.test(txt);
      const groups=[...document.querySelectorAll('.src-group,[data-src],section[aria-label]')].map(e=>e.getAttribute('data-src')||e.getAttribute('aria-label')||e.className);
      const hasDiaobao=/叼报/.test(txt)||/叼报/.test(document.title||'');
      return {script:!!document.getElementById('dd-news-signal'),n:els.length,
        miss:els.filter(e=>!idOk(e.dataset.sigId)||!e.dataset.sigUrl||!e.dataset.sigTitle).length,
        small:[...document.querySelectorAll('.dd-sig button')].filter(b=>{const r=b.getBoundingClientRect();return r.width<44||r.height<44}).length,
        badName,hasDiaobao,groups:groups.slice(0,8),groupN:document.querySelectorAll('.src-group').length};
    }""")
    lvl='ERROR' if D>='2026-10-26' else 'WARN'
    if sg.get('badName'):
      if lvl=='ERROR':bad+=1
      print(tag,lvl,'文案仍含「X 日报」（路径 /go/x/ 除外，正文勿用）')
    if D>='2026-10-26' and not sg.get('hasDiaobao'):
      bad+=1; print(tag,'ERROR 页面未见「叼报」')
    if D>='2026-10-26' and sg.get('groupN',0)<1:
      # 有 public 时应 ≥2；至少要有来源分组容器。无 public 时允许 1（仅 X）
      print(tag,'WARN 来源分组 .src-group =',sg.get('groupN'),sg.get('groups'))
    if not sg['script'] or sg['n']==0 or sg['miss'] or sg['small']:
      if lvl=='ERROR':bad+=1
      print(tag,lvl,'news-signal：脚本',sg['script'],'条目',sg['n'],'缺属性',sg['miss'],'按钮<44px',sg['small'])
    else:print(tag,'OK news-signal 条目',sg['n'],'分组',sg.get('groupN'),'叼报',sg.get('hasDiaobao'))
    if errs:bad+=1;print(tag,'ERROR pageerror',errs)
    await c.close()
  print('AUDIT', 'FAIL' if bad else 'PASS', 'errors=',bad);return bad
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path='/usr/bin/google-chrome')
    bad=await audit(b)
    if D!='2026-10-14': await b.close(); sys.exit(1 if bad else 0)
    for w,h in((390,844),(1440,900)):
      c=await b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=1);pg=await c.new_page()
      errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
      await pg.goto(U);await pg.wait_for_timeout(100)
      for t in (0,300,700,1200,2000):
        await pg.evaluate(f"document.getAnimations().forEach(a=>{{a.pause();a.currentTime={t}}})")
        await pg.screenshot(path=f'{O}{w}-entry-{t}.png')
      await pg.evaluate("document.getAnimations().forEach(a=>a.finish())");await pg.wait_for_timeout(300)
      await pg.screenshot(path=f'{O}{w}-hero.png')
      print(w,'scrollW',await pg.evaluate('document.documentElement.scrollWidth'),errs)
      if w==390:
        await pg.click('#chips button:nth-child(3)');await pg.wait_for_timeout(700)
        await pg.screenshot(path=f'{O}390-filter.png')
        print('visible',await pg.evaluate("document.querySelectorAll('.item:not(.hide)').length"),await pg.text_content('#flip'))
        await pg.click('#chips button:nth-child(1)');await pg.wait_for_timeout(500)
        for el in await pg.query_selector_all('.tick'): await el.scroll_into_view_if_needed(); await el.click()
        await pg.wait_for_timeout(400)
        await pg.screenshot(path=f'{O}390-allread.png')
        print(await pg.text_content('#readc'),await pg.get_attribute('#toast','class'),await pg.text_content('#pos'))
        await pg.evaluate("scrollTo(0,0)");await pg.wait_for_timeout(300)
        for _ in range(5): await pg.click('#logo')
        print('logo',await pg.text_content('#toastt'))
        await pg.click('#proof');await pg.wait_for_timeout(150);await pg.screenshot(path=f'{O}390-reroll.png')
        await pg.dblclick('.fan-card:nth-child(2)',delay=50) if False else None
        await pg.evaluate("const f=document.getElementById('fan');f.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));f.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}))")
        print('fan',await pg.get_attribute('#fan','class'))
      await c.close()
    c=await b.new_context(viewport={'width':390,'height':844},reduced_motion='reduce');pg=await c.new_page();await pg.goto(U);await pg.wait_for_timeout(200)
    await pg.screenshot(path=f'{O}390-reduced.png');print('reduced ok')
    await b.close()
asyncio.run(main())
