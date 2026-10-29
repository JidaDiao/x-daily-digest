# DiaoDaily 公开来源抓取器

命令：`/workspace/daily-portal/collectors/run.sh`（每天 08:20 Asia/Shanghai；在 box 上跑；退出码 0=至少一个来源成功，2=全部失败）
参数：`--no-push`（不写 VPS），`--date YYYY-MM-DD`，`--out-dir DIR`。日志：`collectors/logs/collect-DATE.log`。

## 来源（全部无账号公开数据）
| source | 抓取 | 备注 |
|---|---|---|
| github | github.com/trending 日榜 HTML + Search API（近 7 天新建、stars>50，未鉴权 10 次/分） | via=trending / search-new |
| hf | /api/models?sort=trendingScore + /api/daily_papers | via=trending-model / daily-paper |
| hn | Algolia `tags=front_page` | 带 points、comments、discuss 链接 |
| linuxdo | top.rss?period=daily → latest.rss | box 出口 403（Cloudflare），VPS 直连超时；失败即跳过并标 skipped |
| reddit | r/LocalLLaMA、ClaudeAI、selfhosted、programming 的 top/.rss?t=day，每个间隔 3s | 限流紧，单个 sub 失败只跳过，全失败标 skipped |

## 选择逻辑
1. 每源按 id（`<source>:<id>`）去重。
2. 经 SSH 在 VPS 本机调 `GET /api/profile`，取 `recommend.exploit/explore`；按 lang/author 精确匹配、topic 词边界匹配累加 weight，热度做极小加分。
3. 来源轮转取 exploit 共 16 条，再取 4 条 explore（先命中探索兴趣，再从画像外随机补）；每源 ≤5，总数 ≤20。
4. 输出 `/workspace/digests/items-public-YYYY-MM-DD.json`：`{date, issue, source, generated, profile_used, status{源:{ok,fetched,picked,error}}, items[{source,id,title,url,summary,tags,author,pick,match,...}]}`。`summary` 为原文简介（英文），中文一句话由 9:18 推送时撰写。
5. 写入 VPS：经 SSH 在 VPS 端读 `/etc/daily/api.env` 调 `POST /api/signals/batch`，每条 `action=read` + `meta.candidate=true, weight_factor=0`（只进 items 表/全文检索，不影响偏好分），dedup_key=`<src>:read:cand-DATE-<id>`，同日重跑幂等。token 不出 VPS、不落盘。
依赖：python3、paramiko、<SSH_KEY_PATH>。
