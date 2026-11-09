# x-daily-digest

DiaoDaily「叼报」资讯 + 设计灵感的源码、规则和每日 runbook。

- `main`：脚本、规则、交接文档。推 `main` **不会**更新网站。
- `gh-pages`：线上产物（每日 HTML、`design/`、`hub/`）。**不要改已上线页面的 `data-sig-id`，也不要 force push。**

接手每日任务的 agent 请先读 **[AGENTS.md](AGENTS.md)**，再按 `docs/` 里对应章节执行。

## 这个仓库能让你做什么

一个新 agent 只读 `main`，就应该知道：

1. 每天几点做什么（见 [docs/schedule.md](docs/schedule.md)）
2. 素材从哪来、长什么样（见 [docs/io-schema.md](docs/io-schema.md)）
3. 怎么出设计灵感页和叼报资讯页（见 [docs/design-inspiration.md](docs/design-inspiration.md)、[docs/diaodaily-page.md](docs/diaodaily-page.md)）
4. 怎么校验、怎么同步门户、怎么推送两条消息（见 [docs/publish-verify.md](docs/publish-verify.md)）
5. 出了故障怎么办（见 [docs/troubleshooting.md](docs/troubleshooting.md)）
6. 用户偏好和历史口头规则（见 [docs/prefs.md](docs/prefs.md)、[docs/history-rules.md](docs/history-rules.md)）

## 目录

| 路径 | 作用 |
|---|---|
| `AGENTS.md` | 接手 agent 的每日 runbook |
| `docs/` | 流程图、schema、例程、发布、故障、偏好、历史规则 |
| `src/digests/` | 叼报打分、出页、校验脚本（箱子上对应 `/workspace/digests`） |
| `src/daily-portal/` | 公开源抓取、门户、偏好库、同步脚本（箱子上对应 `/workspace/daily-portal`，VPS 对应 `/srv/daily`） |
| `src/design/` | 设计灵感页构建工具（箱子上对应 `/workspace/inspo/web/design`） |
| `digests/lib/` | 精选硬规则与打分的另一份入口（与 `src/digests/lib/` 保持同步） |
| `portal/` | 门户/偏好库的较早快照；**以 `src/daily-portal/` 为准** |
| `scripts/hub_entry.sh` | 发布后更新 `hub/index.html` |

## 命名

- 对外推送和资讯页叫 **「叼报」**。
- 总览/往期入口页仍叫 **「X 日报」**（不要为了统一改名而覆盖线上 `index.html` / `hub/index.html`）。
- 设计线对外叫 **「设计灵感」**。

## 安全

不要把密钥、令牌、密码、私钥、VPS 密码或带凭据的文件提交进仓库。需要凭据的地方只写环境变量名，配置方法见 `.env.example` 和 [docs/environment.md](docs/environment.md)。
