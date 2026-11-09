# 设计灵感页生成方法

完整阶段化流程、block 格式、截图方法和自检清单以 `src/design/HOWTO.md` 为准。
箱子上的活目录是 `/workspace/inspo/web/design/`（改脚本后应同步回 `src/design/`）。

历史上由 **前端设计灵感库** bot 在凌晨制作并推 `gh-pages`。

## 每日产量

- 固定 **8 条：Web 4 + App 4**。不够不凑，用 `python3 build.py DATE --allow-short` 并写明 `short_reason`。
- 上一期用过的站点/App/元素，下一期不再用（对照 `recommended.md` 和 `blocks/_archive/<上一期>/`）。
- 每条 `focus`：`交互` / `界面` / `兼具`（兼具最多 1 条）。**交互 ≥ 4、界面 ≥ 3**（兼具两边都算）。
- 至少 1 条以卡片、图标、标签的样式和长相为主，交付时点名「本期卡片条」。
- 设计页**不必**每天换外壳；每天换整体风格的是叼报资讯页。

### 交互 vs 界面

- **交互**：价值在怎么操作。必须写 `how`（怎么操作）和 `fresh`（为什么新鲜）。
- **界面**：价值在看一眼就惊艳——版式、字体、配色、留白、插画/质感。

## 阶段（可断点续跑）

状态文件：`stage/<date>/state.json`。开跑第一件事：

```bash
cd /workspace/inspo/web/design   # 或仓库 src/design
python3 tools/stage.py <date> next
```

| 阶段 | 做什么 | 产物 |
|---|---|---|
| pick | 读偏好/recommended/web-pool；Mobbin 找 4 App + 4 Web；写 focus | `stage/<date>/pick.json` |
| assets | App 视频压缩为 `.mp4.b64` + 封面；Web 抓源码+截图 | `assets/<date>/`、`src/<key>/`、`thumbs/` |
| webdemo | 写 4 个 Web block + 4 个 App block | `blocks/NN-<key>.html` |
| build | `python3 build.py <date>` | `<date>.html` |
| check | `timeout -k 5 120 python3 tools/check.py <date>.html`，看 390/360 截图 | `/tmp/design-check-*.png` |
| publish | 推 gh-pages，curl+cmp，跑 `scripts/hub_entry.sh` | 线上页 |
| deliver | 更新日期到 recommended.md / web-pool.md | 给 12:00 推送用的 8 条清单 |

一个外部步骤失败 1 次就换下一个候选，不要卡在同一站反复重试。

## Web

- 用代码复刻 1 个关键元素，做成可交互 live demo，不是链接加截图。
- 色值、时长、缓动尽量照抄源码，并在 `params` 里注明出处；自己加的效果写成「demo 增强」。
- 不用对方的 logo/图标文件。
- demo 根加 `data-replay`；写 `knobs` 做可调参；必须有 `<!--code-->` 最小可运行片段。
- 手机上：怎么操作/为什么新鲜、关键参数、可调参数、关键代码默认折叠（`<details>` 不要加 `open`）。
- 卡片主信息顺序：标题 → demo → 简介/tags → 缩略图+链接 → 打分收藏。

稳定截图（不要用 `google-chrome --headless --screenshot`，它可能挂住数小时）：

```bash
timeout -k 5 45 python3 tools/shot.py https://example.com src/<k>/shotm.png --w 390 --h 844
timeout -k 5 45 python3 tools/shot.py https://example.com src/<k>/shot.png --w 1440 --h 900
```

## App（依赖 Mobbin 连接器）

这是无法只靠仓库还原的环节：需要 `user-Mobbin` 的 `search_screens` / `search_flows`（`platform=ios`）。

1. 每次查询只描述一个界面，例如 “bottom sheet modal with grabber and action buttons”。
2. **一定要看返回的图片再选**，挑克制、圆角、少炫的。
3. 记下 `mobbin_url` 和 `app_name`。
4. 放 Mobbin **原视频或原图**，不复刻。视频：mp4 → `.mp4.b64`，`muted loop playsinline preload="metadata"`，进视口才加载。
5. 压到约 480px 宽、24–30fps、CRF≈30、截短到 15s 内。页面+素材建议 ≤ 8MB。
6. 没有 Mobbin 时：不要用盗图站充数；当天 App 条只能标明「Mobbin 不可用，设计页未凑满」并用 `--allow-short`。

## 今日拼接

写 `blocks/_collage.json`：当日设计立场 + 收藏/自创元素的拼接，不要堆卡片。
字段见 HOWTO（`stance` / `why` / `bits[]`）。元素优先 `design-tokens.json` 里 `status=favorite`，自创 ≤2。

## 发布与交付

1. 用 GitHub 接口把 `design/DATE.html` 和新增素材推到 **gh-pages**（先取 sha，大文件用 `$file:`）。
2. `design-feedback.js` 没变就不要重推。
3. 约 1 分钟后：`curl .../design/DATE.html?t=$RANDOM | cmp - DATE.html`
4. 跑 `scripts/hub_entry.sh`；输出 `PUSH` 再推 `hub/index.html`。
5. 给 12:00 流程：页面链接、8 条清单（Web/App、交互/界面、一句话）、今日拼接一句、本期卡片条、手机检查结果。

门户：`https://daily.jidadiao.fun/go/design/DATE`（GET 302 正常）。
