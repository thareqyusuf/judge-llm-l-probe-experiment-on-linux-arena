#!/usr/bin/env bash
# Start a new experiment: branch exp/<slug> off main, scaffold its namespace,
# commit the scaffold, push with upstream set.
#
#   bash infra/new-experiment.sh induction-heads
#
# <slug>: lowercase, digits, hyphens. Name the *question*, not the method:
#   good: induction-heads, ioi-name-mover, refusal-direction-l12
#   bad:  experiment2, test, qwen
#
# Layout created (all namespaced by slug so branches never conflict at merge):
#   experiments/<slug>/TASK.md       the prompt the experiment session is given, verbatim
#   experiments/<slug>/RESULTS.md    this experiment's running log (from infra/templates)
#   results/raw/<slug>/              raw JSON, append-only
#   results/figures/<slug>/          PNGs
#   logs/<slug>/                     stdout of runs
#   checkpoints/<slug>/              big intermediates (gitignored)

set -euo pipefail

SLUG="${1:-}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

[[ -n "$SLUG" ]] || { echo "usage: bash infra/new-experiment.sh <slug>"; exit 1; }
[[ "$SLUG" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]] || { echo "!! slug must be lowercase letters/digits/hyphens: $SLUG"; exit 1; }
BRANCH="exp/$SLUG"

[[ -z "$(git status --porcelain)" ]] || { echo "!! working tree not clean. Commit or stash first."; exit 1; }
git rev-parse --verify -q "$BRANCH" >/dev/null && { echo "!! branch $BRANCH already exists. git checkout $BRANCH"; exit 1; }
[[ ! -e "experiments/$SLUG" ]] || { echo "!! experiments/$SLUG already exists."; exit 1; }

git checkout -q main
git pull -q --ff-only || echo "(could not fast-forward main; continuing from local main)"
git checkout -q -b "$BRANCH"

mkdir -p "experiments/$SLUG" "results/raw/$SLUG" "results/figures/$SLUG" "logs/$SLUG" "checkpoints/$SLUG"
sed "s/<slug>/$SLUG/g" infra/templates/RESULTS.md > "experiments/$SLUG/RESULTS.md"
cat > "experiments/$SLUG/TASK.md" <<TASK
# TASK — $SLUG

<Paste the exact prompt given to the experiment session here, before running
anything. The reviewer compares what was asked against what was run.>
TASK
touch "results/raw/$SLUG/.gitkeep" "results/figures/$SLUG/.gitkeep" "logs/$SLUG/.gitkeep"

git add "experiments/$SLUG" "results/raw/$SLUG" "results/figures/$SLUG" "logs/$SLUG"
git commit -q -m "exp($SLUG): scaffold"
git push -q -u origin "$BRANCH"

cat <<MSG

Created $BRANCH and pushed. Now:
  1. write experiments/$SLUG/TASK.md (the prompt, verbatim)
  2. write the hypothesis line in experiments/$SLUG/RESULTS.md
  3. run; after each run:  bash infra/handoff.sh "<what ran>"
MSG
