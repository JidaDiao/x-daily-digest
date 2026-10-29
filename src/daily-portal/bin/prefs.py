#!/usr/bin/env python3
"""DiaoDaily 叼报 · 偏好库 (bot-independent). SQLite at /srv/daily/data/prefs.db.
Stdlib only. Import as a module (add_signal/search/profile/memories/remember/derive/export)
or use the CLI: prefs.py -h.  Docs: /srv/daily/data/PREFS_API.md"""
import os, re, sys, json, math, sqlite3, argparse, datetime, hashlib

DB = os.environ.get("PREFS_DB", "/srv/daily/data/prefs.db")
DATA = "/srv/daily/data"; FAV = "/srv/daily/favorites"
SH = datetime.timezone(datetime.timedelta(hours=8))
SOURCE_TYPES = ("news", "design", "github", "chat", "manual", "hf", "hn", "reddit", "linuxdo")
ACTIONS = ("like", "dislike", "fav", "unfav", "read", "open", "rate", "skip", "star", "bookmark", "submit", "comment", "follow", "upvote")
POLARITY = ("like", "avoid", "neutral")
# signal -> preference weight (rate: value-3 => 5★=+2, 1★=-2)
W = {"like": 1.0, "dislike": -1.0, "fav": 1.5, "unfav": -1.5, "read": 0.2, "open": 0.3, "skip": -0.3,
     "star": 1.0, "bookmark": 1.5, "submit": 0.8, "comment": 0.5, "follow": 1.0, "upvote": 0.7}
DEDUP = re.compile(r"^[a-z0-9_-]{1,20}:[a-z_-]{1,20}:[^\s]{1,200}$")  # <src>:<action>:<external_id>
SCHEMA_VERSION = 3
SOURCES_YAML = os.environ.get("DAILY_SOURCES_YAML", "/srv/daily/etc/sources.yaml")
MERGE_SIM = 0.75  # mem0-style: near-duplicate manual memories (char-bigram Jaccard) merge + accumulate evidence
DEFAULT_CFG = {"half_life_by_source": {"github": 90}, "half_life_days": 14, "explore_ratio": 0.2, "avoid_after_dislikes": 3, "min_abs_score": 0.5, "user": "jidadiao"}
SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@#+\-]{0,199}$")

SIGCOLS = """
 id INTEGER PRIMARY KEY, ts TEXT NOT NULL, user TEXT NOT NULL DEFAULT 'jidadiao',
 source_type TEXT NOT NULL CHECK(source_type IN (%s)),
 item_id TEXT, item_url TEXT, title TEXT, topic TEXT, tags TEXT NOT NULL DEFAULT '[]', author TEXT,
 action TEXT NOT NULL CHECK(action IN (%s)),
 value REAL, meta TEXT NOT NULL DEFAULT '{}', dedup_key TEXT UNIQUE, occurred_at TEXT""" % (",".join(f"'{x}'" for x in SOURCE_TYPES), ",".join(f"'{x}'" for x in ACTIONS))
SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS signals(%SIGCOLS%);
CREATE TABLE IF NOT EXISTS memories(
 id INTEGER PRIMARY KEY, text TEXT NOT NULL,
 polarity TEXT NOT NULL CHECK(polarity IN ('like','avoid','neutral')),
 scope TEXT NOT NULL, key TEXT, tags TEXT NOT NULL DEFAULT '[]',
 confidence REAL NOT NULL DEFAULT 0.5, evidence_count INTEGER NOT NULL DEFAULT 0,
 first_seen TEXT, last_seen TEXT, half_life_days REAL NOT NULL DEFAULT 14,
 status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','archived')),
 source TEXT NOT NULL CHECK(source IN ('derived','manual')), score REAL, meta TEXT NOT NULL DEFAULT '{}',
 embedding BLOB, UNIQUE(source, scope, key));
CREATE TABLE IF NOT EXISTS items(
 item_id TEXT PRIMARY KEY, url TEXT, title TEXT, summary TEXT, tags TEXT NOT NULL DEFAULT '[]',
 source TEXT, date TEXT, embedding BLOB);
