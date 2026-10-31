# Web 候选池（浅色 · 克制 · 轻动效）

用途：凑齐每期 **4 Web**（2026-11-01 起，见 HOWTO 硬规则 v3），4 站来自至少 3 个不同方向组。按方向分组，轮换着取，同一站 14 天内不重复。

**轻复刻 = 每站只复刻 1 个关键元素**：一个交互或一段动效，比如一个按钮的按压、一条列表的进场、一个拖拽，再配上它的参数（缓动、时长、圆角、阴影）。不复刻整屏，不复刻品牌插画。

检查记录：2026-10-25，用 `curl -L` 逐个检查，全部返回 200。首页偏暗的站标了「暗」，只取单个元素，配色改成浅色。

## A. 产品工具 · 精致微交互
| 站 | URL | 可取的 1 个元素 |
|---|---|---|
| Linear（暗） | https://linear.app | 命令面板展开 + 列表 stagger 进场 |
| Raycast（暗） | https://www.raycast.com | 快捷键 kbd 按下回弹 |
| Vercel | https://vercel.com | 部署状态点的脉冲 + 进度条 |
| Attio（2026-10-31） | https://attio.com | 表格行 hover 高亮 + 内联编辑 |
| Superhuman | https://superhuman.com | 键盘提示 toast 浮起 |

## B. 建站 / 动效工具
| 站 | URL | 可取的 1 个元素 |
|---|---|---|
| Framer | https://www.framer.com | 卡片 scroll 视差缩放 |
| Rive | https://rive.app | 状态机按钮（idle/hover/press） |
| Spline | https://spline.design | 轻量 3D 卡片倾斜跟随指针 |
| Lottielab | https://www.lottielab.com | 时间轴滑块拖动预览 |
| mmm.page | https://mmm.page | 自由摆放的贴纸拖拽 |

## C. 浏览器 / 写作 / 笔记
| 站 | URL | 可取的 1 个元素 |
|---|---|---|
| Craft（2026-10-26） | https://www.craft.do | 块拖拽排序 |
| Reflect（2026-10-31 curl 无响应，先跳过） | https://reflect.app | 双向链接悬浮预览 |
| Tana | https://tana.inc | 节点 `#标签` 补全 |
| Capacities（2026-10-31） | https://capacities.io | 对象卡片翻面 |
| Obsidian | https://obsidian.md | 图谱节点轻漂浮 |

## D. 日程 / 专注
| 站 | URL | 可取的 1 个元素 |
|---|---|---|
| Sunsama（2026-10-28） | https://www.sunsama.com | 任务拖进日程时间轴 |
| Notion Calendar（原 Cron） | https://www.notion.com/product/calendar | 时间块拉伸 |
| Flighty（2026-10-27） | https://flighty.com | 航班进度条 + 倒计时翻牌 |

## E. 收藏 / 灵感 / 演示
| 站 | URL | 可取的 1 个元素 |
|---|---|---|
| Mymind（2026-10-28） | https://mymind.com | 瀑布流卡片淡入 + 搜索高亮 |
| Are.na | https://www.are.na | 极简块网格 hover |
| Raindrop | https://raindrop.io | 书签卡片收藏动效 |
| Readwise Reader | https://readwise.io | 划线高亮扫过 |
| Pitch | https://pitch.com | 幻灯片缩略图切换 |
| Warp（暗） | https://www.warp.dev | 终端命令块折叠 |
| tldraw（2026-10-27） | https://www.tldraw.com | 手绘线条平滑 |
| Rows | https://rows.com | 单元格公式补全 |
| HEY | https://www.hey.com | 邮件分拣按钮（Screen in/out） |
| Family | https://family.co | 钱包卡片弹性展开 |

## 已排除
- **Read.cv**：返回 402，已停止服务（被 Perplexity 收购）。
- **Height**：域名没有响应，产品已关停。
- **Arc**：2026-10-31 检查，arc.net 已是「A farewell to Arc」告别页（宣布 2026-12-22 停服），排除。

## 池外用过
| 2026-10-26 | Fathom Analytics | https://usefathom.com | 柱状图填满进场 |
