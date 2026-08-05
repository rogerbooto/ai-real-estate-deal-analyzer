#!/usr/bin/env bash
# Regenerate the Mission 2 / task 3.1a before-and-after report pairs.
#
#   BEFORE = the code as it was at the tip of this branch before 3.1a landed. Produced from a
#            throwaway git worktree, so it is genuinely the old code, not a simulation of it.
#   AFTER  = the working tree.
#
# Run from the repo root:  bash artifacts/mission2_3.1a/regenerate.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

# conda's own activate/deactivate hooks reference unset vars, so -u is dropped just for them.
set +u
# shellcheck disable=SC1091
source /home/rtokime/anaconda3/etc/profile.d/conda.sh
conda activate airedeal
set -u

# The commit BEFORE task 3.1a. Override when the branch has moved on:
#   BEFORE_REF=<sha> bash artifacts/mission2_3.1a/regenerate.sh
BEFORE_REF="${BEFORE_REF:-070b60b}"
WORKTREE="$(mktemp -d)/pre-3.1a"

CASES=(
  36_kelly_negotiated_280k_target_400bps
  36_kelly_target_050bps
  36_kelly_target_150bps
  36_kelly_target_250bps
)

git worktree add "$WORKTREE" "$BEFORE_REF" --detach >/dev/null
trap 'git worktree remove "$WORKTREE" --force >/dev/null 2>&1 || true' EXIT

for name in "${CASES[@]}"; do
  cfg="artifacts/mission2_3.1a/configs/${name}.json"
  # BEFORE: the old main.py, run from THIS repo root so it reads the same config and the same
  # sample bundle. sys.path[0] is the worktree, so `src` comes from the pre-3.1a code.
  python "$WORKTREE/main.py" --config "$cfg" --out "artifacts/mission2_3.1a/before/${name}.md" | tail -1
  # AFTER: the working tree.
  python main.py --config "$cfg" --out "artifacts/mission2_3.1a/after/${name}.md" | tail -1
  echo "--- diff: ${name} ---"
  diff -u "artifacts/mission2_3.1a/before/${name}.md" "artifacts/mission2_3.1a/after/${name}.md" || true
done
