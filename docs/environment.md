# 环境变量、依赖和路径对照

示例文件：仓库根目录 `.env.example`（只有占位值）。真正的密钥放在：

- 箱子：`~/.ssh/vps_jidadiao`（私钥文件，不入库）
- VPS：`/etc/daily/api.env`（`DAILY_API_TOKEN`，权限 600）
- 可选：VPS `/etc/daily/sources.env`（各社区 token，目前用户选择大多不连）
- linux.do User API Key 若启用：连接器目录下的 `.secrets/`（已 gitignore，且当前账号连接是关闭的）

## 环境变量

| 变量 | 用途 | 默认/位置 |
|---|---|---|
| `TZ` / 本地时区 | 日程按上海时间 | Asia/Shanghai |
| `DIGESTS_ROOT` | `score.py` 读 items | `/workspace/digests` |
| `PREFS_DB` | 钥匙 factor、短评 | `/srv/daily/data/prefs.db` |
| `DAILY_VPS` | SSH 主机名或 IP | **必须本地配置**，仓库里写 `<VPS_HOST>` |
| `DAILY_SSH_KEY` | SSH 私钥路径 | `~/.ssh/vps_jidadiao` |
| `DAILY_API_TOKEN` | daily-api Bearer | 只存在 VPS `/etc/daily/api.env` |
| `DAILY_SOURCES_YAML` | 半衰期等 | `/srv/daily/etc/sources.yaml` |
| `PAGES_DIR` / `SRC_DIR` | `hub_entry.sh` 克隆目录 | `/tmp/xdd-pages`、`/tmp/xdd-main` |

采集脚本会 SSH 进 VPS，在远端执行 `source /etc/daily/api.env` 再 curl `127.0.0.1:9090`，所以 token 不出 VPS。

## 软件依赖

箱子（出页 / 抓取 / 检查）：

- Python 3，标准库为主
- `paramiko`（采集写回 VPS、pref-summary SSH）
- `PyYAML`（读 `sources.yaml`；缺了会静默跳过覆盖）
- Playwright + 系统 Chrome `/usr/bin/google-chrome`（`chk.py`、设计页 `tools/shot.py` / `check.py`）
- `ffmpeg`（压缩 Mobbin 视频）
- `git`、`curl`、`rsync`（VPS sync 使用）

VPS：

- nginx、python3、git、curl
- systemd `daily-api.service` → `127.0.0.1:9090`
- cron：每 30 分钟 `sync.sh`；08:30 `connectors/run-all.sh`；08:50 `prefs.py derive`（以上为上海时间，cron 本身按 UTC 写）

## 连接器清单（接手 agent 需要）

| 能力 | 做什么 | 没有时 |
|---|---|---|
| GitHub 写权限（`JidaDiao/x-daily-digest`） | 推 gh-pages 页面、偶尔推 main | 无法上线 |
| 公开 X 读取 | 每天 items-DATE.json | 叼报可以只做公开源，并注明 X 缺失 |
| Mobbin（`search_screens` / `search_flows`） | App 4 条原图/原视频 | 设计页 `--allow-short` 并说明 |
| SSH 到 VPS | sync、读 profile、写候选 batch、pref-summary | 门户镜像会滞后；打分没有钥匙 factor |
| 给用户发消息 | 12:00 两条独立消息 | 页面仍可上线，但用户看不到推送 |
| 可选：设计反馈 Worker | 设计页评分备份到 GitHub issue | 主存储已在 VPS `/api/signal` 和 `/api/favorite` |

不需要、也不应索取：linux.do 登录态、Reddit OAuth（默认关闭）、任何支付密钥。

## 路径对照

| 运行时（历史箱子） | 本仓库 `main` |
|---|---|
| `/workspace/digests/*.py`、`lib/`、`web/DAILY.md` | `src/digests/` |
| `/workspace/digests/lib/pick-rules.md` 等 | `src/digests/lib/` 与 `digests/lib/` |
| `/workspace/digests/hub_entry.sh` | `scripts/hub_entry.sh` |
| `/workspace/daily-portal/` | `src/daily-portal/` |
| `/workspace/inspo/web/design/` | `src/design/` |
| `/workspace/inspo/preferences.md`、`recommended.md` | 运行时笔记，不进 main |
| `/workspace/digests/items-*.json`、`media/`、`web/*.html` | 运行时产物；HTML 发布到 **gh-pages** |
| VPS `/srv/daily/bin` | 部署 `src/daily-portal/bin` |
| VPS `/srv/daily/site` | `gh-pages` 镜像 |
| VPS `/srv/daily/data` | 偏好和反馈数据，不入库 |
| VPS `/srv/daily/www` | 门户首页、图标、`pwa-nav.js`、`read-beacon.js` |
| VPS `/etc/nginx/sites-available/daily.jidadiao.fun` | 见 `docs/nginx-standalone.example.conf` |

改脚本：先改仓库 `src/`，再同步到箱子对应目录（或反向同步后提交）。提交前扫描密钥，见根 README。
