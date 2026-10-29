#!/usr/bin/env bash
# 每日发布最后一步：拉最新 gh-pages → 幂等更新 hub 入口（含线上 200 校验）→ 打印是否需要推送
set -euo pipefail
REPO=https://github.com/JidaDiao/x-daily-digest.git
DIR=${PAGES_DIR:-/tmp/xdd-pages}
SRC=${SRC_DIR:-/tmp/xdd-main}
if [ -d "$DIR/.git" ]; then git -C "$DIR" fetch -q --depth 1 origin gh-pages && git -C "$DIR" reset -q --hard origin/gh-pages
else rm -rf "$DIR"; git clone -q --depth 1 -b gh-pages "$REPO" "$DIR"; fi
if [ -d "$SRC/.git" ]; then git -C "$SRC" fetch -q --depth 1 origin main && git -C "$SRC" reset -q --hard origin/main
else rm -rf "$SRC"; git clone -q --depth 1 -b main "$REPO" "$SRC"; fi
echo "gh-pages 基于 $(git -C "$DIR" rev-parse HEAD)"
rc=0; python3 "$SRC/scripts/update_hub_entry.py" --root "$DIR" --check-live || rc=$?
if git -C "$DIR" diff --quiet -- hub/index.html; then echo "NO_PUSH: hub 已是最新"
else echo "PUSH: 用 push_files 把 $DIR/hub/index.html 推到 gh-pages 的 hub/index.html"; fi
exit $rc
