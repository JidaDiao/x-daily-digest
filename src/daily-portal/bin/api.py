#!/usr/bin/env python3
import os, re, json, hmac, threading, subprocess, sys, datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
sys.path.insert(0, os.path.dirname(__file__))
from common import *
import prefs
PDB = prefs.connect(); PDB.close()  # ensure schema
def pdb(): return prefs.connect()
def plog(fn, *a):
    """Best-effort mirror into prefs.db; never breaks legacy endpoints."""
    try:
        c = pdb()
        try: return fn(c, *a)
        finally: c.close()
    except Exception as e: sys.stderr.write("prefs: %r\n" % (e,))
TOKEN = os.environ.get("DAILY_API_TOKEN", "")
LOCK = threading.Lock()
READ = DATA + "/read.json"
HITS = {}
ALLOWED = "https://daily.jidadiao.fun"
SIG_ORIGINS = (ALLOWED, "https://jidadiao.github.io")  # /api/signal browser path (news-signal.js on github.io pages)
BROWSER_ACTIONS = ("like", "dislike", "fav", "unfav", "read", "open", "skip", "comment")
BOT_RE = re.compile(r"bot|crawl|spider|slurp|preview|facebookexternalhit|whatsapp|telegram|discord|slack|curl|wget|python|httpx|go-http|java/|okhttp|libwww|scrapy|headless", re.I)
SH = datetime.timezone(datetime.timedelta(hours=8))
def sh_today(): return datetime.datetime.now(SH).date()
def sync_info():
    a = load(DATA + "/sync-alert.json", None); s = load(DATA + "/sync-state.json", {})
    return bool(a), {"stale": bool(a), "fails": s.get("fails", 0), "last_ok": s.get("last_ok"), "last_fail": s.get("last_fail")}
def known_dates():
    ds = {"x": set(), "design": set()}
    for f in os.listdir(SITE):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.html", f): ds["x"].add(f[:10])
    for f in os.listdir(SITE + "/design"):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.html", f): ds["design"].add(f[:10])
    return ds
def status():
    rd = load(READ, {}); fb = load(STORE, {}); gh = load(DATA + "/gh-ratings.json", {}); ds = known_dates()
    rated = {r["date"] for r in fb.values() if r.get("site") != "test" and not r.get("test") and (r.get("rating") or r.get("fav"))} | {d for d, v in gh.items() if v}
    out = {}
    for d in sorted(ds["x"] | ds["design"]):
        legacy = d < "2026-10-22" and d in rated
        out[d] = {"has_x": d in ds["x"], "has_design": d in ds["design"],
                  "x_read": bool(rd.get(d, {}).get("x")) or legacy,
                  "design_read": bool(rd.get(d, {}).get("design")) or legacy,
                  "rated": d in rated}
    return out

