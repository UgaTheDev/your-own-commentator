# Source this from a stream worktree:  source /Users/kushzingade/Documents/Hackathons/Amazon/scripts/stream-env.sh
# Worktrees have no data/, .env or .venv (all gitignored); point them at the main checkout.
MAIN=/Users/kushzingade/Documents/Hackathons/Amazon
export YOC_DATA="$MAIN/data"
export PY="$MAIN/.venv/bin/python"
[ -f .env ] || cp "$MAIN/.env" .env
