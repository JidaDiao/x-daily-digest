# CHANGELOG

## 2026-11-01
- 新增公开源 **dcr**（Did Codex Reset · AI 快讯）：`https://didcodexreset.com/rss/news.xml?lang=zh-CN`。
- 采集：`collect.py` 专用 `dcr()`（多 category、剥「显示语言」、id=`dcr:<hex>`、via=rss）；`SOURCES` / `etc/sources.yaml` / collectors README 已登记。
- 互动：`news_signal.py` 支持 `dcr:` 规范化与校验；`NEWS_SIGNAL.md` 允许列表补 `dcr:<id>`；`score.py` 按社区公开源 72h 半衰期。
- 说明：该站快讯 RSS 目前最新约停在 **2026-10-08**；恢复更新后会自动进入每日精选池。未接 signals 账号。

## 2026-10-29
