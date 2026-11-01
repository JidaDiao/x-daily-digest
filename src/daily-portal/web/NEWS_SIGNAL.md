# news-signal.js 嵌入说明（给 前端设计灵感库）

文件：`/workspace/daily-portal/web/news-signal.js`（无依赖、无图片、约 8KB）。页面生成时每次现读此路径内联。

## 1. 嵌入
页尾加：
```html
<script src="news-signal.js" defer data-date="YYYY-MM-DD" data-source="news"></script>
```
- `data-source`：资讯叼报页用 `news`，设计页用 `design`。
- `data-endpoint`（可选）：默认同站 `/api/signal`，github.io 上自动用 `https://daily.jidadiao.fun/api/signal`。
- 脚本可内联，或随页面一起发布到 gh-pages 根目录。

## 2. 条目标记（每条一个容器）
```html
<article data-sig-id="x:<post_id>" data-sig-url="<原文链接>" data-sig-title="<标题>"
         data-sig-author="<作者handle>" data-sig-topic="<主题>" data-sig-tags="topic:ai,format:thread"> … </article>
```
- `data-sig-id` 必填：X 帖子用 `x:<post id>`（与推送去重的 post id 一致），其他来源用 `gh:repo/<owner>/<name>`、`hn:<id>`、`hf:<model>`、`ld:<topic id>`、`reddit:<id>`、`dcr:<id>`（Did Codex Reset AI 快讯）。
- tags 前缀：`topic:` 主题、`format:` 呈现形式、`lang:` 编程语言，会进入画像。
- 默认把按钮行插到容器末尾；想换位置就在容器里放 `<div data-sig-bar></div>`。

## 3. 行为
| 交互 | 上报 action | 权重 |
|---|---|---|
| 👍 | like | +1 |
| 👎 | dislike（同一 topic/作者连续 3 次 → 回避） | −1 |
| 👍/👎 后可选短评 | comment（`meta.note`≤200，`meta.vote`=like\|dislike；空则不上报） | +0.5 |
| ⭐ / 再点 | fav / unfav | ±1.5 |
| 在视口停留 ≥2s | read（每条一次） | +0.2 |
| 点原文链接 | open（每条一次） | +0.3 |

👍/👎 互斥，以最后一次为准（两条都会记录，衰减后自然覆盖）。点 👍 或 👎 后弹出一行输入（占位「为什么？（可不写）」），确认或回车提交；空内容只记 like/dislike；有字再发一条同 `item_id` 的 `comment`。Esc 关闭输入框。状态存 localStorage，同一动作不重复上报；只有 HTTP 2xx 算成功。网络错误、5xx、408、429、403 进 localStorage 重试队列（最多 50 条），下次打开页面重发；每条最多尝试 5 次，403（如 UA 被拒）最多 3 次，超限丢弃并 `console.warn`。其他 4xx（参数错误等）不重试，直接丢弃并 warn。

## 4. 服务端
- `POST /api/signal` 浏览器路径只接受 `source_type` 为 news|design、action 为 like|dislike|fav|unfav|read|open|skip|**comment**；不需要也不能带 token，服务端定时间、忽略 dedup_key/occurred_at；每 IP 30 次/分钟。
- `comment` 必须带非空短评：`meta.note` 或顶层 `note`，≤200 字，否则 400。
- 允许的来源：`https://daily.jidadiao.fun` 和 `https://jidadiao.github.io`（返回 `Access-Control-Allow-Origin`）。脚本用 `text/plain` 发送，所以不触发预检；OPTIONS 预检也支持。
- 不需要改 Worker。

## 5. 上线前检查（移动端）
- 按钮与短评「发送」最小点击区域 ≥44×44；输入框不遮挡正文；在 375px / 390×844 下确认不溢出。
- 用 `news-signal-demo.html` 本地打开即可看样式（endpoint 指向 /nowhere，不会真的上报）；点 👍/👎 应弹出短评行。
