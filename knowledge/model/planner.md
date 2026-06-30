# The route planner & optimizer

**Answers:** How does the planner search? What's the objective? Why are mid-swim pumps disabled?
Why the crossover (build + cruise) decomposition? What's the balloon-swim option?
**Status:** validated (live-confirmed plans, frame-exact via DTM).
**Source:** `superswim/plan.py`, `superswim/optimize.py`; the legacy C# `SwimEnvironment`/PSO.

---

## Objective: minimum frames to a destination

The TAS objective is **minimum frames to reach a fixed target distance D**, not max distance over a
fixed window. This shapes the endgame: near D you should NOT boost (no frames to recoup the
[turnaround](../mechanics/turnaround.md) tax), and the optimum wants to finish in
[neutral](../mechanics/neutral.md) (drag-free) for the last stretch — exiting at a good
[head-bob phase](../mechanics/animation.md).

## Search

- **Beam search** over the per-frame {ESS, charge} decision space (`optimize.py`), keeping
  anim-phase diversity so a state that just paid a boost (lower x, better anim) isn't pruned by raw
  x. Air is omitted from the dominance key — every action decrements air by 1, so the whole frontier
  shares the same air per generation. Anim bucket = 0.03.
- The legacy C# tool used Particle Swarm (`Omega=0.7627, Phi_G=1, Phi_P=3`) over `[chargeTime,
  essTime]` with neutral time computed analytically; PSO is overkill for this low-dimensional,
  monotonic-ish space — beam/closed-form is more reliable.
- **Closed-form helpers**: `time_to_travel_distance = (√(2·c·d + v²) − v)/c`; `ess_normal_minima`
  solves the optimal ESS↔neutral switch distance analytically; `avg_ess_rate = (4+3π)/(5π)` (mean
  speed fraction retained as displacement while ESSing).

## Why mid-swim pumps are disabled

A planner free to insert `neu,1` pumps mid-cruise produces plans that FAIL catastrophically live: a
band-1 (v=−806) 200k run planned at 266 fr bled speed to **zero by f252**, reaching only 58k/200k
(**71% short**). Cause: every pump re-enters ESS → re-scrambles the ESS-start anim
[×598](../mechanics/pumps.md#the-x598-scramble) → the sim can't predict the landed phase → it
under-prices the exit `af_drag` cut → the optimizer mines phantom-cheap pumps that drain all speed.
The reboost+ESS-cruise portion tracks live frame-exact; the divergence is **entirely the pumps**.

**Fix:** plan neutral as a ONE-WAY TERMINAL DASH (`allow_pump=False`, the default) — a single
predictable exit from sustained ESS. That replanned to 275 fr and validated plan = sim = live
frame-exact (0.0186% net error). Re-enable mid-swim pumps only after the pump ess_start anim is
validated live per entry-frame.

## Why the crossover (build + cruise) decomposition

The flat pump DP saturates: the x598 pump scramble lands a DISTINCT anim phase per pump entry, so the
frontier hits `max_frontier` on every layer and dominance cannot merge genuinely-distinct futures
(empirically confirmed — frontier pinned at 8000 even after coarsening anim AND v buckets). A flat DP
wastes its whole long-cruise horizon carrying a saturated pumped frontier for nothing (cold
dest=100000: 511s, 388/396 layers capped). **Pumps only pay in the low-speed BUILD** (measured:
cruise dest=60000 pump vs no-pump both 41 fr; greedily inserting pumps into the pump-free optimum
never improves it). So the planner decomposes into a **pumped build + a pump-free cruise suffix**
(crossover), continuing each build-frontier node pump-free toward the far destination. Build distance
scales with seed speed (a fast seed is already cruising → pumps never help → pure cruise DP).

## Balloon swim

Project at current velocity for N frames, then **0.75× speed on landing** + 27-frame resurface
(−3/frame), forced air refill to 900. Decomp confirms the 0.75 landing multiplier
(`mNormalSpeed *= 0.75f`, d_a_player_swim.inc:137) and the 900 air reset (line 126).

## See also

- [Sim precision](sim.md) · [Pumps / x598](../mechanics/pumps.md) ·
  [strategy/reboost](../strategy/reboost.md) · [strategy/phase-ordering](../strategy/phase-ordering.md)
  · [history/resolved-bugs](../history/resolved-bugs.md) (bug#2 / DTM delivery).
