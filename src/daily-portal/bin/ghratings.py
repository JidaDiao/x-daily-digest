#!/usr/bin/env python3
"""Refresh data/gh-ratings.json from public GitHub feedback issues (unauthenticated).
2026-10-25: newest record per (date, site) wins by record ts (fallback comment/issue created_at),
regardless of duplicate same-day issues; records newer than feedback.json are replayed into it
(backfills scores the Worker failed to forward to the VPS)."""
import json, re, urllib.request, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import DATA, STORE, save, load, slug
REPLAY_FROM = "2026-10-21"  # VPS forwarding started 2026-10-21
R = "https://api.github.com/repos/JidaDiao/x-daily-digest"
def g(u): return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "daily-portal", "Accept": "application/vnd.github+json"}), timeout=30))
try:
    latest = {}  # (date, site) -> (ts, record)
    for i in g(R + "/issues?labels=feedback&state=all&per_page=100"):
        m = re.fullmatch(r"design-feedback-(\d{4}-\d{2}-\d{2})", i["title"])
        if not m: continue
        lines = [(l, i["created_at"]) for l in ((i.get("body") or "").strip().splitlines()[-1:] or [""])]
        if i["comments"]: lines += [(c["body"], c["created_at"]) for c in g(i["comments_url"] + "?per_page=100")]
        for l, cts in lines:
            try: d = json.loads(l)
            except Exception: continue
            if not isinstance(d, dict) or d.get("site") == "test" or d.get("date") != m.group(1) or not d.get("site"): continue
            ts = str(d.get("ts") or cts)
            k = (d["date"], d["site"])
            if k not in latest or ts >= latest[k][0]: latest[k] = (ts, d)
    out = {}
    for (date, site), (ts, d) in sorted(latest.items()):
        if d.get("rating") or d.get("fav"): out.setdefault(date, {})[site] = d.get("rating")
    save(os.path.join(DATA, "gh-ratings.json"), out)
    st = load(STORE, None); n = 0
    if isinstance(st, dict):
        for (date, site), (ts, d) in latest.items():
            if date < REPLAY_FROM: continue  # older days were backfilled via library.json
            key = date + "|" + site; cur = st.get(key)
            if cur and str(cur.get("ts") or "") >= ts: continue
            r = dict(cur or {}); r.update({"date": date, "site": site, "url": str(d.get("url") or r.get("url") or "")[:300],
                  "rating": d.get("rating") if isinstance(d.get("rating"), int) else None, "fav": d.get("fav") is True,
                  "ts": ts, "slug": slug(date, site), "replayed_from_gh": True})
            st[key] = r; n += 1
        if n: save(STORE, st)
    print("gh-ratings", {k: len(v) for k, v in out.items()}, "replayed", n)
except Exception as e:
    print("gh-ratings FAIL:", e)
