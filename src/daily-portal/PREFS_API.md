# DiaoDaily 叼报 · 偏好库接口说明（PREFS_API）

偏好数据与任何 bot 解耦：唯一真相是 VPS 上的 SQLite `/srv/daily/data/prefs.db`（WAL）。
访问层只有一个单文件模块 `/srv/daily/bin/prefs.py`（仅标准库，Python ≥3.10，SQLite ≥3.34 用于 trigram FTS）。
以后开发 MCP / CLI 只需包一层：直接 `import prefs`，或调用下面的 HTTP 接口。

## 1. 表结构
| 表 | 作用 | 关键列 |
|---|---|---|
| `signals` | 原始互动事件，**只追加**（触发器禁止 UPDATE） | id, ts(写入时间 UTC), **occurred_at(站点自己的时间，缺省=ts；衰减按它算)**, user, source_type(news\|design\|github\|chat\|manual\|hf\|hn\|reddit\|linuxdo\|dcr\|blog), item_id, item_url, title, topic, tags(JSON 数组), author, action(like\|dislike\|fav\|unfav\|read\|open\|rate\|skip\|star\|bookmark\|submit\|comment\|follow\|upvote), value, meta(JSON；`weight_factor` 0–2 乘到权重上，首次导入的历史=0.5), dedup_key(UNIQUE；约定 `<src>:<action>:<external_id>`) |
| `memories` | 偏好记忆，一行一句自然语言 | id, text, polarity(like\|avoid\|neutral), scope(topic\|author\|design\|format\|element\|…), key, tags(JSON), confidence(0–1), evidence_count, first_seen, last_seen, half_life_days, status(active\|archived), source(derived\|manual), score(衰减分), meta(JSON), embedding(BLOB，预留)，**valid_from, invalid_at, supersedes_id**；UNIQUE(source,scope,key)。被推翻/作废的记忆不删除：设 invalid_at、status=archived、key 改为 `<key>#inv:<id>`，新记忆 supersedes_id 指向旧行 |
| `memory_evidence` | 记忆 ← 信号 证据链（derive 写入，每条记忆最多 200 条） | memory_id, signal_id, weight(衰减后贡献) |
| `sources` | connector 状态 | name(PK), kind, account, cursor, last_sync, last_ok, health(ok\|error\|not_configured\|disabled\|unknown), error, meta(JSON 摘要) |
| `entities` | 实体归一（预留，下一期填） | id, name, aliases(JSON), type, canonical_id；UNIQUE(type,name) |
| `items` | 内容索引 | item_id(PK), url, title, summary, tags(JSON), source, date, embedding(BLOB，预留) |
| `config` | 参数 | half_life_days=14, explore_ratio=0.2, avoid_after_dislikes=3, min_abs_score=0.5, last_derive, schema_version=5 |
| `memories_fts` / `items_fts` | FTS5（trigram）覆盖 memories.text/tags、items.title/summary/tags | 由触发器自动同步 |

约定：
- `item_id` 为 slug：`[A-Za-z0-9][A-Za-z0-9._:/@#+-]{0,199}`。设计页条目 `design:<date>:<slug>`；页面已读 `x-page:<date>` / `design-page:<date>`。
- `tags` 里的前缀有含义：`format:web|app|…` → scope=format；`elem:<token-id>` → scope=element；`lang:<语言>` → scope=lang；`topic:<话题>` → scope=topic（GitHub 仓库 topics 用这个）。
- 迁移：`connect()` 自动执行 `migrate()`，幂等；旧库 signals 按原 id 重建（CHECK 扩充 + occurred_at=ts），行数不一致即回滚。
- 设计页 `topic` = `design:web|design:app`，`author` = 站点/App 品牌（`site` 中「·」之前）。
- 测试数据用 `TEST` 开头的 title/item_id 或 `meta.test=true`；`prefs.py purge-test` 清理。

