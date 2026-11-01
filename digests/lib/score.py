#!/usr/bin/env python3
"""叼报精选 · 确定性打分 + 同题封顶 + URL/标题去重（借鉴 lthero-big/newsp generate.py）。

不做 LLM 选条：按信息差 / 干货 / 相关 / 新鲜度打底分，再乘钥匙 factor，
再按 pick-rules 的类目 cap 与同事件去重，输出 ≤15 条候选排序。

用法：
  python3 /workspace/digests/lib/score.py --date 2026-11-01
  python3 /workspace/digests/lib/score.py --date 2026-11-01 --json -o /tmp/pick.json
  PREFS_DB=/tmp/prefs-dryrun.db python3 ...   # 乘钥匙 factor；没有 DB 则 factor=1

输入默认读：
  /workspace/digests/items-{date}.json
  /workspace/digests/items-public-{date}.json
  /workspace/digests/items-sidehustle-{date}.json（有则并入，周六）
"""
from __future__ import annotations

import argparse
import difflib
import json
import math
import os
import re
import sys
import urllib.parse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

SH = timezone(timedelta(hours=8))
ROOT = Path(os.environ.get("DIGESTS_ROOT", "/workspace/digests"))
LIB = Path(__file__).resolve().parent

# --- 与 newsp 对齐的去重工具 ---
TITLE_STOP = {
    "the", "a", "an", "of", "and", "to", "for", "on", "in", "with", "from",
    "by", "at", "as", "is", "are", "was", "were", "be", "new", "show", "hn",
    "的", "了", "和", "与", "在", "是", "也", "就", "都", "而", "及", "或",
}
TRACKING_KEYS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "utm_id",
    "ref", "fbclid", "gclid", "mc_cid", "mc_eid", "igshid", "si",
}

# pick-rules 类目封顶（同事件另有 EVENT_CAP=1）
TOPIC_CAP = 2  # newsp 同款：同一具体 topic_key 最多 2（模型发布等）
CATEGORY_CAPS = {
    "vps": 2,
    "benchmark": 1,
    "model_release": 2,
    "sidehustle": 3,
}
EVENT_CAP = 1
STALE_DAYS, STALE_FACTOR = 3, 0.6
DEFAULT_LIMIT = 15
MIN_LIMIT = 10  # 目标下限（不够不硬凑）

ANIME_RE = re.compile(
    r"二次元|acg|动画|anime|声优|漫画|周边|剧场版|pv公开|定档|万圣节视觉|"
    r"库洛米|mappa|シャンフロ|柊家|药屋|一式",
    re.I,
)
ANDROID_RE = re.compile(r"安卓去广告|android\s*ad|去广告", re.I)
RUST_RE = re.compile(r"\brust\b|用\s*rust\s*", re.I)
GENEALOGY_RE = re.compile(r"族谱|家谱|genealogy|历史研究", re.I)
LISTICLE_RE = re.compile(
    r"(\d+\s*项设置|入门指南|路线图|一文看懂|最全盘点|盘点\d+|top\s*\d+|listicle)",
    re.I,
)
BENCHMARK_RE = re.compile(
    r"榜上线|排行榜|benchmark|hle[\s\-]?diamond|intelligence\s*index|"
    r"arena\s*elo|lmsys|只.*一张.*榜|只有一张榜",
    re.I,
)
VPS_RE = re.compile(
    r"vps|机场|中转|失联|vless|3x-?ui|节点|住宅\s*ip|家宽|gfw|封锁|端口被封|dmit",
    re.I,
)
MODEL_REL_RE = re.compile(
    r"上线|发布|半价|开源权重|权重|上架|放出|prototype|新模型|flash[\s\-]?\d",
    re.I,
)
RUMOR_RE = re.compile(r"未证实|传闻|据说|有说法称", re.I)
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?(?:\s*%|万|亿|\$|€|¥|tok/s|token|星|star)?", re.I)
ACTION_RE = re.compile(
    r"可跑|实测|步骤|怎么搭|照着|开源|免费|轮换|该在|早买|省\s*token|"
    r"防失联|自建|仓库|skill|工具",
    re.I,
)
RELEVANCE_RE = re.compile(
    r"api\s*key|盗刷|算力|vps|gfw|封锁|中转|拼车|本地|mac|显卡|3060|3090|"
    r"pcb|缺货|价格|降价|涨价|claude|deepseek|unslop|太\s*ai",
    re.I,
)

