# daily.jidadiao.fun 门户（VPS <VPS_HOST>，ssh -i <SSH_KEY_PATH> root@…，box 上 `ssh vps`）
- /srv/daily/site      gh-pages 镜像（git，经 ghfast.top 代理拉取；回退直连/codeload tarball）
- /srv/daily/bin       build.py（生成 www/index.html、favorites.json、favorites.zip）、api.py（收藏接收）、sync.sh、portal.html 模板
- /srv/daily/data      feedback.json（date|site 最新一条）、library.json（回填收藏）、design-tokens.json（快照，需更新时从 box scp）
- /srv/daily/favorites/<slug>/  媒体 + meta.json；nginx autoindex 于 /favorites/
- /etc/daily/api.env   DAILY_API_TOKEN（600，仅服务器 + Worker secret VPS_TOKEN）
- systemd daily-api.service → 127.0.0.1:9090；nginx /etc/nginx/sites-available/daily.jidadiao.fun；certbot 证书
- cron */30 /srv/daily/bin/sync.sh >> /var/log/daily-sync.log
- 路由：/ 门户 · /x/YYYY-MM-DD.html · /design/YYYY-MM-DD.html · /favorites/ · /favorites.zip · /favorites.json · POST /api/favorite (Bearer)
- Worker 改动：额外允许 Origin https://daily.jidadiao.fun；每个合法 POST 用 ctx.waitUntil 转发到 /api/favorite（备份 worker.js.bak-20261021）

## 修改记录
- 2026-10-25（UTC+8）审查后修复（备份 *.bak-20261025，VPS 同名；nginx 备份 /root/daily.jidadiao.fun.nginx.bak-20261025；Worker 源备份 /workspace/design-feedback-worker/worker.js.bak-20261025）
  - ghratings.py：同 (date,site) 按记录 ts 取最新（重复 issue 不再旧覆盖新）；≥2026-10-21 的 GitHub 记录若比 feedback.json 新则回放进去（补 Worker 转发失败的分）
  - portal.html：「今天」按 Asia/Shanghai 日期选；当天未上线显示「今天的页面还没上线」+ 最近一期
  - sync.sh：git/curl 错误写日志，时间标 CST(UTC+8)，失败记 FAIL 保留旧镜像；data/sync-state.json；连续失败≥2 写 data/sync-alert.json → /api/status 顶层 stale/sync
  - api.py：/api/read 仅收 Origin 或 Referer = https://daily.jidadiao.fun，过滤爬虫 UA；Content-Length 非数字 400；限速字典清理；新增 GET /go/(x|design)/YYYY-MM-DD → 记已读（每 IP 20/分钟）→ 302 镜像页（未镜像的今天/昨天 302 到 github.io）
  - nginx：daily 站点新增 location /go/ → 127.0.0.1:9090（未动其他站点）
  - logrotate：/etc/logrotate.d/daily-sync（weekly, rotate 8, compress, copytruncate）
  - Worker design-feedback：CORS 来源按请求局部；POST 必须带合法 Origin；建 issue 后按编号扫描更小号同名 open issue，最小号胜出、自己的行移过去并关闭重复；VPS 转发同步等待+重试 1 次，失败在响应和 issue 行标 "vps":"fail"
- 2026-10-25 晚（UTC+8）DiaoDaily 叼报 · 偏好库第一期（备份 *.bak-20261025b；整包 VPS /root/daily-backup-20261025b.tgz；crontab /root/crontab.bak-20261025b）
  - 新增 /srv/daily/bin/prefs.py（单文件、仅标准库）+ /srv/daily/data/prefs.db（WAL；signals 只追加 / memories / items / config / FTS5 trigram）；接口说明 data/PREFS_API.md（本地 PREFS_API.md）
  - 导入（幂等）：feedback.json、library.json、favorites/*/meta.json、read.json、inspo/preferences.md（盒子上解析为 data/prefs-import-preferences-md.json）→ 100 signals / 62 items / 7 条 manual 记忆 + derive 97 条 derived
  - api.py：新增 POST /api/signal（Origin 或 Bearer，独立限速桶）、GET /api/profile|memories|search（Bearer）；/api/favorite 与 /api/read、/go 原行为不变，额外镜像写 signals（失败不影响旧接口）
  - cron 50 0 * * *（UTC = 08:50 Asia/Shanghai）prefs.py derive >> /var/log/daily-prefs.log；logrotate /etc/logrotate.d/daily-prefs
- 2026-10-25 夜（UTC+8）偏好库 v2 + GitHub connector（备份 *.bak-20261025c；prefs.db 备份 data/prefs.db.bak-20261025c；整包 /root/daily-backup-20261025c.tgz；crontab /root/crontab.bak-20261025c）
  - prefs.py：schema v2 幂等迁移（signals 重建保 id：source_type +hf/hn/reddit/linuxdo、action +star/bookmark/submit/comment/follow/upvote、occurred_at；memories +valid_from/invalid_at/supersedes_id；新表 memory_evidence/sources/entities）；衰减按 occurred_at × meta.weight_factor；derive 写证据、极性翻转走 supersede、尊重用户作废；profile.design Web:App 各自归一化 5:5；新增 lang scope；CLI add-memory/list-memories/invalidate-memory/memory-evidence/sources/export --md；search 只返回 active 记忆
  - api.py：GET /api/memory-evidence、POST /api/memory/invalidate、POST /api/signals/batch（Bearer；≤200 条、≤512KB、6 次/分钟、整批原子）；浏览器路径忽略 dedup_key/occurred_at
  - connectors/github.py + run-all.sh + hn/hf/reddit/linuxdo 骨架；cron 30 0 * * *；/etc/logrotate.d/daily-connectors
- 2026-10-25 深夜（UTC+8）偏好库 v3（备份 *.bak-20261025d；prefs.db 备份 data/prefs.db.bak-20261025d；整包 /root/daily-backup-20261025d.tgz；crontab /root/crontab.bak-20261025d）
  - 新增 /srv/daily/etc/sources.yaml（本地 etc/sources.yaml）：按来源设半衰期（github 90 天，其余 14 天）；hn/hf/reddit/linuxdo 账号不连（enabled:false → health=disabled）；列出公开内容来源
  - prefs.py：每条信号按来源取半衰期；key 大小写归一去重；manual 记忆相似度 ≥0.75 时合并并累加证据，极性相反时 supersede；profile.recommend 按 80/20 分配 exploit/explore 权重；新增 dedupe-memories；Markdown 导出带 frontmatter，用 observation 格式
  - api.py：新增 POST /api/memory（Bearer）；/api/signal 接受 github.io Origin（CORS + OPTIONS），浏览器 action 设白名单
  - run-all.sh：GitHub 账号从 sources.yaml 读取，不再运行 4 个骨架 connector
  - web/news-signal.js + NEWS_SIGNAL.md + demo：日报条目 👍👎⭐/已读 互动脚本，交给前端设计灵感库嵌入（线上页面没改）

- 2026-10-26（UTC+8）可选短评 + 外名「叼报」（备份 *.bak-20261026；VPS 同名）
  - news-signal.js：👍/👎 后可选一行短评 → action=comment（meta.note≤200, meta.vote）
  - api.py / prefs.py：浏览器允许 comment；derive 写 item 记忆；pref-summary.py 供 12:00 概览