## 2. 记忆组织原则
1. **一条记忆 = 一句短句 + 标签**，自带证据数、置信度、最近出现时间，LLM 不需要回表也能读懂。
2. **可检索**：FTS5 trigram（中英文都可，≥3 字符走 FTS，<3 字符自动退化为 LIKE）；`embedding` 列预留给下一期向量检索。
3. **可衰减**：权重 = Σ 动作分 × weight_factor × 0.5^(按 occurred_at 的天数/半衰期)，默认半衰期 14 天；动作分：like +1、fav +1.5、unfav −1.5、dislike −1、open +0.3、read +0.2、skip −0.3、rate = 星级−3（同一 item 只取最新一次打分）、star +1、bookmark +1.5、submit +0.8、comment +0.5、follow +1、upvote +0.7。
7. **双时间轴 + 证据链**（借鉴 Graphiti/Zep 的 bi-temporal 边与 Mem0 的 ADD/UPDATE/DELETE→这里改成「作废不删」）：derive 时极性翻转 → 旧记忆 invalid_at + 新记忆 supersedes_id；用户手动作废的 derived 记忆，只有出现比作废时间更新的信号才会重新生成。每条 derived 记忆可用 memory-evidence 回溯到具体信号。
8. **设计 Web:App = 5:5**：profile 的 `design` 段对 web/app 各自归一化（norm = 0.5×分/该类正分总和），like 列表两类交替各占一半；`by_kind` 给出原始数据。Web 收藏多也不会挤掉 App。
4. **derived 与 manual 分开**：`derive` 只改 source=derived 的行（幂等 upsert；|分|<0.5 归档）；`remember` 写 manual（半衰期默认 3650 天，用户亲口说的偏好）。
5. **回避规则**：同一 key 最近连续 3 次负向信号 → avoid（即使总分未到阈值）。
6. **探索名额**：`config.explore_ratio=0.2`，推荐方应留 20% 给画像之外的内容（profile 输出中带出）。

## 3. Python 函数（`import prefs`）
```python
c = prefs.connect()                       # 自动建表/迁移
prefs.add_signal(c, {...}, dedup_key=None) # -> {"id":..} | {"duplicate":True}；ValueError=校验失败
prefs.search(c, "手绘 动效", limit=20)      # -> {"memories":[...], "items":[...]}
prefs.profile(c, date="2026-10-25", top=8) # 当日画像（Asia/Shanghai 当日 23:59:59 为截止）
prefs.memories(c, scope=None, polarity=None, q=None, limit=50)
prefs.remember(c, "text", polarity="like", scope="topic", tags=[...], confidence=0.8, key=None)  # 别名 prefs.add_memory；同 key 极性变了 → 旧行作废、新行 supersedes
prefs.list_memories(c, scope=None, polarity=None, source=None, include_invalid=False, limit=100)
prefs.invalidate_memory(c, id, reason="user", superseded_by=None)
prefs.memory_evidence(c, id, limit=50)
prefs.export_md(c)                         # active 记忆按 scope 分组的 Markdown
prefs.source_update(c, "github", cursor=..., health="ok") / prefs.sources(c)
prefs.derive(c)                            # 汇总 signals -> memories
prefs.export(c)                            # 全量 JSON
prefs.design_signals(c, rating_record) / prefs.read_signal(c, date, kind)  # daily-api 用
```

