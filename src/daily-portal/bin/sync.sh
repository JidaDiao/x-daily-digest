#!/bin/bash
# pull gh-pages mirror (GitHub is slow from this VPS: try mirror proxy, then direct, then codeload tarball), then rebuild portal
# 2026-10-25: errors logged (not discarded), timestamps in CST (UTC+8), FAIL recorded; >=2 consecutive fails -> data/sync-alert.json
set -u
exec 9>/tmp/daily-sync.lock; flock -n 9 || exit 0
D=/srv/daily/data; ST=$D/sync-state.json; AL=$D/sync-alert.json
ts(){ TZ=Asia/Shanghai date '+%F %T CST(UTC+8)'; }
cd /srv/daily/site || { echo "$(ts) sync FAIL: no site dir"; exit 1; }
ok=0; errs=""
for u in https://ghfast.top/https://github.com/JidaDiao/x-daily-digest.git https://github.com/JidaDiao/x-daily-digest.git; do
  if e=$(timeout 180 git fetch --depth 1 "$u" gh-pages 2>&1); then
    if e2=$(git reset -q --hard FETCH_HEAD 2>&1); then ok=1; break; else errs+="[reset] $e2 "; fi
  else errs+="[$u rc=$?] $(echo "$e" | tail -n 2 | tr '\n' ' ') "; fi
done
if [ $ok = 0 ]; then
  t=$(mktemp -d)
  if e=$(set -o pipefail; timeout 180 curl -fsSL https://codeload.github.com/JidaDiao/x-daily-digest/tar.gz/refs/heads/gh-pages 2>&1 >"$t.tgz") && tar xzf "$t.tgz" -C "$t" --strip-components=1 2>/dev/null; then
    rsync -a --delete --exclude .git "$t"/ /srv/daily/site/ && ok=1
  else errs+="[codeload] $(echo "$e" | tail -n 1) "; fi
  rm -rf "$t" "$t.tgz"
fi
python3 - "$ST" "$AL" "$ok" "$(date -u +%FT%TZ)" "$errs" <<'PY'
import json, sys, os
st, al, ok, now, err = sys.argv[1], sys.argv[2], sys.argv[3] == "1", sys.argv[4], sys.argv[5][:500]
try: s = json.load(open(st))
except Exception: s = {}
if ok: s.update(fails=0, last_ok=now)
else: s.update(fails=s.get("fails", 0) + 1, last_fail=now, last_error=err)
json.dump(s, open(st + ".tmp", "w")); os.replace(st + ".tmp", st)
if s.get("fails", 0) >= 2:
    json.dump({"stale": True, "fails": s["fails"], "last_ok": s.get("last_ok"), "last_fail": now, "last_error": err}, open(al + ".tmp", "w")); os.replace(al + ".tmp", al)
elif os.path.exists(al): os.remove(al)
PY
if [ $ok = 1 ]; then echo "$(ts) sync ok=1 head=$(git rev-parse --short HEAD 2>/dev/null)"; else echo "$(ts) sync ok=0 FAIL (keeping old mirror): $errs"; fi
/usr/bin/python3 /srv/daily/bin/ghratings.py
/usr/bin/python3 /srv/daily/bin/build.py
