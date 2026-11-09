# X 素材与周六副业

历史上由 **Grok Bot** 每天约 10:30 产出，交给出页/推送流程，不直接发给用户。
做法来自用户技能「x」（X 每日素材）和「周六副业精选」。

## 依赖（无法只靠本仓库还原的部分）

- 公开 X 读取接口 / MCP（先读运行环境里的 `x-api-mcp-guide` skill）
- `search_posts_all`：用参数 `start_time`，**不要**在 query 里写 `since:`
- `get_posts_by_ids`：取详情和配图；`expansions=attachments.media_keys,author_id`，`media.fields=url,preview_image_url`，`user.fields=profile_image_url`
- 限流 429：放慢，已拿到的先用，缺的在交付时说明
- 接口 5xx：视为来源故障，不要编条目。写明窗口和错误，让 12:00 推送注明「X 来源今日暂缺」

429 时的配图回退（无密钥）：

- 原帖图：`https://cdn.syndication.twimg.com/tweet-result?id=<id>&token=a`（部分帖会 403）
- 头像：`https://unavatar.io/x/<handle>`

文件存 `/workspace/digests/media/`，路径写进 json。

## 窗口与话题

- 默认窗口：前一天 12:00 到当天 10:30（Asia/Shanghai）
- 交付目标：当天 11:00 前写出文件，得出页流程使用
- 话题：AI 模型与价格、中转站/VPS/网络封锁、一手实测、开源工具
- 2026-11-02 起去掉二次元/ACG 整类

每个话题用几组关键词和关注账号的最新帖搜索，合并去重，按互动量和信息量排序。

## 挑选（先读 `src/digests/lib/pick-rules.md`）

1. 信息差：用户大概率还不知道的新事件、新数据、一手实测。
2. 干货：价格/政策/封锁/可跑的开源工具/实测对比，要有数字或步骤。
3. 同一事件只留信息最全的 1 条。
4. 不收：只有一张榜单图、AI 凑数小文章和 listicle、泛泛无结论、纯情绪、纯广告、动画/ACG。
5. 每条一句中文理由；保留原帖链接。
6. 传闻、社区猜测在摘要里标明「未证实」。

## 输出

写 `/workspace/digests/items-YYYY-MM-DD.json`，schema 见 [io-schema.md](io-schema.md)。
`title` 尽量不超过 14 个汉字。

交付给出页流程：来源名、日期、路径、条目摘要（标题 + 原帖链接）。抓取失败也要说明缺什么、为什么。

## 周六副业

- 覆盖过去一周
- 主题：内容变现、独立开发、接单、跨境、资讯差
- 优先务实、可执行、有来源；挑 3–6 条并可备 1 条
- 过滤夸大收益、拉人头、引流卖课
- 涉及合规风险加一句提醒
- 写入 `/workspace/digests/items-sidehustle-YYYY-MM-DD.json`
- 推送里最多采用 2–3 条，算在当天 10–15 精选之内
- 收入相关表述必须写「公开口径、非投资建议」
- 本周没有像样内容就不要写文件（不算缺失）

风格参考历史上给过一条 X 帖（`cloudhuxxx` 的副业精选体例），不要复制具体收益数字。
