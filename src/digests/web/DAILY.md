# 每日叼报页

完整规则见上级 `README.md`「每日网页生成流程（主题化拼装）」。

简式：一句话主题 → 挑元素（≥一半来自非 gpt888/ChatLab/DigVPS 的站）并统一 token → `python3 ../build_daily.py YYYY-MM-DD`（同时写 used-combos.json）→ playwright 在 390/1440 宽自检（进场帧、联动、≥3 彩蛋、触屏、减少动效）→ `python3 ../publish.py` → 推 gh-pages → curl 校验。

## ★ 版式原型与防撞车硬规则 v2（2026-10-31 用户要求，2026-11-01 起生效，build_daily.py 自动校验，不过 exit 2）
用户原话：「我要每天都有新鲜感，我也要每天都有好看的设计可以看。」背景：10-27～10-31 只换皮不换骨（铭牌+页签+竖排卡片+点开展开+已读）。原「骨架 3 项换 2 项」作废，由下面规则替代（< 11-01 的旧页仍按旧规则）。

**一、先选版式原型，再选元素（原型决定骨架，不是皮肤）**
原型池（可自增，但浏览方式必须真不同）：1 空间/地图型（线路图、星图、平面可缩放画布）· 2 时间/时刻表型 · 3 实物桌面/拼贴型（软木板、标本夹、拖拽）· 4 单列长卷型（报纸、手账、信纸）· 5 索引/墙型（印样、档案柜、相册墙）· 6 一次一条型（抽卡、翻页、幻灯、播放列表）· 7 对话/终端/命令型 · 8 分栏对照/仪表盘型。
- 近 7 天原型不重复。「纵向滚动卡片列表」连续最多 1 天；禁止把「铭牌+页签+竖排卡片+点开展开+已读按钮」当默认骨架。
- 骨架 6 维：信息载体、导航方式、浏览轴（纵/横/平面/翻页）、进场方式、底色色相、字体组合。与前 3 天**任一天**比至少 4 维不同。
- 条数影响原型：30–40 条用索引/地图/分栏；少则可一次一条/长卷。

**二、元素：为原型服务，但不再只用 2–4 个**
- 每页 ≥8 个交互/视觉细节元素（缓动不计）：收藏库 ≥5、自创 ≤2；收藏来源站点 ≥4。
- 仍遵守：前一期用过不再用 / 3 天内最多 1 次 / 相邻 Jaccard≤0.2 / 回避元素不用 / 底色色相每天换。
- 选不进原型的不用；优先从设计灵感库（`/workspace/design-inspiration/`、`design-tokens.json` 的 `added`）最近 3 天新入库元素里补。
- 头条前 3 条必须有视觉层级（大/中/小），不要全部等大卡片。

**三、每天「好看」验收（出页前必过，人工）**
- 先写一句设计立场：场景/隐喻 + 为什么这样组织这些新闻 + 舍弃了什么；对照 10-22 地铁线路图的统一感和手感。
- 自查：只有 1 个强调色；字体 ≤2 套；动效只服务场景；390/360 `chk.py` 过检；无通用 UI kit 堆砌感；逐张看截图再发布，不满意重做。

**四、复盘闭环**
- used-combos.json 每期有 `archetype`、`dims`、`vertical_list`、`stance`、`own`、`score`（发布 24h 后按 👍👎/评分/⭐综合回填，0–5 分，缺省 null）。
- 低分原型（score≤2）30 天内不用（自动校验）；高分原型（≥4）隔 14 天后可回归，但必须换题材和骨架维度。
- 每周至少 2 天含「收藏之外的自创处理」（`own` 非空）。