# 近 7 天已推事件（干跑时可从 recent picks 文件读；默认空）
RECENT_PUSHED_PATH = ROOT / "lib" / "recent-pushed.json"


def fold(text: str) -> str:
    text = (text or "").lower().replace("_", " ")
    text = re.sub(r"[\-./]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def title_tokens(title: str) -> list[str]:
    # 英文词 + 连续中文 2+ 字
    t = fold(title)
    en = [tok for tok in re.findall(r"[a-z0-9]+", t) if tok not in TITLE_STOP and len(tok) > 1]
    zh = [m.group(0) for m in re.finditer(r"[\u4e00-\u9fff]{2,}", title or "")]
    return en + zh


def titles_similar(left: str, right: str) -> bool:
    a, b = title_tokens(left), title_tokens(right)
    if len(a) < 2 or len(b) < 2:
        return False
    sa, sb = set(a), set(b)
    union = sa | sb
    if not union:
        return False
    if len(sa & sb) / len(union) >= 0.72:
        return True
    return difflib.SequenceMatcher(None, " ".join(a), " ".join(b)).ratio() >= 0.86


def normalize_url(url: str) -> str:
    parts = urllib.parse.urlsplit((url or "").strip())
    if parts.scheme not in ("http", "https"):
        return (url or "").strip()
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = re.sub(r"/+$", "", parts.path or "") or "/"
    if host.endswith("reddit.com"):
        match = re.match(r"(/r/[^/]+/comments/[^/]+)", path, re.I)
        if match:
            path = match.group(1).lower()
        host = "reddit.com"
    if host in ("x.com", "twitter.com"):
        host = "x.com"
        path = path.lower()
    if host == "news.ycombinator.com":
        query = urllib.parse.parse_qs(parts.query)
        if "id" in query:
            return f"https://news.ycombinator.com/item?id={query['id'][0]}"
    kept = []
    for key, value in urllib.parse.parse_qsl(parts.query, keep_blank_values=False):
        if key.lower() in TRACKING_KEYS or key.lower().startswith("utm_"):
            continue
        kept.append((key, value))
    kept.sort()
    return urllib.parse.urlunsplit(("https", host, path, urllib.parse.urlencode(kept), ""))


def blob(it: dict) -> str:
    return " ".join(
        str(it.get(k) or "")
        for k in ("title", "summary", "summary_zh", "topic", "cat", "tags", "pick")
    )


def category_of(it: dict) -> str | None:
    text = blob(it)
    topic = str(it.get("topic") or "")
    if it.get("_sidehustle") or "副业" in topic:
        return "sidehustle"
    if BENCHMARK_RE.search(text) or "榜" in (it.get("title") or "") and "AI" in topic:
        # 纯榜单/指数
        if re.search(r"榜|benchmark|index|arena", text, re.I) and not MODEL_REL_RE.search(
            it.get("title") or ""
        ):
            return "benchmark"
    if VPS_RE.search(text) or "中转" in topic or "VPS" in topic.upper():
        return "vps"
    if MODEL_REL_RE.search(text) and re.search(
        r"gpt|claude|gemini|deepseek|qwen|kimi|model|权重|terra|flash|agent",
        text,
        re.I,
    ):
        return "model_release"
    return None


def topic_key(it: dict) -> str | None:
    """具体事件钥匙：优先专有名词，否则标题前几个实词。"""
    title = it.get("title") or ""
    # GitHub owner/repo
    m = re.match(r"https?://github\.com/([\w.-]+)/([\w.-]+)", it.get("url") or "", re.I)
    if m:
        return f"repo:{m.group(1)}/{m.group(2)}".lower()
    # 已知专名
    for pat, key in (
        (r"gpt[\s\-]?6\.1\s*terra|terra\s*半价", "gpt-terra"),
        (r"wiz|黑色十月|api\s*key", "wiz-oct"),
        (r"local\s*code", "local-code"),
        (r"betelgeuse", "betelgeuse"),
        (r"openrouter", "openrouter"),
        (r"hle[\s\-]?diamond", "hle-diamond"),
        (r"unslop", "unslop"),
        (r"dsh-superagent|superagent-prototype", "ds-superagent"),
        (r"postiz", "postiz"),
        (r"防失联|坠机|跑路", "vps-outage"),
        (r"双出口|vless|3x-?ui|固定出口|选协议", "vps-howto"),
        (r"pcb", "pcb-shortage"),
        (r"降价|涨价|11/21|12/1", "price-dates"),
        (r"上下文压缩|compaction", "ctx-compact"),
        (r"deepseek.*flash|v4\.1-flash", "ds-flash"),
    ):
        if re.search(pat, blob(it), re.I):
            return key
    toks = title_tokens(title)
    if len(toks) >= 2:
        return "t:" + "-".join(toks[:3]).lower()
    return None


def hard_exclude(it: dict) -> str | None:
    text = blob(it)
    topic = str(it.get("topic") or "")
    if ANIME_RE.search(text) or topic.upper() in ("ACG", "二次元", "ANIME"):
        return "anime"
    if ANDROID_RE.search(text):
        return "android"
    if RUST_RE.search(it.get("title") or "") and "rust" in (it.get("title") or "").lower():
        # 仅标题主讲 Rust 项目时排除；标签里偶然出现不算
        tags = " ".join(str(t) for t in (it.get("tags") or [])).lower()
        if "rust" in (it.get("title") or "").lower() or tags.strip() == "rust":
            return "rust"
    if GENEALOGY_RE.search(text):
        return "genealogy"
    if LISTICLE_RE.search(text):
        return "listicle"
    # 只有一张榜单图、无干货：标题含榜且 summary 很短又无数字动作
    if BENCHMARK_RE.search(it.get("title") or "") and len(it.get("summary") or it.get("summary_zh") or "") < 40:
        return "benchmark_thin"
    if RUMOR_RE.search(text) and not NUMBER_RE.search(text):
        return "rumor"
    return None


def parse_time(v) -> datetime | None:
    if not v:
        return None
    if isinstance(v, (int, float)):
        ts = float(v)
        if ts > 1e12:
            ts /= 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    s = str(v).strip().replace("Z", "+00:00")
    try:
        d = datetime.fromisoformat(s)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                d = datetime.strptime(s[:16], fmt)
                break
            except ValueError:
                d = None
        if d is None:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=SH)
    return d.astimezone(timezone.utc)


