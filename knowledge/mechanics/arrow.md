# Arrow swimming

**Answers:** What is arrow swimming? How much speed do you lose by tilting? What's the tilt
limit before it breaks? How does the cross-track drift scale? What is the arrow spin-up cost?
**Status:** validated (decomp + live, closed-form in `superswim/predict/swim_arbitrary.py` /
`ArrowState`).
**Source:** decomp `setSpeedAndAngleSwim` (d_a_player_swim.inc:41,66); live 2026-06-27 (slot 9).

---

## What it is

Instead of charging straight back-and-forth, you **tilt the alternation axis toward the target**.
Link still snaps 180° each frame (see [turnaround](turnaround.md)), but now each pair of snaps
points slightly toward the destination, so he **drifts toward it while still building speed** —
forming the "tip of an arrow" pointing at the target. You trade charge rate for early progress.

## The closed-form model (parameterized by tilt α)

α = the move-direction offset from the pure-back axis toward the target. Each alternation rotates
facing by **(180° − 2α)**, and:

```
charge_rate(α) = −3 · dist · cos(2α)          # α=0 → −3 (pure back); falls as you tilt
cross_drift(α) = disp · sin(α)   per frame     # toward the target, ACCUMULATES every frame
along_move(α)  = disp · cos(α),  sign alternates (net ~cancels, like pure charge)
disp           = charge_disp_factor · true_disp(v, anim, air)
```

So tilting trades **charge rate (`cos 2α`)** for steady **cross-track drift (`sin α`)**.
`mStickDistance` stays capped at 1 — **tilt changes the cosine (the snap angle), not the
magnitude**. The decomp gain `delta = mStickDistance·3·cos(Δfacing)` is frame-exact.

### Live match

| Xbias | α | model charge rate | live |
|-------|---|-------------------|------|
| 128 | 0° | −3.00 | −3.00 |
| 160 | 8° | −2.88 | −2.88 |
| 180 | 18° | −2.43 | −2.44 |

`dz/|move| = sin α` to < 0.004. Earlier 12-frame sweep (alternating `(Xbias,255)/(Xbias,0)`):

| X-bias | off | charge rate | net disp | regime |
|--------|-----|-------------|----------|--------|
| 128–135 | ≤7 | −3.0/fr | ~0 | dead zone (no effect) |
| 145 | 17 | −3.0/fr | 44 | arrow onset |
| 160 | 32 | −2.90/fr (97%) | 387 | arrow charge |
| 180 | 52 | −2.52/fr (84%) | 845 | arrow charge (sweet spot) |
| 200 | 72 | +2.0/fr (LOSS) | 2290 | tipped into pure release |

## The usable range and tip-over

**Usable α ∈ [0°, ~20°]** (up to Xbias ≈ 180–190). Past that the two alternation targets fall
within 135° of each other, the backward snap dies (see [turnaround](turnaround.md#beyond-the-budget-gradual-turn)),
and the stick drives a **forward release** — speed LOSS with a large forward displacement. This is
the same **45° angular budget** as the turnaround snap, expressed as a stick tilt.

## Arrow spin-up cost (2 frames)

When the alternation begins, the first sticks are **< 135°** away from facing → they are **non-snap
forward frames** that each **lose ~+3/fr** before the 0↔180 swing locks in. Live-measured at **~2
frames**. A planner must charge this cost, or it will pick short arrow phases that never pay it off.

## Stick angle (why the dead zone matters)

The tilt the game reads is **not** raw `atan2(ax, −ay)` — a **per-axis dead zone of 15** (the same
constant as the [decay curve](../reference/constants.md#stick-geometry)) is removed first. That is
what makes a partial-Y arrow stick read the correct tilt: `(0,96)` → α ≈ 8° (raw atan2 would give
~14°). For an on-axis stick the closed form is exact; off-axis, the exact `mMainStickAngle` is read
from a live grid (`stick_angle_table.csv`) because Dolphin's byte→analog mapping diverges from the
closed form at the deadzone boundary and octagon. That table's `stick_dist`/`value` magnitude columns
**equal** the closed-form `/54` the gain already uses (see [model/predictors](../model/predictors.md#why-a-live-stick-angle-grid-not-a-closed-form)).

## 2-D geometry (the stepper)

`ArrowState` decodes the full 2-D mapping: `move_bearing = camAngle − facing` (a reflection;
`K = camAngle`). Stick→angle: `stickAngle = atan2(ax, −ay)` after the dead-zone-15, then
`m34E8 = stickAngle + 180 + camAngle`; snap iff `|angdiff(m34E8, facing)| > 135°`. The chain
reproduces facing to ≤ 0.6° and net drift bearing to ~1° live. `reorient_chain()` generalizes to
any start/target axis via a facing-BFS (it is not hardcoded — see
[turnaround: reorienting](turnaround.md#reorienting-the-charge-axis-turnaround-chains)).

> The state-54→55 **entry release** (the arrow↔cruise hand-off, live f1 −300→−24) is priced
> separately by the planner, not inside the stepper.

## Open question — does arrow swimming save time?

**Current verdict: probably not.** Offline the planner finds arrow **loses ~2–4 frames** at 200k
(the early `sin α` cross-drift doesn't cover the prefix overhead), and it is **not yet validated
from a cold start** — `ArrowState` is validated charged-only and does not model the state-54→55
entry release + [x598 scramble](../reference/glossary.md#x598). Treat "use arrow swimming" as
**unproven**, not recommended, until a cold-start DTM validation lands. Full provenance and the next
experiment: [history/reboost-strobo-history.md](../history/reboost-strobo-history.md).

## Constants used here

charge_disp_factor 0.9466, dead zone 15, divisor 54, tip-over ≈ Xbias 190 (α ≈ 20°), spin-up 2
frames. (α↔Xbias: Xbias 160 ≈ α 8°, Xbias 180 ≈ α 18°.) See
[reference/constants](../reference/constants.md#turnaround--arrow-angular-budget).

## See also

- [Turnaround](turnaround.md) — the snap mechanic and the 45° budget this lives inside.
- [Constants](../reference/constants.md#speed-gain-while-charging--arrow-swimming).
