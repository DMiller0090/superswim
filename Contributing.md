# Contributing to superswim

Short, repo-specific conventions. The mechanics source of truth is `SUPERSWIM_KNOWLEDGE.md`.
(Session handoffs are local working notes under `_notes/`, not tracked in the repo.)

## Setup

```bash
pip install -e ".[test]"                                 # editable install + pytest
git config blame.ignoreRevsFile .git-blame-ignore-revs   # skip bulk-move commits in blame
git config core.hooksPath .githooks                      # enable the tracked pre-commit hook
```

The pre-commit hook (`.githooks/`) is tracked, so `core.hooksPath` wires it for every clone — no
per-file copy needed.

## Tests — run both before and after any `superswim/sim.py` change

```bash
pytest                              # offline unit + golden suite (no Dolphin), runs anywhere/CI
python tests/dolphin/run_tests.py   # live sim-vs-Dolphin accuracy (needs Dolphin + booted ISO)
```

After a *deliberate, live-verified* behavior change, refresh the goldens with
`python -m tests.golden_regen`, then re-run the Dolphin gate. A golden diff with no intended change
is a regression — investigate, don't regenerate. See `tests/dolphin/` for the live harness.

## Style

- **Code:** match the surrounding style; 4-space indent, ~100-char lines (`.editorconfig`). No
  autoformatter — the dense, hand-aligned physics code is intentional.
- **Comments:** follow [`STYLE.md`](STYLE.md) — `#`-only and terse for inline rationale, docstrings
  for longer prose, explain *why* not *what*, `TODO/FIXME/HACK/NOTE/WARNING` tags verbatim, no
  change-log narration or restate-the-code filler. When a comment grows past ~2 lines, promote the
  explanation to the knowledge base with a one-line pointer (STYLE.md §2). The pre-commit hook flags
  added `#` blocks over two lines; bypass a genuine exception with `git commit --no-verify`.

## Commits, branches, PRs

See [`STYLE.md`](STYLE.md) §6. In short:

- **Subject:** `Component: Imperative, sentence-case summary` (e.g. `Sim: Fix warm-pump f32 order`).
  No `feat:`/`fix:` prefixes, no trailing period, no co-author trailers. Bodies optional — only when
  the *why* is non-obvious; never restate the diff.
- **Branches:** `author/topic-in-kebab-case` (e.g. `dmiller/repo-reorg`). No ticket numbers.
- **PR title:** same `Component: Summary` form; body = what changed and why, no padding.