def engagement(it: dict) -> float:
    src = str(it.get("source") or "").lower()
    pts = max(0, int(it.get("likes") or it.get("points") or it.get("stars") or 0))
    com = max(0, int(it.get("rts") or it.get("comments") or it.get("forks") or 0))
    if "github" in src or (it.get("url") or "").startswith("https://github.com"):
        scale = 2000
    elif "reddit" in src:
        scale = 200
    elif "hn" in src or "ycombinator" in (it.get("url") or ""):
        scale = 400
    elif "hf" in src or "huggingface" in (it.get("url") or ""):
        scale = 500
    else:  # x
        scale = 80
    return min(1.0, (math.log1p(pts) + 0.5 * math.log1p(com)) / (1.5 * math.log1p(scale)))


def score_parts(it: dict, now: datetime) -> dict:
    text = blob(it)
    # 信息差：有具体数字 / 新事件动词 / 非传闻
    info = 0.25
    if NUMBER_RE.search(text):
        info += 0.35
    if re.search(r"上线|发布|披露|开源|实测|定档|短缺|被盗|半价|涨价|降价", text):
        info += 0.25
    if RUMOR_RE.search(text):
        info -= 0.35
    if BENCHMARK_RE.search(text) and not NUMBER_RE.search(it.get("summary") or ""):
        info -= 0.2
    info = max(0.0, min(1.0, info))

    # 干货：可行动 / 开源可跑 / 步骤
    dry = 0.15
    if ACTION_RE.search(text):
        dry += 0.4
    if re.search(r"github\.com|huggingface\.co", it.get("url") or "", re.I):
        dry += 0.25
    if NUMBER_RE.search(text):
        dry += 0.15
    if LISTICLE_RE.search(text):
        dry -= 0.4
    dry = max(0.0, min(1.0, dry))

    # 相关：和他踩过的坑 / 工具链
    rel = 0.2
    if RELEVANCE_RE.search(text):
        rel += 0.5
    if category_of(it) == "vps":
        rel += 0.25
    if "中招" in text or "你踩过" in text:
        rel += 0.2
    rel = max(0.0, min(1.0, rel))

    # 新鲜度
    pub = parse_time(it.get("published_at") or it.get("created_at") or it.get("date"))
    age_h = max(0.0, (now - pub).total_seconds() / 3600) if pub else 12.0
    half_life = 24.0 if str(it.get("source") or "").lower() in ("x", "grok bot x 日报", "reddit") else 72.0
    decay = 0.5 ** (age_h / half_life)

    eng = engagement(it)
    # 权重：信息差 0.35 + 干货 0.30 + 相关 0.20 + 热度 0.15，再乘新鲜度
    base = (0.35 * info + 0.30 * dry + 0.20 * rel + 0.15 * eng) * (0.45 + 0.55 * decay)
    total = round(base * 100, 2)
    return {
        "total": total,
        "info_gap": round(info, 3),
        "dry_goods": round(dry, 3),
        "relevance": round(rel, 3),
        "engagement": round(eng, 3),
        "decay": round(decay, 3),
        "age_h": round(age_h, 1),
    }


