# 接手 agent 每日 runbook

你负责用户每天约 12:00（Asia/Shanghai）看到的两条独立消息：**叼报**（资讯精选）和 **设计灵感**。用户查看所有每日推送都只从这里进。不配图，不放往期入口。缺哪个来源只说明缺失，不要自己补抓假数据。

本文是入口。细节链到 `docs/` 和 `src/`，不要只靠记忆。

## 0. 每天开始前

1. 时区按 **Asia/Shanghai（UTC+8）**。
2. 读 `src/digests/lib/pick-rules.md` 和 `docs/history-rules.md`。
3. 确认箱子路径还在（历史运行环境）：

| 角色 | 箱子绝对路径 | 本仓库 |
|---|---|---|
| 叼报素材与出页 | `/workspace/digests` | `src/digests/` |
| 公开源抓取与门户脚本 | `/workspace/daily-portal` | `src/daily-portal/` |
| 设计灵感工作区 | `/workspace/inspo/web/design` | `src/design/` |
| 设计元素收藏笔记 | `/workspace/inspo/preferences.md`、`recommended.md` | 运行时文件，不进 main |
| 偏好库 | VPS `/srv/daily/data/prefs.db` | 只提交 schema 说明，不提交数据 |
| SSH 密钥 | `~/.ssh/vps_jidadiao` | 只写路径 |

如果新环境没有这些目录：从本仓库 `src/` 拷到对应位置，再按 `.env.example` 配环境变量。

## 1. 每日时间线

```
凌晨前后     设计灵感页上线（Web 4 + App 4）
10:20        公开源抓取 → items-public-DATE.json
约 10:30     X 素材到达 → items-DATE.json
周六约 10:16  另有副业 items-sidehustle-DATE.json（其他日子没有，不算缺失）
素材齐后     出叼报资讯页 → 手机尺寸 review → 推 gh-pages
随后         SSH 到 VPS 跑 /srv/daily/bin/sync.sh
12:00        发两条消息：先叼报，再设计灵感
```

详情与例程原文改写见 [docs/schedule.md](docs/schedule.md)，流程图见 [docs/flow.md](docs/flow.md)。

历史上这几段由不同 bot 分担：

- X 素材 / 周六副业：Grok Bot（公开 X 读取接口）
- 设计灵感页 + 叼报资讯页：前端设计灵感库（Mobbin 连接器 + GitHub 推送）
- 10:20 抓取、12:00 推送、门户 sync：每日推送 / DiaoDaily

现在整条线交给你。缺连接器时按 [docs/troubleshooting.md](docs/troubleshooting.md) 降级，不要编数据。

## 2. 公开源抓取（10:20）

```bash
# 箱子上的历史入口（例程一直这么跑）
/workspace/daily-portal/collectors/run.sh
# 仓库内对应
./src/daily-portal/collectors/run.sh
```

- 文档：`src/daily-portal/collectors/README.md`
- 产出：`/workspace/digests/items-public-YYYY-MM-DD.json`，并尝试写入 VPS 候选库
- 完成后只确认：文件存在、各来源 `status.*.picked` 条数、失败原因
- **linux.do** 已知被 Cloudflare 拦截，标 `skipped` 即可
- **reddit** 常见 SSL 超时，也跳过
- 失败不要自己补抓，不要改用登录态硬闯

依赖：`python3`、`paramiko`、`DAILY_VPS` + `~/.ssh/vps_jidadiao`。VPS 上的 `DAILY_API_TOKEN` 只在 VPS 本地 `source /etc/daily/api.env`，不出机器、不落仓库。

## 3. X 素材（约 10:30）与周六副业

做法见 [docs/x-collect.md](docs/x-collect.md)。

