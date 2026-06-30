# History — resolved bugs & their provenance

> **status: historical** — how these were found and fixed. The current truth is in the linked
> mechanics/model pages. Kept because the *reasons* (and the wrong turns) matter for future debugging.

---

## bug#2 — dense-pump live divergence = pipe artifact, NOT physics

Dense back-to-back pump plans reached only ~127k live vs the sim's ~300k. Root cause: the external
`advanceseq` pipe's FrameAdvance listener **jitters SI polls** on dense neutral↔ESS transitions
(off-thread input misses the emu-thread poll). A cleanly **authored** DTM (8 ControllerState rows per
30 fps game-frame, 254/1 calibration) played via the movie system is **bit-exact** (cruise_pump300k:
net 300,816). A DTM *recorded* from the pipe inherits the jitter — only an independently authored DTM
is unbiased. **Dense plans are valid.** → [reference/commands](../reference/commands.md#live-validation--dtm-the-faithful-delivery-path), [model/planner](../model/planner.md).

## 554 / "anim drifts ~3 fr by f400" — truncated-seed artifact

A phantom ~3-frame anim drift by f400 was a **truncated cold-start seed** (anim 8.9417 vs true
8.941699028…); the cold-start [×598 scramble](../mechanics/pumps.md#the-x598-scramble) amplified the
sub-ULP error ~600×. With the full-precision seed the sim is bit-exact per-frame. Fix: never seed a
truncated anim. → [model/sim](../model/sim.md#cold-start-seeding-the-mrate-rule).

## Off-axis charge v residual — corrupt stick-angle table

A 0.0105 too-high v on off-axis charge was traced (after a wrong "camera-field mismatch" hypothesis)
to `stick_angle_table.csv` being dumped via the **calibrated `set_gc_buttons`** path while the
game/tests/DTM use the **raw-byte `advancewith`** path — differing up to ±155 s16 on ~12k off-axis
cells. Regenerating via `advancewith` → v bit-exact. → [model/predictors](../model/predictors.md#the-off-axis-charge-residual-resolved).

## Omega camera grid — input-path corruption + coarse subsample

The camera-rate grid had the same input-path bug (`set_gc_buttons` recorded −546 where `advancewith`
gives −547; 1816/4096 cells off by +1), and the shipped grid had been a **coarse 4096-cell
subsample**. Regenerated as the full raw-byte grid (`omega_full_redump.py`); charge cases go cam=0hw
(commit ff1bbfb). Dump method: fresh `loadstate 10` per cell (the value the swim experiences is the
from-rest one). → [mechanics/camera](../mechanics/camera.md), [camera-model-history](camera-model-history.md).

## Console cosine table — 1-ULP exits

x86 `cos()` differs from the console `jmaCosTable` at 2964/4096 entries; ×598-amplified, a 1 ULP
became a 0.07 v jump at pump exits. Fixed by baking the live table from `0x80498168`. →
[model/sim](../model/sim.md#console-cosine-table).

## release_ess_speed — 2-increment phase error

The exit speed was computed off the wrong (last-ESS) anim frame; the game applies `af_drag` at the
release frame (exit-frame physics + 1-frame lag), up to ~40% off when the offset lands a mid-cos
frame. Fixed by advancing the exit-frame physics before `af_drag`. →
[mechanics/neutral](../mechanics/neutral.md#ess--neutral-exit-release_ess_speed).
