#!/usr/bin/env python3
"""钥匙级偏好学习（移植自 lthero-big/newsp scripts/collect/learning.py，适配 prefs.db）。

钥匙：
  repo:owner/name · x:@账号 · sub:版块 · feed:源名 · site:域名 · kw:词
大话题（AI / VPS / LLM / 二次元…）与品牌名永不进入 kw:。
「收起」dismiss 与 skip/read/open 不算学习信号；dislike=少推(0.5)，unfav=全负(1.0)。
公式：strength = Σ weight·0.5^(age/30)，单钥匙封顶 2；
factor = clamp(1 − 0.25·Σpenalty, 0.4, 1) × (1 + min(0.30, 0.08·Σboost))。
kw: 与一线实验室的 feed:/site: 需 ≥2 条不同条目才生效（门控）。
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

BROAD = {
    "ai", "llm", "agent", "agents", "model", "models", "gpt", "benchmark", "diffusion",
    "fine-tune", "open weights", "open source", "quantization", "text-to-image",
    "text-to-video", "tokenizer", "transformer", "workflow", "coding agent",
    "computer use", "gguf", "hugging face", "inference", "图片视频音频",
    # 中文大话题 / 栏目名：不进 kw 惩罚
    "二次元", "二次元/acg", "acg", "动画", "anime", "vps", "中转站", "中转站/vps/自建", "中转/vps", "中转",
    "自建", "行业", "工具", "开源", "模型", "ai 模型", "localllama", "typescript",
    "javascript", "python", "rust", "go", "java", "c++", "新闻", "设计",
    # 噪声 / 元标签
    "github", "gitlab", "web", "app", "news", "design", "own", "people", "thread",
    "repo", "status", "null", "true", "false", "http", "https", "www",
}
BRANDS = {
    "gpt", "openai", "anthropic", "claude", "gemini", "google", "deepmind", "nvidia",
    "deepseek", "qwen", "meta", "llama", "mistral", "xai", "grok", "kimi", "moonshot",
    "minimax", "chatgpt", "codex", "cursor", "apple", "microsoft", "copilot", "amazon",
    "aws", "huggingface", "hugging_face", "flux", "sora", "veo", "midjourney", "zhipu",
    "glm", "baidu", "ernie", "alibaba", "tencent", "hunyuan", "bytedance", "doubao",
    "ollama", "vllm", "comfyui", "perplexity", "stability", "runway", "kling",
}
BRAND_RE = re.compile(
    r"^(?:%s)(?:$|[-_.\d])" % "|".join(re.escape(b) for b in sorted(BRANDS, key=len, reverse=True))
)
FIRST_PARTY_RE = re.compile(
    r"openai|anthropic|deepmind|google|gemini|hf-blog|huggingface|nvidia|"
    r"meta\.com|ai\.meta|mistral|x\.ai|qwen|deepseek|microsoft|apple"
)
GENERIC_HOSTS = {
    "github.com", "x.com", "twitter.com", "reddit.com", "old.reddit.com",
    "huggingface.co", "news.ycombinator.com", "youtube.com", "youtu.be",
    "medium.com", "substack.com", "i.redd.it", "v.redd.it", "mobbin.com",
}
HALF_LIFE_DAYS = 30
KEY_CAP = 2.0
PENALTY_PER = 0.25
PENALTY_FLOOR = 0.4
BOOST_PER = 0.08
BOOST_CAP = 0.30
DISLIKE_WEIGHT = 0.5   # 少推
TRASH_WEIGHT = 1.0     # unfav / 强负
LIKE_WEIGHT = 1.0

# 动作 → 学习侧（None = 不参与钥匙学习）
# dismiss 预留：UI「收起」不算负反馈
ACTION_SIDE = {
    "dislike": ("penalty", DISLIKE_WEIGHT),
    "unfav": ("penalty", TRASH_WEIGHT),
    "like": ("boost", LIKE_WEIGHT),
    "fav": ("boost", LIKE_WEIGHT),
    "star": ("boost", LIKE_WEIGHT),
    "bookmark": ("boost", LIKE_WEIGHT),
    "follow": ("boost", LIKE_WEIGHT),
    "upvote": ("boost", 0.7),
    "submit": ("boost", 0.8),
    # dismiss/skip/read/open/comment(单独处理)/rate(单独) → 见 signal_event
    "dismiss": None,
    "skip": None,
    "read": None,
    "open": None,
}

ANIME_MARKERS = ("二次元", "acg", "动画", "anime", "漫画", "声优")
ANDROID_MARKERS = ("安卓", "android")


def is_brand(term: str) -> bool:
    return bool(BRAND_RE.match(re.sub(r"\s+", "_", term.lower().strip())))


def gated(k: str) -> bool:
    """需 ≥2 条不同条目才惩罚的钥匙。"""
    return k.startswith("kw:") or (k.startswith(("feed:", "site:")) and bool(FIRST_PARTY_RE.search(k)))


def _norm_kw(t: str) -> str | None:
    t = str(t).lower().strip()
    t = re.sub(r"\s+", "_", t)
    t = t.strip("_")
    if len(t) < 3 or t in BROAD or is_brand(t):
        return None
    # 栏目式 topic 带斜杠也当大话题
    if "/" in t and t.replace("_", " ") in BROAD:
        return None
    if t in {b.replace(" ", "_") for b in BROAD}:
        return None
    return t


def item_keys(card: dict) -> list[str]:
    """从卡片或信号行抽出钥匙列表（小写、排序、去重）。"""
    keys: set[str] = set()
    url = str(card.get("url") or card.get("item_url") or "")
    label = str(card.get("source_label") or "")
    source = str(card.get("source") or card.get("source_type") or "").lower()
    author = str(card.get("author") or card.get("handle") or "").strip()
    topic = str(card.get("topic") or "").strip()
    item_id = str(card.get("item_id") or card.get("id") or "")

    m = re.match(r"^https?://github\.com/([\w.-]+)/([\w.-]+)", url, re.I)
    if m:
        keys.add(f"repo:{m.group(1)}/{m.group(2)}".lower())
    if not m and item_id.startswith("gh:repo/"):
        rest = item_id[len("gh:repo/"):]
        if "/" in rest:
            keys.add("repo:" + rest.lower())

    m = re.match(r"^https?://huggingface\.co/([\w.-]+)/([\w.-]+)", url, re.I)
    if m and source in ("hf", "huggingface"):
        keys.add(f"hf:{m.group(1)}".lower())
        keys.add(f"hffam:{m.group(1)}/{m.group(2).split('-')[0]}".lower())

    m = re.match(r"^X · @(\w+)", label, re.I)
    if m:
        keys.add(f"x:@{m.group(1)}".lower())
    elif author and (source in ("news", "x", "") or item_id.startswith("x:") or "x.com/" in url or "twitter.com/" in url):
        if re.match(r"^[\w.]{1,40}$", author) and source != "design":
            # design 的 author 是品牌名，不当 x:@
            if "x.com/" in url or "twitter.com/" in url or item_id.startswith("x:") or source in ("news", "x"):
                keys.add(f"x:@{author}".lower())

    m = re.match(r"^r/(\w+)", label, re.I)
    if m:
        keys.add(f"sub:{m.group(1)}".lower())
    elif source in ("reddit",) and topic and re.match(r"^[\w]+$", topic):
        keys.add(f"sub:{topic}".lower())
    elif item_id.startswith("reddit:") or "reddit.com/r/" in url:
        m = re.search(r"reddit\.com/r/([\w]+)", url, re.I)
        if m:
            keys.add(f"sub:{m.group(1)}".lower())

    if source == "rss" and label:
        keys.add(f"feed:{label}".lower())

    if source in ("hn", "rss", "linuxdo"):
        try:
            h = (urlparse(url).hostname or "").lower()
            h = h[4:] if h.startswith("www.") else h
            if h and h not in GENERIC_HOSTS:
                keys.add(f"site:{h}")
        except ValueError:
            pass

    kws = list(card.get("keywords") or [])
    tags = card.get("tags") or []
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except Exception:
            tags = []
    for t in tags:
        t = str(t)
        if t.startswith("topic:"):
            kws.append(t[6:])
        elif t.startswith(("format:", "elem:", "lang:", "src:", "pick:", "item_id:", "design", "comment")):
            continue
        elif ":" in t:
            continue
        else:
            kws.append(t)
    # topic 字段：仅当不是大话题时进 kw
    if topic and not topic.startswith("design:") and not topic.startswith("page:"):
        kws.append(topic)

    for k in kws:
        nk = _norm_kw(k)
        if nk:
            keys.add("kw:" + nk)

    return sorted(keys)


def strengths(events: list[dict], overrides: dict, now_ms: float, gate: bool = False) -> dict:
    out: dict = {}
    seen: dict = {}
    if gate:
        for n, e in enumerate(events):
            if (now_ms - e["at"]) / 864e5 <= HALF_LIFE_DAYS:
                for k in e.get("keys") or []:
                    if not (overrides.get(k) and e["at"] <= overrides[k]):
                        seen.setdefault(k, set()).add(e.get("id") or n)
    for e in events:
        for k in e.get("keys") or []:
            if overrides.get(k) and e["at"] <= overrides[k]:
                continue
            if gate and (k.startswith("kw:") and is_brand(k[3:]) or gated(k) and len(seen.get(k, ())) < 2):
                continue
            out[k] = out.get(k, 0.0) + e.get("weight", 1) * 0.5 ** ((now_ms - e["at"]) / 864e5 / HALF_LIFE_DAYS)
    return {k: min(KEY_CAP, v) for k, v in out.items()}


class Feedback:
    def __init__(self, data: dict | None, now_ms: float):
        data = data or {}
        ov = data.get("overrides") or {}
        self.trashed_ids = {e["id"] for e in data.get("trashed") or []}
        neg = (data.get("trashed") or []) + (data.get("disliked") or [])
        self.penalty = strengths(neg, ov, now_ms, gate=True)
        self.boost = strengths(
            data.get("liked") or [],
            {k[1:]: v for k, v in ov.items() if k.startswith("+")},
            now_ms,
        )
        self.overrides = ov
        self.now_ms = now_ms

    @classmethod
    def from_events(cls, liked, disliked, trashed, overrides, now_ms):
        return cls({"liked": liked, "disliked": disliked, "trashed": trashed, "overrides": overrides}, now_ms)

    def factor(self, keys: list[str]) -> float:
        p = sum(self.penalty.get(k, 0) for k in keys)
        b = sum(self.boost.get(k, 0) for k in keys)
        return round(max(PENALTY_FLOOR, 1 - PENALTY_PER * p) * (1 + min(BOOST_CAP, BOOST_PER * b)), 4)

    def why(self, keys: list[str], n: int = 2) -> list[str]:
        b = sorted((k for k in keys if self.boost.get(k)), key=lambda k: -self.boost[k])
        p = sorted((k for k in keys if self.penalty.get(k)), key=lambda k: -self.penalty[k])
        return (b or p)[:n]


def _ts_ms(v) -> float:
    if v is None:
        return datetime.now(timezone.utc).timestamp() * 1000
    if isinstance(v, (int, float)):
        return float(v) if v > 1e12 else float(v) * 1000
    d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.timestamp() * 1000


def signal_to_card(row) -> dict:
    """sqlite Row / dict → item_keys 用的卡片。"""
    r = dict(row)
    tags = r.get("tags") or []
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except Exception:
            tags = []
    st = (r.get("source_type") or "").lower()
    author = r.get("author") or ""
    url = r.get("item_url") or r.get("url") or ""
    topic = r.get("topic") or ""
    label = ""
    if st == "news" or (url and ("x.com/" in url or "twitter.com/" in url)):
        if author:
            label = f"X · @{author}"
    elif st == "reddit":
        sub = topic if topic and re.match(r"^[\w]+$", topic) else ""
        if not sub:
            for t in tags:
                if str(t).startswith("topic:") and re.match(r"^[\w]+$", str(t)[6:]):
                    sub = str(t)[6:]
                    break
        if sub:
            label = f"r/{sub}"
    source = {"news": "news", "github": "github", "hf": "hf", "hn": "hn",
              "reddit": "reddit", "linuxdo": "linuxdo", "design": "design"}.get(st, st)
    return {
        "url": url,
        "item_url": url,
        "item_id": r.get("item_id") or r.get("id") or "",
        "id": r.get("item_id") or r.get("id") or "",
        "source": source,
        "source_type": st,
        "source_label": label,
        "author": author,
        "handle": author,
        "topic": topic,
        "tags": tags,
        "title": r.get("title") or "",
        "keywords": [],
    }


def signal_event(row) -> tuple[str, dict] | None:
    """一条信号 → ('liked'|'disliked'|'trashed', event) 或 None（不参与学习）。"""
    r = dict(row)
    action = r.get("action")
    meta = r.get("meta") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            meta = {}
    if meta.get("test"):
        return None

    side_w = ACTION_SIDE.get(action, None)
    weight = None
    side = None

    if action == "rate":
        val = r.get("value")
        if val is None:
            return None
        if val <= 2:
            side, weight = "disliked", DISLIKE_WEIGHT
        elif val >= 4:
            side, weight = "liked", LIKE_WEIGHT
        else:
            return None
    elif action == "comment":
        vote = meta.get("vote")
        if vote == "dislike":
            side, weight = "disliked", DISLIKE_WEIGHT
        elif vote == "like":
            side, weight = "liked", LIKE_WEIGHT
        else:
            return None
    elif side_w is None:
        return None
    else:
        side_name, weight = side_w
        side = {"penalty": "disliked", "boost": "liked"}[side_name]
        if action == "unfav":
            side = "trashed"

    card = signal_to_card(r)
    keys = item_keys(card)
    if not keys:
        return None
    eid = r.get("item_id") or f"sig:{r.get('id')}"
    at = _ts_ms(r.get("occurred_at") or r.get("ts"))
    return side, {"id": eid, "at": at, "keys": keys, "weight": weight, "signal_id": r.get("id")}


def card_markers_hit(card: dict, markers: tuple[str, ...]) -> bool:
    blob = " ".join([
        str(card.get("topic") or ""),
        str(card.get("title") or ""),
        " ".join(str(t) for t in (card.get("tags") or [])),
    ]).lower()
    return any(m.lower() in blob for m in markers)


