# x-daily-digest · DiaoDaily 叼报

每日两份网页：**叼报**（X + GitHub/HF/HN 等精选资讯）与 **设计灵感**。线上：https://jidadiao.github.io/x-daily-digest/ ，门户 https://daily.jidadiao.fun （`/go/x/DATE`、`/go/design/DATE` 302 跳转）。

## 分支对应关系
| 分支 | 内容 |
|---|---|
| `main` | 源码：生成/发布脚本（`src/`）、入口更新脚本（`scripts/`）、测试（`tests/`）、文档（`docs/`）、CHANGELOG |
| `gh-pages` | 发布产物，GitHub Pages 从根目录发布：`YYYY-MM-DD.html`（叼报）、`design/YYYY-MM-DD.html`（设计灵感）、`index.html`（叼报往期）、`hub/index.html`（今日推送入口）、`.github/workflows/hub-entry.yml`（兜底） |
| `master` | 仓库初始提交（默认分支，未使用） |

`src/digests/` 对应箱子 `/workspace/digests/`，`src/daily-portal/` 对应 `/workspace/daily-portal/`（VPS 上 `/srv/daily/`），均为脱敏副本。

## 每日流程
```
Grok Bot 素材 items-DATE.json ─┐
公开来源 items-public-DATE.json ┴→ 前端设计灵感库 build_daily.py / publish.py
   → push_files 推 gh-pages：DATE.html 或 design/DATE.html（+ index.html）
   → bash scripts/hub_entry.sh（箱子上 /workspace/digests/hub_entry.sh）   # 拉最新 gh-pages，选各类最新有效一期，线上 200 校验
   → 输出 PUSH 时把 hub/index.html 推到 gh-pages
   → gh-pages 上的 hub-entry workflow 兜底再跑一次（幂等）
   → VPS 每 30 分钟 sync.sh 拉 gh-pages 供门户 /go 跳转
```

## 入口规则（scripts/update_hub_entry.py）
- 叼报、设计灵感**各自**取 gh-pages 中最新且有效的一期（文件存在、≥20KB、以 `</html>` 结束；`--check-live` 时 github.io 必须 200），卡片显示各自真实日期。
- 某类没有有效页：保留 hub 中该类原入口，不出空链接，不影响另一类；退出码 2。
- 输出只由两类日期决定，重复运行无 diff。

## 手动修复
```
git clone -b gh-pages https://github.com/JidaDiao/x-daily-digest.git pages
git clone -b main https://github.com/JidaDiao/x-daily-digest.git src
python3 src/scripts/update_hub_entry.py --root pages --check-live
cd pages && git add hub/index.html && git commit -m "hub: 修复入口" && git pull --rebase && git push   # 不要 force push
```
或在 Actions 页手动运行 `hub-entry`。测试：`python3 tests/test_update_hub_entry.py`。运维见 `docs/ops.md`。
