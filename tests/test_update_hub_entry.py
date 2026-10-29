#!/usr/bin/env python3
"""可重复测试：python3 tests/test_update_hub_entry.py"""
import pathlib, subprocess, sys, tempfile, re
S = pathlib.Path(__file__).resolve().parent.parent / "scripts/update_hub_entry.py"
PAGE = "<!doctype html><html><body>" + "x" * 30000 + "</body></html>"
OLD_HUB = '<a class="card" href="https://jidadiao.github.io/x-daily-digest/2026-10-24.html"></a><a class="card" href="https://jidadiao.github.io/x-daily-digest/design/2026-10-24.html"></a>'

def setup(x, d):
    r = pathlib.Path(tempfile.mkdtemp()); (r / "design").mkdir(); (r / "hub").mkdir()
    for t in x: (r / f"{t}.html").write_text(PAGE)
    for t in d: (r / "design" / f"{t}.html").write_text(PAGE)
    (r / "hub/index.html").write_text(OLD_HUB); return r

def run(r):
    p = subprocess.run([sys.executable, str(S), "--root", str(r)], capture_output=True, text=True)
    return p.returncode, (r / "hub/index.html").read_text()

def ent(h):
    return dict(re.findall(r'data-kind="(\w+)" data-date="([\d-]+)"', h))

results = []
def check(name, cond, info=""):
    results.append(cond); print(("PASS" if cond else "FAIL"), name, info)

# 1 正常发布
r = setup(["2026-10-24", "2026-10-28"], ["2026-10-24", "2026-10-28"]); c, h = run(r)
check("正常发布：两类都指向 10-28", ent(h) == {"x": "2026-10-28", "design": "2026-10-28"} and c == 0, ent(h))
# 2 两类日期不同
r = setup(["2026-10-28", "2026-10-29"], ["2026-10-28"]); c, h = run(r)
check("日期不同：叼报 10-29 / 设计 10-28", ent(h) == {"x": "2026-10-29", "design": "2026-10-28"}, ent(h))
check("日期不同：卡片显示各自日期", ">2026-10-29<" in h and ">2026-10-28<" in h)
# 3a 单类失败：设计最新一期损坏（截断）→ 回退到上一有效期
r = setup(["2026-10-29"], ["2026-10-28", "2026-10-29"]); (r / "design/2026-10-29.html").write_text("<html>半截")
c, h = run(r); check("单类损坏：设计回退 10-28，叼报照常 10-29", ent(h) == {"x": "2026-10-29", "design": "2026-10-28"}, ent(h))
# 3b 单类全无：设计目录为空 → 保留 hub 原入口 10-24，叼报正常更新
r = setup(["2026-10-29"], []); c, h = run(r)
check("单类缺失：设计保留原入口 10-24，叼报 10-29", ent(h) == {"x": "2026-10-29", "design": "2026-10-24"} and c == 2, ent(h))
check("不生成空链接", 'href=""' not in h and "None" not in h)
# 4 重复运行幂等
r = setup(["2026-10-29"], ["2026-10-28"]); run(r); _, h1 = run(r); _, h2 = run(r)
check("重复运行无 diff", h1 == h2)
print(f"{sum(results)}/{len(results)} 通过"); sys.exit(0 if all(results) else 1)
