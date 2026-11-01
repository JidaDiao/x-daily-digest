# x-daily-digest

DiaoDaily 叼报：日报页面在 `gh-pages`；源码与门户脚本在 `main`。

## main 目录
- `portal/`：VPS `/srv/daily` 对应的门户与偏好库（无密钥）
  - `bin/prefs.py` / `bin/learning.py`：偏好库 + **钥匙级学习**（repo / x:@ / sub / feed / site / kw）
  - `bin/api.py`：daily-api
  - `PREFS_API.md`：接口说明
  - `tests/test_learning.py`：钥匙学习单测
- `digests/lib/pick-rules.md`：12:00 精选硬规则（含钥匙 factor）

网站发布看 `gh-pages`，推 main 不会更新 Pages。
