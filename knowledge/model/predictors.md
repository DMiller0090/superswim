# Position & camera predictors

**Answers:** What are the predict/ modules and how do they relate? How is arbitrary-direction gain
priced? Why a live stick-angle grid instead of atan2? What was the off-axis charge residual?
**Status:** validated bit-exact (`tests/test_complicated.py`).
**Source:** `superswim/predict/*`; live RE 2026-06-27/28. Full log: [history/camera-predict-history](../history/camera-predict-history.md).

---

The base [sim](sim.md) is bit-exact for v/anim/air/state under one assumption: **C-stick held down
(camera frozen)**. The `predict/` modules remove that assumption to predict the **camera (csangle)**
and **Link's position (x/z)** bit-exactly under arbitrary main-stick + C-stick. They import the sim
read-only.

| Module | Role |
|--------|------|
| `swim_arbitrary.py` (`ArbitrarySwimState`) | speed gain for arbitrary stick direction |
| `stick_angle.py` (+ `stick_angle_table.csv`) | exact main-stick → angle |
| `camera_exact.py` / `camera_arbitrary.py` (+ `omega_table*.csv`) | camera yaw recurrence |
| `swim_exact.py` | exact displacement direction + magnitude given the camera angle |
| `swim_predict_complicated.py` | the unified predictor |

> The 4 `swim_predict*` variants form an evolution chain kept as separate modules; consolidating them
> is a known follow-up (each merge re-validated bit-exact).

## Arbitrary-direction gain

The decomp prices EVERY deflected swim frame identically: gain = `mStickDistance · 3 · cM_scos(d_turn)`
with a 1-frame lag — there is **no chg/ess distinction in the game**. So `ArbitrarySwimState` routes
every deflected frame through the charge path (correct 1-frame lag); neutral → `neu`. The earlier
snap-cone chg/ess split mis-priced the snap↔non-snap boundary. Ordering (live-pinned): the facing/gain
`m34E8` uses **cam[f]** (the current frame's csangle), not cam[f−1].

## Why a live stick-angle grid

The game's main-stick → angle is **not** a clean `atan2 + per-axis dead-zone` — that closed form is
only good to ~0.86° (156 s16) because the game applies the **GC radial gate** normalization. The
exact `mMainStickAngle` for all 65536 (sx,sy) cells is captured live into `stick_angle_table.csv`.
For an **on-axis** stick (sx==128: ESS / pure charge) the closed form IS exact (no capture). The
table's `stick_dist`/`value` **magnitude** columns are **NOT** the swim gain magnitude (live-disproven,
`tests/test_partial_magnitude.py`) — gain magnitude stays closed-form `/54`.

## The off-axis charge residual (resolved)

A 0.0105 too-high v on off-axis charge was **not** a camera bug (an earlier "controlled-vs-smoothed
yaw" hypothesis was wrong). Root cause: `stick_angle_table.csv` had been dumped via Dolphin's
**calibrated `set_gc_buttons`** path, but the game/tests/DTM use the **raw-byte `advancewith`** path
— they differ by up to ±155 s16 (~0.85°) on off-axis cells. Regenerating via `advancewith` (with a
2-frame settle on sy=0 wrap cells to avoid slip) → v **bit-exact** (0.0105 → 0.0). The
[omega camera grid](../mechanics/camera.md) had the same input-path bug (−546 vs −547) and was
regenerated the same way. See [history/resolved-bugs](../history/resolved-bugs.md).

## See also

- [Camera](../mechanics/camera.md) · [Arrow](../mechanics/arrow.md) (`ArrowState` 2-D stepper) ·
  [Sim](sim.md) · [history/camera-predict-history](../history/camera-predict-history.md).
