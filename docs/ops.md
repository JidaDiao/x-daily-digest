# 运维说明（仓库外任务，脱敏）

不含任何密钥、密码、令牌。VPS 主机记为 `<VPS_HOST>`，SSH 密钥只在运维机本地。

## VPS（daily.jidadiao.fun，服务器时区 UTC）
| cron (UTC) | 上海时间 | 作用 |
|---|---|---|
| `*/30 * * * * /srv/daily/bin/sync.sh` | 每 30 分钟 | 拉 gh-pages 到 `/srv/daily/site`，供门户 `/go/x/DATE`、`/go/design/DATE` 302 |
| `30 0 * * * /srv/daily/bin/connectors/run-all.sh` | 08:30 | GitHub 账号公开数据同步 |
| `50 0 * * * python3 /srv/daily/bin/prefs.py derive` | 08:50 | 偏好推导（SQLite） |
| `15 0 * * * acme.sh --cron` | 08:15 | 证书续期 |
daily-api 监听 127.0.0.1:9090，nginx 反代；`DAILY_API_TOKEN` 通过环境变量注入，不入库。

## Grok Bot 例程（上海时间）
- 10:20 公开来源抓取：`daily-portal/collectors/run.sh` → `items-public-DATE.json`
- ~10:30 Grok Bot X 素材：`items-DATE.json`
- 07:17 设计灵感页、11:07 起叼报页：前端设计灵感库 bot 生成并 push_files 推 gh-pages，**最后执行 `bash /workspace/digests/hub_entry.sh`**，输出 PUSH 时再推 `hub/index.html`
- 12:00 DiaoDaily 推送两条消息

## 维护
- 改脚本：先改 main 的 `src/`/`scripts/`，再同步到箱子 `/workspace/digests`、`/workspace/daily-portal`（或反向同步后提交）。推送前 `git pull --rebase`，禁止 force push。
- 提交前检查：`grep -rnEi 'ghp_|github_pat|BEGIN .*PRIVATE|password|sk-' .`
- 入口异常：Actions 手动运行 `hub-entry`，或按 README「手动修复」。
