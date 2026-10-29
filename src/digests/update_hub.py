#!/usr/bin/env python3
"""已废弃按日期拼链接的旧逻辑。转调仓库里的 scripts/update_hub_entry.py（见 JidaDiao/x-daily-digest main 分支）。
用法：bash /workspace/digests/hub_entry.sh   → 产出 /tmp/xdd-pages/hub/index.html，再用 push_files 推 gh-pages"""
import subprocess, sys
sys.exit(subprocess.call(["bash", "/workspace/digests/hub_entry.sh"]))
