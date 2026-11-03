# CHANGELOG

## 2026-11-03

- blog 选文二次优化：think_score 主导（独立于其他来源轮转，blog_rank=think_score×画像系数 0.8–1.2，跨站取前 2）；短正文抓原文补算（每站最新 3 篇、1s 限速、失败回退）；收紧教程/指南/清单识别（缺反思词扣 2.5），标题含取舍/反思加 1。
- blog 公开源：`collect.py` 支持 Atom（`<entry>`、link rel=alternate、published/updated）与 RSS；去掉硬性 `/posts/` 过滤，改为每站可选 `include_paths`/`exclude_paths`。
- blog 时间窗 180 天；每站每天 ≤1、总 ≤2；按已推 URL 跨天去重；新增 think_score「思考深度粗筛」（篇幅、第一人称、结论/取舍/反思词加分，listicle/周刊/高频扣分），item 增加 think_score/think_why 字段，其余字段不变。
- 白名单扩到 9 站：fomoxx、ROYWANG、WuSiYu、Joway、oldj、MouT.me、puppylpg、rxliuli、piglei。加站流程：候选池 → 每周 3 个给用户确认 → 白名单。

## 2026-11-02

- prefs `SOURCE_TYPES` 增加 `dcr` / `blog`（schema v5，signals CHECK 重建）；`sources.yaml` 为两者写入 half_life；公开源候选可入库。
- 新增公开源 **blog**（白名单个人实践博客）：首发 [fomoxx](https://fomoxx.com/) RSS `https://fomoxx.com/index.xml`；配置 `src/daily-portal/collectors/feeds-blog.json`。
- 采集：只保留 `/posts/` 文章；跳过 privacy/about/editorial-policy 等；id=`blog:<site>/<slug>`；author=站名；**每日精选 ≤2**；画像 exploit/explore 打分。
- 打分：`score.py` 对 blog 用 **7 天**半衰期；复盘/排障/实测略抬干货。`pick-rules` 允许真人踩坑长文、推送消息里最多 1–2 条。
- 互动：`news_signal` / `NEWS_SIGNAL.md` 支持 `blog:`。加下一站只改 `feeds-blog.json`。
- 门户新增 `pwa-nav.js`（仅独立窗口：悬浮返回键 + 下拉刷新），由 VPS nginx `sub_filter` 注入 `/x/` 与 `/design/` 页面，`portal.html` 首页引入；nginx 改动备份在 VPS `/root/daily.nginx.bak-20261102`。
- pwa-nav v2：返回键改为顶部 sticky 返回栏（随页面深浅配色），不再悬浮遮挡内容。
- pwa-nav v3：恢复深色圆角悬浮返回键，顶部加占位避免遮挡首屏内容，下滑自动收起、上滑出现。
- pwa-nav v4：增加状态栏遮罩（内容滚到时间/信号下面不再穿模）。
- news-signal：短评输入框字号 16px 并取消自动聚焦（防 iOS 自动放大）。

## 2026-11-01
- 新增公开源 **dcr**（Did Codex Reset · AI 快讯）：`https://didcodexreset.com/rss/news.xml?lang=zh-CN`。
- 采集：`collect.py` 专用 `dcr()`（多 category、剥「显示语言」、id=`dcr:<hex>`、via=rss）；`SOURCES` / `etc/sources.yaml` / collectors README 已登记。
- 互动：`news_signal.py` 支持 `dcr:` 规范化与校验；`NEWS_SIGNAL.md` 允许列表补 `dcr:<id>`；`score.py` 按社区公开源 72h 半衰期。
- 说明：该站快讯 RSS 目前最新约停在 **2026-10-08**；恢复更新后会自动进入每日精选池。未接 signals 账号。

## 2026-10-29
