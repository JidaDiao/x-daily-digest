# CHANGELOG

## 2026-10-29
- 修复：gh-pages `hub/index.html` 停在 2026-10-24。原因：旧 `update_hub.py` 只按传入/当天日期拼两个链接，且未接入每日发布步骤（发布只推当天页面和 index.html），hub 从 10-24 后再没更新；按日期拼链接也会在某类未发布时产生坏链接。
- 新增 `scripts/update_hub_entry.py`：两类各取最新有效一期、各自显示日期、单类失败保留旧入口、幂等。
- 新增 `scripts/hub_entry.sh` 接入每日发布末尾；箱子上的 `update_hub.py` 改为转调它。
- 新增 gh-pages 兜底 workflow `hub-entry.yml`。
- 往期页 `index.html` 与 `publish.py` 的标题「X 每日 AI 推荐」改为「叼报 · 往期」。
- 新增 `tests/`、`docs/verification-2026-10-29.md`、`docs/ops.md`；同步脱敏源码到 `src/`。
