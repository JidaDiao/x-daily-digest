#!/usr/bin/env python3
"""DiaoDaily 公开来源抓取器：GitHub Trending/Search、HF 模型/论文、HN、linux.do RSS、Reddit RSS、Did Codex Reset AI 快讯、白名单个人实践博客。
无账号。token 不落盘：画像读取与入库都经 SSH 在 VPS 端用 /etc/daily/api.env 执行。"""
import json, re, sys, os, html, time, datetime, random, urllib.request, urllib.parse, xml.etree.ElementTree as ET, argparse
from email.utils import parsedate_to_datetime
SH = datetime.timezone(datetime.timedelta(hours=8))
UA = "Mozilla/5.0 (X11; Linux x86_64) DiaoDaily/1.0 (+https://daily.jidadiao.fun)"
VPS, KEY = os.environ.get("DAILY_VPS") or "", os.path.expanduser("~/.ssh/vps_jidadiao")
PER_SRC, TOTAL, EXPLORE = 5, 20, 0.2
PER_SRC_CAP = {"blog": 2}  # 个人实践博客每日精选上限
HERE = os.path.dirname(os.path.abspath(__file__))
BLOG_SKIP_RE = re.compile(r"/(?:privacy|editorial-policy|about|topics)(?:/|$)", re.I)

def get(url, accept="*/*", tries=2):
    last = None
    for i in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept}), timeout=20)
            return r.read().decode("utf-8", "replace")
        except Exception as e:
            last = e
            if getattr(e, "code", 0) in (403, 404): break
            time.sleep(2 + i * 3)
    raise last

def clean(s, n=200):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or "")); s = re.sub(r"\s+", " ", s).strip()
    return s[:n]

def it(src, iid, title, url, desc="", tags=(), author="", **kw):
    return {"source": src, "id": f"{src}:{iid}", "title": clean(title, 160), "url": url, "summary": clean(desc), "tags": [t for t in tags if t], "author": author, **kw}

def gh_trending():
    h = get("https://github.com/trending?since=daily"); out = []
    for art in h.split('<article class="Box-row')[1:]:
        m = re.search(r'<h2[^>]*>\s*<a[^>]*href="/([^"]+)"', art)
        if not m: continue
        repo = m.group(1).strip(); d = re.search(r'<p class="[^"]*">(.*?)</p>', art, re.S)
        lang = re.search(r'itemprop="programmingLanguage">([^<]+)<', art)
        st = re.search(r'([\d,]+) stars today', art)
        out.append(it("github", "trending/" + repo, repo, "https://github.com/" + repo, d.group(1) if d else "",
                      [lang.group(1) if lang else ""], repo.split("/")[0], stars_today=int(st.group(1).replace(",", "")) if st else 0, via="trending"))
    return out

def gh_search():
    since = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    q = urllib.parse.quote(f"created:>{since} stars:>50")
    d = json.loads(get(f"https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page=30", "application/vnd.github+json"))
    return [it("github", "new/" + r["full_name"], r["full_name"], r["html_url"], r.get("description") or "",
               [r.get("language") or ""] + r.get("topics", [])[:6], r["owner"]["login"], stars=r["stargazers_count"], via="search-new")
            for r in d.get("items", [])]

def hf():
    out = []
    for m in json.loads(get("https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=30")):
        out.append(it("hf", "model/" + m["id"], m["id"], "https://huggingface.co/" + m["id"], m.get("pipeline_tag") or "",
                      [m.get("pipeline_tag") or "", m.get("library_name") or ""] + [t for t in m.get("tags", []) if ":" not in t][:5],
                      m["id"].split("/")[0], likes=m.get("likes", 0), via="trending-model"))
    try:
        for p in json.loads(get("https://huggingface.co/api/daily_papers?limit=20")):
            pp = p.get("paper", p); pid = pp.get("id")
            out.append(it("hf", "paper/" + pid, pp.get("title", ""), "https://huggingface.co/papers/" + pid, pp.get("summary", ""),
                          ["paper"] + (pp.get("ai_keywords") or [])[:5], "", upvotes=pp.get("upvotes", 0), via="daily-paper"))
    except Exception as e: print("hf papers fail:", e, file=sys.stderr)
    return out