## 4. CLI（`python3 /srv/daily/bin/prefs.py …`，输出 JSON；`profile --md` 输出 markdown）
| 命令 | 示例 |
|---|---|
| add-signal | `prefs.py add-signal --source-type news --action like --item-id hn:4123 --title "…" --topic selfhost --author 0xjackkk --tags vps,format:thread` 或 `--json '{…}'` / `--json -` |
| search | `prefs.py search "VPS 实操" --limit 10` |
| profile | `prefs.py profile [--date 2026-10-25] [--md] [--top 8]` |
| memories | `prefs.py memories [--scope design] [--polarity avoid] [--q 关键词] [--all]` |
| remember / add-memory | `prefs.py add-memory "喜欢自建和 VPS 实操，不看推广帖" --polarity like --scope topic --tags vps,自建 [--key k]` |
| list-memories | `prefs.py list-memories [--scope design] [--polarity like] [--source derived] [--include-invalid]` |
| invalidate-memory | `prefs.py invalidate-memory 123 --reason "不再喜欢" [--superseded-by 456]` |
| memory-evidence | `prefs.py memory-evidence 123 [--limit 20]` |
| sources | `prefs.py sources`（connector 健康） |
| derive | `prefs.py derive`（cron 每天 08:50 Asia/Shanghai） |
| export | `prefs.py export --json`（含 memory_evidence/sources/entities）；`prefs.py export --md`（active 记忆 Markdown） |
| 维护 | `import --md-json …`（幂等导入旧数据）、`stats`、`config [key value]`、`purge-test`、`--db <path>` 指定库 |

## 5. HTTP（daily-api，经 https://daily.jidadiao.fun）
| 方法 路径 | 鉴权 | 说明 |
|---|---|---|
| POST /api/signal | `Origin: https://daily.jidadiao.fun` 或 `https://jidadiao.github.io`（浏览器，仅 source_type=news/design，action=like\|dislike\|fav\|unfav\|read\|open\|skip\|comment；comment 须非空 note≤200；服务器定 ts/user/occurred_at，忽略 dedup_key，30 次/分钟/IP）或 `Authorization: Bearer <DAILY_API_TOKEN>`（任意 source_type，60 次/分钟） | body ≤4KB，字段同 signals；400 带错误字段名 |
| GET /api/profile?date=YYYY-MM-DD&limit=8 | Bearer | 画像 |
| GET /api/memories?scope=&polarity=&q=&limit= | Bearer | 记忆列表 / 检索 |
| GET /api/search?q=&limit= | Bearer | 记忆（仅 active）+ 内容全文检索 |
| GET /api/memory-evidence?id=&limit= | Bearer | 记忆 + 证据信号；id 非数字 400，不存在 404 |
| POST /api/memory/invalidate | Bearer，30 次/分钟 | body `{"id":123,"reason":"…","superseded_by":456?}`；重复调用返回 already_invalid（幂等） |
| POST /api/signals/batch | Bearer，**6 次/分钟**，body ≤512KB | `{"signals":[…≤200]}`；逐条同 add_signal 校验（dedup_key 须匹配 `<src>:<action>:<id>`），**任一条失败整批回滚**（400 带 index）；返回 inserted/duplicate |
| POST /api/favorite（原有） | Bearer | 行为不变；**同时**写 items + rate/fav signals（Worker 转发的设计页打分因此自动入库） |
| POST /api/read、GET /go/(x\|design)/DATE（原有） | Origin / 公开 | 行为不变；首次已读同时写 read signal |

示例：
```bash
curl -s -X POST https://daily.jidadiao.fun/api/signal -H 'Origin: https://daily.jidadiao.fun' -H 'Content-Type: application/json' \
  -d '{"source_type":"news","action":"fav","item_id":"x:2114031712430948410","item_url":"https://x.com/longhaiqwe123/status/2114031712430948410","title":"Agent Relay 让双 Agent 对聊","topic":"ai-tools","author":"longhaiqwe123","tags":["agent","format:thread"]}'
curl -s -H "Authorization: Bearer $DAILY_API_TOKEN" 'https://daily.jidadiao.fun/api/profile?date=2026-10-25'
curl -s -H "Authorization: Bearer $DAILY_API_TOKEN" 'https://daily.jidadiao.fun/api/search?q=手绘'
```
令牌只在 `/etc/daily/api.env`（600）；不要写进页面或仓库。

