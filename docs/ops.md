# 运维说明（仓库外任务，脱敏）

不含任何密钥、密码、令牌。VPS 主机记为 `<VPS_HOST>`，SSH 密钥只在运维机本地：`~/.ssh/vps_jidadiao`。
更完整的每日步骤见 `AGENTS.md` 与 `docs/schedule.md`。

## VPS（daily.jidadiao.fun，服务器时区 UTC）

目录：

- `/srv/daily/site`：gh-pages 镜像
- `/srv/daily/bin`：api / prefs / sync / build / pwa-nav 等
- `/srv/daily/data`：prefs.db、feedback、sync-state（不入库）
- `/srv/daily/www`：门户首页与注入用的 JS/图标
- `/srv/daily/etc/sources.yaml`
- `/srv/daily/favorites/`
- `/etc/daily/api.env`：`DAILY_API_TOKEN`（600）

| cron (UTC) | 上海时间 | 作用 |
|---|---|---|
| `*/30 * * * * /srv/daily/bin/sync.sh` | 每 30 分钟 | 拉 gh-pages 到 `/srv/daily/site` |
| `30 0 * * * /srv/daily/bin/connectors/run-all.sh` | 08:30 | GitHub 账号公开数据同步 |
| `50 0 * * * python3 /srv/daily/bin/prefs.py derive` | 08:50 | 偏好推导 |
| `15 0 * * * acme.sh --cron` | 08:15 | 证书续期 |

daily-api 监听 `127.0.0.1:9090`，nginx 反代 `/api/` 和 `/go/`。

手动同步（页面刚推上 gh-pages 后、12:00 前建议做一次）：

```bash
ssh -i ~/.ssh/vps_jidadiao root@<VPS_HOST> 'bash /srv/daily/bin/sync.sh'
```

不要在箱子本机跑这份脚本。

## 维护

- 改脚本：先改 `main` 的 `src/` / `scripts/` / `docs/`，再同步到箱子 `/workspace/digests`、`/workspace/daily-portal`、`/workspace/inspo/web/design`（或反向同步后提交）。
- 推送前 `git pull --rebase`，禁止 force push。
- 提交前检查：`rg -nEi 'ghp_|github_pat_|BEGIN .*PRIVATE|password\s*=|sk-|-----BEGIN' .`
- 不要提交 `prefs.db`、`.env`、`.secrets/`、VPS 主机地址以外的连接信息。需要写主机时用 `<VPS_HOST>`。
- 入口异常：再跑 `scripts/hub_entry.sh`，或按它的「PUSH」提示更新 `hub/index.html`。
