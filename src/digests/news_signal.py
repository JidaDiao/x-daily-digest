"""叼报页嵌入共用互动脚本 news-signal.js（👍👎⭐ + 停留 2s 已读 + 可选短评）。

- normalize_sig_id(source, raw_id)：把各来源 id 规范成 NEWS_SIGNAL.md 的写法
  （x:<id> / gh:repo/<owner>/<name> / hf:... / hn:<id>）。
- sig_attrs(it)：生成条目容器上的 data-sig-* 属性。
- load_day_items(date)：合并 items-DATE.json（X）与 items-public-DATE.json（社区精选）；
  缺 public 文件时只返回 X 并打日志。
- embed_signal(html, date)：每次从 SIG_PATH 现读最新脚本并内联；单文件离线可显示。
- check_signal(html, n_items)：校验脚本存在、每条有合法 data-sig-id。

短评（已启用）：点 👍/👎 后弹出可选一行「为什么？（可不写）」；有字再发
action=comment，meta.note≤200、meta.vote=like|dislike。脚本自带 .dd-note 样式
（含 min-height:44px）。不要改 daily-portal 里的脚本文件；embed 只现读内联。
"""
import re, json, os, sys
SIG_PATH='/workspace/daily-portal/web/news-signal.js'

def _e(s): return ''.join('&#%d;'%ord(c) if c in '&<>"\'' else c for c in str(s))

def normalize_sig_id(source, raw_id):
    """把各来源原始 id 规范成 NEWS_SIGNAL.md 的写法。
    X 帖子 → x:<post id>
    github:new|trending|.../owner/repo → gh:repo/owner/repo
    hf:... → 原样（已是 hf: 前缀）
    hn:<id> → 原样
    已是 x:/gh:/hf:/hn:/ld:/reddit: 前缀的原样返回。
    """
    s=(source or '').lower().strip(); rid=str(raw_id or '').strip()
    if not rid: raise ValueError('empty id')
    if re.match(r'^(x|gh|hf|hn|ld|reddit):', rid): return rid
    if s in ('github','gh'):
        # github:new/owner/repo | github:trending/owner/repo | owner/repo
        m=re.match(r'^(?:github:)?(?:new|trending|search-new|repo)?/?([^/]+)/([^/]+)$', rid)
        if not m: m=re.match(r'^github:(?:[^/]+)/([^/]+)/([^/]+)$', rid)
        if m: return f'gh:repo/{m.group(1)}/{m.group(2)}'
        raise ValueError(f'bad github id: {rid}')
    if s in ('hf','huggingface'):
        return rid if rid.startswith('hf:') else 'hf:'+rid
    if s in ('hn','hackernews'):
        m=re.search(r'(\d+)$', rid)
        if not m: raise ValueError(f'bad hn id: {rid}')
        return 'hn:'+m.group(1)
    if s in ('x','twitter','x.com') or rid.isdigit():
        return 'x:'+rid
    # fallback：若 raw 已带前缀则用，否则 source:raw
    return rid if ':' in rid else f'{s or "item"}:{rid}'

def sig_attrs(it):
    """生成 data-sig-*。X 条目用 id 数字；社区条目的 id 已带前缀，走 normalize_sig_id。"""
    src=it.get('sig_source') or it.get('source') or 'x'
    # X 条目的 source 常是「Grok Bot 早报」之类，用数字 id 判定
    raw=str(it['id'])
    if raw.isdigit() or (it.get('handle') and not raw.startswith(('github:','hf:','hn:','gh:'))):
        sid=normalize_sig_id('x', raw)
        author=it.get('handle') or it.get('author') or ''
        topic=it.get('topic') or it.get('cat') or ''
        url=it.get('url') or f"https://x.com/{author}/status/{raw}"
        tags=','.join(t for t in [f'topic:{topic}' if topic else '', f"slot:{it['slot']}" if it.get('slot') else '', 'src:x'] if t)
    else:
        # 社区：source 字段是 github/hf/hn
        kind=it.get('source') or src
        sid=normalize_sig_id(kind, raw)
        author=it.get('author') or ''
        topic=(it.get('tags') or ['community'])[0] if isinstance(it.get('tags'),list) else (it.get('topic') or kind)
        url=it.get('url') or it.get('discuss') or ''
        tags=','.join(t for t in [f'topic:{topic}' if topic else '', f'src:{kind}', f"pick:{it['pick']}" if it.get('pick') else ''] if t)
    return (f' data-sig-id="{_e(sid)}" data-sig-url="{_e(url)}" data-sig-title="{_e(it.get("title",""))}"'
            f' data-sig-author="{_e(author)}" data-sig-topic="{_e(topic)}" data-sig-tags="{_e(tags)}"')

SRC_LABEL={'x':'X','github':'GitHub','hf':'Hugging Face','hn':'Hacker News'}
CJK_RE=re.compile(r'[\u4e00-\u9fff]')
def check_zh_summaries(day):
    """社区条目简介须含至少一个汉字。返回错误列表。"""
    return [f'社区简介非中文：{it.get("id") or it.get("title")}' for g in day['groups'] if g['key']!='x' for it in g['items'] if not CJK_RE.search(it.get('summary') or '')]