def hn():
    d = json.loads(get("https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=40"))
    return [it("hn", h["objectID"], h.get("title", ""), h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}", "",
               ["hn"], h.get("author", ""), points=h.get("points", 0), comments=h.get("num_comments", 0),
               discuss=f"https://news.ycombinator.com/item?id={h['objectID']}") for h in d.get("hits", [])]

def rss(src, url, idf):
    x = get(url, "application/rss+xml, application/atom+xml, application/xml")
    if x.lstrip().startswith("<!DOCTYPE html") or "<html" in x[:300].lower(): raise RuntimeError("got HTML (blocked/challenge)")
    root = ET.fromstring(x); ns = {"a": "http://www.w3.org/2005/Atom"}; out = []
    for e in root.iter("item"):
        link = (e.findtext("link") or "").strip()
        out.append(it(src, idf(link), e.findtext("title") or "", link, e.findtext("description") or "", [e.findtext("category") or ""], e.findtext("{http://purl.org/dc/elements/1.1/}creator") or ""))
    for e in root.findall("a:entry", ns):
        l = e.find("a:link", ns); link = l.get("href") if l is not None else ""
        cat = e.find("a:category", ns)
        out.append(it(src, idf(link), e.findtext("a:title", "", ns), link, e.findtext("a:content", "", ns), [cat.get("term") if cat is not None else ""], (e.findtext("a:author/a:name", "", ns) or "").lstrip("/u/")))
    return out

def linuxdo():
    out = []
    for u in ("https://linux.do/top.rss?period=daily", "https://linux.do/latest.rss"):
        try: out += rss("linuxdo", u, lambda l: (re.search(r"/t/(?:[^/]+/)?(\d+)", l) or re.search(r"(\d+)", l)).group(1))
        except Exception as e: print("linuxdo", u, "fail:", e, file=sys.stderr)
        if out: break
    if not out: raise RuntimeError("linux.do RSS 不可用（多为 Cloudflare 挑战）")
    return out

def reddit(subs=("LocalLLaMA", "ClaudeAI", "selfhosted", "programming")):
    out, errs = [], []
    for s in subs:
        try: out += rss("reddit", f"https://www.reddit.com/r/{s}/top/.rss?t=day&limit=10", lambda l: (re.search(r"/comments/([a-z0-9]+)", l) or re.search(r"(.+)", l)).group(1))
        except Exception as e: errs.append(f"{s}:{getattr(e,'code',e)}")
        time.sleep(3)
    if not out: raise RuntimeError("全部失败 " + ",".join(errs))
    return out

def dcr():
    """Did Codex Reset · AI 快讯（中文 RSS）。专用解析：多 category、剥「显示语言」。"""
    url = "https://didcodexreset.com/rss/news.xml?lang=zh-CN"
    x = get(url, "application/rss+xml, application/atom+xml, application/xml")
    if x.lstrip().startswith("<!DOCTYPE html") or "<html" in x[:300].lower():
        raise RuntimeError("got HTML (blocked/challenge)")
    root = ET.fromstring(x); out = []
    for e in root.iter("item"):
        link = (e.findtext("link") or "").strip()
        guid = (e.findtext("guid") or "").strip()
        m = re.search(r":news:([0-9a-f]+)$", guid, re.I) or re.search(r"/news/([0-9a-f]+)\.html", link, re.I)
        if not m: continue
        desc = e.findtext("description") or ""
        desc = re.sub(r"\s*显示语言:\s*\S+\s*$", "", desc).strip()
        cats = [c.text.strip() for c in e.findall("category") if (c.text or "").strip()]
        pub = (e.findtext("pubDate") or "").strip()
        kw = {"via": "rss"}
        if pub: kw["published_at"] = pub
        out.append(it("dcr", m.group(1).lower(), e.findtext("title") or "", link, desc, cats, "", **kw))
    if not out: raise RuntimeError("dcr RSS empty")
    return out


def _blog_feeds():
    path = os.path.join(HERE, "feeds-blog.json")
    doc = json.load(open(path, encoding="utf-8"))
    feeds = doc.get("feeds") or []
    if not feeds: raise RuntimeError("feeds-blog.json empty")
    return feeds