## 6. 建议的 MCP 工具（命名已对齐；所有工具带可选 `user_id`，默认 "jidadiao"）
| 工具 | 对应 | readOnly | destructive | idempotent |
|---|---|---|---|---|
| get_profile | GET /api/profile · `prefs.profile` | ✅ | ❌ | ✅ |
| search | GET /api/search · `prefs.search` | ✅ | ❌ | ✅ |
| list_memories | GET /api/memories · `prefs.list_memories` | ✅ | ❌ | ✅ |
| get_memory_evidence | GET /api/memory-evidence · `prefs.memory_evidence` | ✅ | ❌ | ✅ |
| add_memory | `prefs.add_memory`（HTTP 版待加 POST /api/memory） | ❌ | ❌ | ✅（同 key 覆盖；极性变化走 supersede） |
| invalidate_memory | POST /api/memory/invalidate | ❌ | ✅（软作废，可追溯，不删行） | ✅ |
| add_signal | POST /api/signal（批量：/api/signals/batch） | ❌ | ❌ | ✅（带 dedup_key 时） |

```json
[
 {"name":"get_profile","annotations":{"readOnlyHint":true,"destructiveHint":false,"idempotentHint":true},
  "description":"Decayed preference profile (topic/author/design[web:app=5:5]/format/element/lang) + manual memories + explore_ratio.",
  "inputSchema":{"type":"object","properties":{"user_id":{"type":"string","default":"jidadiao"},"date":{"type":"string","pattern":"^\\d{4}-\\d{2}-\\d{2}$"},"top":{"type":"integer","minimum":1,"maximum":20,"default":8}}}},
 {"name":"search","annotations":{"readOnlyHint":true,"destructiveHint":false,"idempotentHint":true},
  "description":"Full-text search over active preference memories and indexed items.",
  "inputSchema":{"type":"object","required":["query"],"properties":{"user_id":{"type":"string"},"query":{"type":"string","maxLength":200},"limit":{"type":"integer","minimum":1,"maximum":100,"default":20}}}},
 {"name":"list_memories","annotations":{"readOnlyHint":true,"destructiveHint":false,"idempotentHint":true},
  "inputSchema":{"type":"object","properties":{"user_id":{"type":"string"},"scope":{"type":"string"},"polarity":{"enum":["like","avoid","neutral"]},"source":{"enum":["derived","manual"]},"include_invalid":{"type":"boolean","default":false},"limit":{"type":"integer","maximum":200,"default":100}}}},
 {"name":"get_memory_evidence","annotations":{"readOnlyHint":true,"destructiveHint":false,"idempotentHint":true},
  "inputSchema":{"type":"object","required":["id"],"properties":{"user_id":{"type":"string"},"id":{"type":"integer"},"limit":{"type":"integer","maximum":100,"default":50}}}},
 {"name":"add_memory","annotations":{"readOnlyHint":false,"destructiveHint":false,"idempotentHint":true},
  "description":"Store/update a user-stated preference as one short sentence. Same key + different polarity supersedes the old memory.",
  "inputSchema":{"type":"object","required":["text","polarity"],"properties":{"user_id":{"type":"string"},"text":{"type":"string","maxLength":300},"polarity":{"enum":["like","avoid","neutral"]},"scope":{"type":"string","default":"topic"},"tags":{"type":"array","items":{"type":"string"}},"confidence":{"type":"number","minimum":0,"maximum":1,"default":0.8},"key":{"type":"string"}}}},
 {"name":"invalidate_memory","annotations":{"readOnlyHint":false,"destructiveHint":true,"idempotentHint":true},
  "description":"Soft-invalidate a memory (sets invalid_at; never deletes).",
  "inputSchema":{"type":"object","required":["id"],"properties":{"user_id":{"type":"string"},"id":{"type":"integer"},"reason":{"type":"string","maxLength":200},"superseded_by":{"type":"integer"}}}},
 {"name":"add_signal","annotations":{"readOnlyHint":false,"destructiveHint":false,"idempotentHint":true},
  "description":"Append one interaction signal. Use dedup_key <src>:<action>:<external_id> for idempotency.",
  "inputSchema":{"type":"object","required":["source_type","action"],"properties":{"user_id":{"type":"string"},"source_type":{"enum":["news","design","github","chat","manual","hf","hn","reddit","linuxdo","dcr","blog"]},"action":{"enum":["like","dislike","fav","unfav","read","open","rate","skip","star","bookmark","submit","comment","follow","upvote"]},"item_id":{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9._:/@#+\\-]{0,199}$"},"item_url":{"type":"string","format":"uri"},"title":{"type":"string","maxLength":300},"topic":{"type":"string","maxLength":80},"author":{"type":"string","maxLength":120},"tags":{"type":"array","items":{"type":"string","maxLength":40},"maxItems":20},"value":{"type":"number"},"occurred_at":{"type":"string","format":"date-time"},"dedup_key":{"type":"string"},"meta":{"type":"object"}}}}
]
```
说明：`user_id` 映射到 signals.user（当前单用户，记忆表暂无 user 列，多用户时再加）。MCP 服务器在 VPS 上直接 `import prefs`（stdio），或远端用 Bearer 调 HTTP。

