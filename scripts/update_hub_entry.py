#!/usr/bin/env python3
"""幂等更新 gh-pages 的 hub/index.html「今日推送」入口。

用法：python3 scripts/update_hub_entry.py --root <gh-pages 工作目录> [--check-live] [--min-bytes 20000]

- 叼报：扫描 <root>/YYYY-MM-DD.html；设计灵感：扫描 <root>/design/YYYY-MM-DD.html
- 各类独立取「最新且有效」的一期（文件存在、体积 >= min-bytes、含 </html>；
  加 --check-live 时还要求 https://jidadiao.github.io/x-daily-digest/... 返回 200）
- 某类没有有效页 → 保留 hub 里该类原有入口（不生成空链接，不影响另一类）
- 输出内容只由两类入口决定，重复运行无 diff。退出码：0 正常；2 有一类沿用旧入口。
"""
import argparse, html, pathlib, re, sys, urllib.request

BASE = "https://jidadiao.github.io/x-daily-digest/"
KINDS = [  # key, 子目录, 标签, 标题, 说明
    ("x", "", "叼报", "今日叼报", "精选资讯：X、GitHub、HF、HN 等"),
    ("design", "design/", "设计灵感", "今日设计灵感", "可交互演示，可打分、收藏"),
]
DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.html$")

def live_ok(url):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0 hub-entry-check"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200
    except Exception:
        return False

def valid(path, min_bytes):
    try:
        b = path.read_bytes()
    except OSError:
        return False
    return len(b) >= min_bytes and b"</html>" in b[-4096:].lower()

def pick(root, sub, min_bytes, check_live, log):
    d = root / sub
    dates = sorted((m.group(1) for p in d.glob("*.html") if (m := DATE_RE.match(p.name))), reverse=True) if d.is_dir() else []
    for dt in dates:
        if not valid(d / f"{dt}.html", min_bytes):
            log(f"  跳过 {sub}{dt}.html：本地校验不过"); continue
        if check_live and not live_ok(f"{BASE}{sub}{dt}.html"):
            log(f"  跳过 {sub}{dt}.html：线上非 200"); continue
        return dt
    return None

def old_entry(text, key, sub):
    m = re.search(rf'data-kind="{key}"[^>]*href="{re.escape(BASE)}{re.escape(sub)}(\d{{4}}-\d\d-\d\d)\.html"', text) or \
        re.search(rf'href="{re.escape(BASE)}{re.escape(sub)}(\d{{4}}-\d\d-\d\d)\.html"', text)
    return m.group(1) if m else None

CSS = """:root{--bg:#fafafa;--fg:#1d1d1f;--muted:#6e6e73;--border:#e5e5e8;--card:#fff;--primary:#0071e3}
@media(prefers-color-scheme:dark){:root{--bg:#080808;--fg:#ededed;--muted:#8e8e93;--border:#282828;--card:#111;--primary:#4ea1ff}}
*{box-sizing:border-box;margin:0}
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans SC",system-ui,sans-serif;background:var(--bg);color:var(--fg);line-height:1.55;min-height:100vh}
.wrap{max-width:720px;margin:0 auto;padding:48px 20px}
.k{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin-bottom:10px}
h1{font-size:clamp(28px,6vw,44px);font-weight:600;letter-spacing:-.03em;margin-bottom:8px}
.lead{color:var(--muted);margin-bottom:32px;font-size:15px}
.card{display:block;background:var(--card);border:1px solid var(--border);border-radius:18px;padding:20px 22px;margin-bottom:14px;text-decoration:none;color:inherit;transition:transform .2s,box-shadow .2s}
.card:hover{transform:translateY(-2px);box-shadow:0 16px 40px -28px rgba(0,0,0,.45)}
.card .tag{font-size:11px;color:var(--primary);letter-spacing:.08em;text-transform:uppercase;margin-bottom:6px}
.card .date{font-family:ui-monospace,monospace;color:var(--muted);margin-left:8px;letter-spacing:0}
.card h2{font-size:18px;font-weight:600;letter-spacing:-.02em;margin-bottom:6px}
.card p{font-size:13px;color:var(--muted)}
.card .go{margin-top:12px;font-size:13px;color:var(--primary);font-weight:500}
.card.none{opacity:.6;pointer-events:none}
footer{margin-top:40px;font-size:12px;color:var(--muted)}
footer a{color:inherit}"""

def render(entries):
    cards = []
    for key, sub, tag, title, desc in KINDS:
        dt = entries[key]
        if dt:
            cards.append(f'''  <a class="card" data-kind="{key}" data-date="{dt}" href="{BASE}{sub}{dt}.html">
    <div class="tag">{tag}<span class="date">{dt}</span></div>
    <h2>{title}</h2>
    <p>{html.escape(desc)}</p>
    <div class="go">打开 →</div>
  </a>''')
        else:
            cards.append(f'  <div class="card none" data-kind="{key}"><div class="tag">{tag}</div><h2>{title}</h2><p>暂无已发布的一期</p></div>')
    latest = max([d for d in entries.values() if d] or ["—"])
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>今日推送 · DiaoDaily 叼报</title>
<style>
{CSS}
</style>
</head>
<body>
<div class="wrap">
  <div class="k">最新一期 {latest}</div>
  <h1>今日推送</h1>
  <p class="lead">叼报和设计灵感各自指向最新已发布的一期，日期以卡片上为准。</p>

{chr(10).join(cards)}

  <footer>由「DiaoDaily 叼报」汇总 · <a href="{BASE}">叼报往期</a></footer>
</div>
</body>
</html>
'''

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--min-bytes", type=int, default=20000)
    ap.add_argument("--check-live", action="store_true")
    a = ap.parse_args(argv)
    root = pathlib.Path(a.root); hub = root / "hub/index.html"
    old = hub.read_text(encoding="utf-8") if hub.exists() else ""
    entries, kept = {}, False
    for key, sub, tag, *_ in KINDS:
        dt = pick(root, sub, a.min_bytes, a.check_live, print)
        if dt is None:
            dt = old_entry(old, key, sub); kept = True
            print(f"{tag}: 无有效新页，保留原入口 {dt}")
        else:
            print(f"{tag}: {dt}")
        entries[key] = dt
    new = render(entries)
    if new != old:
        hub.parent.mkdir(parents=True, exist_ok=True); hub.write_text(new, encoding="utf-8"); print("hub/index.html 已更新")
    else:
        print("hub/index.html 无变化")
    return 2 if kept else 0

if __name__ == "__main__":
    sys.exit(main())