def load_items(date: str) -> list[dict]:
    out: list[dict] = []
    for name, flag in (
        (f"items-{date}.json", None),
        (f"items-public-{date}.json", None),
        (f"items-sidehustle-{date}.json", "sidehustle"),
    ):
        path = ROOT / name
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("items") if isinstance(data, dict) else data
        for it in items or []:
            row = dict(it)
            row["_file"] = name
            if flag:
                row["_sidehustle"] = True
            if not row.get("summary") and row.get("summary_zh"):
                row["summary"] = row["summary_zh"]
            out.append(row)
    return out


def load_recent_pushed(date: str, days: int = 7) -> set[str]:
    """近 N 天已推事件 key / 归一化 URL。文件可选。"""
    keys: set[str] = set()
    if RECENT_PUSHED_PATH.is_file():
        try:
            data = json.loads(RECENT_PUSHED_PATH.read_text(encoding="utf-8"))
            cutoff = datetime.fromisoformat(date).date() - timedelta(days=days)
            for row in data if isinstance(data, list) else data.get("items") or []:
                d = str(row.get("date") or "")[:10]
                try:
                    if datetime.fromisoformat(d).date() < cutoff:
                        continue
                except ValueError:
                    continue
                if d == date:
                    continue
                for k in row.get("keys") or []:
                    keys.add(str(k).lower())
                for u in row.get("urls") or []:
                    keys.add(normalize_url(u))
        except Exception:
            pass
    return keys


def key_factor_for(it: dict, prefs_mod, conn, fb) -> dict:
    if prefs_mod is None or conn is None:
        return {"factor": 1.0, "keys": [], "why": []}
    card = {
        "url": it.get("url") or "",
        "title": it.get("title") or "",
        "author": it.get("handle") or it.get("author") or "",
        "handle": it.get("handle") or it.get("author") or "",
        "topic": it.get("topic") or "",
        "source": it.get("source") or "",
        "tags": it.get("tags") or [],
        "id": it.get("id") or "",
        "item_id": it.get("id") or "",
    }
    info = prefs_mod.item_factor(conn, card, fb=fb)
    return info


