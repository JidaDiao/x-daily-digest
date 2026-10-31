> **硬规则 v3（2026-10-31 用户确认，2026-11-01 起生效，取代「2 Web + 2 App」）**
> 1. 每期固定 **8 条：Web 4 + App 4**。上一期用过的站点/App/元素，下一期不再用（build 会对照 recommended.md 和 blocks/_archive/<上一期>/ 自动拦）。
> 2. 每条在 meta 里写 `focus`：`交互` / `界面` / `兼具`（最多 1 条兼具）。**交互 ≥ 4、界面 ≥ 3**（兼具两边都算）。
>    - **交互**：价值在「怎么操作」——新的手势、拖拽、按住、状态切换、动效反馈。必须写 `how`（怎么操作，一句话）和 `fresh`（为什么新鲜，一句话），页面会显示这两行。
>    - **界面**：价值在「看一眼就惊艳」——版式、字体、配色、留白、插画/质感。
> 3. 质量优先：不够 8 条不凑。用 `python3 build.py <date> --allow-short`，并在任一 meta 或 `blocks/_short.json` 写 `short_reason`（缺了什么、为什么），页面顶部会显示；交付消息里也要写。
> 4. Web 仍是代码 live demo（可轻复刻，每站 1 个关键元素）；App 放 Mobbin 原视频（mp4 → .mp4.b64，`muted loop playsinline preload="metadata"`，外壳进视口才加载/播放）或原图。
> 5. 页面变长：`--check` 跑 390/360 手机检查；页面+素材合计建议 ≤ 8MB（build 超了会提示，视频压到 480px 宽、24–30fps、CRF≈30、截短到 15s 内）。
> 6. 日期 < 2026-11-01 仍按旧规则（2 Web + 2 App）校验，旧页面可照常重建。
> 7. **任何一期 07:30 前发布不了，立刻告诉「每日推送」**（id 550c708e-e3d6-4f4d-aa2c-e8a1ef4ad9ef，SendToAgent priority:true）：哪一期、卡在哪个阶段、预计何时补发。不要等到推送时才暴露。

## 阶段化流程（可断点续跑）
状态文件：`stage/<date>/state.json`，用 `python3 tools/stage.py <date> next|done <阶段> [备注]|show`。
**每次开跑第一件事：`python3 tools/stage.py <date> next`**，从返回的阶段继续，已完成的阶段不重做（产物都在磁盘上）。

| # | 阶段 | 做什么 | 落盘 | 预估 |
|---|---|---|---|---|
| 1 | pick 选题 | 读 preferences/recommended/web-pool；Mobbin search_flows 找 4 个 App 流程并跑 `src/mobbin/hasvid.sh` 确认视频；定 4 个 Web 站；写 focus | `stage/<date>/pick.json`（8 条：key/kind/focus/url/理由） | 8–12 分钟 |
| 2 | assets 素材 | 下载 Mobbin 视频→ffmpeg 压缩→.mp4.b64 + 封面 webp；Web 站 curl 源码 + `tools/shot.py` 截图 + thumbs | `assets/<date>/`、`src/<key>/`、`thumbs/` | 6–10 分钟（每个视频 ~1 分钟，截图 ≤45s/张） |
| 3 | webdemo | 写 4 个 Web block + 4 个 App block（一条写完就落盘，done 时备注已完成的 key） | `blocks/NN-<key>.html` | 15–25 分钟 |
| 4 | build | `python3 build.py <date>`（exit 2 就按提示补） | `<date>.html` | 1 分钟 |
| 5 | check | `timeout -k 5 120 python3 tools/check.py <date>.html` + 逐张看 /tmp/design-check-390/360.png | 截图 | 2–4 分钟 |
| 6 | publish | 推 gh-pages（html + design-feedback.js 不变就不推 + 新的 .b64 素材），curl+cmp 验证；hub_entry.sh | — | 5–8 分钟 |
| 7 | deliver | 写 recommended.md / web-pool.md 日期；交付每日推送 | — | 2 分钟 |
合计约 40–60 分钟。07:17 开跑时，**07:30 检查点**：若 stage 还停在 1–2，先给每日推送发「预计 xx:xx 出页」；整体在 08:30 前没发出去就按第 7 条上报。
- 某阶段里中断：webdemo 阶段按「已存在的 blocks 文件」续写缺的；assets 阶段按 `assets/<date>/` 里已有文件跳过。
- 一个外部步骤（某个站截图/某个视频下载）失败 1 次就换下一个候选，不要卡在同一站反复重试。

