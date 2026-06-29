# Superswim — TWW superswimming simulation & route planner

A bit-exact, **offline** physics simulation and route planner for *The Wind Waker*
(GZLJ01 / JP) superswimming TAS optimization, plus an optional live-Dolphin validation
harness. The physics are reproduced from the game's decompilation and validated frame-by-frame
against the real game (single-precision arithmetic, the console cosine table, the x598 pump
scramble — see [`SUPERSWIM_KNOWLEDGE.md`](SUPERSWIM_KNOWLEDGE.md)).

The importable `superswim` package is **pure Python (numpy only) with no emulator dependency**,
so other projects can depend on it to run simulations.

## Install

```bash
pip install -e .          # from the repo root; makes `superswim` importable anywhere
```

## Use as a library

```python
from superswim import SwimState, plan_min_frames, expand

# Simulate an action sequence (one action = one game frame).
st = SwimState(v=0.0, anim=0.06392288208007812, air=900)   # a real cold-start anim
for a in expand("chg,60;ess,200;neu,50"):
    st.step(a)
print(st.v, st.anim, st.air, st.state)

# Plan the minimum-frame route to a destination.
res = plan_min_frames(dest=200000, v=0.0, anim=0.06392288208007812, air=900)
print(res["frames"], "frames")
```

Or from the CLI: `python -m superswim.sim seq "ess,200;neu,50"` (prints a SUMMARY line and can
emit an animated HTML viewer with `viz=out.html`).

## Layout

| Path | What |
|------|------|
| **`superswim/`** | The library. `sim` (physics), `plan` / `optimize` (route planner), `coldstart`, `actions` (seq helpers), `predict/` (position + camera predictors), `tables/` (console lookup data). |
| `tests/` | Offline `pytest` suite: unit tests for the physics helpers + golden/characterization tests freezing bit-exact sim/planner output (`test_*.py`, `golden/`). No Dolphin needed. |
| `tests/dolphin/` | Live sim-vs-Dolphin validators (`run_tests.py`, `verify_state.py`, `spotcheck_*`). Need a running Dolphin. |
| `harness/` | Live-Dolphin research tooling — `capture/` (read game state), `validate/` (sim-vs-live), `dtm/` (movie authoring/playback), `search/` (live-grounded planning). Depends on `../tools/dolphin_mem`. |
| `viz/` | HTML/JSON trajectory artifact builders (offline). |
| `fixtures/` | Code-referenced baseline action sequences. |
| `knowledge/` | Reference docs (measurement tables, camera model, JP addresses). |
| `archive/` | One-off probes, calibrations, and traces kept for provenance (not part of the supported surface). |

## Docs

- [`SUPERSWIM_KNOWLEDGE.md`](SUPERSWIM_KNOWLEDGE.md) — **source of truth** for the mechanics & TAS optimization.
- [`HANDOFF.md`](HANDOFF.md) — current project state ("where we are / what's next").
- [`knowledge/`](knowledge/) — `SUPERSWIM_DATA.md` (measurement tables), `CAMERA_MODEL.md` +
  `SWIM_CAMERA_PREDICT_NOTES.md` (camera steering), `jp_swim_addrs.md` (JP map addresses).

## Testing

Two layers, run both before/after any sim change:

```bash
pip install -e ".[test]"
pytest                              # offline: unit + golden suite (no Dolphin), runs anywhere/CI
python tests/dolphin/run_tests.py   # live: sim-vs-Dolphin accuracy (needs Dolphin, see below)
```

- **Offline (`pytest`)** — unit tests for the physics helpers plus golden/characterization tests
  that freeze the current bit-exact sim/planner output. This is the fast logic-regression gate.
  After a deliberate, live-verified behavior change, refresh the goldens with
  `python -m tests.golden_regen`.
- **Live (`tests/dolphin/`)** — replays baselines on a running Dolphin and compares to the sim,
  confirming the model still matches the real game. See [`tests/dolphin/README.md`](tests/dolphin/README.md):
  it needs Dolphin + `twwgz.iso` and a cold-start slate you supply (`TWWGZ_SLATE=...` or `slot=N`) —
  the slate is a dump of copyrighted game RAM and is **not** shipped here.

## Standalone vs. workspace

The **offline `superswim` package and `pytest` suite work standalone** — `pip install -e .` and go.
The **live tooling** (`harness/`, `tests/dolphin/`) additionally needs `dolphin_mem` from the sibling
`../tools/` workspace (reached via a path bootstrap; absent in a standalone clone) and a running
Dolphin. Read [`../tools/DOLPHIN_CONTROL.md`](../tools/DOLPHIN_CONTROL.md) before using it.

## Status / follow-ups

- The 4 `swim_predict*` variants in `superswim/predict/` form an evolution chain and are kept
  as separate modules; consolidating them into one predictor is a known follow-up (each merge
  step must be re-validated bit-exact).
- `bug#2` (dense-pump live divergence) is resolved as a pipe input-delivery artifact — DTM movie
  playback is the faithful delivery path, not the `advanceseq` pipe (see `HANDOFF.md`).