def dedupe(items: list[dict]) -> list[dict]:
    items = sorted(items, key=lambda i: -i["score"]["total"])
    kept: list[dict] = []
    by_url: dict[str, dict] = {}
    for item in items:
        nu = normalize_url(item.get("url") or "")
        twin = by_url.get(nu) if nu else None
        if twin is None:
            twin = next((k for k in kept if titles_similar(k.get("title") or "", item.get("title") or "")), None)
        if twin is not None:
            twin.setdefault("also", []).append(
                {"source": item.get("source"), "url": item.get("url"), "title": item.get("title")}
            )
            continue
        kept.append(item)
        if nu:
            by_url[nu] = item
    return kept


def apply_caps(ranked: list[dict], limit: int) -> tuple[list[dict], dict]:
    """同事件 EVENT_CAP、类目 CATEGORY_CAPS、topic_key TOPIC_CAP，再截断到 limit。"""
    picked: list[dict] = []
    cat_counts: dict[str, int] = defaultdict(int)
    topic_counts: dict[str, list] = defaultdict(list)
    event_counts: dict[str, int] = defaultdict(int)
    rejected = defaultdict(int)

    for it in ranked:
        ek = topic_key(it) or normalize_url(it.get("url") or "") or it.get("id") or it.get("title")
        cat = category_of(it)
        tk = topic_key(it)

        if ek and event_counts[ek] >= EVENT_CAP:
            # 并入第一条
            for p in picked:
                if topic_key(p) == ek or titles_similar(p.get("title") or "", it.get("title") or ""):
                    p.setdefault("also", []).append(
                        {"source": it.get("source"), "url": it.get("url"), "title": it.get("title")}
                    )
                    break
            rejected["event_cap"] += 1
            continue
        if cat and cat_counts[cat] >= CATEGORY_CAPS.get(cat, 99):
            rejected[f"cap_{cat}"] += 1
            continue
        if tk and len(topic_counts[tk]) >= TOPIC_CAP:
            topic_counts[tk][0].setdefault("also", []).append(
                {"source": it.get("source"), "url": it.get("url"), "title": it.get("title")}
            )
            rejected["topic_cap"] += 1
            continue

        picked.append(it)
        if ek:
            event_counts[ek] += 1
        if cat:
            cat_counts[cat] += 1
        if tk:
            topic_counts[tk].append(it)
        if len(picked) >= limit:
            break

    # 未入选的剩余记为 truncated
    seen = {id(x) for x in picked}
    for it in ranked:
        if id(it) not in seen:
            # 已被各类 cap 计过的跳过粗略：只对完全没进 rejected 增量的补 truncated
            pass
    leftover = len(ranked) - len(picked) - sum(rejected.values())
    if leftover > 0:
        rejected["truncated"] += leftover
    return picked, dict(rejected)


def mark_stale_by_age(items: list[dict], edition_date: str) -> None:
    """无外链日期时：条目 published_at 早于出刊日 3 天 → 降权。"""
    try:
        ed = datetime.fromisoformat(edition_date).replace(tzinfo=SH)
    except ValueError:
        return
    for it in items:
        pub = parse_time(it.get("published_at") or it.get("created_at"))
        if not pub:
            continue
        if (ed - pub.astimezone(SH)).days > STALE_DAYS:
            it["score"] = {
                **it["score"],
                "total": round(it["score"]["total"] * STALE_FACTOR, 2),
                "stale": STALE_FACTOR,
            }
            it["stale"] = True