**cfg 新字段（pages/DATE.py 的 RESULT['cfg']，build 时写进 used-combos.json）**
```python
cfg = dict(
  theme=..., bg='#hex', elements=['收藏 token id', ...],   # ≥5 个、来源站 ≥4
  stance='一句设计立场：场景/隐喻 + 为何这样组织 + 舍弃了什么',
  archetype='8 分栏对照/仪表盘型',      # 写编号或池内名；新原型另加 archetype_why='浏览方式为何不同'
  vertical_list=False,                   # 本页是否纵向滚动卡片列表骨架
  dims=dict(carrier='信息载体', nav='导航方式', axis='纵|横|平面|翻页',
            entrance='进场方式', bg_hue='底色色相', fonts='字体组合'),
  own=[{'name':'自创处理','desc':'一句'}],  # ≤2；收藏+自创 ≥8
)
```
校验项（≥11-01）：stance 非空；archetype 有效（新原型需 why）；vertical_list 已写；dims 六维齐全且 axis 合法；近 7 天原型不重复；纵向卡片列表不连续 2 天；低分原型 30 天内不用；与前 3 天任一天 dims ≥4 维不同；元素 ≥8 / 收藏 ≥5 / 自创 ≤2 / 来源 ≥4 / 收藏 id 必须存在；外加原有前一期禁用、3 天 1 次、Jaccard、底色色相、回避元素。10-22～10-31 的 archetype/dims 已回填（标 `backfill`）。

## 工具（2026-10-15 起）
- 页面模板按日放 `pages/YYYY-MM-DD.py`（产出 RESULT: html/cfg/used）；`python3 build_daily.py YYYY-MM-DD` 会优先用它，并写 `used-combos.json`。
- 自查：`python3 chk.py YYYY-MM-DD v1`（截图到 `shots/YYYY-MM-DD-v1/`；10-15 的交互脚本在 `chk_1015.py`，新一天复制改选择器）。看图后再发布。
- 新拆元素先进 `design-tokens.json`（status: recommended）；先读 feedback issue（`design-feedback.md` 的 Reading recipe）更新回避/收藏。
- 午间补充：若有 `items-YYYY-MM-DD-noon.json`，合并进当天 items（原早报备份为 `items-YYYY-MM-DD-morning.json`，条目加 `slot: morning/noon`），配图用 x MCP `get_posts_by_ids` 补到 `media/`。10-15 v2 页模板按 slot 分「上午 / 午间」两段；交互自检脚本 `chk_1015b.py`。
- 反馈 issue 里当天打低分（≤2）的元素，当天中午页面就不再用（10-15 因此整页从 Stripe 风重做为 Things 风；旧模板 `pages/2026-10-15.v1-stripe.bak`）。

## 2026-10-18 新规则（用户要求，10-19 起）
- 每天换一种有创意的呈现形式（时间线/终端/聊天/报纸/星图/播放器/收件箱/拖拽桌面/看板等），不再只是卡片列表；已用形式记在 used-combos.json 的 form 字段，不重复。
- 页面最顶部放「今天怎么玩」小块，一两句话说明交互方式与彩蛋。

## 设计气质（2026-10-26 用户再澄清）
- **少「AI 拼出来」的感觉**：问题在设计，不在文案。
- **每天仍换不一样的呈现**（`used-combos.json` 不重复）。地铁只是「不像 AI」的气质举例，**不要天天地铁、不要复刻地铁**。
- **气质正例**：2026-10-22 地铁线路图（对照 `web/2026-10-22.html` / `site/2026-10-22.html`）——统一主题、场景手感；新形式要达到同级统一感，但题材必须是新的。
- **反例**：热敏小票等「通用 UI 组件堆砌 / 花哨 UI kit 冒充创意」。
- 形式要有可摸到的场景隐喻；整页为一个场景服务；少通用卡片墙、按钮墙；别靠动效名或 UI kit 零件凑数。
- 动效克制、服务于场景，彩蛋至多 1～2 处；务必 `prefers-reduced-motion`。页脚灵感来源写站名。展示名仍「叼报」。
- 以后用户再说太 AI，由「每日推送」汇总转发。

## 先立场、再选料（2026-10-27 用户反馈）
- 不要把收藏元素堆上去；要有自己的审美判断。**先定整体设计思路**（场景/隐喻、版式、节奏、信息层级，一句话说明为什么），再从收藏里**只选真正服务这个思路的元素**。
- 拼不进去的宁可不用；可以有收藏之外的自创处理。（11-01 起元素下限见 v2：≥8，收藏 ≥5。）
- 设计思路写进 `used-combos.json` 的 theme/notes，含「选了什么、舍弃了什么、为什么」；交付给每日推送时附一句设计思路。
- 每天仍换不同呈现；仍别靠堆组件/动效名冒充创意。


