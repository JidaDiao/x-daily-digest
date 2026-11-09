# 各环节输入输出

路径若无特别说明，箱子上以 `/workspace/digests` 为根；仓库内脚本在 `src/digests/`。
日期文件名一律 `YYYY-MM-DD`。示例见 `docs/examples/`。

## 1. X 素材 `items-DATE.json`

| 字段 | 说明 |
|---|---|
| `date` | `YYYY-MM-DD` |
| `issue` | 如 `NO. 1109`（月日） |
| `source` | 习惯写 `Grok Bot X 日报` |
| `window` | 字符串，如 `2026-11-08 12:00 至 2026-11-09 10:30（Asia/Shanghai）` |
| `items[]` | 约 8–15 条，宁少勿滥 |

每条至少有 `source, id, title, url`；常用：

| 字段 | 说明 |
|---|---|
| `source` | `"x"` |
| `id` | 推文数字 id（`data-sig-id` 会变成 `x:<id>`） |
| `title` | 尽量不超过 14 个汉字 |
| `url` | `https://x.com/<handle>/status/<id>` |
| `summary` | 一句中文。传闻标「未证实」 |
| `cat` | 教程 / 工具 / 行业 / 观点 / 实测 / 研究 / AIGC / 变现 |
| `handle` | 作者 |
| `likes`, `rts` | 互动 |
| `media` | `media/<id>.jpg`，可空 |
| `avatar` | `media/<handle>.jpg` |

配图目录：`/workspace/digests/media/`（运行时文件，不提交 main）。

## 2. 公开源 `items-public-DATE.json`

由 `src/daily-portal/collectors/collect.py` 写出。

顶层：`date, issue, source, generated, profile_used, status, items`。

`status` 按来源：`ok / fetched / picked / skipped / error / secs`。

`items[].source` 取值：`github` | `hf` | `hn` | `linuxdo` | `reddit` | `dcr` | `blog`。

共用字段：`id, title, url, summary, summary_en, summary_zh, tags, author, pick, match`。

补充字段：

| 来源 | 额外字段 |
|---|---|
| github | `stars`, `via`（trending / search-new） |
| hf | `likes`, `upvotes`, `via` |
| hn | `points`, `comments`, `discuss` |
| dcr | `published_at`, `via=rss` |
| blog | `site`, `published_at`, `blog_rank`, `think_score`, `think_why`, `via` |

约束：

- 社区简介必须是中文：写在 `summary_zh`（构建时会覆盖 `summary`，英文留在 `summary_en`）。缺汉字会让 `build_daily.py` 报错。
- blog：`feeds-blog.json` 白名单，每站每天最多 1 条，总量通常 1–2（推送展示 1–3）。`id` 形如 `blog:<site>/<slug>`。
- dcr：Did Codex Reset 中文 RSS `https://didcodexreset.com/rss/news.xml?lang=zh-CN`，`id` 形如 `dcr:<hex>`。

选择逻辑概要：调 VPS `GET /api/profile` 取 exploit/explore；轮转取约 16 条 exploit + 4 条 explore；每源 ≤5（blog ≤2），总数 ≤20。

## 3. 周六副业 `items-sidehustle-DATE.json`

顶层常见字段：`date, source, group, note, items, alternates`。

每条：`id`（如 `sh-YYYYMMDD-N`）、`title`、`url`、`summary`（含合规提醒，如需要）。

没有这个文件 = 当天无副业，不是故障。

## 4. 打分输出 `/tmp/pick-DATE.json`

```bash
PREFS_DB=/srv/daily/data/prefs.db \
  python3 src/digests/lib/score.py --date DATE --json -o /tmp/pick-DATE.json
```

关键字段：

- `selected[]`：≤15，按 score 降序，供消息一使用
- `excluded[]`：供「今天筛掉 N 条」统计
- 每条通常带 `score`、`factor`（钥匙）、原因标签

没有 `prefs.db` 时 factor 记为 1.0，脚本仍可跑。

## 5. 叼报页

| 产物 | 路径 |
|---|---|
| 日模板 | `/workspace/digests/pages/DATE.py` |
| 构建结果 | `/workspace/digests/web/DATE.html` |
| 发布副本 | gh-pages 根目录 `DATE.html` |
| 组合记录 | `/workspace/digests/used-combos.json` 的 `DATE` 键 |
| 手机截图 | `/workspace/digests/shots/DATE-VER/` |

`pages/DATE.py` 的 `CFG` / `RESULT['cfg']` 必填字段见 `src/digests/web/DAILY.md`：`theme, bg, elements, stance, archetype, vertical_list, dims, own`，建议带上相对前一天的 `diffs`（style / motion / ui / ux / card）。

## 6. 设计灵感页

| 产物 | 路径 |
|---|---|
| 工作区 | `/workspace/inspo/web/design/`（仓库 `src/design/`） |
| 块 | `blocks/NN-<key>.html` |
| 构建 | `python3 build.py DATE` → `DATE.html` |
| 发布 | gh-pages `design/DATE.html` + 新素材（如 `.mp4.b64`） |
| 状态 | `stage/DATE/state.json` |

## 7. 门户链接

| 用途 | URL | 期望 |
|---|---|---|
| 叼报正式入口 | `https://daily.jidadiao.fun/go/x/DATE` | GET 302 → `/x/DATE.html` |
| 设计正式入口 | `https://daily.jidadiao.fun/go/design/DATE` | GET 302 → `/design/DATE.html` |
| 叼报备份 | `https://jidadiao.github.io/x-daily-digest/DATE.html` | GET 200 |
| 设计备份 | `https://jidadiao.github.io/x-daily-digest/design/DATE.html` | GET 200 |

HEAD 这些 `/go/` 地址返回 501 是正常的，不要当成故障。

## 8. data-sig-id

由 `src/digests/news_signal.py` 的 `normalize_sig_id` / `sig_attrs()` 生成，必须稳定：

- X：`x:<post id>`
- GitHub：`gh:repo/<owner>/<name>`
- HF：`hf:<model>`
- HN：`hn:<id>`
- linux.do：`ld:<topic id>`
- Reddit：`reddit:<id>`
- DCR：`dcr:<id>`
- blog：`blog:<site>/<slug>`

已上线页面禁止改已有条目的 id。测试用 `x:TEST-...` 这类明显假 id。