## 稳定截图（替代 google-chrome --screenshot）
**不要再用 `google-chrome --headless --screenshot`**：它的 `--timeout` 不会结束进程，遇到长连接/指纹脚本会一直挂住（10-29 就是 mymind/readwise/sunsama/framer 四个并行截图挂了 7 小时以上）。统一用：
```bash
timeout -k 5 45 python3 tools/shot.py https://example.com src/<k>/shotm.png --w 390 --h 844   # 手机
timeout -k 5 45 python3 tools/shot.py https://example.com src/<k>/shot.png --w 1440 --h 900   # 桌面
```
`tools/shot.py`：playwright + `/usr/bin/google-chrome`，只等 domcontentloaded（20s 上限）再等 2.5s 截图，外层 `timeout` 保证最多 45s 必退出。2026-10-31 实测 mymind/sunsama/framer/readwise 各 4–5 秒完成。
开跑前清理残留：`pkill -f "headless=new.*--screenshot" || true`。

# 每日设计灵感页：Live Demo 流程

产出是单文件 `design/<date>.html`，手机优先。每个设计块是一个**用代码复刻、可直接交互的 demo**，不是链接加截图。

## 目录
```
design/
  template.html        外壳：灰阶极简、统一缓动 cubic-bezier(.22,1,.36,1)、模糊上浮进场、sticky 目录、重播/进视口播放、反馈脚本
  build.py             python3 build.py <date> → <date>.html（拼 blocks、内嵌缩略图、检查 HTML 实体）
  blocks/NN-<key>.html 每个设计一块（按文件名排序）
  thumbs/<key>.webp    小尺寸对照图（≤360px 宽，几 KB）
  src/<key>/           抓取的 index.html / all.css / shot.png（原始资料，不发布）
  design-feedback.js   自动反馈脚本（和页面一起放在 gh-pages 的 design/ 下）
```
每天开始前，把昨天的 blocks 移到 `blocks/_archive/<date>/`，或直接删除。

## block 文件格式
```html
<!--meta {"key":"dub","name":"Dub","kind":"Web|App","focus":"交互|界面|兼具","how":"交互类必填：怎么操作","fresh":"交互类必填：为什么新鲜","elements":["dub-logo-blur"],"url":"原站或 mobbin_url","ref":"链接文字",
"thumb":"thumbs/dub.webp","subtitle":"一行元素清单","tags":[...],
"why":"为什么好（2–3 句，说清楚要看哪里、怎么玩）","params":["关键参数，注明哪些来自源码、哪些是估计"],"note":"可选"}-->
<!--demo--> HTML + <style> + <script>。所有选择器限定在 .d-<key> 下 <!--/demo-->
<!--code--> 给读者看的关键代码（纯文本，放进 textarea） <!--/code-->
```
- 需要「重播」时，给 demo 根元素加 `data-replay`，动画写在 `.play` 下，并放一个 `<button class="replay">`。外壳会在 demo 进入视口时自动加 `.play`，点按钮会重新触发；JS 动画监听 `replay` 事件。
- build 会自动给每块加上 `data-site` / `data-url` 和空的 `.df-stars` / `.df-fav`，不要手写。

