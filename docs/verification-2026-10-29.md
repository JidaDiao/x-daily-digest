# 验证记录 2026-10-29

## 单元场景（python3 tests/test_update_hub_entry.py）
```
PASS 正常发布：两类都指向 10-28 {'x': '2026-10-28', 'design': '2026-10-28'}
PASS 日期不同：叼报 10-29 / 设计 10-28 {'x': '2026-10-29', 'design': '2026-10-28'}
PASS 日期不同：卡片显示各自日期 
PASS 单类损坏：设计回退 10-28，叼报照常 10-29 {'x': '2026-10-29', 'design': '2026-10-28'}
PASS 单类缺失：设计保留原入口 10-24，叼报 10-29 {'x': '2026-10-29', 'design': '2026-10-24'}
PASS 不生成空链接 
PASS 重复运行无 diff 
7/7 通过
```

## 真实 gh-pages（基于 f2b0d61，--check-live）
```
叼报: 2026-10-29
设计灵感: 2026-10-28
hub/index.html 已更新
二次运行:
hub/index.html 无变化
```

## 部署后实测（2026-10-29 11:24 上海时间，gh-pages 45e3854）
```
hub/index.html（不带参数与 ?t=随机 结果一致，缓存已更新）:
  最新一期 2026-10-29
  叼报 2026-10-29 -> https://jidadiao.github.io/x-daily-digest/2026-10-29.html
  设计 2026-10-28 -> https://jidadiao.github.io/x-daily-digest/design/2026-10-28.html
200 178263  /2026-10-29.html
200 121899  /design/2026-10-28.html
200   2781  /hub/
200   5343  /   (title: 叼报 · 往期)
门户 /go/x/2026-10-29      302 -> https://jidadiao.github.io/x-daily-digest/2026-10-29.html
门户 /go/design/2026-10-28 302 -> https://daily.jidadiao.fun/design/2026-10-28.html (200)
Actions: hub-entry success（无 diff，未产生额外提交）；pages build and deployment success
```
