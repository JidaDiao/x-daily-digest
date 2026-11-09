# 发布与校验

## 推哪条分支

| 内容 | 分支 | 路径 |
|---|---|---|
| 叼报当日页 | `gh-pages` | `YYYY-MM-DD.html` |
| 设计当日页 | `gh-pages` | `design/YYYY-MM-DD.html` 及新素材 |
| hub 入口 | `gh-pages` | `hub/index.html`（`hub_entry.sh` 说 PUSH 才推） |
| 脚本与文档 | `main` | `src/`、`docs/`、`scripts/` |

推 `main` 不会更新网站。禁止 force push。不要把密钥写进页面或仓库。

页面里不要出现 `&amp;`、`&lt;` 这类具名实体（GitHub 连接器有时会把它们还原，导致页面坏掉）。

## 叼报页校验

```bash
cd /workspace/digests
python3 build_daily.py DATE          # 失败即 exit 2：骨架/元素/signal/中文简介
python3 chk.py DATE v1               # 390×844 与 360×740
# 自己逐张看 shots/DATE-v1/
```

`chk.py` 会查：横向溢出、大面积 `touch-action:none`、过小点击区/字号、`100vh`、底部 safe-area、signal 按钮 ≥44px。截图必须人工看，不要只看 exit code。

## 设计页校验

```bash
cd /workspace/inspo/web/design
python3 build.py DATE --check
# 或
timeout -k 5 120 python3 tools/check.py DATE.html
# 看 /tmp/design-check-390.png 和 /tmp/design-check-360.png
```

## 推 gh-pages 之后

等约 1 分钟，避开 CDN 缓存：

```bash
# 叼报
curl -fsS "https://jidadiao.github.io/x-daily-digest/${DATE}.html?t=$RANDOM" | cmp - "/workspace/digests/web/${DATE}.html"

# 设计
curl -fsS "https://jidadiao.github.io/x-daily-digest/design/${DATE}.html?t=$RANDOM" | cmp - "/workspace/inspo/web/design/${DATE}.html"
```

必须逐字节一致。WebFetch 可能返回缓存，404 时以 curl 为准。

## 门户

```bash
# GET：成功是 302
curl -sI -o /tmp/h -w "%{http_code} %{redirect_url}\n" "https://daily.jidadiao.fun/go/x/${DATE}"
curl -sI -o /tmp/h -w "%{http_code} %{redirect_url}\n" "https://daily.jidadiao.fun/go/design/${DATE}"

# 不要用 HEAD 判断（会 501）
```

镜像滞后（github.io 已 200，门户还 302 到 github.io 或 404）时，SSH 到 VPS 拉镜像：

```bash
ssh -i "${DAILY_SSH_KEY:-$HOME/.ssh/vps_jidadiao}" root@"${DAILY_VPS:?set DAILY_VPS}" \
  'bash /srv/daily/bin/sync.sh'
```

成功日志类似：`sync ok=1 head=<shortsha>`（时区标 CST UTC+8）。

**不要在箱子本机跑** `src/daily-portal/bin/sync.sh` 或 `/workspace/daily-portal/bin/sync.sh`：脚本会 `cd /srv/daily/site`，本机没有这个目录，直接 `FAIL: no site dir`。

sync 末尾会跑 `ghratings.py` 和 `build.py`。`gh-ratings` 403 限流可以忽略，不影响镜像本身。

VPS 上还有每 30 分钟的 cron 会跑同一条 `sync.sh`（服务器时区是 UTC，cron `*/30`）。不要假设它立刻跟上；12:00 前如果刚推完页面，应主动 SSH 同步一次。

## hub 入口

每次发布后：

```bash
bash /workspace/digests/hub_entry.sh
# 仓库入口：
# bash scripts/hub_entry.sh
```

它会浅克隆 `gh-pages` 和 `main`，跑 `scripts/update_hub_entry.py --root ... --check-live`。
叼报和设计各取各自最新的、线上能 200 的一期。输出 `NO_PUSH` 就不用动；输出 `PUSH` 就把生成的 `hub/index.html` 推到 gh-pages。

总览页名称仍为「X 日报」，不要顺便改成「叼报」去覆盖线上入口。

## 12:00 推送前最后检查

- 叼报门户 GET 302 或 github.io GET 200，才附链接
- 设计页同样
- `score.py` 已跑，文案跟 `copy-prompt.md`
- 消息一有「📝 今日博客」
- 两条独立消息，无图片、无往期入口
- 结尾问排版喜不喜欢
