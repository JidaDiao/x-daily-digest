# X 每日 AI 报 · 杂志式图片模板

所有风格都移植自 [op7418/guizang-social-card-skill](https://github.com/op7418/guizang-social-card-skill)，配色取自它的 theme-presets.md，字体和版式规范取自 components.md 与 style-system.md。


## 每日网页生成流程（主题化拼装 · 2026-10-14 起）

1. **先定一句话设计主题**（写进 `build_daily.py` 的 `THEMES[date]`）。按主题挑元素，再统一成**一套 token**：一个配色（只留一个强调色）、一套字号、一种圆角、一条主缓动。不准原样贴各站的样式。
   - 口味：最爱 Dub / Ollama / Things / Cash App 成功页 / Clerk（浅色、克制、轻动效、大留白）；避开 Resend 式暗黑、组件墙、Cal.com 预约胶囊、stoic Toggle、Cosmos 搜索条（见 `/workspace/inspo/preferences.md`）。
2. **至少一半元素来自 gpt888 / ChatLab / DigVPS 以外的站**。优先 Dub、Ollama、Things、Clerk、Cash App；Mintlify 可作中性素材；回避 Cal.com / stoic / Cosmos（素材在 `/workspace/inspo/web/design/{src,blocks}`）。
   - 新元素要写进 `design-tokens.json`。只有真收藏或高评分才设 `favorite` / `rating`，其余标 `status: recommended`。
   - 每天的主题和元素组合记进 `used-combos.json`（构建时自动写入）。新组合不要和前 7 天重复。
3. **页面必须有**：
   - 编排好的首屏分层进场（标题和卡片错峰）
   - 滚动出现
   - 卡片联动（筛选条↔内容、滚动进度、视差、当前第 n 条）
   - 动效克制：彩蛋至多 1～2 处；文案口语、少 AI 味（见 DAILY.md「文案与气质」）
   - hover 都要有触屏可用的替代（:active 或点按）
   - `prefers-reduced-motion` 支持
4. 内容只用 `items-YYYY-MM-DD.json`。做成单文件，图片 base64 内嵌，移动优先。页脚写明主题和灵感来源（元素 id 与来源站）。
5. **自检**：用 playwright 截 390 和 1440 两个宽度，包括进场的几帧（`getAnimations` 暂停在 0/300/700/1200/2000ms），确认 390 宽时 scrollWidth 为 390，并逐个触发彩蛋。亲自打开截图看：是否统一、有没有进场、有没有联动、彩蛋能不能触发。不通过就继续改。脚本可参考 `/workspace/digests/chk.py` 的写法，截图放 `shots/<版本>/`。
6. `python3 build_daily.py YYYY-MM-DD` → `python3 publish.py` → 用 create_or_update_file 推 gh-pages 的 `YYYY-MM-DD.html`（先取 sha，content 用 `$file:`，页面里不要出现 `&amp;` 这类具名实体）。`index.html` 有变化才推。不动 `design/` 和 main。最后用 curl 加 `?t=随机数` 拉 live，和本地 cmp 一致才算完成。


### 防撞车硬规则（2026-10-25 起，build_daily.py 自动校验）
- **前一期用过的元素，当天一律不能用**。缓动不受这条限制（目前只有 `gpt888-ease`，见 `EASING`）。
- **3 天内同一元素最多出现 1 次**：DATE-1 和 DATE-2 用过的元素都不能再用。
- **相邻两天元素集合的 Jaccard ≤ 0.2**。
- **骨架每天换**。`cfg.skeleton = {topbar, card, nav}` 分别是顶栏、说明卡形式、导航，与前一期相比至少换 2 项。
- **背景色相每天换**。`cfg.bg` 写主底色 hex，与前一期的色相差要 ≥30°，或者一个是中性色、一个是有色。两天都是中性白/灰也算没换。
- 10-26 起 cfg 必须写 `skeleton` 和 `bg`，build 时会一起写进 used-combos.json。校验失败时 exit 2，不写任何文件。`--no-check` 只给重建旧页用。
- 回避元素（status=avoid 或 rating≤2）一律不能用。

### 移动端上线前检查（对应 review-2026-10-25.md 第 4 部分）
运行 `python3 chk.py DATE VER [html路径]`，它会在 390×844 和 360×740 两个视口自动检查：
1. `scrollWidth == innerWidth`，不一致就报错（横向溢出）。
2. 面积 >20000px² 的元素如果带 `touch-action:none`，报错（会把页面滚动卡死）。拖拽区要用 `pan-y`，并处理 `pointercancel`。
3. 统计小于 44px 的点击目标和小于 12px 的字号，作为警告。
4. 用了 `100vh` 的发出警告，改成 `100dvh`，或者写成 `100vh` 后再用 `100dvh` 覆盖。
5. 底部 fixed 栏要加 `padding-bottom:env(safe-area-inset-bottom)`，viewport 加 `viewport-fit=cover`。
6. 只在桌面端出现的区域（侧栏、已读区）在手机上要有替代入口，比如按钮或底部条。
7. 截图会存到 `shots/DATE-VER/`，每次检查用新的 VER，免得看到缓存的旧图。截图要自己逐张看。


### 命名与链接（2026-10-26 起）
- 资讯页与对外链接统一叫 **「叼报」**，不要再写「X 日报」。
- 门户正式链接：`https://daily.jidadiao.fun/go/x/YYYY-MM-DD`（无 `.html`）。
- `https://jidadiao.github.io/x-daily-digest/` 只作备份镜像。

### 社区精选合并
- 构建时除 `items-YYYY-MM-DD.json`（X）外，再读 `items-public-YYYY-MM-DD.json`（`items[].source` 为 github/hf/hn）。
- 同一页按来源分组：X / GitHub / Hugging Face / Hacker News。
- `data-sig-id` 用 `news_signal.normalize_sig_id`：X → `x:<id>`；`github:...` → `gh:repo/<owner>/<name>`；`hf:...` / `hn:<id>` 按 NEWS_SIGNAL.md 规范。
- 缺 public 文件时只建 X 部分，并在构建日志里写明。
- 页面模板：`load_day_items(DATE)` 拿分组；每条容器写 `{sig_attrs(it)}`。

### 短评（已启用）
- 点 👍/👎 后弹出可选一行「为什么？（可不写）」；有字再发 `action=comment`，`meta.note`≤200、`meta.vote`=like|dislike。
- `news-signal.js` 与 VPS API 均已允许 comment；`embed_signal` 每次从 `/workspace/daily-portal/web/news-signal.js` 现读内联（脚本自带 `.dd-note` 样式）。**不要改 daily-portal 里的脚本文件。**

### 互动信号 news-signal（2026-10-25 起，每期必做）
- 每天的叼报页都要内联共用脚本 `/workspace/daily-portal/web/news-signal.js`，提供 👍 👎 ⭐，条目停留约 2 秒自动记已读，点原文记 open。信号 POST 到 `https://daily.jidadiao.fun/api/signal`。
- **不用手动加**：`build_daily.py` 会调用 `news_signal.embed_signal()`，把脚本和手机端覆盖样式内联到 `</body>` 前（按钮 ≥44px，`touch-action:manipulation`）。页面是单文件，离线也能显示；请求只有 2xx 算成功；失败进 localStorage 重试队列（上限 50 条，下次打开页面重发）：403 最多试 3 次，网络错误/408/429/5xx 最多 5 次，其余 4xx 直接丢弃，都不影响页面。`embed_signal()` 每次构建都直接从 `/workspace/daily-portal/web/news-signal.js` 读最新版，不保留副本。
- **页面模板要做的**：`pages/DATE.py` 里每条新闻的容器元素都写上 `{sig_attrs(it)}`，生成的属性如下：
  - `data-sig-id="x:<post id>"`
  - `data-sig-url`
  - `data-sig-title`
  - `data-sig-author`
  - `data-sig-topic`
  - `data-sig-tags`
- 参考 `pages/2026-10-25.py` 里的 `.note`。如果条目里有拖拽或点开的逻辑，pointerdown 要跳过 `button`，免得点 👍 时触发拖拽或展开。
- **校验**：从 10-26 起，`build_daily.py` 会做 `check_signal` 检查，下面任一项不满足就 exit 2：
  - 脚本存在；
  - `data-sig-id` 个数等于 items 条数；
  - id 格式符合 x:/gh:/hf:/hn: 等前缀，且没有重复；
  - 每条都有 url 和 title。
- `chk.py` 会在 390 和 360 两个宽度检查：脚本存在、每个条目都有属性、`.dd-sig` 按钮 ≥44px。10-26 起不满足算 ERROR。
- 测试一律用明显的测试 id，比如 `x:TEST-xxx`，不要用真实帖子 id。服务端会挡掉 UA 里带 headless/python/curl 的请求，返回 403 `{"error":"ua"}`。用无头浏览器测试时这是正常现象。

## 文件
- `build_templates.py`：模板生成器。改设计请改这里，再运行 `python3 build_templates.py`，会重新生成所有 `template-*.html` 和 `styles.json`
- `template-editorial-<theme>.html`：编辑杂志风（Editorial Magazine × E-ink），共 6 套：ink-classic / indigo-porcelain / forest-ink / kraft-paper / dune / midnight-ink（唯一的深色主题）
- `template-swiss-<theme>.html`：瑞士国际主义风（Swiss International），共 4 套：ikb-blue / lemon-yellow / lemon-green / safety-orange
- `styles.json`：`rotation` 是每日轮换顺序（编辑风和瑞士风交替）；`legacy_not_in_rotation` 列出旧的单页长图模板（v2 / terminal / cute / swiss / newspaper），这些不参与轮换
- `render.py`：出图脚本；旧版在 `legacy/render_v1.py`
- `items-YYYY-MM-DD.json`：每天的数据；`media/`：配图和头像
- `out/<style>/<date>-NN.png`：输出图片；`showcase/`：展示用的套图

## 设计规范要点（照原仓库）
- **编辑杂志风：** 标题用衬线字体 Noto Serif SC，英文点缀用 Playfair 斜体；小标签用 IBM Plex Mono 大写，字距加宽 0.2em；标题遵循"字越大越细"（字重 500 加宽字距）；用发丝线和双线分隔；背景叠一层纸纹颗粒和渐变（paper-wash），midnight-ink 换成它专用的深色叠层；点缀色只少量使用。
- **瑞士风：** 只用无衬线字体 Inter 和 Noto Sans SC，不加载任何衬线字体；大字用 200 细字重；只有一个点缀色，黄、绿底上的文字用 #0a0a0a；用 2px 黑线做网格；没有圆角、阴影和渐变。

## 输出（1080×1440，3:4 小红书比例）
`python3 render.py <style> items-YYYY-MM-DD.json [out_prefix]`
- `-01.png` 封面（今日概览）：
  - 报头和一行数据：条数、总赞、总转发、热度指数
  - 头条：配图（图 1）加标题和摘要
  - 图 2：分类占比环形图
  - 图 3：互动量 Top 5 横向条形图
  - 本期目录（标注每条在第几版）
  - 关键词云
- `-02.png` 起是内容页：
  - 每页 3–4 条，按条数自动均分（7 条分成 4 + 3）
  - 每页有栏目名标题
  - 每页第一条是重点稿：左边大配图加图注，右边编号、标题、摘要、引文块、热度条
  - 其余各条按 2–3 栏排列，各带缩略配图和作者头像
- 互动量 = 点赞 + 2×转发。单条热度 = 本条互动量 ÷ 当期最高 × 100。热度指数 = 当期互动量总和。
- 配图规则：有 `media`（原帖配图）就用；没有的话，大图位置放 SVG 插画（斜线、圆形、大字编号和分类）。`avatar` 显示在署名旁边。
- 封面目录超过 7 条时自动压缩行高，保证页脚可见。
- 旧模板（含 `{{ITEMS}}` 占位符）仍然可以出单张长图，会自动裁掉底部空白。

## items json
```json
{"date":"2026-10-13","issue":"NO. 1013","items":[
 {"cat":"工具","title":"Relay 官方 MCP 上线","handle":"RelayGPU","id":"2109680218294079786",
  "likes":16,"rts":11,"summary":"一句中文摘要","quote":"原帖引文（可选）",
  "media":"media/2109680218294079786.jpg","avatar":"media/RelayGPU.jpg"}]}
```
- 分类可选：教程、工具、行业、观点、实测、研究、AIGC、变现（对应栏目名：学习札记、工具箱、行业观察、评论、实验室、前沿研究、AIGC、落地变现）。
- 标题最好不超过 14 个汉字，否则先缩短文字。

## 配图获取
1. 首选 x MCP：`get_posts_by_ids`，参数 `expansions=attachments.media_keys,author_id`、`media.fields=url,preview_image_url`、`user.fields=profile_image_url`。
2. 如果 x MCP 返回 429：
   - 原帖配图用公开接口 `https://cdn.syndication.twimg.com/tweet-result?id=<id>&token=a`，取其中 `mediaDetails[].media_url_https`（部分帖子会返回 403）
   - 头像用 `https://unavatar.io/x/<handle>`
3. 文件存到 `media/`，路径写进 json。

## 自检
用 Read 打开每张 PNG，检查：没有乱码；底部页脚完整可见（没有被挤出画面）；标题末行不只剩一两个字；条形图和环形图的颜色与当前主题一致。
多套样式可以拼成缩略总览图一起检查（参考做法：用 PIL 把每张缩到 270×360 后拼贴）。

## 每日网页发布（GitHub Pages）
- 线上首页（往期列表）：https://jidadiao.github.io/x-daily-digest/ ；单日页：`https://jidadiao.github.io/x-daily-digest/YYYY-MM-DD.html`
- 仓库：https://github.com/JidaDiao/x-daily-digest （公开）。**Pages 从 `gh-pages` 分支根目录发布**（main 只做备份，推 main 不会更新网站）。
- 步骤：
  1. 准备 `items-YYYY-MM-DD.json`。当天页面放到 `web/YYYY-MM-DD.html`（由前端设计灵感库交付；还没交付时，先改 `web/build.py` 里的日期，用 `web/template.html` 生成占位页）。页面必须是单文件：图片用 base64 内嵌，或者放进 `site/media/` 后一起推送。
  2. `python3 publish.py`：把 `web/*.html` 复制到 `site/`，并重新生成 `site/index.html`（往期列表，标题取自对应的 items json）。
  3. 用 user-GitHub-xai 的 `push_files` 推到 owner=JidaDiao、repo=x-daily-digest、**branch=gh-pages**，文件包括 `index.html` 和 `YYYY-MM-DD.html`（往期页面已经在线上的，不需要重推）。文件很大时，先用 python 生成 files 数组 json，再以 `"files": "$file:/workspace/agent-tools/files.json"` 的方式传入。
  4. 等约 1 分钟后，用 WebFetch 或 `curl -I` 检查新链接（WebFetch 可能返回缓存，404 时以 curl 的结果为准）。
- 不要往页面里放任何密钥或 token。
