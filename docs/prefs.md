# 偏好系统

运行时数据库在 VPS：`/srv/daily/data/prefs.db`（WAL）。**只提交 schema 和接口说明，不提交数据或备份库。**

权威接口文档：`src/daily-portal/PREFS_API.md`。实现：`src/daily-portal/bin/prefs.py`、`learning.py`、`api.py`。

## 原则

- 硬规则以 `src/digests/lib/pick-rules.md` 和库里的 **manual 记忆**为准。
- 钥匙是 `repo:` / `x:@` / `sub:` / `feed:` / `site:` / `kw:`，不是「AI」「VPS」这种大话题。
- `dismiss`（收起）不算负反馈；只有 dislike / unfav / 低星才少推。
- 少推 −25%/次、多推 +8%/次、30 天半衰期；地板 0.4，多推帽 +30%。
- `score.py` 通过 `prefs.item_factor` / `apply_key_factors` 乘钥匙 factor。

常用 CLI（在 VPS 上，或 `PREFS_DB=/srv/daily/data/prefs.db`）：

```bash
python3 prefs.py learned
python3 prefs.py clear-key 'x:@foo'
python3 prefs.py factor --url 'https://...' --author '...'
```

短评摘要（12:00 可选）：

```bash
# 在 VPS
PREFS_DB=/srv/daily/data/prefs.db python3 /srv/daily/bin/pref-summary.py
# 在箱子上会 SSH 到 VPS 跑远端脚本（需要 DAILY_VPS）
python3 src/digests/lib/pref-summary.py
```

## Schema（schema_version = 5）

`SOURCE_TYPES`：news, design, github, chat, manual, hf, hn, reddit, linuxdo, dcr, blog

`ACTIONS`：like, dislike, fav, unfav, read, open, rate, skip, star, bookmark, submit, comment, follow, upvote, dismiss

表：

```
signals (
  id INTEGER PRIMARY KEY,
  ts TEXT NOT NULL,
  user TEXT NOT NULL DEFAULT 'jidadiao',
  source_type TEXT NOT NULL,          -- CHECK 见 SOURCE_TYPES
  item_id TEXT, item_url TEXT, title TEXT, topic TEXT,
  tags TEXT NOT NULL DEFAULT '[]',
  author TEXT,
  action TEXT NOT NULL,               -- CHECK 见 ACTIONS
  value REAL,
  meta TEXT NOT NULL DEFAULT '{}',
  dedup_key TEXT UNIQUE,
  occurred_at TEXT
)
-- signals 只追加，UPDATE 会被 trigger 拒绝

memories (
  id INTEGER PRIMARY KEY,
  text TEXT NOT NULL,
  polarity TEXT NOT NULL,             -- like / avoid / neutral
  scope TEXT NOT NULL, key TEXT,
  tags TEXT NOT NULL DEFAULT '[]',
  confidence REAL NOT NULL DEFAULT 0.5,
  evidence_count INTEGER NOT NULL DEFAULT 0,
  first_seen TEXT, last_seen TEXT,
  half_life_days REAL NOT NULL DEFAULT 14,
  status TEXT NOT NULL DEFAULT 'active',   -- active / archived
  source TEXT NOT NULL,                    -- derived / manual
  score REAL, meta TEXT NOT NULL DEFAULT '{}',
  embedding BLOB,
  valid_from TEXT, invalid_at TEXT, supersedes_id INTEGER,
  UNIQUE(source, scope, key)
)

items (
  item_id TEXT PRIMARY KEY,
  url TEXT, title TEXT, summary TEXT,
  tags TEXT NOT NULL DEFAULT '[]',
  source TEXT, date TEXT, embedding BLOB
)

config (k TEXT PRIMARY KEY, v TEXT)

memory_evidence (
  memory_id INTEGER NOT NULL,
  signal_id INTEGER NOT NULL,
  weight REAL,
  PRIMARY KEY(memory_id, signal_id)
)

sources (
  name TEXT PRIMARY KEY, kind TEXT, account TEXT,
  cursor TEXT, last_sync TEXT, last_ok TEXT,
  health TEXT NOT NULL DEFAULT 'unknown',
  error TEXT, meta TEXT NOT NULL DEFAULT '{}'
)

entities (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  aliases TEXT NOT NULL DEFAULT '[]',
  type TEXT NOT NULL DEFAULT 'topic',
  canonical_id TEXT, meta TEXT NOT NULL DEFAULT '{}',
  UNIQUE(type, name)
)

key_overrides (
  key TEXT PRIMARY KEY,
  cleared_at TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'both',   -- penalty / boost / both
  meta TEXT NOT NULL DEFAULT '{}'
)

-- FTS5 trigram：memories_fts、items_fts（由 trigger 维护）
```

半衰期默认 14 天；GitHub 账号信号 90 天；blog 内容源在 `etc/sources.yaml` 里是 30 天。可通过 `/srv/daily/etc/sources.yaml` 覆盖（仓库 `src/daily-portal/etc/sources.yaml`）。

页面互动：`news-signal.js` POST `https://daily.jidadiao.fun/api/signal`（github.io 走 CORS）。服务端会挡带 headless/python/curl 的 UA，返回 403 `{"error":"ua"}`，无头测试时是正常现象。

VPS cron（服务器时区 UTC）：

- `50 0 * * *` → 08:50 上海时间 `prefs.py derive`
- `30 0 * * *` → 08:30 上海时间 `connectors/run-all.sh`（目前实际只开了 GitHub 公开数据）

用户决定：只连 GitHub 账号公开数据，HN / Reddit / linux.do / HF 账号不连。
