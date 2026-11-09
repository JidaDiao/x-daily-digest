# 定时任务清单

接手 agent 应建立（或接手）以下定时任务。时区一律 **Asia/Shanghai**。
已暂停的午间汇总不要重建。

## 任务 A · 每天 10:20 · 公开来源抓取

**目的**：产出当天社区/博客候选，供出页和 12:00 精选使用。

**做什么**：

1. 运行 `src/daily-portal/collectors/run.sh`（箱子历史路径 `/workspace/daily-portal/collectors/run.sh`）。
2. 文档：`src/daily-portal/collectors/README.md`。
3. 确认 `/workspace/digests/items-public-YYYY-MM-DD.json` 存在。
4. 汇报各来源条数（`status.*.fetched` / `picked`）和失败原因。
5. 失败不要自己补抓。
6. linux.do 被 Cloudflare 拦截：标记跳过。
7. reddit 常见 SSL 超时：跳过。

**提示词（可直接贴进例程）**：

```
DiaoDaily 叼报的公开来源抓取。运行 /workspace/daily-portal/collectors/run.sh
（文档 collectors/README.md；仓库对应 src/daily-portal/collectors/）。
产出 /workspace/digests/items-public-YYYY-MM-DD.json 并写入 VPS。
完成后只确认文件存在、各来源条数与失败原因；失败不要自己补抓。
linux.do 已知被 Cloudflare 拦截，标记为跳过即可；reddit 常见 SSL 超时，也跳过。
```

## 任务 B · 每天约 10:16（仅周六）· 副业素材

**目的**：给当天叼报消息一末尾单列「副业精选」。

**做什么**：按 [x-collect.md](x-collect.md) 周六一节，写 `items-sidehustle-DATE.json`。没有像样内容就不要写文件，也不算缺失。其他日子不要跑。

## 任务 C · 每天约 10:30 · X 素材

**目的**：覆盖前一天 12:00 到当天 10:30 的 X 帖，写成 `items-DATE.json`。

**做什么**：按 [x-collect.md](x-collect.md)。抓取失败要说明原因，不要补假数据。

历史上由 Grok Bot 的例程触发，完成后把路径和条目摘要交给出页/推送流程。

## 任务 D · 凌晨前后 · 设计灵感页

**目的**：当天设计灵感 8 条上线，供 12:00 消息二使用。

**做什么**：按 [design-inspiration.md](design-inspiration.md) 和 `src/design/HOWTO.md`。
建议 08:30 前发出；若预计赶不上 12:00，提前在流程里标明「设计页延迟」。

历史上前端设计灵感库约 05:30–07:17 开跑，07:30 仍停在素材阶段就要预报进度。

## 任务 E · 素材齐后（通常 10:40–11:30）· 出叼报页

**目的**：把 X + 公开源（+ 周六副业）做成当天资讯页并镜像到门户。

**做什么**：按 [diaodaily-page.md](diaodaily-page.md) 和 [publish-verify.md](publish-verify.md)。
出页后 SSH 到 VPS 跑 `bash /srv/daily/bin/sync.sh`。

## 任务 F · 每天 12:00 · 唯一一次用户推送

**目的**：给用户发两条独立消息（先叼报，再设计灵感）。无图片、无往期入口。

**提示词（可直接贴进例程）**：

```
每天 12:00 统一推送一次，分成两条独立消息（设计是设计，资讯叫「叼报」）。
无图片、无往期入口，页面链接 curl GET 200（门户 302 也可）才附。HEAD 501 正常。

【精选】先完整读 src/digests/lib/pick-rules.md（箱子路径 /workspace/digests/lib/pick-rules.md），再跑：
PREFS_DB=/srv/daily/data/prefs.db python3 /workspace/digests/lib/score.py --date DATE --json -o /tmp/pick-DATE.json
用输出的 selected（≤15）作为精选，按 score 顺序写消息；文案严格跟 copy-prompt.md
（标题≤28 字、一句话 30–50 字写清新在哪/数字/对他有用，禁「重磅」「值得关注」等空话）。
筛掉统计用 excluded。不够 10 条不硬凑，并说明。总数 10–15，宁少勿滥；不按来源均衡；探索项 🔭 最多 1 条。
资讯页保留全量，消息注明「完整 N 条见页面」。对外一律叫「叼报」。
硬规则：禁 ACG/动画、Android 去广告、AI 垃圾小文章、没信息差、一张图表关于 AI、没干货。

【每日博客——硬要求】消息一里必须有独立的「📝 今日博客」小节，放在精选列表后面，固定 1–3 条，
来自 items-public-DATE.json 里 source=blog 的条目，按 blog_rank 取前 1–3，且不得被人工剔除
（除非明显违反硬规则，须说明剔了哪篇及原因）。每条写：标题链接 + 一句话说清作者的核心观点/判断 + 站名。
选文标准是作者有独立思考、能引发读者思考，非 AI 编写，近半年内；纯教程/产品发布降权，
但当天只有这些时仍要推并注明偏教程。没有就明说「今日无博客入选」。叼报页上博客条目要有「博客」标识。

【钥匙级偏好】score.py 已乘钥匙 factor；manual 记忆优先。短评摘要若有则跑 pref-summary.py 2–3 句。

【周六副业】items-sidehustle-DATE.json 若有，在消息一末尾单列，算在 10–15 之内，最多 2–3 条；
收入注明「公开口径、非投资建议」。

【页面】推送前确认今日叼报资讯页已上线且 curl GET 200/302。
页面须用收藏设计元素每天拼接出不同的整体风格/动画/UI/UX/卡片图表（五维相对前一天都要有差异）；
缺页或未换呈现只说明、仍推文字精选。设计灵感页不强制每天换壳。
门户优先 https://daily.jidadiao.fun/go/x/DATE ；镜像滞后可附 github.io 备份。
必要时 ssh 到 VPS 跑 /srv/daily/bin/sync.sh 拉镜像。不要在本机跑 sync.sh。

消息一：概览一句 +（可选）偏好摘要 + 精选列表 + 📝今日博客 +（周六）副业 + 筛掉统计
+ 「打开今日叼报」链接 https://daily.jidadiao.fun/go/x/DATE。
消息二「设计灵感」：每天 8 条，Web 4 + App 4，每条一行，标「交互」或「界面」；
附 https://daily.jidadiao.fun/go/design/DATE（200/302 才附）。
缺哪个只说明。结尾问排版喜不喜欢。素材或页面缺失时仍发能发的那条并说明缺什么，不要自行补抓。
```

## 不要接手

**午间汇总 12:38**：已暂停，不要重建，也不要再产出 `items-DATE-noon.json` 或二次推送。