## 防撞车硬规则（2026-10-25 起；≥11-01 骨架项由上方 v2 取代，其余仍有效）
- **前一期用过的元素，当天一律不能用**。缓动不受这条限制（目前只有 `gpt888-ease`，见 `EASING`）。
- **3 天内同一元素最多出现 1 次**：DATE-1 和 DATE-2 用过的元素都不能再用。
- **相邻两天元素集合的 Jaccard ≤ 0.2**。
- ~~骨架每天换~~（11-01 起作废，改用 v2 六维）。`cfg.skeleton = {topbar, card, nav}` 分别是顶栏、说明卡形式、导航，与前一期相比至少换 2 项。
- **背景色相每天换**。`cfg.bg` 写主底色 hex，与前一期的色相差要 ≥30°，或者一个是中性色、一个是有色。两天都是中性白/灰也算没换。
- 10-26 起 cfg 必须写 `skeleton` 和 `bg`，build 时会一起写进 used-combos.json。校验失败时 exit 2，不写任何文件。`--no-check` 只给重建旧页用。
- 回避元素（status=avoid 或 rating≤2）一律不能用。

## 移动端上线前检查（对应 review-2026-10-25.md 第 4 部分）
运行 `python3 chk.py DATE VER [html路径]`，它会在 390×844 和 360×740 两个视口自动检查：
1. `scrollWidth == innerWidth`，不一致就报错（横向溢出）。
2. 面积 >20000px² 的元素如果带 `touch-action:none`，报错（会把页面滚动卡死）。拖拽区要用 `pan-y`，并处理 `pointercancel`。
3. 统计小于 44px 的点击目标和小于 12px 的字号，作为警告。
4. 用了 `100vh` 的发出警告，改成 `100dvh`，或者写成 `100vh` 后再用 `100dvh` 覆盖。
5. 底部 fixed 栏要加 `padding-bottom:env(safe-area-inset-bottom)`，viewport 加 `viewport-fit=cover`。
6. 只在桌面端出现的区域（侧栏、已读区）在手机上要有替代入口，比如按钮或底部条。
7. 截图会存到 `shots/DATE-VER/`，每次检查用新的 VER，免得看到缓存的旧图。截图要自己逐张看。


## 命名与链接（2026-10-26 起）
- 资讯页与对外链接统一叫 **「叼报」**，不要再写「X 日报」。
- 门户正式链接：`https://daily.jidadiao.fun/go/x/YYYY-MM-DD`（无 `.html`）。
- `https://jidadiao.github.io/x-daily-digest/` 只作备份镜像。

## 社区精选合并
- 构建时除 `items-YYYY-MM-DD.json`（X）外，再读 `items-public-YYYY-MM-DD.json`（`items[].source` 为 github/hf/hn）。
- 同一页按来源分组：X / GitHub / Hugging Face / Hacker News。
- `data-sig-id` 用 `news_signal.normalize_sig_id`：X → `x:<id>`；`github:...` → `gh:repo/<owner>/<name>`；`hf:...` / `hn:<id>` 按 NEWS_SIGNAL.md 规范。
- 缺 public 文件时只建 X 部分，并在构建日志里写明。
- 页面模板：`load_day_items(DATE)` 拿分组；每条容器写 `{sig_attrs(it)}`。

## 短评（已启用）
- 点 👍/👎 后弹出可选一行「为什么？（可不写）」；有字再发 `action=comment`，`meta.note`≤200、`meta.vote`=like|dislike。
- `news-signal.js` 与 VPS API 均已允许 comment；`embed_signal` 每次从 `/workspace/daily-portal/web/news-signal.js` 现读内联（脚本自带 `.dd-note` 样式）。**不要改 daily-portal 里的脚本文件。**

## 互动信号 news-signal（2026-10-25 起，每期必做）
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

## 社区简介一律中文（2026-10-27 起）
- 社区条目（GitHub/HF/HN/Reddit）页面简介一律用中文一句话（≤60 字），写在 items-public-DATE.json 每条的 `summary_zh`；没有就照英文原文翻译精简，不编造原文没有的事实。
- 原帖标题、仓库名、专有名词不翻，保持原样。
- `news_signal.load_day_items` 自动用 summary_zh 覆盖 summary（英文留在 summary_en）；缺 summary_zh 直接报错「需要中文简介」，build_daily 校验社区简介至少含一个汉字。