CREATE TABLE IF NOT EXISTS config(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS memory_evidence(memory_id INTEGER NOT NULL, signal_id INTEGER NOT NULL, weight REAL, PRIMARY KEY(memory_id, signal_id));
CREATE INDEX IF NOT EXISTS mev_sig ON memory_evidence(signal_id);
CREATE TABLE IF NOT EXISTS sources(name TEXT PRIMARY KEY, kind TEXT, account TEXT, cursor TEXT, last_sync TEXT, last_ok TEXT,
 health TEXT NOT NULL DEFAULT 'unknown' CHECK(health IN ('ok','error','not_configured','disabled','unknown')), error TEXT, meta TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS entities(id INTEGER PRIMARY KEY, name TEXT NOT NULL, aliases TEXT NOT NULL DEFAULT '[]', type TEXT NOT NULL DEFAULT 'topic',
 canonical_id TEXT, meta TEXT NOT NULL DEFAULT '{}', UNIQUE(type, name));
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(text, tags, content='memories', content_rowid='id', tokenize='trigram');
CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(title, summary, tags, content='items', content_rowid='rowid', tokenize='trigram');
CREATE TRIGGER IF NOT EXISTS m_ai AFTER INSERT ON memories BEGIN INSERT INTO memories_fts(rowid,text,tags) VALUES(new.id,new.text,new.tags); END;
CREATE TRIGGER IF NOT EXISTS m_ad AFTER DELETE ON memories BEGIN INSERT INTO memories_fts(memories_fts,rowid,text,tags) VALUES('delete',old.id,old.text,old.tags); END;
CREATE TRIGGER IF NOT EXISTS m_au AFTER UPDATE ON memories BEGIN INSERT INTO memories_fts(memories_fts,rowid,text,tags) VALUES('delete',old.id,old.text,old.tags); INSERT INTO memories_fts(rowid,text,tags) VALUES(new.id,new.text,new.tags); END;
CREATE TRIGGER IF NOT EXISTS i_ai AFTER INSERT ON items BEGIN INSERT INTO items_fts(rowid,title,summary,tags) VALUES(new.rowid,new.title,new.summary,new.tags); END;
CREATE TRIGGER IF NOT EXISTS i_ad AFTER DELETE ON items BEGIN INSERT INTO items_fts(items_fts,rowid,title,summary,tags) VALUES('delete',old.rowid,old.title,old.summary,old.tags); END;
CREATE TRIGGER IF NOT EXISTS i_au AFTER UPDATE ON items BEGIN INSERT INTO items_fts(items_fts,rowid,title,summary,tags) VALUES('delete',old.rowid,old.title,old.summary,old.tags); INSERT INTO items_fts(rowid,title,summary,tags) VALUES(new.rowid,new.title,new.summary,new.tags); END;
CREATE TRIGGER IF NOT EXISTS sig_noupd BEFORE UPDATE ON signals BEGIN SELECT RAISE(ABORT,'signals is append-only'); END;
""".replace("%SIGCOLS%", SIGCOLS)

def now(): return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def connect(path=None):
    c = sqlite3.connect(path or DB, timeout=10); c.row_factory = sqlite3.Row
    c.execute("PRAGMA busy_timeout=10000"); c.executescript(SCHEMA); migrate(c)
    for k, v in DEFAULT_CFG.items(): c.execute("INSERT OR IGNORE INTO config VALUES(?,?)", (k, json.dumps(v)))
    c.commit(); return c
def _cols(c, t): return [r[1] for r in c.execute(f"PRAGMA table_info({t})")]
def migrate(c):
    """Idempotent v1->v2 migration. Rebuilds signals only if CHECK lists/occurred_at are outdated (ids preserved)."""
    sql = c.execute("SELECT sql FROM sqlite_master WHERE name='signals'").fetchone()[0]
    if "occurred_at" not in sql or "'linuxdo'" not in sql or "'upvote'" not in sql:
        n0 = c.execute("SELECT count(*) FROM signals").fetchone()[0]
        has_occ = "occurred_at" in _cols(c, "signals")
        c.execute("BEGIN IMMEDIATE")
        try:
            c.execute("DROP TRIGGER IF EXISTS sig_noupd")
            c.execute(f"CREATE TABLE signals_v2({SIGCOLS})")
            cols = "id,ts,user,source_type,item_id,item_url,title,topic,tags,author,action,value,meta,dedup_key"
            c.execute(f"INSERT INTO signals_v2({cols},occurred_at) SELECT {cols},{'coalesce(occurred_at,ts)' if has_occ else 'ts'} FROM signals")
            c.execute("DROP TABLE signals"); c.execute("ALTER TABLE signals_v2 RENAME TO signals")
            if c.execute("SELECT count(*) FROM signals").fetchone()[0] != n0: raise RuntimeError("migration row count mismatch")
            c.execute("COMMIT")
        except Exception:
            c.execute("ROLLBACK"); raise
    mc = _cols(c, "memories")
    for col in ("valid_from TEXT", "invalid_at TEXT", "supersedes_id INTEGER"):
        if col.split()[0] not in mc: c.execute(f"ALTER TABLE memories ADD COLUMN {col}")
    c.execute("UPDATE memories SET valid_from=coalesce(first_seen,last_seen) WHERE valid_from IS NULL")
    c.executescript("""CREATE INDEX IF NOT EXISTS sig_ts ON signals(ts); CREATE INDEX IF NOT EXISTS sig_item ON signals(item_id);
      CREATE INDEX IF NOT EXISTS sig_occ ON signals(occurred_at); CREATE INDEX IF NOT EXISTS sig_src ON signals(source_type, action);
      CREATE TRIGGER IF NOT EXISTS sig_noupd BEFORE UPDATE ON signals BEGIN SELECT RAISE(ABORT,'signals is append-only'); END;""")
    c.execute("INSERT OR REPLACE INTO config VALUES('schema_version',?)", (json.dumps(SCHEMA_VERSION),)); c.commit()
def load_sources_yaml(path=None):
    """Glance-style YAML source config (no secrets). Missing file / no PyYAML -> {}."""
    try:
        import yaml
        with open(path or SOURCES_YAML, encoding="utf-8") as f: return yaml.safe_load(f) or {}
    except (OSError, ImportError): return {}
    except Exception as e: sys.stderr.write("sources.yaml: %r\n" % (e,)); return {}
def cfg(c):
    """config table, overlaid by sources.yaml: prefs.* keys and signals.<source>.half_life_days."""
    o = {r["k"]: json.loads(r["v"]) for r in c.execute("SELECT k,v FROM config")}
    y = load_sources_yaml()
    for k, v in (y.get("prefs") or {}).items():
        if k in DEFAULT_CFG: o[k] = v
    hb = dict(o.get("half_life_by_source") or {})
    for src, sc in (y.get("signals") or {}).items():
        if isinstance(sc, dict) and sc.get("half_life_days"): hb[src] = float(sc["half_life_days"])
    o["half_life_by_source"] = hb
    return o
def hl_for(cf, src): return float((cf.get("half_life_by_source") or {}).get(src) or cf["half_life_days"])
def _s(v, n): return None if v is None else str(v).strip()[:n] or None
def _tags(t):
    if t is None: return []
    if isinstance(t, str): t = [x for x in re.split(r"[,，\s]+", t) if x]
    if not isinstance(t, list): raise ValueError("tags must be list")
    return [str(x).strip()[:40] for x in t if str(x).strip()][:20]
def _ts(v):
    if not v: return now()
    v = str(v)[:40]
    try: datetime.datetime.fromisoformat(v.replace("Z", "+00:00")); return v
    except ValueError: raise ValueError("ts must be ISO-8601")
def _parse_ts(v):
    d = datetime.datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)

def add_signal(c, d, dedup_key=None, commit=True):
    """Validate + append one signal. Returns {'id':..} or {'duplicate':True}. Raises ValueError."""
    if not isinstance(d, dict): raise ValueError("body must be object")
    st, act = d.get("source_type"), d.get("action")
    if st not in SOURCE_TYPES: raise ValueError("source_type")
    if act not in ACTIONS: raise ValueError("action")
    iid = _s(d.get("item_id"), 200)
    if iid and not SLUG.match(iid): raise ValueError("item_id must be slug-like [A-Za-z0-9._:/@#+-]")
    url = _s(d.get("item_url"), 500)
    if url and not re.match(r"^https?://", url): raise ValueError("item_url must be http(s)")
    val = d.get("value")
    if val is not None:
        if isinstance(val, bool) or not isinstance(val, (int, float)) or not -100 <= val <= 100: raise ValueError("value")
    if act == "rate" and (val is None or not 1 <= val <= 5): raise ValueError("rate needs value 1-5")
    meta = d.get("meta") or {}
    if not isinstance(meta, dict) or len(json.dumps(meta)) > 2000: raise ValueError("meta must be object <=2KB")
    if act == "comment":
        note = meta.get("note") if isinstance(meta.get("note"), str) else None
        if not note and isinstance(d.get("note"), str): note = d["note"]
        note = (note or "").strip()
        if not note: raise ValueError("comment needs non-empty note (meta.note or note)")
        if len(note) > 200: raise ValueError("note <=200 chars")
        meta = {**meta, "note": note}
        if meta.get("vote") not in (None, "like", "dislike"): raise ValueError("meta.vote must be like|dislike")
    wf = meta.get("weight_factor")
    if wf is not None and (isinstance(wf, bool) or not isinstance(wf, (int, float)) or not 0 <= wf <= 2): raise ValueError("meta.weight_factor 0-2")
    dedup_key = dedup_key or d.get("dedup_key")
    if dedup_key is not None and (not isinstance(dedup_key, str) or len(dedup_key) > 250): raise ValueError("dedup_key")
    ts = _ts(d.get("ts")); occ = _ts(d.get("occurred_at")) if d.get("occurred_at") else ts
    row = (ts, _s(d.get("user"), 40) or "jidadiao", st, iid, url, _s(d.get("title"), 300), _s(d.get("topic"), 80),
           json.dumps(_tags(d.get("tags")), ensure_ascii=False), _s(d.get("author"), 120), act, val, json.dumps(meta, ensure_ascii=False), dedup_key, occ)
    cur = c.execute("INSERT OR IGNORE INTO signals(ts,user,source_type,item_id,item_url,title,topic,tags,author,action,value,meta,dedup_key,occurred_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", row)
    if commit: c.commit()
    return {"id": cur.lastrowid} if cur.rowcount else {"duplicate": True}

def upsert_item(c, item_id, url=None, title=None, summary=None, tags=None, source=None, date=None, commit=True):
    c.execute("""INSERT INTO items(item_id,url,title,summary,tags,source,date) VALUES(?,?,?,?,?,?,?)
      ON CONFLICT(item_id) DO UPDATE SET url=coalesce(excluded.url,url), title=coalesce(excluded.title,title),
      summary=coalesce(excluded.summary,summary), tags=CASE WHEN excluded.tags='[]' THEN tags ELSE excluded.tags END,
      source=coalesce(excluded.source,source), date=coalesce(excluded.date,date)""",
      (item_id, _s(url, 500), _s(title, 300), _s(summary, 2000), json.dumps(_tags(tags), ensure_ascii=False), source, date))
    if commit: c.commit()

def remember(c, text, polarity="like", scope="topic", tags=None, confidence=0.8, key=None, half_life_days=None, meta=None):
    """Manual memory (user-stated preference). Upserts by (manual, scope, key|text-hash)."""
    text = _s(text, 300)
    if not text: raise ValueError("text")
    if polarity not in POLARITY: raise ValueError("polarity")
    scope = _s(scope, 40) or "topic"
    key = _s(key, 120) or "h:" + hashlib.sha1(text.encode()).hexdigest()[:12]
    t = now(); hl = half_life_days or 3650  # manual memories barely decay
    old = c.execute("SELECT id,polarity FROM memories WHERE source='manual' AND scope=? AND key=?", (scope, key)).fetchone()
    if not old:
        sim = similar_memory(c, text, scope)
        if sim and sim[1] >= MERGE_SIM:
            m = sim[0]
            if m["polarity"] == polarity:  # same fact restated: merge, accumulate evidence, keep longer wording
                tg = sorted(set(json.loads(m["tags"])) | set(_tags(tags)))[:20]
                mt = json.loads(m["meta"] or "{}"); mt["merged"] = (mt.get("merged") or [])[-9:] + [text]
                c.execute("""UPDATE memories SET evidence_count=evidence_count+1, last_seen=?, confidence=max(confidence,?), tags=?, meta=?,
                  text=CASE WHEN length(?)>length(text) THEN ? ELSE text END WHERE id=?""",
                  (t, max(0, min(1, float(confidence))), json.dumps(tg, ensure_ascii=False), json.dumps(mt, ensure_ascii=False), text, text, m["id"]))
                c.commit()
                r = dict(c.execute("SELECT id,text,polarity,scope,key,supersedes_id,evidence_count FROM memories WHERE id=?", (m["id"],)).fetchone())
                return {**r, "merged_into": m["id"], "similarity": round(sim[1], 3)}
            old = m; key = m["key"]  # same fact, opposite polarity -> supersede below (Graphiti-style validity)
    sup = None
    if old and old["polarity"] != polarity:  # opinion flipped: keep history, new row supersedes old
        _retire(c, old["id"], t, "superseded: polarity %s->%s" % (old["polarity"], polarity)); sup = old["id"]
    c.execute("""INSERT INTO memories(text,polarity,scope,key,tags,confidence,evidence_count,first_seen,last_seen,half_life_days,status,source,meta,valid_from,supersedes_id)
      VALUES(?,?,?,?,?,?,1,?,?,?,'active','manual',?,?,?) ON CONFLICT(source,scope,key) DO UPDATE SET text=excluded.text,
      polarity=excluded.polarity, tags=excluded.tags, confidence=excluded.confidence, last_seen=excluded.last_seen, status='active', meta=excluded.meta""",
      (text, polarity, scope, key, json.dumps(_tags(tags), ensure_ascii=False), max(0, min(1, float(confidence))), t, t, hl, json.dumps(meta or {}, ensure_ascii=False), t, sup))
    if sup: c.execute("UPDATE memories SET meta=json_set(meta,'$.superseded_by',(SELECT id FROM memories WHERE source='manual' AND scope=? AND key=?)) WHERE id=?", (scope, key, sup))
    c.commit()
    c.commit()
    return dict(c.execute("SELECT id,text,polarity,scope,key,supersedes_id FROM memories WHERE source='manual' AND scope=? AND key=?", (scope, key)).fetchone())
add_memory = remember  # MCP name alias

def _grams(s):
    s = re.sub(r"[\W_]+", "", (s or "").lower())
    return {s[i:i + 2] for i in range(len(s) - 1)} or {s}
def similarity(a, b):
    A, B = _grams(a), _grams(b)
    return len(A & B) / len(A | B) if A and B else 0.0
def similar_memory(c, text, scope, source="manual"):
    """Best active memory of same scope/source by char-bigram Jaccard -> (row, sim) or None."""
    best = None
    for m in c.execute("SELECT * FROM memories WHERE source=? AND scope=? AND status='active' AND invalid_at IS NULL", (source, scope)):
        s_ = similarity(text, m["text"])
        if not best or s_ > best[1]: best = (m, s_)
    return best
def dedupe_memories(c, dry_run=False):
    """One-off merge of existing near-duplicate active manual memories (keeps oldest id, sums evidence)."""
    rows = c.execute("SELECT * FROM memories WHERE source='manual' AND status='active' AND invalid_at IS NULL ORDER BY id").fetchall()
    gone, pairs, t = set(), [], now()
    for i, a in enumerate(rows):
        if a["id"] in gone: continue
        for b in rows[i + 1:]:
            if b["id"] in gone or b["scope"] != a["scope"] or b["polarity"] != a["polarity"]: continue
            s_ = similarity(a["text"], b["text"])
            if s_ >= MERGE_SIM:
                pairs.append({"keep": a["id"], "merged": b["id"], "sim": round(s_, 3)}); gone.add(b["id"])
                if not dry_run:
                    c.execute("UPDATE memories SET evidence_count=evidence_count+?, last_seen=max(coalesce(last_seen,''),?) WHERE id=?", (b["evidence_count"], b["last_seen"] or "", a["id"]))
                    _retire(c, b["id"], t, "merged into #%d (sim %.2f)" % (a["id"], s_), "dedupe")
    if not dry_run: c.commit()
    return {"merged": pairs}

def _retire(c, mid, t, reason, by="system"):
    """Mark a memory invalid (never deleted). Its key gets '#inv:<id>' so the (source,scope,key) slot can be reused."""
    c.execute("""UPDATE memories SET invalid_at=?, status='archived', key=coalesce(key,'')||'#inv:'||id,
      meta=json_set(json_set(meta,'$.invalid_reason',?),'$.invalidated_by',?) WHERE id=? AND invalid_at IS NULL""", (t, reason[:200], by, mid))

def invalidate_memory(c, mid, reason="user", superseded_by=None):
    r = c.execute("SELECT id,invalid_at FROM memories WHERE id=?", (int(mid),)).fetchone()
    if not r: raise ValueError("memory not found")
    if r["invalid_at"]: return {"id": r["id"], "already_invalid": r["invalid_at"]}
    t = now(); _retire(c, r["id"], t, _s(reason, 200) or "user", "user")
    if superseded_by: c.execute("UPDATE memories SET supersedes_id=? WHERE id=?", (r["id"], int(superseded_by)))
    c.commit(); return {"id": r["id"], "invalid_at": t}

def memory_evidence(c, mid, limit=50):
    m = c.execute("SELECT * FROM memories WHERE id=?", (int(mid),)).fetchone()
    if not m: raise ValueError("memory not found")
    ev = [dict(r) for r in c.execute("""SELECT s.id,s.occurred_at,s.source_type,s.action,s.value,s.item_id,s.item_url,s.title,s.author,e.weight
      FROM memory_evidence e JOIN signals s ON s.id=e.signal_id WHERE e.memory_id=? ORDER BY s.occurred_at DESC LIMIT ?""", (m["id"], int(limit)))]
    return {"memory": _mem(m, True), "evidence_total": c.execute("SELECT count(*) FROM memory_evidence WHERE memory_id=?", (m["id"],)).fetchone()[0], "evidence": ev}

def source_update(c, name, **kw):
    """Connector bookkeeping (cursor/last_sync/last_ok/health/error)."""
    c.execute("INSERT OR IGNORE INTO sources(name) VALUES(?)", (name,))
    for k, v in kw.items():
        if k not in ("kind", "account", "cursor", "last_sync", "last_ok", "health", "error", "meta"): raise ValueError(k)
        c.execute(f"UPDATE sources SET {k}=? WHERE name=?", (json.dumps(v, ensure_ascii=False) if k == "meta" else v, name))
    c.commit()
def sources(c): return [dict(r) for r in c.execute("SELECT * FROM sources ORDER BY name")]

# ---------- aggregation ----------
def _weight(r):
    if r["action"] == "rate": return (r["value"] or 3) - 3
    return W.get(r["action"], 0)

def _keys(r):
    """(scope, key) buckets a signal contributes to."""
    out = []
    if r["topic"] and not r["topic"].startswith("page:"): out.append(("topic", r["topic"]))
    if r["author"]: out.append(("author" if r["source_type"] != "design" else "design", r["author"]))
    for t in json.loads(r["tags"] or "[]"):
        if t.startswith("format:"): out.append(("format", t[7:]))
        elif t.startswith("elem:"): out.append(("element", t[5:]))
        elif t.startswith("lang:"): out.append(("lang", t[5:]))
        elif t.startswith("topic:"): out.append(("topic", t[6:]))
    return out

def _cut(asof):  # exclusive upper bound covering every ts inside asof's second
    return (asof.astimezone(datetime.timezone.utc) + datetime.timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%S")

def aggregate(c, asof=None, half_life=None):
    cf = cfg(c)
    asof = asof or datetime.datetime.now(datetime.timezone.utc)
    rows = c.execute("SELECT * FROM signals WHERE coalesce(occurred_at,ts)<? ORDER BY coalesce(occurred_at,ts), id", (_cut(asof),)).fetchall()
    # newest rating per item wins (re-rating replaces, not adds)
    latest_rate = {}
    for r in rows:
        if r["action"] == "rate" and r["item_id"]: latest_rate[r["item_id"]] = r["id"]
    b, alias = {}, {}
    for r in rows:
        if r["action"] == "rate" and r["item_id"] and latest_rate[r["item_id"]] != r["id"]: continue
        meta = json.loads(r["meta"] or "{}")
        if meta.get("test"): continue
        w = _weight(r) * float(meta.get("weight_factor", 1))
        if not w: continue
        occ = r["occurred_at"] or r["ts"]
        age = max(0.0, (asof - _parse_ts(occ)).total_seconds() / 86400)
        hl = float(half_life) if half_life else hl_for(cf, r["source_type"])
        dw = w * 0.5 ** (age / hl)
        kind = (r["topic"] or "")[7:] if (r["topic"] or "").startswith("design:") else None
        for k in _keys(r):
            nk = (k[0], k[1].strip().lower())  # dedupe buckets: "React" / "react " -> one memory (first spelling kept)
            k = alias.setdefault(nk, k)
            e = b.setdefault(k, {"score": 0.0, "raw": 0.0, "n": 0, "first": occ, "last": occ, "seq": [], "ex": [], "tags": set(), "ids": [], "kinds": {}, "src": {}})
            e["src"][r["source_type"]] = e["src"].get(r["source_type"], 0) + 1
            e["score"] += dw; e["raw"] += w; e["n"] += 1; e["last"] = occ; e["seq"].append(w); e["ids"].append((r["id"], round(dw, 4)))
            if kind: e["kinds"][kind] = e["kinds"].get(kind, 0) + 1
            if r["title"] and r["title"] not in e["ex"]: e["ex"].append(r["title"])
            e["tags"].update(t for t in json.loads(r["tags"] or "[]") if not t.startswith("elem:"))
    return b, cf

LABEL = {"topic": "话题", "author": "作者", "design": "设计站点/App", "format": "呈现形式", "element": "设计元素", "lang": "编程语言"}
def _text(scope, key, pol, e):
    lab = LABEL.get(scope, scope); ex = "；例：" + "、".join(e["ex"][-2:]) if e["ex"] else ""
    verb = {"like": "偏好", "avoid": "回避", "neutral": "中性"}[pol]
    return f"{verb}{lab}「{key}」（衰减分 {e['score']:+.2f}，{e['n']} 条证据{ex}）"[:300]


def derive_comment_notes(c, asof=None):
    """Turn comment signals with meta.note into item-scoped memories (喜欢/不喜欢〈标题〉：短评). Merges same key."""
    asof = asof or datetime.datetime.now(datetime.timezone.utc)
    rows = c.execute("SELECT * FROM signals WHERE action='comment' AND coalesce(occurred_at,ts)<? ORDER BY id", (_cut(asof),)).fetchall()
    n_new, n_merge = 0, 0
    for r in rows:
        if c.execute("SELECT 1 FROM memory_evidence WHERE signal_id=?", (r["id"],)).fetchone(): continue
        meta = json.loads(r["meta"] or "{}")
        if meta.get("test"): continue
        note = (meta.get("note") or "").strip()
        if not note: continue
        vote = meta.get("vote")
        if vote not in ("like", "dislike") and r["item_id"]:
            prev = c.execute("""SELECT action FROM signals WHERE item_id=? AND action IN ('like','dislike')
              AND coalesce(occurred_at,ts)<=? ORDER BY coalesce(occurred_at,ts) DESC, id DESC LIMIT 1""",
              (r["item_id"], r["occurred_at"] or r["ts"])).fetchone()
            vote = prev["action"] if prev else "like"
        if vote not in ("like", "dislike"): vote = "like"
        pol = "like" if vote == "like" else "avoid"
        title = (r["title"] or r["item_id"] or "条目").strip()[:80]
        text = ("喜欢" if pol == "like" else "不喜欢") + f"〈{title}〉：{note}"[:300]
        scope = "item" if r["item_id"] else "topic"
        key = "note:" + (r["item_id"] or ("h:" + hashlib.sha1(text.encode()).hexdigest()[:12]))
        tags = list(json.loads(r["tags"] or "[]"))
        if r["item_id"] and ("item_id:" + r["item_id"]) not in tags: tags.append("item_id:" + r["item_id"])
        if "comment" not in tags: tags.append("comment")
        out = remember(c, text, pol, scope, tags[:20], 0.85, key=key,
                       meta={"origin": "derive:comment", "item_id": r["item_id"], "signal_id": r["id"], "vote": vote, "note": note})
        mid = out.get("merged_into") or out.get("id")
        if out.get("merged_into"): n_merge += 1
        else: n_new += 1
        if mid:
            c.execute("INSERT OR REPLACE INTO memory_evidence(memory_id,signal_id,weight) VALUES(?,?,?)", (mid, r["id"], 0.5))
    c.commit()
    return {"comment_memories": n_new, "comment_merged": n_merge}

def derive(c, asof=None):
    """Summarise signals into derived memories (idempotent upsert). Returns counts."""
    b, cf = aggregate(c, asof); need = int(cf["avoid_after_dislikes"]); mn = float(cf["min_abs_score"])
    seen, stats = set(), {"active": 0, "archived": 0, "avoid_by_streak": 0, "superseded": 0, "skipped_user_invalid": 0}
    t = now()
    for (scope, key), e in b.items():
        uinv = c.execute("""SELECT max(invalid_at) FROM memories WHERE source='derived' AND scope=? AND key LIKE ? ESCAPE '\\'
          AND json_extract(meta,'$.invalidated_by')='user'""", (scope, key.replace("%", "\\%").replace("_", "\\_") + "#inv:%")).fetchone()[0]
        if uinv and e["last"] <= uinv: stats["skipped_user_invalid"] += 1; seen.add((scope, key)); continue
        tail = e["seq"][-need:]
        streak = len(tail) == need and all(w < 0 for w in tail)
        if streak: pol = "avoid"; stats["avoid_by_streak"] += 1
        elif e["score"] >= mn: pol = "like"
        elif e["score"] <= -mn: pol = "avoid"
        else: pol = "neutral"
        status = "active" if (pol != "neutral" or streak) else "archived"
        conf = round(min(0.95, abs(e["score"]) / (abs(e["score"]) + 1.5) + min(e["n"], 10) * 0.02), 3)
        tags = sorted(e["tags"] | {scope})[:20]
        old = c.execute("SELECT id,polarity,status FROM memories WHERE source='derived' AND scope=? AND key=?", (scope, key)).fetchone()
        sup = None
        if old and old["status"] == "active" and status == "active" and old["polarity"] != pol:
            _retire(c, old["id"], t, f"superseded: {old['polarity']}->{pol}", "derive"); sup = old["id"]; stats["superseded"] += 1
        c.execute("""INSERT INTO memories(text,polarity,scope,key,tags,confidence,evidence_count,first_seen,last_seen,half_life_days,status,source,score,meta
          ,valid_from,supersedes_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,'derived',?,?,?,?) ON CONFLICT(source,scope,key) DO UPDATE SET text=excluded.text,polarity=excluded.polarity,
          tags=excluded.tags,confidence=excluded.confidence,evidence_count=excluded.evidence_count,last_seen=excluded.last_seen,
          half_life_days=excluded.half_life_days,status=excluded.status,score=excluded.score,meta=excluded.meta""",
          (_text(scope, key, pol, e), pol, scope, key, json.dumps(tags, ensure_ascii=False), conf, e["n"], e["first"], e["last"],
           hl_for(cf, max(e["src"], key=e["src"].get)), status, round(e["score"], 4), json.dumps({"raw": round(e["raw"], 2), "sources": e["src"], "streak_avoid": streak, "examples": e["ex"][-3:], **({"kinds": e["kinds"]} if e["kinds"] else {})}, ensure_ascii=False), t, sup))
        mid = c.execute("SELECT id FROM memories WHERE source='derived' AND scope=? AND key=?", (scope, key)).fetchone()[0]
        c.execute("DELETE FROM memory_evidence WHERE memory_id=?", (mid,))
        c.executemany("INSERT OR REPLACE INTO memory_evidence(memory_id,signal_id,weight) VALUES(?,?,?)", [(mid, i, w) for i, w in e["ids"][-200:]])
        seen.add((scope, key)); stats[status] += 1
    for r in c.execute("SELECT id,scope,key FROM memories WHERE source='derived' AND status='active' AND invalid_at IS NULL").fetchall():
        if (r["scope"], r["key"]) not in seen: c.execute("UPDATE memories SET status='archived' WHERE id=?", (r["id"],)); stats["archived"] += 1
    c.execute("INSERT OR REPLACE INTO config VALUES('last_derive',?)", (json.dumps(now()),)); c.commit()
    stats.update(derive_comment_notes(c, asof)); return stats

def _mem(r, full=False):
    d = {"id": r["id"], "text": r["text"], "polarity": r["polarity"], "scope": r["scope"], "key": r["key"],
         "tags": json.loads(r["tags"]), "confidence": r["confidence"], "evidence": r["evidence_count"],
         "last_seen": r["last_seen"], "source": r["source"]}
    if full: d.update(status=r["status"], first_seen=r["first_seen"], half_life_days=r["half_life_days"], score=r["score"],
                      valid_from=r["valid_from"], invalid_at=r["invalid_at"], supersedes_id=r["supersedes_id"])
    return d

def memories(c, scope=None, polarity=None, q=None, status="active", limit=50):
    if q: return search(c, q, limit=limit, kinds=("memories",))["memories"]
    sql, a = "SELECT * FROM memories WHERE status=?" + (" AND invalid_at IS NULL" if status == "active" else ""), [status]
    if scope: sql += " AND scope=?"; a.append(scope)
    if polarity: sql += " AND polarity=?"; a.append(polarity)
    sql += " ORDER BY source='manual' DESC, abs(coalesce(score,1))*confidence DESC LIMIT ?"; a.append(int(limit))
    return [_mem(r) for r in c.execute(sql, a)]

def _fts_q(q):
    terms = [t for t in re.split(r"\s+", q.strip()) if t][:8]
    return " OR ".join('"' + t.replace('"', '""') + '"' for t in terms if len(t) >= 3)

def search(c, q, limit=20, kinds=("memories", "items"), include_invalid=False):
    """Full-text search (trigram FTS5; terms <3 chars fall back to LIKE). Case-insensitive."""
    q = (q or "").strip()[:200]; out = {"query": q}
    if not q: raise ValueError("q")
    fq = _fts_q(q); short = [t for t in re.split(r"\s+", q) if t and len(t) < 3][:8]
    def run(tbl, fts, cols, sel):
        ids = []
        if fq:
            ids += [r[0] for r in c.execute(f"SELECT rowid FROM {fts} WHERE {fts} MATCH ? ORDER BY rank LIMIT ?", (fq, limit))]
        for t in short:
            like = "%" + t.replace("%", r"\%").replace("_", r"\_") + "%"
            w = " OR ".join(f"{x} LIKE ? ESCAPE '\\'" for x in cols)
            ids += [r[0] for r in c.execute(f"SELECT rowid FROM {tbl} WHERE {w} LIMIT ?", (*[like] * len(cols), limit))]
        ids = list(dict.fromkeys(ids))[:limit]
        return [sel(c.execute(f"SELECT rowid AS _r,* FROM {tbl} WHERE rowid=?", (i,)).fetchone()) for i in ids]
    if "memories" in kinds:
        out["memories"] = [m for m in run("memories", "memories_fts", ("text", "tags"), lambda r: _mem(r, True)) if include_invalid or (m["status"] == "active" and not m["invalid_at"])]
    if "items" in kinds:
        out["items"] = run("items", "items_fts", ("title", "summary", "tags"),
                           lambda r: {"item_id": r["item_id"], "url": r["url"], "title": r["title"], "summary": (r["summary"] or "")[:200],
                                      "tags": json.loads(r["tags"]), "source": r["source"], "date": r["date"]})
    return out

def _kind(e):
    k = e.get("kinds") or {}
    return max(k, key=k.get) if k else "web"
def _design_balanced(es, top, need):
    """Web:App = 5:5. Each kind normalised separately (weight / sum of positive weights of that kind), then
    half of the slots each, interleaved — so many Web favourites cannot crowd out App."""
    out = {"mix": {"web": 0.5, "app": 0.5}, "like": [], "avoid": [], "by_kind": {}}
    half = max(1, top // 2)
    for kind in ("web", "app"):
        ks = [(k, e) for k, e in es if _kind(e) == kind]
        pos = sum(e["score"] for _, e in ks if e["score"] > 0) or 1.0
        like = sorted([x for x in ks if x[1]["score"] > 0], key=lambda x: -x[1]["score"])[:half]
        avoid = sorted([x for x in ks if x[1]["score"] < 0 or (len(x[1]["seq"]) >= need and all(w < 0 for w in x[1]["seq"][-need:]))], key=lambda x: x[1]["score"])[:half]
        f = lambda k, e: {"key": k, "kind": kind, "weight": round(e["score"], 3), "norm": round(0.5 * e["score"] / pos, 4), "evidence": e["n"], "last": e["last"], "examples": e["ex"][-2:]}
        out["by_kind"][kind] = {"raw_positive_total": round(pos, 3), "like": [f(*x) for x in like], "avoid": [f(*x) for x in avoid]}
    for i in range(half):
        for kind in ("web", "app"):
            if i < len(out["by_kind"][kind]["like"]): out["like"].append(out["by_kind"][kind]["like"][i])
    out["avoid"] = sorted(out["by_kind"]["web"]["avoid"] + out["by_kind"]["app"]["avoid"], key=lambda x: x["weight"])[:top]
    return out

def profile(c, date=None, top=8):
    """Daily profile: decayed weights recomputed as of end of `date` (Asia/Shanghai)."""
    if date:
        d = datetime.date.fromisoformat(date)
        asof = datetime.datetime.combine(d, datetime.time(23, 59, 59), SH).astimezone(datetime.timezone.utc)
    else: asof = datetime.datetime.now(datetime.timezone.utc)
    b, cf = aggregate(c, asof); need = int(cf["avoid_after_dislikes"])
    res = {"date": (date or asof.astimezone(SH).date().isoformat()), "tz": "Asia/Shanghai", "half_life_days": cf["half_life_days"], "half_life_by_source": cf["half_life_by_source"],
           "explore_ratio": cf["explore_ratio"], "signals": c.execute("SELECT count(*) FROM signals WHERE coalesce(occurred_at,ts)<?", (_cut(asof),)).fetchone()[0]}
    for scope in ("topic", "author", "design", "format", "element", "lang"):
        es = [(k, e) for (s, k), e in b.items() if s == scope]
        if not es: continue
        def item(k, e): return {"key": k, "weight": round(e["score"], 3), "evidence": e["n"], "last": e["last"], "examples": e["ex"][-2:]}
        like = sorted([x for x in es if x[1]["score"] > 0], key=lambda x: -x[1]["score"])[:top]
        avoid = sorted([x for x in es if x[1]["score"] < 0 or (len(x[1]["seq"]) >= need and all(w < 0 for w in x[1]["seq"][-need:]))], key=lambda x: x[1]["score"])[:top]
        res[scope] = {"like": [item(*x) for x in like], "avoid": [item(*x) for x in avoid]}
        if scope == "design": res[scope] = _design_balanced(es, top, need)
    res["recommend"] = recommend_weights(b, cf, need)
    res["manual"] = [_mem(r) for r in c.execute("SELECT * FROM memories WHERE source='manual' AND status='active' AND invalid_at IS NULL ORDER BY last_seen DESC LIMIT 30")]
    return res

def recommend_weights(b, cf, need=3, n_exploit=12, n_explore=6):
    """Exploit/explore slot weights for the daily picker (sum = 1). exploit = (1-r) split by decayed score of top likes
    across scopes; explore = r split evenly over weak/stale/new keys (0<score<min_abs or few evidence), never avoids."""
    r_ = float(cf.get("explore_ratio", 0.2)); mn = float(cf["min_abs_score"])
    isavoid = lambda e: e["score"] < 0 or (len(e["seq"]) >= need and all(w < 0 for w in e["seq"][-need:]))
    b = {k: e for k, e in b.items() if set(e["src"]) - {"design"}}  # design picks have their own Web:App 5:5 block (profile.design)
    like = sorted([(k, e) for k, e in b.items() if e["score"] >= mn and not isavoid(e)], key=lambda x: -x[1]["score"])[:n_exploit]
    taken = {k for k, _ in like}
    pool = sorted([(k, e) for k, e in b.items() if k not in taken and not isavoid(e) and (0 <= e["score"] < mn or e["n"] <= 2)],
                  key=lambda x: (x[1]["n"], x[1]["last"]))[:n_explore]
    tot = sum(e["score"] for _, e in like) or 1.0
    f = lambda k, e, w, why: {"scope": k[0], "key": k[1], "weight": round(w, 4), "score": round(e["score"], 3), "evidence": e["n"], "why": why}
    ex = [f(k, e, (1 - r_) * e["score"] / tot, "exploit") for k, e in like]
    xp = [f(k, e, r_ / len(pool), "explore") for k, e in pool] if pool else []
    if not xp and ex:  # nothing to explore -> give its share back to exploit
        for x in ex: x["weight"] = round(x["weight"] / (1 - r_), 4)
    return {"explore_ratio": r_ if xp else 0.0, "exploit": ex, "explore": xp,
            "scope_note": "新闻/项目类（不含设计，设计见 design 块）", "note": "按 weight 分配当日条目名额；explore 为 20% 探索位（弱信号/新兴趣/久未出现），回避项永不入选"}

def export(c):
    t = lambda q: [dict(r) for r in c.execute(q)]
    return {"exported_at": now(), "config": cfg(c),
            "signals": t("SELECT id,ts,user,source_type,item_id,item_url,title,topic,tags,author,action,value,meta FROM signals ORDER BY id"),
            "memories": t("SELECT id,text,polarity,scope,key,tags,confidence,evidence_count,first_seen,last_seen,half_life_days,status,source,score,meta FROM memories ORDER BY id"),
            "items": t("SELECT item_id,url,title,summary,tags,source,date FROM items ORDER BY date,item_id"),
            "memory_evidence": t("SELECT memory_id,signal_id,weight FROM memory_evidence ORDER BY memory_id,signal_id"),
            "sources": t("SELECT * FROM sources ORDER BY name"), "entities": t("SELECT * FROM entities ORDER BY id")}

def list_memories(c, scope=None, polarity=None, source=None, include_invalid=False, limit=100):
    sql, a = "SELECT * FROM memories WHERE 1=1", []
    if not include_invalid: sql += " AND status='active' AND invalid_at IS NULL"
    for col, v in (("scope", scope), ("polarity", polarity), ("source", source)):
        if v: sql += f" AND {col}=?"; a.append(v)
    sql += " ORDER BY source='manual' DESC, abs(coalesce(score,1))*confidence DESC, id LIMIT ?"; a.append(int(limit))
    return [_mem(r, True) for r in c.execute(sql, a)]

def export_md(c):
    """Active memories grouped by scope, as Markdown (LLM-friendly, one memory per line)."""
    rows = c.execute("""SELECT * FROM memories WHERE status='active' AND invalid_at IS NULL
      ORDER BY scope, source='manual' DESC, abs(coalesce(score,1))*confidence DESC""").fetchall()
    out = ["---", "title: DiaoDaily 偏好记忆", "type: preferences", f"exported_at: {now()}", f"active: {len(rows)}", "---", "",
           f"# DiaoDaily 偏好记忆（active {len(rows)} 条，导出于 {now()} UTC）", "",
           "格式（basic-memory observation 风格）：- [polarity] 文本 #tag … (source, conf, evidence) `#id`；工具：search / memory-evidence <id> / invalidate-memory <id>"]
    cur = None
    for r in rows:
        if r["scope"] != cur:
            cur = r["scope"]; out += ["", f"## {LABEL.get(cur, cur)}（{cur}）"]
        tg = " ".join("#" + re.sub(r"\s+", "-", x) for x in json.loads(r["tags"])[:6])
        out.append(f"- [{r['polarity']}] {r['text']} {tg} ({r['source']}, {r['confidence']:.2f}, {r['evidence_count']}) `#{r['id']}`")
    return "\n".join(out) + "\n"

def purge_test(c):
    """Remove rows marked TEST (meta.test or title starting 'TEST'). Only maintenance path that deletes signals."""
    c.execute("DROP TRIGGER IF EXISTS sig_noupd")
    n = c.execute("DELETE FROM signals WHERE json_extract(meta,'$.test') OR title GLOB 'TEST*' OR item_id GLOB 'TEST*'").rowcount
    m = c.execute("DELETE FROM memories WHERE text GLOB 'TEST*' OR key GLOB '*TEST*'").rowcount
    c.execute("DELETE FROM memory_evidence WHERE signal_id NOT IN (SELECT id FROM signals) OR memory_id NOT IN (SELECT id FROM memories)")
    c.execute("DELETE FROM sources WHERE name GLOB 'TEST*'")
    i = c.execute("DELETE FROM items WHERE item_id GLOB 'TEST*' OR title GLOB 'TEST*'").rowcount
    c.commit(); c.executescript(SCHEMA)
    return {"signals": n, "memories": m, "items": i}

# ---------- design helpers (used by daily-api and import) ----------
def design_item_id(date, site):
    a = re.sub(r"[^a-z0-9]+", "-", site.lower()).strip("-")[:40] or "item"
    return f"design:{date}:{a}-{hashlib.sha1(site.encode()).hexdigest()[:6]}"
def design_brand(site): return site.split("·")[0].strip()[:120]
def design_signals(c, r, origin="api", commit=True):
    """Map a design-page rating record {date,site,url,rating,fav,ts,notes,tokens} -> items + rate/fav signals."""
    date, site = r["date"], r["site"]
    if site == "test" or r.get("test"): return []
    iid = design_item_id(date, site); kind = "app" if "mobbin.com" in (r.get("url") or "") else "web"
    tags = ["design", "format:" + kind] + ["elem:" + t["id"] for t in (r.get("tokens") or []) if isinstance(t, dict) and t.get("id")][:15]
    upsert_item(c, iid, r.get("url") or None, site, r.get("notes"), tags, "design", date, commit=False)
    base = {"source_type": "design", "item_id": iid, "item_url": r.get("url") or None, "title": site, "topic": "design:" + kind,
            "tags": tags, "author": design_brand(site), "ts": r.get("ts"), "meta": {"origin": origin, "date": date}}
    out = []
    if r.get("rating"):
        out.append(add_signal(c, {**base, "action": "rate", "value": r["rating"]}, f"rate|{date}|{site}|{r.get('rating')}|{r.get('ts')}", commit=False))
    if r.get("fav") is True:
        out.append(add_signal(c, {**base, "action": "fav"}, f"fav|{date}|{site}", commit=False))
    if commit: c.commit()
    return out
def read_signal(c, date, kind, ts=None, origin="api"):
    st = "design" if kind == "design" else "news"
    return add_signal(c, {"source_type": st, "action": "read", "item_id": f"{kind}-page:{date}", "title": f"{'设计灵感' if kind=='design' else '叼报'} {date}",
                          "topic": "page:" + kind, "ts": ts, "meta": {"origin": origin, "date": date}}, f"read|{date}|{kind}")

def import_existing(c, md_json=None):
    """Idempotent import of legacy JSON files (dedup_key + upserts)."""
    L = lambda p, d: json.load(open(p, encoding="utf-8")) if os.path.exists(p) else d
    before = c.execute("SELECT count(*) FROM signals").fetchone()[0]
    for r in L(DATA + "/feedback.json", {}).values(): design_signals(c, r, "import:feedback.json", False)
    for r in L(DATA + "/library.json", []): design_signals(c, r, "import:library.json", False)
    if os.path.isdir(FAV):
        for s in sorted(os.listdir(FAV)):
            m = L(f"{FAV}/{s}/meta.json", None)
            if not m: continue
            if s.startswith("lib-") or not m.get("date"):
                upsert_item(c, "design:" + s, m.get("url"), m.get("site") or s, (m.get("notes") or "")[:2000], ["design", "library"], "design", m.get("date"), commit=False)
                add_signal(c, {"source_type": "design", "action": "fav", "item_id": "design:" + s, "item_url": m.get("url") if str(m.get("url", "")).startswith("http") else None,
                               "title": m.get("site") or s, "author": design_brand(m.get("site") or s[4:]), "topic": "design:web", "tags": ["design", "format:web", "library"],
                               "ts": m.get("ts"), "meta": {"origin": "import:favorites/" + s}}, f"fav|lib|{s}", commit=False)
            else: design_signals(c, m, "import:favorites/" + s, False)
    for d, v in L(DATA + "/read.json", {}).items():
        for k, ts in v.items():
            if k in ("x", "design"): read_signal(c, d, k, ts, "import:read.json")
    if md_json and os.path.exists(md_json):
        md = json.load(open(md_json, encoding="utf-8"))
        for r in md["rows"]:
            r["ts"] = r["date"] + "T12:00:00Z"
            # md is a summary: only add when no richer record exists for that (date,site)
            if c.execute("SELECT 1 FROM signals WHERE item_id=? LIMIT 1", (design_item_id(r["date"], r["site"]),)).fetchone(): continue
            design_signals(c, r, "import:preferences.md", False)
        for n in md["notes"]:
            remember(c, n, "avoid" if "勿用" in n else ("neutral" if "中性" in n else ("avoid" if ("回避" in n or "少用" in n) else "like")), "design",
                     ["design", "preferences.md"], 0.7, meta={"origin": "import:preferences.md"})
    c.commit()
    return {"new_signals": c.execute("SELECT count(*) FROM signals").fetchone()[0] - before}

def counts(c):
    return {t: c.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("signals", "memories", "items")}

# ---------- CLI ----------
def _out(o, md=False):
    if md and isinstance(o, dict) and "date" in o and "explore_ratio" in o:
        print(f"# 偏好画像 {o['date']}（{o['tz']}，半衰期 {o['half_life_days']} 天，按来源 {o.get('half_life_by_source')}，探索名额 {int(o['explore_ratio']*100)}%，信号 {o['signals']}）")
        for s in ("topic", "author", "design", "format", "element", "lang"):
            if s not in o: continue
            print(f"\n## {LABEL[s]}")
            for pol in ("like", "avoid"):
                xs = o[s][pol]
                if xs: print(f"- {'喜欢' if pol=='like' else '回避'}：" + "；".join(f"{x['key']} {x['weight']:+.2f}（{x['evidence']}）" for x in xs))
        rc = o.get("recommend") or {}
        if rc.get("exploit"): print("\n## 推荐权重（exploit %d%% / explore %d%%）" % (round((1 - rc["explore_ratio"]) * 100), round(rc["explore_ratio"] * 100)))
        for x in rc.get("exploit", []) + rc.get("explore", []): print(f"- {x['why']} {x['scope']}:{x['key']} {x['weight']:.3f}")
        if o["manual"]: print("\n## 手动记忆\n" + "\n".join(f"- [{m['polarity']}] {m['text']}" for m in o["manual"]))
        return
    print(json.dumps(o, ensure_ascii=False, indent=1))

def main(argv=None):
    p = argparse.ArgumentParser(prog="prefs.py", description="DiaoDaily 叼报 偏好库 CLI")
    p.add_argument("--db"); sp = p.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("add-signal"); a.add_argument("--json", help="full JSON object (or '-' for stdin)")
    for f in ("source-type", "action", "item-id", "item-url", "title", "topic", "tags", "author", "ts", "user"): a.add_argument("--" + f)
    a.add_argument("--value", type=float); a.add_argument("--meta")
    s = sp.add_parser("search"); s.add_argument("query"); s.add_argument("--limit", type=int, default=20)
    pr = sp.add_parser("profile"); pr.add_argument("--date"); pr.add_argument("--md", action="store_true"); pr.add_argument("--top", type=int, default=8)
    m = sp.add_parser("memories"); m.add_argument("--scope"); m.add_argument("--polarity"); m.add_argument("--q"); m.add_argument("--all", action="store_true"); m.add_argument("--limit", type=int, default=50)
    for nm in ("remember", "add-memory"):
      r = sp.add_parser(nm); r.add_argument("text"); r.add_argument("--polarity", default="like", choices=POLARITY)
      r.add_argument("--scope", default="topic"); r.add_argument("--tags"); r.add_argument("--confidence", type=float, default=0.8); r.add_argument("--key")
    lm = sp.add_parser("list-memories"); lm.add_argument("--scope"); lm.add_argument("--polarity"); lm.add_argument("--source")
    lm.add_argument("--include-invalid", action="store_true"); lm.add_argument("--limit", type=int, default=100)
    iv = sp.add_parser("invalidate-memory"); iv.add_argument("id", type=int); iv.add_argument("--reason", default="user"); iv.add_argument("--superseded-by", type=int)
    me = sp.add_parser("memory-evidence"); me.add_argument("id", type=int); me.add_argument("--limit", type=int, default=50)
    sp.add_parser("sources"); dd = sp.add_parser("dedupe-memories"); dd.add_argument("--dry-run", action="store_true")
    sp.add_parser("derive"); e = sp.add_parser("export"); e.add_argument("--json", action="store_true", default=True); e.add_argument("--md", action="store_true")
    i = sp.add_parser("import"); i.add_argument("--md-json")
    sp.add_parser("stats"); sp.add_parser("purge-test")
    c_ = sp.add_parser("config"); c_.add_argument("key", nargs="?"); c_.add_argument("value", nargs="?")
    ar = p.parse_args(argv); c = connect(ar.db)
    try:
        if ar.cmd == "add-signal":
            if ar.json: d = json.load(sys.stdin) if ar.json == "-" else json.loads(ar.json)
            else:
                d = {k.replace("-", "_"): getattr(ar, k.replace("-", "_")) for k in ("source-type", "action", "item-id", "item-url", "title", "topic", "author", "ts", "user", "value")}
                d["tags"] = ar.tags; d["meta"] = json.loads(ar.meta) if ar.meta else {}
                d = {k: v for k, v in d.items() if v is not None}
            _out(add_signal(c, d))
        elif ar.cmd == "search": _out(search(c, ar.query, ar.limit))
        elif ar.cmd == "profile": _out(profile(c, ar.date, ar.top), ar.md)
        elif ar.cmd == "memories": _out(memories(c, ar.scope, ar.polarity, ar.q, "archived" if ar.all else "active", ar.limit) if not ar.all else
                                         [_mem(x, True) for x in c.execute("SELECT * FROM memories ORDER BY id")])
        elif ar.cmd == "list-memories": _out(list_memories(c, ar.scope, ar.polarity, ar.source, ar.include_invalid, ar.limit))
        elif ar.cmd == "invalidate-memory": _out(invalidate_memory(c, ar.id, ar.reason, ar.superseded_by))
        elif ar.cmd == "memory-evidence": _out(memory_evidence(c, ar.id, ar.limit))
        elif ar.cmd == "sources": _out(sources(c))
        elif ar.cmd == "dedupe-memories": _out(dedupe_memories(c, ar.dry_run))
        elif ar.cmd in ("remember", "add-memory"): _out(remember(c, ar.text, ar.polarity, ar.scope, ar.tags, ar.confidence, ar.key))
        elif ar.cmd == "derive": _out({"at": now(), **derive(c), **counts(c)})
        elif ar.cmd == "export":
            if ar.md: sys.stdout.write(export_md(c))
            else: _out(export(c))
        elif ar.cmd == "import": _out({**import_existing(c, ar.md_json), **counts(c)})
        elif ar.cmd == "stats": _out({**counts(c), "by_action": {r[0]: r[1] for r in c.execute("SELECT action,count(*) FROM signals GROUP BY 1")},
            "by_source": {r[0]: r[1] for r in c.execute("SELECT source_type,count(*) FROM signals GROUP BY 1")},
            "memory_evidence": c.execute("SELECT count(*) FROM memory_evidence").fetchone()[0],
            "invalid_memories": c.execute("SELECT count(*) FROM memories WHERE invalid_at IS NOT NULL").fetchone()[0], "config": cfg(c)})
        elif ar.cmd == "purge-test": _out(purge_test(c))
        elif ar.cmd == "config":
            if ar.key and ar.value is not None:
                c.execute("INSERT OR REPLACE INTO config VALUES(?,?)", (ar.key, json.dumps(json.loads(ar.value)))); c.commit()
            _out(cfg(c))
    except ValueError as ex:
        print(json.dumps({"error": str(ex)}, ensure_ascii=False)); return 2
    return 0

if __name__ == "__main__": sys.exit(main())