## 7. Connectors（/srv/daily/bin/connectors/）
- 统一参数：`--user --feed --token --mode local|http --db --dry-run`；状态写 `sources` 表；cron `30 0 * * *`（UTC = 08:30 Asia/Shanghai）`run-all.sh >> /var/log/daily-connectors.log`（logrotate daily-connectors）；08:50 derive 不变。
- `github.py`：已上线（VPS 直连 api.github.com 可用；截断响应自动重试，star 分页 50）。可选 `GITHUB_TOKEN`（env 或 `/etc/daily/sources.env`，脚本不创建、不打印）。`--mode http` 用于盒子等境外机器抓取后经 /api/signals/batch 写入（需 env DAILY_API_TOKEN；每批间隔 11s 以符合 6 次/分钟）。
- `hn.py` `hf.py` `reddit.py` `linuxdo.py`：骨架，不联网；文件头注释是信号映射表；运行只把 sources.health 记为 not_configured。

## v3 变更（2026-10-25 夜，UTC+8）
### 来源配置 `/srv/daily/etc/sources.yaml`（无密钥；Glance 风格）
- `prefs.*` 覆盖 config 表同名键（half_life_days / explore_ratio / avoid_after_dislikes / min_abs_score）。
- `signals.<source>.half_life_days`：按来源设半衰期。当前 github=90 天，其余 14 天。`signals.<source>.enabled:false`（hn/hf/reddit/linuxdo）表示不连账号，run-all.sh 会把它们标成 health=disabled。
- `content:`：日报内容的公开来源清单（GitHub Trending/Search、HF trending、HN top、linux.do RSS、Reddit RSS），采集器还没写。
- 环境变量 `DAILY_SOURCES_YAML` 可以换路径。缺文件或缺 PyYAML 时退回 config 表。
### 衰减与去重
- 每条信号按自己的 `source_type` 取半衰期。derived 记忆的 `half_life_days` 取证据里占多数的来源，`meta.sources` 记录各来源的证据数。
- 聚合时 key 先 casefold 再分桶（"React" 和 "react" 算同一条，保留第一次出现的写法）。
### 记忆合并（借鉴 mem0）
- `remember/add_memory`：同 scope 的 active manual 记忆按字符二元组 Jaccard 计算相似度，≥0.75 视为同一条。
  - 极性相同：合并。evidence_count+1，置信度取较大值，tags 取并集，保留较长的措辞，`meta.merged` 记下原句。返回 `merged_into`、`similarity`。
  - 极性相反：旧记忆写 invalid_at，新记忆用 `supersedes_id` 指向它（借鉴 Graphiti 的事实有效期）。