- 窗口：前一天 12:00 到当天 10:30（Asia/Shanghai）
- 话题：AI 模型与价格、中转/VPS/网络封锁、一手实测、开源工具
- **整类不收二次元/ACG/动画**（用户原话：「以后不要给我推动画了」）
- 先读 `src/digests/lib/pick-rules.md`
- 写出 `/workspace/digests/items-YYYY-MM-DD.json`
- 工具：公开 X 读取（`search_posts_all` 用 `start_time`，不要在 query 里写 `since:`；`get_posts_by_ids` 取配图）
- 429 就用已拿到的，缺的在推送里说明
- 周六另写 `/workspace/digests/items-sidehustle-YYYY-MM-DD.json`（务实、可执行；过滤夸大收益/拉人头/卖课）。没有像样内容就不要写这个文件

## 4. 设计灵感页（凌晨前后）

做法见 [docs/design-inspiration.md](docs/design-inspiration.md) 和 `src/design/HOWTO.md`。

硬规则：

- 每天 **8 条：Web 4 + App 4**。不够不凑。
- Web：代码复刻 live demo（可调参/可复制）；App：Mobbin **原图或原视频**，不复刻
- 每条标 `交互` 或 `界面`（兼具最多 1 条）；交互 ≥ 4、界面 ≥ 3
- 至少 1 条以卡片/图标/标签的「长相」为主
- 上线前 `390/360` 手机检查，无横向溢出
- 设计页**不必**每天换外壳；每天换整体风格的是叼报资讯页
- 推到 `gh-pages` 的 `design/YYYY-MM-DD.html`（以及新增素材）。用 GET 校验 200，并和本地 `cmp`
- 门户链接：`https://daily.jidadiao.fun/go/design/YYYY-MM-DD`（GET 会 302；HEAD 返回 501 是正常的）

## 5. 叼报资讯页（素材齐之后）

做法见 [docs/diaodaily-page.md](docs/diaodaily-page.md) 和 `src/digests/web/DAILY.md`。

1. 确认当日 `items-DATE.json` + `items-public-DATE.json` 都在（缺哪个就在页上和推送里说明）。
2. 先定一句设计立场，再从收藏元素里选料。每天换整体风格 / 动画 / UI / UX / 卡片图表，五维相对前一天都要有差异。要有审美立场，不能太 AI。
3. 写 `pages/YYYY-MM-DD.py`（`RESULT['cfg']` 含 stance / archetype / dims / elements / own / bg）。
4. `python3 build_daily.py YYYY-MM-DD`（在 `/workspace/digests` 或拷出来的 `src/digests`）。
5. 内联最新 `src/daily-portal/web/news-signal.js`（扁平 2D SVG 评分按钮，按下态实心底色反白）。**不要手写另一套按钮。**
6. 每条容器必须有稳定的 `data-sig-id`（`x:` / `gh:repo/` / `hf:` / `hn:` / `dcr:` / `blog:` …）。博客条目要有可辨认的「博客」标识。
7. `python3 chk.py YYYY-MM-DD v1`，看 390×844 和 360×740 截图，不通过就改。
8. 推 `gh-pages` 根目录 `YYYY-MM-DD.html`（不是 `x/` 目录；门户的 `/x/` 是 nginx alias）。
9. `bash scripts/hub_entry.sh`（或箱子上 `/workspace/digests/hub_entry.sh`）。输出 `PUSH` 时再推 `hub/index.html`。
10. SSH 到 VPS 执行：

```bash
ssh -i "$DAILY_SSH_KEY" root@"$DAILY_VPS" 'bash /srv/daily/bin/sync.sh'
```

**不要在箱子本机跑** `/workspace/daily-portal/bin/sync.sh`：本机没有 `/srv/daily/site`，会报 `FAIL: no site dir`。sync 日志里 `gh-ratings` 403 限流可以忽略。

对已上线的当天页面只能增量修改，不得覆盖用户已看过、已打分的条目和 `data-sig-id`。改完要核对评分按钮还在、id 没变。

## 6. 12:00 推送两条消息

先完整读 `src/digests/lib/pick-rules.md` 和 `src/digests/lib/copy-prompt.md`，再打分：

```bash
PREFS_DB=/srv/daily/data/prefs.db \
  python3 src/digests/lib/score.py --date YYYY-MM-DD --json -o /tmp/pick-YYYY-MM-DD.json
# 箱子历史命令：
# PREFS_DB=/srv/daily/data/prefs.db python3 /workspace/digests/lib/score.py --date DATE --json -o /tmp/pick-DATE.json
```

