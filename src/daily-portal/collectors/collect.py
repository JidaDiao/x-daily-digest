#!/usr/bin/env python3
"""DiaoDaily 公开来源抓取器：GitHub Trending/Search、HF 模型/论文、HN、linux.do RSS、Reddit RSS。
无账号。token 不落盘：画像读取与入库都经 SSH 在 VPS 端用 /etc/daily/api.env 执行。"""
import json, re, sys, os, html, time, datetime, random, urllib.request, urllib.parse, xml.etree.ElementTree as ET, argparse
SH = datetime.timezone(datetime.timedelta(hours=8))
UA = "Mozilla/5.0 (X11; Linux x86_64) DiaoDaily/1.0 (+https://daily.jidadiao.fun)"
VPS, KEY = "<VPS_HOST>", os.path.expanduser("<SSH_KEY_PATH>")
PER_SRC, TOTAL, EXPLORE = 5, 20, 0.2

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

SOURCES = {"github": lambda: gh_trending() + gh_search(), "hf": hf, "hn": hn, "linuxdo": linuxdo, "reddit": reddit}

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

def select(by_src, rec):
    ex, xp = rec.get("exploit", []), rec.get("explore", [])
    n_explore = round(TOTAL * EXPLORE); cands = []
    for src, items in by_src.items():
        for i in items:
            s, why = score(i, ex); xs, xwhy = score(i, xp)
            i["_s"] = s + popularity(i); i["_x"] = xs; i["match"] = why or xwhy
            cands.append(i)
    picked, cnt = [], {}
    def take(i, kind):
        if cnt.get(i["source"], 0) >= PER_SRC or i in picked: return False
        i["pick"] = kind; picked.append(i); cnt[i["source"]] = cnt.get(i["source"], 0) + 1; return True
    # exploit：轮转各来源取最高分，保证来源多样
    ranked = {s: sorted(v, key=lambda i: -i["_s"]) for s, v in by_src.items()}
    goal = TOTAL - n_explore
    while sum(1 for p in picked if p["pick"] == "exploit") < goal and any(ranked.values()):
        for s in list(ranked):
            while ranked[s] and not take(ranked[s].pop(0), "exploit"):
                pass
            if sum(1 for p in picked if p["pick"] == "exploit") >= goal: break
        ranked = {s: v for s, v in ranked.items() if v and cnt.get(s, 0) < PER_SRC}
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