ATOM = "{http://www.w3.org/2005/Atom}"
CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}"
BLOG_WINDOW_DAYS = 180
BLOG_PER_SITE = 1
THINK_RE = re.compile(r"结论|取舍|反思|教训|复盘|思考|为什么|权衡|代价|边界|踩坑|经验|总结|我认为|我觉得|回顾|误区|本质|trade-?off|lesson|retro", re.I)
LISTICLE_RE = re.compile(r"周刊|weekly|第\s*\d+\s*期|\bvol\.?\s*\d+|合集|盘点|汇总|清单|\d+\s*(?:个|款|条)(?:工具|网站|推荐)|top\s*\d+|教程|入门|安装指南", re.I)

TUTORIAL_RE = re.compile(r"指南|教程|入门|步骤|怎么做|如何|一文搞懂|一文读懂|手把手|清单|攻略|速查|cheatsheet|how to|guide", re.I)
REFLECT_RE = re.compile(r"取舍|反思|教训|复盘|权衡|代价|边界|本质|误区|为什么|我认为|我觉得|思考|trade-?off|lesson", re.I)
BLOG_FETCH_TOP, BLOG_FETCH_MIN, BLOG_FETCH_SLEEP = 3, 1500, 1.0

def _article_text(url):
    """抓原文页面正文（article/main 优先），超时 15s；失败返回空串。"""
    try: h = get(url, "text/html", tries=1)
    except Exception: return ""
    h = re.sub(r"(?is)<(script|style|nav|header|footer|aside)[^>]*>.*?</\1>", " ", h)
    m = re.search(r"(?is)<article[^>]*>(.*)</article>", h) or re.search(r"(?is)<main[^>]*>(.*)</main>", h)
    return m.group(1) if m else h

def _blog_seen():
    """已推过的 blog URL（读 /workspace/digests/items-public-*.json 历史，跨天去重）。"""
    import glob
    seen = set(); today = datetime.datetime.now(SH).date().isoformat()
    for f in glob.glob("/workspace/digests/items-public-*.json"):
        if today in f: continue
        try:
            for i in json.load(open(f)).get("items", []):
                if i.get("source") == "blog": seen.add(i.get("url", "").rstrip("/"))
        except Exception: pass
    return seen

def _parse_dt(v):
    v = (v or "").strip()
    if not v: return None
    try: d = parsedate_to_datetime(v)
    except (TypeError, ValueError, IndexError):
        try: d = datetime.datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError: return None
    return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)

def think_score(title, body, recent_n=0):
    """思考深度粗筛（0~约 8）：篇幅、第一人称、结论/取舍/反思词加分；数字/截图小加分；listicle/周刊/高频扣分。"""
    t = clean(body, 100000); n = len(t); s, why = 0.0, []
    if n >= 3000: s += 2; why.append("long")
    elif n >= 1200: s += 1; why.append("mid")
    fp = len(re.findall(r"我|\bI\b|\bmy\b", t)) / max(n / 1000, 1)
    if fp >= 3: s += 1.5; why.append("1st-person")
    elif fp >= 1: s += 0.5
    k = len(set(m.lower() for m in THINK_RE.findall(title + " " + t)))
    s += min(k, 6) * 0.5; why += ["think%d" % k] if k else []
    if re.search(r"\d+(?:\.\d+)?\s*(?:%|倍|ms|GB|MB|分钟|小时|美元|\$)", t): s += 0.5; why.append("numbers")
    if re.search(r"<img|截图", body or ""): s += 0.3
    if LISTICLE_RE.search(title): s -= 3; why.append("listicle")
    head = title + " " + t[:300]
    if TUTORIAL_RE.search(head):
        r = len(set(m.lower() for m in REFLECT_RE.findall(title + " " + t)))
        if r < 3: s -= 2.5; why.append("tutorial")
        else: s -= 0.5; why.append("tutorial-soft")
    if REFLECT_RE.search(title): s += 1; why.append("reflect-title")
    if recent_n > 30: s -= 2; why.append("high-freq")
    return round(s, 2), why