class H(BaseHTTPRequestHandler):
    def j(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/api/health"): return self.j(200, {"ok": True})
        if self.path.startswith("/api/status"):
            o = status(); o["stale"], o["sync"] = sync_info(); return self.j(200, o)
        if self.path.startswith("/go/"): return self.go()
        if self.path.split("?")[0] in ("/api/profile", "/api/memories", "/api/search", "/api/memory-evidence"): return self.prefs_get()
        self.j(404, {"error": "not found"})
    def cors(self):
        o = self.headers.get("Origin") or ""
        return o if o in SIG_ORIGINS[1:] else None
    def end_headers(self):
        if getattr(self, "_cors", None):
            self.send_header("Access-Control-Allow-Origin", self._cors); self.send_header("Vary", "Origin")
        super().end_headers()
    def do_OPTIONS(self):
        self._cors = self.cors() if self.path.split("?")[0] == "/api/signal" else None
        if not self._cors: return self.j(403, {"error": "origin"})
        self.send_response(204); self.send_header("Access-Control-Allow-Methods", "POST")
        self.send_header("Access-Control-Allow-Headers", "Content-Type"); self.send_header("Access-Control-Max-Age", "86400")
        self.send_header("Content-Length", "0"); self.end_headers()
    def do_POST(self):
        if self.path.startswith("/api/read"): return self.read()
        if self.path.split("?")[0] == "/api/memory": return self.mem_add()
        if self.path.split("?")[0] == "/api/signal": self._cors = self.cors(); return self.signal()
        if self.path.split("?")[0] == "/api/signals/batch": return self.signal_batch()
        if self.path.split("?")[0] == "/api/memory/invalidate": return self.mem_invalidate()
        if not self.path.startswith("/api/favorite"): return self.j(404, {"error": "not found"})
        auth = self.headers.get("Authorization", "")
        if not TOKEN or not hmac.compare_digest(auth, "Bearer " + TOKEN): return self.j(401, {"error": "auth"})
        n = self.clen()
        if n is None: return self.j(400, {"error": "content-length"})
        if n > 65536: return self.j(413, {"error": "too large"})
        try: d = json.loads(self.rfile.read(n))
        except Exception: return self.j(400, {"error": "json"})
        date = str(d.get("date", ""))
        site = str(d.get("site", "")).strip()[:100]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) or not site: return self.j(400, {"error": "date/site"})
        rating = d.get("rating")
        if rating is not None and not (isinstance(rating, int) and 1 <= rating <= 5): return self.j(400, {"error": "rating"})
        r = {"date": date, "site": site, "url": str(d.get("url") or "")[:300], "rating": rating, "fav": d.get("fav") is True,
             "ts": d.get("ts") or datetime.datetime.utcnow().isoformat() + "Z", "slug": slug(date, site)}
        for k in ("notes", "tokens", "library"):
            if k in d: r[k] = d[k]
        if site == "test": r["test"] = True
        with LOCK:
            st = load(STORE, {}); key = date + "|" + site
            st[key] = r; save(STORE, st)
            fav = qualifies(r)
            if fav: materialize(r)
            plog(prefs.design_signals, r, "api:/api/favorite")
        subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__), "build.py")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.j(200, {"ok": True, "key": key, "favorite": fav})

    def clen(self):
        v = (self.headers.get("Content-Length") or "0").strip()
        return int(v) if v.isdigit() else None
    def ip(self): return self.headers.get("X-Real-IP") or self.client_address[0]
    def is_bot(self): ua = self.headers.get("User-Agent") or ""; return not ua or bool(BOT_RE.search(ua))
    def limited(self, n=20, bucket=""):
        import time
        ip, now = bucket + self.ip(), time.time()
        with LOCK:
            if len(HITS) > 500:  # periodic cleanup of idle IPs
                for k in [k for k, v in HITS.items() if not v or now - v[-1] >= 60]: HITS.pop(k, None)
            h = [t for t in HITS.get(ip, []) if now - t < 60]
            if len(h) >= n: HITS[ip] = h; return True
            h.append(now); HITS[ip] = h; return False
    def mark(self, date, kind):
        with LOCK:
            rd = load(READ, {}); e = rd.setdefault(date, {})
            if not e.get(kind): e[kind] = datetime.datetime.utcnow().isoformat() + "Z"; save(READ, rd)
            ts = e[kind]
        plog(prefs.read_signal, date, kind, ts, "api:read")

    def read(self):
        o, ref = self.headers.get("Origin") or "", self.headers.get("Referer") or ""
        if not (o == ALLOWED or (not o and (ref == ALLOWED or ref.startswith(ALLOWED + "/")))): return self.j(403, {"error": "origin"})
        if self.is_bot(): return self.j(403, {"error": "ua"})
        if self.limited(): return self.j(429, {"error": "rate"})
        n = self.clen()
        if n is None: return self.j(400, {"error": "content-length"})
        if n > 200: return self.j(413, {"error": "too large"})
        try: d = json.loads(self.rfile.read(n) or b"{}")
        except Exception: return self.j(400, {"error": "json"})
        if not isinstance(d, dict): return self.j(400, {"error": "json"})
        date, kind = str(d.get("date", "")), str(d.get("kind", ""))
        if kind not in ("x", "design") or date not in known_dates()[kind]: return self.j(400, {"error": "unknown date/kind"})
        self.mark(date, kind)
        self.j(200, {"ok": True})

    def authed(self):
        auth = self.headers.get("Authorization", "")
        return bool(TOKEN) and hmac.compare_digest(auth, "Bearer " + TOKEN)
    def signal(self):
        tok = self.authed()
        if not tok:
            o, ref = self.headers.get("Origin") or "", self.headers.get("Referer") or ""
            if not (o in SIG_ORIGINS or (not o and any(ref.startswith(x + "/") for x in SIG_ORIGINS))): return self.j(403, {"error": "origin or bearer required"})
            if self.is_bot(): return self.j(403, {"error": "ua"})
        if self.limited(60 if tok else 30, "sig:"): return self.j(429, {"error": "rate"})
        n = self.clen()
        if n is None: return self.j(400, {"error": "content-length"})
        if n > 4096: return self.j(413, {"error": "too large"})
        try: d = json.loads(self.rfile.read(n) or b"{}")
        except Exception: return self.j(400, {"error": "json"})
        if not isinstance(d, dict): return self.j(400, {"error": "json"})
        if not tok:  # browser path: only light page interactions, server sets user/ts
            if d.get("source_type") not in ("news", "design"): return self.j(400, {"error": "source_type (browser: news|design)"})
            if d.get("action") not in BROWSER_ACTIONS: return self.j(400, {"error": "action (browser: %s)" % "|".join(BROWSER_ACTIONS)})
            d.pop("user", None); d.pop("ts", None); d.pop("dedup_key", None); d.pop("occurred_at", None)
            meta = d.get("meta") if isinstance(d.get("meta"), dict) else {}
            if d.get("action") == "comment":
                note = meta.get("note") if isinstance(meta.get("note"), str) else None
                if not note and isinstance(d.get("note"), str): note = d.get("note")
                note = (note or "").strip()
                if not note: return self.j(400, {"error": "comment needs non-empty note (meta.note or note)"})
                if len(note) > 200: return self.j(400, {"error": "note <=200 chars"})
                meta = {**meta, "note": note}
                vote = meta.get("vote")
                if vote not in (None, "like", "dislike"): return self.j(400, {"error": "meta.vote must be like|dislike"})
                d["note"] = note
            d["meta"] = {**meta, "origin": "browser"}
        try:
            c = pdb()
            try: r = prefs.add_signal(c, d)
            finally: c.close()
        except ValueError as e: return self.j(400, {"error": str(e)})
        self.j(200, {"ok": True, **r})
    def prefs_get(self):
        if not self.authed(): return self.j(401, {"error": "auth"})
        from urllib.parse import urlsplit, parse_qs
        u = urlsplit(self.path); q = {k: v[0][:200] for k, v in parse_qs(u.query).items()}
        try:
            lim = max(1, min(100, int(q.get("limit", "20"))))
            c = pdb()
            try:
                if u.path == "/api/profile":
                    dt = q.get("date")
                    if dt and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", dt): return self.j(400, {"error": "date"})
                    o = prefs.profile(c, dt, min(lim, 20))
                elif u.path == "/api/memory-evidence":
                    if not re.fullmatch(r"\d{1,9}", q.get("id", "")): return self.j(400, {"error": "id"})
                    try: o = prefs.memory_evidence(c, int(q["id"]), lim)
                    except ValueError: return self.j(404, {"error": "memory not found"})
                elif u.path == "/api/memories":
                    o = {"memories": prefs.memories(c, q.get("scope"), q.get("polarity"), q.get("q"), limit=lim)}
                else:
                    if not q.get("q"): return self.j(400, {"error": "q"})
                    o = prefs.search(c, q["q"], lim)
            finally: c.close()
        except ValueError as e: return self.j(400, {"error": str(e)})
        self.j(200, o)

    def body(self, maxn):
        n = self.clen()
        if n is None: return 400, "content-length"
        if n > maxn: return 413, "too large"
        try: d = json.loads(self.rfile.read(n) or b"{}")
        except Exception: return 400, "json"
        return 200, d
    def signal_batch(self):
        """Bearer only. {"signals":[...<=200]} each validated by prefs.add_signal; one transaction; 6 req/min."""
        if not self.authed(): return self.j(401, {"error": "auth"})
        if self.limited(6, "batch:"): return self.j(429, {"error": "rate"})
        code, d = self.body(512 * 1024)
        if code != 200: return self.j(code, {"error": d})
        sigs = d.get("signals") if isinstance(d, dict) else None
        if not isinstance(sigs, list) or not sigs: return self.j(400, {"error": "signals must be non-empty list"})
        if len(sigs) > 200: return self.j(413, {"error": "max 200 signals per batch"})
        res, errs = [], []
        try:
            c = pdb()
            try:
                for i, s in enumerate(sigs):
                    try:
                        if isinstance(s, dict) and s.get("dedup_key") is not None and not prefs.DEDUP.match(str(s["dedup_key"])):
                            raise ValueError("dedup_key must be <src>:<action>:<external_id>")
                        res.append(prefs.add_signal(c, s, commit=False))
                    except ValueError as e: errs.append({"index": i, "error": str(e)})
                if errs: c.rollback(); return self.j(400, {"error": "validation", "details": errs[:20], "accepted": 0})
                c.commit()
            finally: c.close()
        except Exception as e:
            sys.stderr.write("batch: %r\n" % (e,)); return self.j(500, {"error": "db"})
        self.j(200, {"ok": True, "inserted": sum(1 for r in res if "id" in r), "duplicate": sum(1 for r in res if r.get("duplicate"))})
    def mem_add(self):
        """Bearer. {"text", "polarity"?, "scope"?, "tags"?, "confidence"?, "key"?} -> remember() (near-duplicates merge)."""
        if not self.authed(): return self.j(401, {"error": "auth"})
        if self.limited(30, "madd:"): return self.j(429, {"error": "rate"})
        code, d = self.body(4096)
        if code != 200: return self.j(code, {"error": d})
        if not isinstance(d, dict) or not isinstance(d.get("text"), str): return self.j(400, {"error": "text"})
        cf = d.get("confidence", 0.8)
        if isinstance(cf, bool) or not isinstance(cf, (int, float)): return self.j(400, {"error": "confidence"})
        c = pdb()
        try: o = prefs.remember(c, d["text"], d.get("polarity") or "like", d.get("scope") or "topic", d.get("tags"), cf, d.get("key"), meta={"origin": "api:/api/memory"})
        except ValueError as e: return self.j(400, {"error": str(e)})
        finally: c.close()
        self.j(200, {"ok": True, **o})
    def mem_invalidate(self):
        if not self.authed(): return self.j(401, {"error": "auth"})
        if self.limited(30, "minv:"): return self.j(429, {"error": "rate"})
        code, d = self.body(2048)
        if code != 200: return self.j(code, {"error": d})
        mid = d.get("id") if isinstance(d, dict) else None
        if isinstance(mid, bool) or not isinstance(mid, int): return self.j(400, {"error": "id"})
        sb = d.get("superseded_by")
        if sb is not None and (isinstance(sb, bool) or not isinstance(sb, int)): return self.j(400, {"error": "superseded_by"})
        c = pdb()
        try: o = prefs.invalidate_memory(c, mid, str(d.get("reason") or "user")[:200], sb)
        except ValueError as e: return self.j(404, {"error": str(e)})
        finally: c.close()
        self.j(200, {"ok": True, **o})

    def go(self):
        m = re.fullmatch(r"/go/(x|design)/(\d{4}-\d{2}-\d{2})/?", self.path.split("?", 1)[0])
        if not m: return self.j(400, {"error": "bad path"})
        kind, date = m.groups()
        try: dd = datetime.date.fromisoformat(date)
        except ValueError: return self.j(400, {"error": "bad date"})
        known = date in known_dates()[kind]
        # not mirrored yet (sync lags <=30 min): still count today/yesterday, send to GitHub Pages
        if (known or 0 <= (sh_today() - dd).days <= 1) and not self.is_bot() and not self.limited(): self.mark(date, kind)
        rel = (f"{date}.html" if kind == "x" else f"design/{date}.html")
        loc = f"/{kind}/{date}.html" if known else "https://jidadiao.github.io/x-daily-digest/" + rel
        self.send_response(302); self.send_header("Location", loc); self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", "0"); self.end_headers()

if __name__ == "__main__":
    os.makedirs(DATA, exist_ok=True); os.makedirs(FAV, exist_ok=True)
    ThreadingHTTPServer(("127.0.0.1", 9090), H).serve_forever()
