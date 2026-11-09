#!/usr/bin/env python3
"""DiaoDaily 叼报 · 近 7 天短评/赞踩摘要，供 12:00 推送概览调用。
输出 stdout JSON: {like_reasons:[], dislike_reasons:[], summary:"…"}
用法：
  # 在 VPS 上（有 prefs.db）
  PREFS_DB=/srv/daily/data/prefs.db python3 pref-summary.py
  # 在 box 上（默认 SSH 到 VPS 跑远端同脚本 /srv/daily/bin/pref-summary.py）
  python3 /workspace/digests/lib/pref-summary.py
  python3 pref-summary.py --days 7 --local   # 强制本地 DB
"""
from __future__ import annotations
import argparse, datetime, json, os, sys

SH = datetime.timezone(datetime.timedelta(hours=8))
VPS = os.environ.get("DAILY_VPS") or ""
KEY = os.environ.get("DAILY_SSH_KEY", os.path.expanduser("~/.ssh/vps_jidadiao"))
REMOTE = "/srv/daily/bin/pref-summary.py"
DB_DEFAULT = os.environ.get("PREFS_DB", "/srv/daily/data/prefs.db")

def _cut_iso(days: int) -> str:
    t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")

def summarize(db: str, days: int = 7) -> dict:
    sys.path.insert(0, os.path.dirname(db) if False else "/srv/daily/bin")
    # Prefer sibling prefs.py next to this file's deployed copy, else daily-portal bin on box
    for d in (os.path.dirname(os.path.abspath(__file__)), "/srv/daily/bin", "/workspace/daily-portal/bin"):
        if os.path.isfile(os.path.join(d, "prefs.py")):
            if d not in sys.path: sys.path.insert(0, d)
            break
    import prefs  # noqa
    c = prefs.connect(db)
    try:
        since = _cut_iso(days)
        rows = c.execute("""SELECT id, action, title, topic, author, item_id, meta, coalesce(occurred_at,ts) AS occ
            FROM signals WHERE action IN ('comment','like','dislike')
              AND coalesce(occurred_at,ts)>=? AND coalesce(json_extract(meta,'$.test'),0)=0
            ORDER BY coalesce(occurred_at,ts) DESC, id DESC LIMIT 400""", (since,)).fetchall()
        likes, dislikes = [], []
        seen_note = set()
        for r in rows:
            meta = json.loads(r["meta"] or "{}")
            if r["action"] == "comment":
                note = (meta.get("note") or "").strip()
                if not note: continue
                vote = meta.get("vote")
                title = (r["title"] or r["item_id"] or "条目")[:60]
                key = (r["item_id"] or "") + "|" + note
                if key in seen_note: continue
                seen_note.add(key)
                line = f"「{title}」：{note}"[:160]
                if vote == "dislike": dislikes.append(line)
                else: likes.append(line)
        # Fallback: like/dislike without note → topic/author hints (最多各 2 条，无短评时)
        if not likes and not dislikes:
            for r in rows:
                if r["action"] not in ("like", "dislike"): continue
                label = r["title"] or r["topic"] or r["author"] or r["item_id"]
                if not label: continue
                line = str(label)[:80]
                (likes if r["action"] == "like" else dislikes).append(line)
                if len(likes) >= 3 and len(dislikes) >= 3: break
        likes, dislikes = likes[:5], dislikes[:5]
        parts = []
        if likes:
            parts.append("最近喜欢：" + "；".join(likes[:3]))
        if dislikes:
            parts.append("最近不喜欢：" + "；".join(dislikes[:3]))
        if not parts:
            summary = ""
        else:
            summary = " ".join(parts)
            if len(summary) > 220:
                summary = summary[:217] + "…"
        return {"like_reasons": likes, "dislike_reasons": dislikes, "summary": summary, "days": days, "tz": "Asia/Shanghai"}
    finally:
        c.close()

def via_ssh(days: int) -> dict:
    if not VPS:
        raise SystemExit("DAILY_VPS is not set; export it or pass --local with PREFS_DB")
    import paramiko
    c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(VPS, username="root", key_filename=KEY, timeout=15)
    cmd = f"PREFS_DB=/srv/daily/data/prefs.db /usr/bin/python3 {REMOTE} --local --days {int(days)}"
    _, o, e = c.exec_command(cmd, timeout=60)
    out, err = o.read().decode(), e.read().decode(); c.close()
    if err and not out:
        raise RuntimeError(err.strip()[:500])
    return json.loads(out)

def main(argv=None):
    ap = argparse.ArgumentParser(description="叼报偏好短评摘要")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--local", action="store_true", help="只用本地 PREFS_DB，不 SSH")
    ap.add_argument("--db", default=DB_DEFAULT)
    ar = ap.parse_args(argv)
    if ar.local or os.path.isfile(ar.db):
        if not os.path.isfile(ar.db):
            print(json.dumps({"error": f"db missing: {ar.db}"}, ensure_ascii=False)); return 2
        o = summarize(ar.db, ar.days)
    else:
        o = via_ssh(ar.days)
    print(json.dumps(o, ensure_ascii=False, indent=1))
    return 0

if __name__ == "__main__":
    sys.exit(main())
