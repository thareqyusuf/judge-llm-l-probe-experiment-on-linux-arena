#!/usr/bin/env bash
# Start (or reattach to) the working tmux session.
#
#   bash session.sh
#
# Windows:
#   0 work    shell in the repo, with a VRAM monitor underneath
#   1 exp     Claude Code -- the experiment session
#   2 verify  empty shell -- you start Claude here yourself, with your own prompt
#   3 logs    tail on the log directory
#
# Window 2 is deliberately not auto-started. The verification session must be
# opened by you, with a prompt you wrote. If the experiment session (or a
# subagent it spawned) frames the verification, the check inherits the belief
# it is supposed to be testing.

set -euo pipefail

WORKSPACE="${WORKSPACE:-/workspace}"
REPO="$WORKSPACE/repo"
LOGS="$WORKSPACE/logs"
SESSION="mi"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Reattaching to existing session '$SESSION'."
  exec tmux attach -t "$SESSION"
fi

mkdir -p "$REPO" "$LOGS"

tmux new-session  -d -s "$SESSION" -n work -c "$REPO"
tmux split-window -v -t "$SESSION:work" -c "$REPO" \
  'watch -n2 --no-title nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv'
tmux resize-pane  -t "$SESSION:work.1" -y 6

tmux new-window -t "$SESSION" -n exp    -c "$REPO" 'claude'
tmux new-window -t "$SESSION" -n verify -c "$REPO"
tmux new-window -t "$SESSION" -n logs   -c "$LOGS" \
  "tail -F $LOGS/*.log 2>/dev/null || (echo 'no logs yet'; exec bash)"

tmux select-window -t "$SESSION:work"
exec tmux attach -t "$SESSION"