def load_day_items(date, root='.'):
    """合并 X + 社区精选。返回 {groups:[{key,label,items}], all:[...], log:str}。"""
    groups=[]; log=[]
    xp=os.path.join(root,f'items-{date}.json')
    x_items=[]
    if os.path.exists(xp):
        x_items=json.load(open(xp))['items']
        for it in x_items: it.setdefault('sig_source','x'); it.setdefault('_group','x')
        groups.append({'key':'x','label':SRC_LABEL['x'],'items':x_items})
    else:
        log.append(f'[load_day_items] 缺 {xp}')
    pp=os.path.join(root,f'items-public-{date}.json')
    if os.path.exists(pp):
        pub=json.load(open(pp))['items']
        by={}
        miss=[]
        for it in pub:
            # 社区简介一律中文：有 summary_zh 用之（英文原文留在 summary_en），标题/仓库名不翻
            zh=(it.get('summary_zh') or '').strip()
            if zh:
                it.setdefault('summary_en',it.get('summary',''));it['summary']=zh
            else: miss.append(it.get('id') or it.get('title'))
            k=(it.get('source') or 'community').lower()
            it.setdefault('sig_source',k); it.setdefault('_group',k)
            by.setdefault(k,[]).append(it)
        for k in ('github','hf','hn'):
            if k in by: groups.append({'key':k,'label':SRC_LABEL.get(k,k),'items':by.pop(k)})
        for k,v in by.items(): groups.append({'key':k,'label':k,'items':v})
        if miss and date>='2026-10-27':
            raise SystemExit(f'[load_day_items] 需要中文简介：{pp} 有 {len(miss)} 条社区条目缺 summary_zh：{miss}')
        log.append(f'[load_day_items] 合并社区精选 {sum(len(g["items"]) for g in groups if g["key"]!="x")} 条')
    else:
        log.append(f'[load_day_items] 缺 {pp}，只建 X 部分')
        print(log[-1], file=sys.stderr)
    all_items=[it for g in groups for it in g['items']]
    return {'groups':groups,'all':all_items,'log':'\n'.join(log)}

OVERRIDE='''<style id="dd-sig-mobile">
/* news-signal 按钮：手机端 ≥44px、不遮挡、可点；短评 .dd-note 样式由脚本自带，此处不重复 */
body .dd-sig{flex-wrap:wrap;gap:8px;margin-top:10px;position:relative;z-index:2}
body .dd-sig button{min-width:44px;min-height:44px;box-sizing:border-box;touch-action:manipulation;font-size:16px}
</style>'''
# 短评已启用：SIG_PATH 现读内联；点赞/踩后可选 comment（meta.note≤200，meta.vote=like|dislike）。
EMBED_NOTE='<!-- news-signal: 叼报互动。短评已启用 action=comment / meta.note≤200 / meta.vote=like|dislike（勿改 daily-portal 脚本；embed 现读）。门户链接 https://daily.jidadiao.fun/go/x/YYYY-MM-DD ；github.io 作备份。 -->'

def embed_signal(html,date,source='news'):
    if 'id="dd-news-signal"' in html: return html
    js=open(SIG_PATH).read()
    js=re.sub(r'</(script)',r'<\/\1',js,flags=re.I)
    tag=f'{EMBED_NOTE}\n{OVERRIDE}\n<script id="dd-news-signal" data-date="{date}" data-source="{source}">\n{js}\n</script>\n'
    i=html.lower().rfind('</body>'); assert i>0,'页面缺 </body>'
    return html[:i]+tag+html[i:]

def check_signal(html,n_items=None):
    errs=[]
    if 'id="dd-news-signal"' not in html or 'news-signal.js' not in html: errs.append('缺少内联 news-signal 脚本')
    body=html.split('<script id="dd-news-signal"')[0]
    ids=re.findall(r'data-sig-id="([^"]*)"',body)
    bad=[x for x in ids if not re.fullmatch(r'(?:x|gh|hf|hn|ld|reddit):[A-Za-z0-9._:/\-@#+]{1,199}',x)]
    if bad: errs.append(f'data-sig-id 格式不对：{bad[:3]}')
    if len(set(ids))!=len(ids): errs.append('data-sig-id 有重复')
    for a in ('data-sig-url','data-sig-title'):
        if body.count(a+'="')<len(ids): errs.append(f'有条目缺 {a}')
    if n_items is not None and len(ids)!=n_items: errs.append(f'条目 {n_items} 条，但 data-sig-id 只有 {len(ids)} 个')
    return errs

if __name__=='__main__':
    # 单测 normalize_sig_id
    cases=[
        ('x','2114362163678859330','x:2114362163678859330'),
        ('github','github:new/DenisSergeevitch/ex-ussr-kinship-research','gh:repo/DenisSergeevitch/ex-ussr-kinship-research'),
        ('github','github:trending/AgriciDaniel/claude-seo','gh:repo/AgriciDaniel/claude-seo'),
        ('hf','hf:model/deepseek-ai/DeepSeek-V4.1-Flash-1017','hf:model/deepseek-ai/DeepSeek-V4.1-Flash-1017'),
        ('hf','hf:paper/2610.04184','hf:paper/2610.04184'),
        ('hn','hn:50227041','hn:50227041'),
        ('hn','50227041','hn:50227041'),
        ('github','gh:repo/a/b','gh:repo/a/b'),
    ]
    for src,raw,want in cases:
        got=normalize_sig_id(src,raw)
        assert got==want,(src,raw,got,want)
        print('ok',src,raw,'→',got)
    print('all normalize_sig_id tests passed')