def _blog_entries(root):
    """统一 RSS <item> 与 Atom <entry> → (title, link, desc, body, pub, cats)。"""
    if root.tag == ATOM + "feed" or root.tag.endswith("}feed") or root.tag == "feed":
        ns = ATOM if root.tag.startswith(ATOM) else ""
        for e in root.iter(ns + "entry"):
            link = ""
            for l in e.findall(ns + "link"):
                if l.get("rel", "alternate") == "alternate": link = l.get("href", ""); break
            body = e.findtext(ns + "content") or ""; desc = e.findtext(ns + "summary") or body
            cats = [c.get("term", "") for c in e.findall(ns + "category")]
            yield (e.findtext(ns + "title") or "", link.strip(), desc, body or desc,
                   e.findtext(ns + "published") or e.findtext(ns + "updated") or "", cats)
    else:
        for e in root.iter("item"):
            desc = e.findtext("description") or ""; body = e.findtext(CONTENT_NS + "encoded") or desc
            cats = [(c.text or "").strip() for c in e.findall("category")]
            yield (e.findtext("title") or "", (e.findtext("link") or "").strip(), desc, body, e.findtext("pubDate") or "", cats)

def blog(debug=False):
    """白名单个人博客 RSS/Atom。每站可配 include/exclude 路径；近 180 天；每站只留思考分最高的 1 篇（跨天去重）。"""
    out, errs, report = [], [], []
    seen = _blog_seen(); cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=BLOG_WINDOW_DAYS)
    for feed in _blog_feeds():
        fid = (feed.get("id") or "").strip()
        name = (feed.get("name") or fid).strip() or "blog"
        rss_url = (feed.get("rss") or "").strip()
        inc = feed.get("include_paths") or ([feed["post_path_must_include"]] if feed.get("post_path_must_include") else [])
        exc = feed.get("exclude_paths") or []
        base_tags = [t for t in (feed.get("topics") or []) if t]
        if not fid or not rss_url:
            errs.append(f"{fid or '?'}:bad-config"); continue
        try:
            x = get(rss_url, "application/rss+xml, application/atom+xml, application/xml")
            if x.lstrip().startswith("<!DOCTYPE html") or "<html" in x[:300].lower():
                raise RuntimeError("got HTML (blocked/challenge)")
            root = ET.fromstring(x.lstrip("\ufeff").strip())
            ents = list(_blog_entries(root)); cands = []
            recent_n = sum(1 for e in ents if (_parse_dt(e[4]) or cutoff) > cutoff)
            for idx, (title, link, desc, body, pub, cats) in enumerate(ents):
                if not link: continue
                path = urllib.parse.urlsplit(link).path or "/"
                if inc and not any(p in path for p in inc): continue
                if any(p in path for p in exc) or BLOG_SKIP_RE.search(path): continue
                if path.rstrip("/") in ("", "/") and "?" not in link: continue
                dt = _parse_dt(pub)
                if dt and dt < cutoff: continue
                m = re.search(r"/posts/([^/]+)/?", path)
                slug = (m.group(1) if m else (path.strip("/").replace("/", "-") or urllib.parse.urlsplit(link).query))[:120]
                if not slug: continue
                fetched = False
                if idx < BLOG_FETCH_TOP and len(clean(body, 100000)) < BLOG_FETCH_MIN and link.rstrip("/") not in seen:
                    page = _article_text(link); time.sleep(BLOG_FETCH_SLEEP)
                    if len(clean(page, 100000)) > len(clean(body, 100000)): body, fetched = page, True
                ts, twhy = think_score(title, body, recent_n)
                if fetched: twhy = twhy + ["fulltext"]
                kw = {"via": "rss", "site": name, "think_score": ts, "think_why": twhy}
                if dt: kw["published_at"] = dt.isoformat()
                elif pub: kw["published_at"] = pub
                tags = list(dict.fromkeys(base_tags + [c for c in cats if c]))[:8]
                cands.append((link.rstrip("/") in seen, it("blog", f"{fid}/{slug}", title, link, desc, tags, name, **kw)))
            if not cands:
                errs.append(f"{fid}:no-posts"); report.append({"site": fid, "latest": None}); continue
            fresh = [c for d, c in cands if not d]
            best = max(fresh, key=lambda i: i["think_score"]) if fresh else None
            if best: out.extend([best][:BLOG_PER_SITE])
            report.append({"site": fid, "fetched": len(cands), "recent_180d": recent_n,
                           "latest": cands[0][1]["title"], "latest_dup": cands[0][0],
                           "pick": best and best["title"], "pick_score": best and best["think_score"], "why": best and best["think_why"],
                           "cands": sorted([(c["think_score"], c["title"][:40]) for d, c in cands if not d], reverse=True)[:5]})
        except Exception as e:
            errs.append(f"{fid}:{getattr(e,'code',e)}"); report.append({"site": fid, "error": str(e)[:120]})
    if debug: print(json.dumps({"errs": errs, "sites": report}, ensure_ascii=False, indent=1))
    if not out: raise RuntimeError("blog RSS empty " + ",".join(errs))
    return out

