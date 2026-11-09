# 故障处理

## 素材缺失

| 现象 | 处理 |
|---|---|
| 没有 `items-DATE.json` | 12:00 仍发能发的内容，注明「X 来源今日暂缺」和原因。不要编帖子。 |
| 没有 `items-public-DATE.json` | 出页只做 X 部分并在构建日志/推送里写明。不要手抓 GitHub/HF/HN 充数。 |
| linux.do skipped | 已知 Cloudflare，不算事故。 |
| reddit SSL 超时 | 跳过，不算事故。 |
| 非周六没有副业文件 | 正常。 |
| 博客 0 条 | 消息一写「今日无博客入选」。 |
| 设计页没出 | 消息二说明缺失，仍发消息一。 |
| 叼报页没出 | 仍发文字精选，不附页面链接（或只附 github.io，如果其实已经上线）。 |

X 搜索连续 5xx：记录时间窗和错误原文，等接口恢复再补跑（需用户/流程明确要求）。补跑窗口可扩到当前时刻。

## 门户与同步

| 现象 | 处理 |
|---|---|
| 本机跑 sync.sh 报 `no site dir` | 改 SSH 到 VPS 执行 `/srv/daily/bin/sync.sh`。 |
| 门户 `/go/x/DATE` 404 或仍跳旧镜像 | SSH 同步后再 curl GET 看 Location。 |
| HEAD `/go/...` 返回 501 | 正常，改用 GET。 |
| GET 返回 302 | 成功。 |
| sync 日志 `gh-ratings` 403 | 忽略。 |
| 连续 sync 失败 | VPS `data/sync-alert.json` 会出现；看 `data/sync-state.json` 的 `last_error`。不要把 VPS 上的 env 文件拷进仓库。 |

## 页面构建

| 现象 | 处理 |
|---|---|
| `build_daily.py` exit 2 | 读报错：通常是原型撞车、元素重复、缺 stance/dims、signal 数量不对、社区简介没中文。按提示改 `pages/DATE.py`，不要 `--no-check` 强行出新页。 |
| `chk.py` 横向溢出 | 改 CSS；跑马灯类容器除外，但不要用它当借口放过真溢出。 |
| 大面积区域不能滚 | 不要用 `touch-action:none`；拖拽区用 `pan-y` 并处理 `pointercancel`。 |
| 评分按钮不像扁平 2D / 按下态看不出来 | 确认内联的是最新 `news-signal.js`，重新 build，不要改 `data-sig-id`。 |
| 已上线页改坏了评分 | 立即对照发布前 HTML 恢复原来的 `data-sig-id` 和条目集合。 |

## 设计页

| 现象 | 处理 |
|---|---|
| Chrome `--screenshot` 挂住 | 杀掉残留进程，改用 `tools/shot.py` + 外层 `timeout`。 |
| Mobbin 连接器不可用 | `--allow-short` 并说明，不要盗图。 |
| 页面+视频过大 | 再压视频（480 宽 / CRF≈30 / ≤15s）。 |
| 构建抱怨 HTML 实体 | 去掉 `&amp;` 等具名实体后再推。 |

## GitHub

| 现象 | 处理 |
|---|---|
| 推送冲突 | `git pull --rebase`（或先取最新 sha 再 `create_or_update_file`），禁止 force push。 |
| 只推了 main，网站没变 | 网站看 `gh-pages`。 |
| hub 入口日期不对 | 再跑 `scripts/hub_entry.sh`，确认它校验的是线上 200 的最新一期。 |

## 偏好 / 打分

| 现象 | 处理 |
|---|---|
| 没有 prefs.db | `score.py` 仍可运行，factor=1.0。在推送里不必假装读过钥匙。 |
| pref-summary 要 SSH | 设置 `DAILY_VPS` 和 `DAILY_SSH_KEY`；或在 VPS 上直接跑 `/srv/daily/bin/pref-summary.py`。 |
| 想撤销某把钥匙的惩罚 | 在 VPS：`prefs.py clear-key 'x:@foo'`（不要把数据库拷下来提交）。 |
