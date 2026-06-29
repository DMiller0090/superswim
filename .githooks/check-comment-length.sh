#!/usr/bin/env bash
# Flags newly-added comment blocks that exceed the one-line default from STYLE.md. Heuristic gate:
# blocks > MAX consecutive added `#` comment lines for review — a nudge to promote long rationale
# to the knowledge base (see STYLE.md). Genuine rare exceptions bypass via git commit --no-verify.
#
#   (default)   scan staged diff          -- used by .githooks/pre-commit
#   --worktree  scan working tree vs HEAD  -- handy for a manual / editor-stop check
#
# Exit 0 = clean, 1 = an over-long added comment block was found.

MAX=${COMMENT_MAX_LINES:-2}   # allowed consecutive added comment lines
RANGE="--cached"
[ "${1:-}" = "--worktree" ] && RANGE="HEAD"

# Python only. Docstrings (triple-quoted) are NOT `#` comments and are intentionally not gated.
diff=$(git diff $RANGE -U0 --no-color -- '*.py' 2>/dev/null)
[ -z "$diff" ] && exit 0

# Track each run of consecutive added `#` comment lines; report runs > MAX.
report=$(printf '%s\n' "$diff" | awk -v MAX="$MAX" '
  /^\+\+\+ /  { file = substr($0, 7); next }
  /^@@ /      { match($0, /\+[0-9]+/); line = substr($0, RSTART+1, RLENGTH-1) + 0; run = 0; next }
  /^\+/ {
    s = substr($0, 2); sub(/^[ \t]+/, "", s)
    isc = (s ~ /^#/)
    if (s ~ /^#!/)        isc = 0   # shebang
    if (s ~ /^# -\*-/)    isc = 0   # encoding cookie
    if (isc) { if (run == 0) start = line; run++; len[file "\t" start] = run }
    else     { run = 0 }
    line++
    next
  }
  END { for (k in len) if (len[k] > MAX) { split(k, p, "\t"); printf "  %s:%s  (%d-line added comment block)\n", p[1], p[2], len[k] } }
')

if [ -n "$report" ]; then
  echo "$report" >&2
  echo "" >&2
  echo "comment-length gate: over-long added comment block(s) (max $MAX lines)." >&2
  echo "Promote long rationale to the knowledge base per STYLE.md, or tighten to one line." >&2
  echo "Genuine rare exception? bypass with: git commit --no-verify" >&2
  echo "(or raise the bar for a commit: COMMENT_MAX_LINES=N git commit ...)" >&2
  exit 1
fi
exit 0
