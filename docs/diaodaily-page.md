# 叼报资讯页生成方法与设计原则

完整规则在 `src/digests/web/DAILY.md` 和 `src/digests/README.md`。
箱子上的活目录是 `/workspace/digests/`。

历史上由 **前端设计灵感库** 在素材齐后出页（常见 10:40–11:30），再把链接交给 12:00 推送。

## 设计原则（用户反复强调的）

1. **先立场，再选料**。先写一句场景/隐喻：为什么这样组织这些新闻、舍弃了什么，再从收藏里只选服务这个思路的元素。不要把收藏元素堆上去。
2. **每天换整体风格**，五维相对前一天都要有差异：style / motion / ui / ux / card。写进 `cfg.diffs`。
3. **要有审美判断，不能太 AI**。正例：2026-10-22 地铁线路图的统一感和手感（不要再复刻地铁）。反例：通用 UI kit 堆砌、花哨组件墙、热敏小票式「假创意」。
4. **形式服务于场景**。整页是一个场景；动效克制，彩蛋至多 1–2 处；`prefers-reduced-motion` 必须支持。
5. 收藏元素 ≥5、来源站 ≥4、自创 ≤2、合计交互/视觉细节 ≥8。前一期用过的元素当天不能再用；3 天内同一元素最多 1 次；相邻 Jaccard ≤ 0.2；回避元素（`avoid` 或 rating≤2）不用。
6. 先选版式原型（8 种池，近 7 天不重复）。「纵向滚动卡片列表」连续最多 1 天。禁止把「铭牌+页签+竖排卡片+点开展开+已读」当默认骨架。
7. 骨架 6 维（信息载体、导航方式、浏览轴、进场方式、底色色相、字体组合）与前 3 天**任一天**比至少 4 维不同。底色色相每天换（相差 ≥30°，或一中性一有色）。
8. 只有 1 个强调色；字体 ≤2 套。头条前 3 条必须有大/中/小层级。
9. 低分原型（used-combos `score`≤2）30 天内不用；高分原型（≥4）隔 14 天后可回归，但必须换题材和骨架维度。

原型池：1 空间/地图型 · 2 时间/时刻表型 · 3 实物桌面/拼贴型 · 4 单列长卷型 · 5 索引/墙型 · 6 一次一条型 · 7 对话/终端/命令型 · 8 分栏对照/仪表盘型。

## 内容组织

- 主区是精选 10–15 条（好内容少就少），**不按来源分组**，按价值/话题分组。来源只作小标。
- 全量放在可展开的「全部条目」里，互动按钮照常。
- 博客条目必须有可辨认的「博客」标识（贴纸、路牌、侧标都可以，但要一眼能认出）。
- 社区条目简介必须是中文（`summary_zh`）。
- 评分/电平用「价值」（信息差、干货、相关），不要只用热度。
- `data-sig-id` 用 `news_signal.sig_attrs(it)`，保持稳定。

精选规则以 `src/digests/lib/pick-rules.md` 为准。出页时可以先跑 `score.py` 得到候选，再人工剔明显违规项（白嫖脚本、诉讼吃瓜、纯 A/B 传闻等），并在页顶或交付里写筛掉统计。

## 构建步骤

```bash
cd /workspace/digests
# 1. 写 pages/YYYY-MM-DD.py（参考最近一天，但必须换原型和五维）
# 2. 构建（会校验 used-combos、signal、中文简介）
python3 build_daily.py YYYY-MM-DD
# 3. 手机检查，截图到 shots/YYYY-MM-DD-v1/，必须自己看图
python3 chk.py YYYY-MM-DD v1
# 4. 发布到 site/（可选；很多时候直接推 web/DATE.html）
python3 publish.py
```

`build_daily.py` 会从 `/workspace/daily-portal/web/news-signal.js` **现读内联**最新评分脚本。仓库对应 `src/daily-portal/web/news-signal.js`。按钮必须是扁平 2D SVG，按下态（`aria-pressed`）实心底色反白。不要再手写一套立体按钮。

校验失败 exit 2，不写文件。不要用 `--no-check` 出新页（只给重建旧页用）。

## 发布路径

- gh-pages 根目录：`YYYY-MM-DD.html`
- github.io：`https://jidadiao.github.io/x-daily-digest/YYYY-MM-DD.html`
- 门户：`https://daily.jidadiao.fun/go/x/YYYY-MM-DD` → 302 → `/x/YYYY-MM-DD.html`
- `/x/` 是 nginx alias，**gh-pages 上没有 `x/` 目录**

推送用 GitHub 接口写 `gh-pages`（先取 sha；大文件 `$file:`）。约 1 分钟后 curl GET + `cmp` 与本地一致。然后跑 `scripts/hub_entry.sh`，必要时再 SSH sync。详见 [publish-verify.md](publish-verify.md)。

## 已上线页面的修改

只能增量修改。禁止：

- 改已有条目的 `data-sig-id`
- 删掉或重排导致用户已打分条目对不上
- 整页覆盖

改完必须再核对：评分按钮还在、id 集合没变、已有评分能对上。
