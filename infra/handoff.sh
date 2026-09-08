#!/usr/bin/env bash
# Commit and push a finished run on the current experiment branch so the
# laptop-side review can pull it.
#
#   bash infra/handoff.sh "full run, seed 0"        -> commit "exp(<slug>): full run, seed 0"
#
# Refuses if:
#   - not on an exp/<slug> branch (never commit results to main)
#   - nothing under results/raw/<slug>/ changed (a run that wrote no raw file is not a run)
#   - experiments/<slug>/RESULTS.md was not touched (every run gets an entry, even a failed one)
#   - a file about to be committed is larger than MAX_MB (tensors go to checkpoints/)
#   - changes exist outside this experiment's namespace (they belong on main or another branch)
# Pass --force as the second arg to override the RESULTS.md check only.

set -euo pipefail

MSG="${1:-}"
FORCE="${2:-}"
MAX_MB=10
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

[[ -n "$MSG" ]] || { echo "usage: bash infra/handoff.sh \"<what ran>\" [--force]"; exit 1; }

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[[ "$BRANCH" == exp/* ]] || { echo "!! on '$BRANCH', not an exp/<slug> branch. Results never go on main directly."; exit 1; }
SLUG="${BRANCH#exp/}"
NS=("experiments/$SLUG" "results/raw/$SLUG" "results/figures/$SLUG" "logs/$SLUG")

git add -A "${NS[@]}"

if git diff --cached --quiet -- "results/raw/$SLUG"; then
  echo "!! nothing staged under results/raw/$SLUG/. Where is the raw output of this run?"
  exit 1
fi

if git diff --cached --quiet -- "experiments/$SLUG/RESULTS.md" && [[ "$FORCE" != "--force" ]]; then
  echo "!! experiments/$SLUG/RESULTS.md unchanged. Every run gets an entry (pass --force to skip)."
  exit 1
fi

big=0
while IFS= read -r f; do
  [[ -f "$f" ]] || continue
  sz=$(( $(stat -c %s "$f") / 1024 / 1024 ))
  if (( sz > MAX_MB )); then
    echo "!! $f is ${sz} MB (> ${MAX_MB} MB). Move it to checkpoints/$SLUG/ and commit the numbers, not the tensor."
    big=1
  fi
done < <(git diff --cached --name-only)
(( big == 0 )) || exit 1

outside="$(git status --porcelain | grep -vE " (experiments|results/raw|results/figures|logs)/$SLUG/" || true)"
if [[ -n "$outside" ]]; then
  echo "!! changes outside this experiment's namespace are NOT being committed:"
  echo "$outside" | sed 's/^/     /'
  echo "   Infra/doc changes go on main; other experiments go on their own branch."
fi

echo "Staged:"; git diff --cached --stat
git commit -q -m "exp($SLUG): $MSG"
git push -q -u origin "$BRANCH"
echo "Pushed $(git rev-parse --short HEAD) to $BRANCH. On the laptop: git fetch && git checkout $BRANCH, then VERIFY.md."