- 用输出的 `selected`（≤15）做精选，按 score 顺序写消息。
- 文案：标题 ≤28 字；一句话 30–50 字，写清新在哪 / 数字 / 对他有用。禁止「重磅」「值得关注」等空话。
- 筛掉统计用 `excluded`。不够 10 条不硬凑，并说明。总数 10–15，宁少勿滥；不按来源均衡；探索项 🔭 最多 1 条。
- 资讯页保留全量，消息注明「完整 N 条见页面」。
- 钥匙 factor 已由 `score.py` 乘过；manual 记忆优先。若有短评，跑 `pref-summary.py` 写 2–3 句摘要。
- 页面链接必须 `curl` **GET** 到 200（门户是 302 到镜像页，也算可用）才附上。HEAD 501 请忽略。

### 消息一「叼报」

1. 概览一句
2. （可选）偏好摘要
3. 精选列表
4. **📝 今日博客**（硬要求，放精选列表后面）：固定 1–3 条，来自 `items-public-DATE.json` 里 `source=blog` 的条目，按 `blog_rank` 取前 1–3，**不得被人工剔除**（除非明显违反硬规则，须说明剔了哪篇及原因）。每条：标题链接 + 一句话说清作者的核心观点/判断 + 站名。没有就写「今日无博客入选」。
5. 周六才有：副业精选（算在 10–15 之内，最多 2–3 条；收入注明「公开口径、非投资建议」）
6. 筛掉统计
7. 「打开今日叼报」链接 `https://daily.jidadiao.fun/go/x/DATE`（200/302 才附；镜像滞后可附 `https://jidadiao.github.io/x-daily-digest/DATE.html` 备份）

### 消息二「设计灵感」

- 每天 8 条，Web 4 + App 4，每条一行，标「交互」或「界面」
- 附 `https://daily.jidadiao.fun/go/design/DATE`（200/302 才附）

缺哪个只说明。结尾问一句排版喜不喜欢。素材或页面缺失时仍发能发的那条并说明缺什么。

## 7. 绝对不要做的事

- 提交密钥、token、私钥、`prefs.db` 数据、`/etc/daily/api.env`
- force push，或改 `gh-pages` 上已发布页面的 `data-sig-id`
- 覆盖用户已打分的条目
- 为了凑数推 ACG/动画、安卓去广告、没信息差、没干货、只有一张 AI 榜单图的内容
- 自己补抓例程明确要求跳过的来源
- 在本机跑 VPS 专用的 `sync.sh`
- 改独立窗口返回按钮的样式（深色圆角悬浮，下滚收起、上滑出现；由 nginx 注入，只在 standalone 生效）

## 8. 需要的权限和连接器

见 [docs/environment.md](docs/environment.md)。最低配：

- GitHub 写 `JidaDiao/x-daily-digest` 的 `gh-pages` 和 `main`（日常出页只写 `gh-pages`）
- SSH 到 VPS（密钥路径 `~/.ssh/vps_jidadiao`）
- 公开 X 读取（出 X 素材时）
- Mobbin 连接器（出 App 设计灵感时）
- 能给用户发两条独立消息（当前产品里由拥有用户会话的 bot 发出）

## 9. 当天自检清单

- [ ] `items-public-DATE.json` 存在，失败来源已记录
- [ ] `items-DATE.json` 存在，或已注明 X 缺失
- [ ] 设计页 github.io GET 200，且与本地一致；门户 `/go/design/DATE` GET 302
- [ ] 叼报页 github.io GET 200，与本地一致；门户 `/go/x/DATE` GET 302
- [ ] `data-sig-id` 无重复、前缀合法、条数对得上
- [ ] 博客有标识；社区简介是中文
- [ ] 390/360 无横向溢出
- [ ] VPS `sync.sh` 已在远端执行
- [ ] 12:00 两条消息：精选 10–15（或更少并说明）+ 📝 今日博客 + 设计 8 条 + 结尾问排版
