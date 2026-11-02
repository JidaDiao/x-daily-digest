# CHANGELOG

## 2026-11-02

- prefs `SOURCE_TYPES` 增加 `dcr` / `blog`（schema v5，signals CHECK 重建）；`sources.yaml` 为两者写入 half_life；公开源候选可入库。
- 新增公开源 **blog**（白名单个人实践博客）：首发 [fomoxx](https://fomoxx.com/) RSS `https://fomoxx.com/index.xml`；配置 `src/daily-portal/collectors/feeds-blog.json`。
- 采集：只保留 `/posts/` 文章；跳过 privacy/about/editorial-policy 等；id=`blog:<site>/<slug>`；author=站名；**每日精选 ≤2**；画像 exploit/explore 打分。
- 打分：`score.py` 对 blog 用 **7 天**半衰期；复盘/排障/实测略抬干货。`pick-rules` 允许真人踩坑长文、推送消息里最多 1–2 条。
- 互动：`news_signal` / `NEWS_SIGNAL.md` 支持 `blog:`。加下一站只改 `feeds-blog.json`。

## 2026-11-01
- 新增公开源 **dcr**（Did Codex Reset · AI 快讯）：`https://didcodexreset.com/rss/news.xml?lang=zh-CN`。
- 采集：`collect.py` 专用 `dcr()`（多 category、剥「显示语言」、id=`dcr:<hex>`、via=rss）；`SOURCES` / `etc/sources.yaml` / collectors README 已登记。
- 互动：`news_signal.py` 支持 `dcr:` 规范化与校验；`NEWS_SIGNAL.md` 允许列表补 `dcr:<id>`；`score.py` 按社区公开源 72h 半衰期。
- 说明：该站快讯 RSS 目前最新约停在 **2026-10-08**；恢复更新后会自动进入每日精选池。未接 signals 账号。

## 2026-10-29
