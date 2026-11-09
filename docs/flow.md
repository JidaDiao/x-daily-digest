# 每日流程图

时区：Asia/Shanghai（UTC+8）。所有日期 `DATE` 为当天 `YYYY-MM-DD`。

```mermaid
flowchart TD
  A[凌晨前后<br/>设计灵感选题与出页] --> B[推 gh-pages design/DATE.html]
  B --> C[hub_entry.sh]
  C --> D[10:20 公开源抓取<br/>collectors/run.sh]
  D --> E[items-public-DATE.json]
  F[约 10:30 X 素材<br/>search_posts_all] --> G[items-DATE.json]
  H[周六约 10:16 副业] -.->|仅周六| I[items-sidehustle-DATE.json]
  E --> J[素材齐：出叼报页]
  G --> J
  I -.-> J
  J --> K[build_daily.py + chk.py<br/>390/360 review]
  K --> L[推 gh-pages DATE.html]
  L --> M[hub_entry.sh]
  M --> N[SSH VPS: /srv/daily/bin/sync.sh]
  N --> O[12:00 score.py + 文案]
  O --> P[消息一 叼报]
  O --> Q[消息二 设计灵感]
  B --> Q
```

```mermaid
flowchart LR
  subgraph box [共用箱子]
    X[items-DATE.json]
    P[items-public-DATE.json]
    S[items-sidehustle-DATE.json]
    W["/workspace/digests/web/DATE.html"]
    D["/workspace/inspo/web/design/DATE.html"]
  end
  subgraph gh [GitHub gh-pages]
    W2[DATE.html]
    D2[design/DATE.html]
    H[hub/index.html]
  end
  subgraph vps [VPS /srv/daily]
    M[site/ 镜像]
    API[daily-api :9090]
    DB[data/prefs.db]
  end
  W --> W2
  D --> D2
  W2 --> M
  D2 --> M
  M -->|GET /go/x/DATE 302| U[用户]
  M -->|GET /go/design/DATE 302| U
  W2 -->|内联 news-signal.js| API
  D2 -->|design-feedback / signal| API
  API --> DB
  DB -->|钥匙 factor| SC[score.py]
  X --> SC
  P --> SC
  S --> SC
```

门户路由（nginx，详见 `nginx-standalone.example.conf`）：

- `GET /go/x/DATE` → daily-api 记已读 → 302 `/x/DATE.html`
- `GET /go/design/DATE` → 302 `/design/DATE.html`
- `/x/` alias 到 `/srv/daily/site/`（对应 gh-pages 根目录的 `DATE.html`）
- `/design/` alias 到 `/srv/daily/site/design/`
- nginx 在 `</body>` 前注入 `read-beacon.js` 和 `pwa-nav.js`（只对门户镜像页；github.io 没有这层注入）