SOURCES = {"github": lambda: gh_trending() + gh_search(), "hf": hf, "hn": hn, "linuxdo": linuxdo, "reddit": reddit, "dcr": dcr, "blog": blog}

def ssh(cmd, stdin=None):
    import paramiko
    c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(VPS, username="root", key_filename=KEY, timeout=15)
    i, o, e = c.exec_command(cmd, timeout=90)
    if stdin is not None: i.write(stdin); i.channel.shutdown_write()
    out, err = o.read().decode(), e.read().decode(); c.close()
    return out, err

def profile():
    out, _ = ssh('. /etc/daily/api.env; curl -s -m 20 -H "Authorization: Bearer $DAILY_API_TOKEN" http://127.0.0.1:9090/api/profile')
    return json.loads(out).get("recommend", {})

def score(item, keys):
    hay = " ".join([item["title"], item["summary"], item["author"], " ".join(item["tags"])]).lower()
    s, why = 0.0, []
    for k in keys:
        kk = k["key"].lower()
        if len(kk) < 2: continue
        if (k["scope"] in ("lang", "author") and (kk in [t.lower() for t in item["tags"]] or kk == item["author"].lower())) or \
           (k["scope"] == "topic" and re.search(r"(?<![a-z0-9])" + re.escape(kk) + r"(?![a-z0-9])", hay)):
            s += k["weight"]; why.append(k["key"])
    return s, why

def popularity(i):
    v = i.get("stars_today") or i.get("points") or i.get("upvotes") or i.get("likes") or i.get("stars") or 0
    return min(v, 5000) / 5000 * 0.02

BLOG_TOTAL = 2

def select_blog(items, rec):
    """blog：think_score 主导；画像匹配只乘 0.8–1.2。每站已在 blog() 内取最优，这里跨站取前 BLOG_TOTAL。"""
    ex, xp = rec.get("exploit", []), rec.get("explore", [])
    for i in items:
        s, why = score(i, ex); xs, xwhy = score(i, xp)
        f = max(0.8, min(1.2, 1 + 0.1 * (s + 0.5 * xs)))
        i["blog_rank"] = round(i.get("think_score", 0) * f, 2); i["match"] = why or xwhy
    best = {}
    for i in items:
        k = i.get("site") or i["id"]
        if k not in best or i["blog_rank"] > best[k]["blog_rank"]: best[k] = i
    out = sorted(best.values(), key=lambda i: -i["blog_rank"])[:BLOG_TOTAL]
    for i in out: i["pick"] = "exploit"
    return out

def select(by_src, rec):
    by_src = dict(by_src); blogs = select_blog(by_src.pop("blog", []), rec)
    return blogs + _select(by_src, rec, TOTAL - len(blogs))