def pick(date: str, limit: int = DEFAULT_LIMIT, prefs_db: str | None = None) -> dict:
    raw = load_items(date)
    now = datetime.now(timezone.utc)
    try:
        # 出刊日中午作为参照
        now = datetime.fromisoformat(f"{date}T12:00:00").replace(tzinfo=SH).astimezone(timezone.utc)
    except ValueError:
        pass

    recent = load_recent_pushed(date)
    exclude_counts: dict[str, int] = defaultdict(int)
    scored: list[dict] = []

    prefs_mod = conn = fb = None
    db_path = prefs_db or os.environ.get("PREFS_DB")
    if db_path and os.path.isfile(db_path):
        for d in ("/workspace/daily-portal/bin", "/srv/daily/bin", str(LIB)):
            if os.path.isfile(os.path.join(d, "prefs.py")):
                if d not in sys.path:
                    sys.path.insert(0, d)
                break
        try:
            import prefs as prefs_mod  # type: ignore
            conn = prefs_mod.connect(db_path)
            fb = prefs_mod.feedback_from_db(conn)
        except Exception as e:
            exclude_counts["prefs_error"] = 1
            prefs_mod = conn = fb = None
            sys.stderr.write(f"[score] prefs unavailable: {e}\n")

    for it in raw:
        reason = hard_exclude(it)
        if reason:
            exclude_counts[reason] += 1
            continue
        tk = topic_key(it)
        nu = normalize_url(it.get("url") or "")
        if (tk and tk in recent) or (nu and nu in recent):
            exclude_counts["recent_7d"] += 1
            continue
        parts = score_parts(it, now)
        it = dict(it)
        it["score"] = parts
        it["category"] = category_of(it)
        it["topic_key"] = tk
        info = key_factor_for(it, prefs_mod, conn, fb)
        factor = float(info.get("factor") or 1.0)
        it["key_factor"] = factor
        it["key_keys"] = info.get("keys") or []
        it["key_why"] = info.get("why") or []
        it["score"] = {
            **parts,
            "total": round(parts["total"] * factor, 2),
            "feedback": factor,
        }
        scored.append(it)

    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass

    scored = dedupe(scored)
    mark_stale_by_age(scored, date)
    scored.sort(key=lambda i: -i["score"]["total"])
    selected, cap_rej = apply_caps(scored, limit)
    for k, v in cap_rej.items():
        exclude_counts[k] += v

    return {
        "date": date,
        "tz": "Asia/Shanghai",
        "limit": limit,
        "input_total": len(raw),
        "after_exclude": len(scored),
        "selected_count": len(selected),
        "selected": [
            {
                "rank": i + 1,
                "id": it.get("id"),
                "title": it.get("title"),
                "url": it.get("url"),
                "source": it.get("source"),
                "topic": it.get("topic"),
                "category": it.get("category"),
                "topic_key": it.get("topic_key"),
                "score": it.get("score"),
                "key_factor": it.get("key_factor"),
                "key_why": it.get("key_why"),
                "summary": (it.get("summary") or it.get("summary_zh") or "")[:180],
                "also": it.get("also") or [],
            }
            for i, it in enumerate(selected)
        ],
        "excluded": dict(exclude_counts),
        "caps": {"event": EVENT_CAP, "topic": TOPIC_CAP, "category": CATEGORY_CAPS},
        "copy_prompt": str(LIB / "copy-prompt.md"),
        "rules": str(LIB / "pick-rules.md"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="叼报精选确定性打分")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    ap.add_argument("--json", action="store_true", help="只打 JSON 到 stdout")
    ap.add_argument("-o", "--out", help="写入 JSON 文件")
    ap.add_argument("--prefs-db", default=None, help="prefs.db 路径；默认读 PREFS_DB")
    args = ap.parse_args(argv)

    result = pick(args.date, limit=args.limit, prefs_db=args.prefs_db)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    if args.json or args.out:
        if args.json:
            print(text)
    else:
        print(f"date={result['date']} input={result['input_total']} "
              f"scored={result['after_exclude']} selected={result['selected_count']} "
              f"excluded={result['excluded']}")
        for row in result["selected"]:
            s = row["score"]
            print(
                f"{row['rank']:2d}. [{s['total']:5.1f}×{row['key_factor']}] "
                f"{(row.get('category') or '-'):12s} {row['title'][:48]}"
            )
            print(f"    {row['url']}")
    # 断言：条数与 cap
    assert result["selected_count"] <= args.limit, "over limit"
    cats = defaultdict(int)
    keys = defaultdict(int)
    for row in result["selected"]:
        if row.get("category"):
            cats[row["category"]] += 1
        if row.get("topic_key"):
            keys[row["topic_key"]] += 1
    for c, n in cats.items():
        cap = CATEGORY_CAPS.get(c)
        if cap is not None:
            assert n <= cap, f"{c} cap broken: {n}>{cap}"
    for k, n in keys.items():
        assert n <= max(TOPIC_CAP, EVENT_CAP), f"topic {k} over cap"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