## Web 站（每站挑 1–3 个元素）
1. 抓取：`curl -sL -A "Mozilla/5.0" URL -o src/<k>/index.html`，再把 HTML 里引用的 CSS 拼成 `all.css`。CSS 拿不到时用 headless Chrome 的 `--dump-dom`。
2. 截图：只用 `timeout -k 5 45 python3 tools/shot.py URL OUT.png [--w 1440 --h 900]`（见上「稳定截图」）。一个站失败 1 次就跳过，用源码分析代替截图。
3. 找值得学的地方：
   - 搜 `@keyframes`、`cubic-bezier`、`animation:`、`animation-timeline`、`clip-path`、`mask-image`、`backdrop-filter`、`box-shadow`、主色，以及 `.is-selected` 这类状态类。
   - CSS 文件很大且只有一行时，用 python 的 `re` 搜，比 grep 快。
4. 复刻：色值、时长、缓动尽量照抄源码，并在 params 里注明出处；自己加的效果（比如数字滚动）要明确写成「demo 增强」。
5. 版权：不用对方的 logo 和图标文件，用文字或 CSS 图形占位；原站链接只作次要小链接。

## App（Mobbin）
1. 用 `user-Mobbin` 连接器的 `search_screens` 或 `search_flows`（platform=ios），每次查询只描述一个界面。例：`"bottom sheet modal with grabber and action buttons"`、`"onboarding screen with page indicator dots and continue button"`、`"segmented control tab switcher"`。task_intent 和 output_destination=code 在同一任务里要保持一致。
2. 一定要看返回的图片再选（只看元数据不算数），挑和用户口味相符的：灰阶、圆角、克制。记下 `mobbin_url` 和 `app_name`。
3. 复刻成手机尺寸 demo：外框用 `.ph`（宽 min(100%,340px)、高 600px、40px 圆角），复刻关键组件和交互流程，比如弹层开关和拖拽、分段切换、多选计数、引导页翻页。文案只用截图里真实可见的，或者明确标注为占位；人名和邮箱一律用占位。
4. 预览图可以缩到约 180px 宽做对照图；需要高清图时从 `image_url` 下载（30 天后过期）。链接用 `mobbin_url`。
5. meta 里写 `"kind":"App"`，params 里注明「尺寸和色值按截图估计」。

## 手机优先检查清单
- 390px 宽下 `document.documentElement.scrollWidth == 390`，没有元素超出视口（跑马灯、轨道类容器除外）。
- 点击区不小于 36–44px；正文 ≥15px，demo 内小字 ≥11px。
- hover 效果都要有点击或自动播放的替代，滑动手势用 pointer 事件，并设置 `touch-action`。
- `prefers-reduced-motion`：外壳已全局把动画缩到 0.01ms；JS 动画需要自己判断 `matchMedia`。
- 页面里不能出现 `&amp;`、`&lt;` 等 HTML 实体（build.py 会检查），因为 GitHub 连接器会把它们还原。

## 自查（playwright + 系统 Chrome）
一键：`python3 build.py <date> --check`（或 `timeout -k 5 120 python3 tools/check.py <date>.html`），检查 390/360 不横向溢出、无 pageerror、视频属性，长图在 /tmp/design-check-<w>.png。
`pip install --break-system-packages playwright`，然后：
```python
b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
pg = await b.new_page(viewport={'width':390,'height':844}, has_touch=True)
```
- 先滚到底触发所有进视口动画，再截 `full_page` 长图，桌面 1440 宽再截一张。
- 截动画帧：点重播后，用 `el.getAnimations().forEach(a=>{a.pause();a.currentTime=T})` 定格在 150、400、700ms 各截一张，比 sleep 准。headless 的 `--screenshot` 会停在动画中途，不要用它判断动画。
- 交互检查：用 tap 走一遍每个 App demo 的流程，同时收集 `pageerror`。
- 坑：`background-clip:text` 要直接放在被 clip-path 动画的元素上，放在父元素上擦除不会生效。

## 发布
1. 用 `user-GitHub-xai` 的 `get_file_contents`（ref=gh-pages）拿 sha，再用 `create_or_update_file`，`content` 写成 `"$file:/abs/path/<date>.html"`。
2. 等约 1 分钟，用 `curl https://jidadiao.github.io/x-daily-digest/design/<date>.html?t=$RANDOM | cmp - <date>.html` 确认和本地一致。
3. 新增的站同步写进 `/workspace/inspo/recommended.md`，避免以后重复推荐。
