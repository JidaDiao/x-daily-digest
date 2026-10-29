#!/usr/bin/env bash
# DiaoDaily 公开来源抓取，每天 08:20 Asia/Shanghai
set -o pipefail
cd "$(dirname "$0")"
mkdir -p logs
python3 collect.py "$@" 2>&1 | tee -a "logs/collect-$(TZ=Asia/Shanghai date +%F).log"
