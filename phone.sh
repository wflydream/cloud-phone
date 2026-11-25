#!/usr/bin/env bash
# 起一台云端安卓机（GitHub Actions 免费 runner + KVM 模拟器 + noVNC），打印可操作链接。
# 用法：./phone.sh [分钟数=45]
set -euo pipefail
MIN=${1:-45}
REPO=wflydream/cloud-phone
: "${GH_TOKEN:=$(python3 -c "import json;print(json.load(open('/Users/wfly/Documents/code/wfly/bolierplate/.secrets/github/wflydream.json'))['full'])")}"
export GH_TOKEN

gh workflow run cloud-phone.yml -R "$REPO" -f minutes="$MIN"
sleep 15
RID=$(gh api "repos/$REPO/actions/runs?per_page=1" -q '.workflow_runs[0].id')
echo "run $RID, 等模拟器启动（约 4 分钟）..."
for i in $(seq 1 60); do
  URL=$(gh run view "$RID" -R "$REPO" --log 2>/dev/null | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com/vnc\.html[^ ]*' | head -1) || true
  [ -n "$URL" ] && { echo "$URL"; exit 0; }
  [ "$(gh api "repos/$REPO/actions/runs/$RID" -q .status)" != in_progress ] && { echo "run 结束未拿到链接:" >&2; gh run view "$RID" -R "$REPO" --log 2>/dev/null | grep -E 'BOOT FAILED|exit 1|Error' | tail -5 >&2; exit 1; }
  sleep 15
done
echo "超时，手动看 https://github.com/$REPO/actions/runs/$RID" >&2
exit 1