- CLI `prefs.py dedupe-memories [--dry-run]` 一次性合并存量重复（当前 0 对）。
### HTTP
- `POST /api/memory`（Bearer，30 次/分钟，≤4KB）：`{"text","polarity"?,"scope"?,"tags"?,"confidence"?,"key"?}`，返回值同 remember。
- `POST /api/signal` 浏览器路径：Origin 允许 `https://daily.jidadiao.fun` 和 `https://jidadiao.github.io`（带 CORS 头，支持 OPTIONS 预检）。action 只能是 like|dislike|fav|unfav|read|open|skip|comment（comment 须非空 meta.note/note ≤200 字）。前端脚本见 `web/news-signal.js` 和 `web/NEWS_SIGNAL.md`。
- `GET /api/profile` 新增：
  - `half_life_by_source`
  - `recommend`：`{explore_ratio, exploit:[{scope,key,weight,score,evidence,why}], explore:[...]}`，weight 总和为 1。80% 按衰减分分给前 12 个喜好；20% 平均分给最多 6 个弱信号/新兴趣，回避项不入选。不含纯设计来源（设计看 `design` 块的 5:5）。
### Markdown 导出（借鉴 basic-memory）
- `export --md` 带 YAML frontmatter，每行写成 `- [polarity] 文本 #tag… (source, conf, evidence) \`#id\``，并注明可用的工具（search / memory-evidence / invalidate-memory）。

## v3.1 变更（2026-10-26，UTC+8）
- 浏览器 `/api/signal` 增加 `action=comment`；须 `meta.note` 或 `note` 非空且 ≤200 字；可选 `meta.vote=like|dislike`。
- `prefs.derive` 把带 note 的 comment 写成 item 范围记忆「喜欢/不喜欢〈标题〉：短评」，同 key 合并证据（幂等：已挂 memory_evidence 的 signal 跳过）。
- 推送摘要：`/workspace/digests/lib/pref-summary.py`（VPS 副本 `/srv/daily/bin/pref-summary.py`）。
- 外名统一「叼报」；`news-signal.js` 👍/👎 后可选短评行。

## v3.2 变更（2026-11-01，UTC+8）钥匙级偏好学习
移植 [lthero-big/newsp](https://github.com/lthero-big/newsp) 的 `scripts/collect/learning.py` 思路，落在 `bin/learning.py` + `prefs.py`。

### 行为
- 钥匙：`repo:owner/name` · `x:@账号` · `sub:版块` · `feed:源` · `site:域名` · `kw:词`（另兼容 `hf:` / `hffam:`）。
- **大话题 / 品牌不进 `kw:`**（AI、VPS、LLM、二次元、Python…）。
- 信号映射：dislike=少推(0.5)、unfav=全负(1.0)、like/fav/star/bookmark=多推(1.0)；rate≤2 少推、≥4 多推；comment 跟 `meta.vote`。
- **`dismiss`（收起）预留**：写入 signals，权重 0，**不进**钥匙学习；`skip`/`read`/`open` 同样不进钥匙学习（topic 聚合里 skip 仍为 −0.3，行为未改）。
- 公式：`strength=Σ w·0.5^(age/30)` 封顶 2；`factor=clamp(1−0.25·Σp,0.4,1)×(1+min(0.30,0.08·Σb))`。
- `kw:` 与一线实验室 `feed:`/`site:` 需 ≥2 条不同条目才惩罚（门控）。
- **manual 记忆优先**：`anime-hard` / `android` 等对匹配条目直接地板；钥匙形 manual key 可覆盖。
- 新表 `key_overrides(key,cleared_at,kind,meta)`：撤销少推/多推。

### API / CLI
| 接口 | 说明 |
|---|---|
| `prefs.learned_keys(c)` / CLI `learned` / `GET /api/learned` | 列出生效钥匙 |
| `prefs.clear_learned_key(c,key)` / CLI `clear-key` | 撤销 |
| `prefs.item_factor(c,card)` / CLI `factor` | 单条 factor |
| `prefs.apply_key_factors(c,items)` | 列表乘分排序 |
| `profile()` 增加 `keys` 段 | 给 12:00 例程 |

浏览器 `POST /api/signal` 允许 `action=dismiss`。