def _select(by_src, rec, total):
    TOTAL = total
    ex, xp = rec.get("exploit", []), rec.get("explore", [])
    n_explore = round(TOTAL * EXPLORE); cands = []
    for src, items in by_src.items():
        for i in items:
            s, why = score(i, ex); xs, xwhy = score(i, xp)
            i["_s"] = s + popularity(i); i["_x"] = xs; i["match"] = why or xwhy
            cands.append(i)
    picked, cnt = [], {}
    def src_cap(s): return PER_SRC_CAP.get(s, PER_SRC)
    def take(i, kind):
        if cnt.get(i["source"], 0) >= src_cap(i["source"]) or i in picked: return False
        i["pick"] = kind; picked.append(i); cnt[i["source"]] = cnt.get(i["source"], 0) + 1; return True
    # exploit：轮转各来源取最高分，保证来源多样
    ranked = {s: sorted(v, key=lambda i: -i["_s"]) for s, v in by_src.items()}
    goal = TOTAL - n_explore
    while sum(1 for p in picked if p["pick"] == "exploit") < goal and any(ranked.values()):
        for s in list(ranked):
            while ranked[s] and not take(ranked[s].pop(0), "exploit"):
                pass
            if sum(1 for p in picked if p["pick"] == "exploit") >= goal: break
        ranked = {s: v for s, v in ranked.items() if v and cnt.get(s, 0) < src_cap(s)}
    # explore：先命中探索兴趣，再从画像外随机补
    rest = [i for i in cands if i not in picked]
    rest.sort(key=lambda i: (-i["_x"], random.random()))
    for i in rest:
        if sum(1 for p in picked if p["pick"] == "explore") >= n_explore or len(picked) >= TOTAL: break
        if i["_x"] > 0 or i["_s"] < 0.01: take(i, "explore")
    for i in picked: i.pop("_s"); i.pop("_x")
    return picked

def push(items, date):
    sig = [{"source_type": i["source"], "action": "read", "item_id": i["id"][:200], "item_url": i["url"][:500], "title": i["title"],
            "topic": (i["match"] or [i["source"]])[0], "tags": i["tags"][:8], "author": i["author"] or None,
            "summary": i.get("summary") or None,
            "meta": {"candidate": True, "weight_factor": 0, "pick": i["pick"], "date": date, "via": i.get("via", "")},
            "dedup_key": f"{i['source']}:read:cand-{date}-{i['id'].split(':',1)[1]}"[:240]} for i in items]
    for s in sig:
        if not s["author"]: s.pop("author")
        if not s["summary"]: s.pop("summary")
        s["item_id"] = re.sub(r"[^A-Za-z0-9._:/@#+-]", "-", s["item_id"]); s["dedup_key"] = re.sub(r"\s", "-", s["dedup_key"])
    body = json.dumps({"signals": sig}, ensure_ascii=False)
    out, err = ssh('. /etc/daily/api.env; curl -s -m 30 -X POST -H "Authorization: Bearer $DAILY_API_TOKEN" -H "Content-Type: application/json" --data-binary @- http://127.0.0.1:9090/api/signals/batch', body)
    return out.strip() or err.strip()

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date"); ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--out-dir", default="/workspace/digests"); a = ap.parse_args()
    date = a.date or datetime.datetime.now(SH).date().isoformat()
    by_src, status = {}, {}
    for name, fn in SOURCES.items():
        t = time.time()
        try:
            got = fn(); seen = {}
            for i in got: seen.setdefault(i["id"], i)
            by_src[name] = list(seen.values()); status[name] = {"ok": True, "fetched": len(by_src[name])}
        except Exception as e:
            status[name] = {"ok": False, "skipped": True, "error": str(getattr(e, "code", "") or e)[:200]}
        status[name]["secs"] = round(time.time() - t, 1)
    try: rec = profile(); prof_ok = bool(rec.get("exploit"))
    except Exception as e: rec, prof_ok = {}, False; print("profile fail:", e, file=sys.stderr)
    picked = select(by_src, rec)
    for s in status: status[s]["picked"] = sum(1 for i in picked if i["source"] == s)
    doc = {"date": date, "issue": f"社区精选 {date}", "source": "公开来源抓取", "generated": datetime.datetime.now(SH).isoformat(timespec="seconds"),
           "profile_used": prof_ok, "status": status, "items": picked}
    path = os.path.join(a.out_dir, f"items-public-{date}.json")
    json.dump(doc, open(path, "w"), ensure_ascii=False, indent=1)
    res = "skipped (--no-push)" if a.no_push else (push(picked, date) if picked else "nothing")
    print(json.dumps({"file": path, "profile_used": prof_ok, "total": len(picked), "explore": sum(1 for i in picked if i["pick"] == "explore"),
                      "status": status, "vps": res}, ensure_ascii=False, indent=1))
    return 0 if any(v["ok"] for v in status.values()) else 2

if __name__ == "__main__": sys.exit(main())
