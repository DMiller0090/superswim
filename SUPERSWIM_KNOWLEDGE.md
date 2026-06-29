# Superswimming — Mechanics & TAS Optimization Reference

Knowledge base for understanding/expanding superswim TASing in The Wind Waker.
Sources cross-referenced:
- zeldaspeedruns.com/tww/techniques/superswim (community docs)
- Decomp: `tww/src/d/actor/d_a_player_swim.inc` (game truth)
- `SuperSwimPredictionTool/` (C# live-prediction model; messy repo)
- **SUPERSWIM_DATA.md** — raw live measurement tables behind every "validated"
  claim here (decay sweep, pump entry tax, neutral→ESS scramble, anim lengths,
  exit-speed offset, strobo/reboost). Read it to re-analyze without re-running.

---

## 1. What superswimming is

Setup via Storage + Camera Lock with the Wind Waker leaves Link in a swimming
state where holding the control stick builds speed. Superswim proper is
**alternating the stick fully back-and-forth every frame**. Each alternation
adds **3 units of "potential speed"** (the decomp's `mNormalSpeed`). Speed is
negative-signed in convention (the tool stores velocity, charging does `+= 3`).

The two speeds that matter:
- **Potential speed** (`velocity` / `mNormalSpeed`): the underlying speed value.
- **True speed / true displacement**: how far Link *actually* moves this frame,
  = potential speed scaled by two drag factors (animation frame + air meter).

---

## 2. Core formulas (tool ↔ decomp)

All from `SwimEnvironment.cs` / `Predictor.cs`, confirmed against the decomp.

### Animation frame
- Animation cycles **0..23** (`nfmod(..., 23.0)`), 24 positions.
- Per-frame increment:
  ```
  dx = |velocity|/36 + 3/5 + (1 - (air+1)/900)
  ```
  - `|velocity|/36` → speed term (`/(2*maxSpeed)`, maxSpeed=18).
  - `3/5` → base.
  - `(1 - (air+1)/900)` → air term. **Decomp confirm:** `getSwimTimerRate()`
    = `1 - itemTimeCount * 0.0011111111` = `1 - air/900`
    (`d_a_player_swim.inc:283`), fed into the anim frame-controller rate in
    `setSwimMoveAnime` / `procSwimMove` (lines 268, 578).
- Higher speed and lower air both speed up the animation cycle.

### Animation-frame drag (→ "release ESS speed")
```
af_drag(v, x) = (2v/5)*|cos(pi*x/23)| + (3v/5)
```
Link's head bobs with the animation; this cos term modulates true speed.
**Decomp confirm:** `total_drag_coef` in `Predictor.cs:99` mirrors the in-game
`((sin*0.6) + (sin*cos)*0.4)/((cos*0.35)+1)` true-speed expression.

### Air-meter drag
```
air_drag(v, air) = 18000*v / (24300 - 7*air)
```
Lower air → larger denominator shrinks → **less** true speed. Air is an
effective multiplicative scalar on top of animation-frame drag.

### True displacement (per frame, ESS/charge)
```
true_displacement = air_drag( af_drag(velocity, animation_frame), air )
```

> **EXACT DECOMP (2026-06-27 pt 8) — `d_a_player_main.cpp:2424-2428`.** The head-bob is
> ```
> f1 = ( speedF*(1-0x60) + 0x60 * speedF*|cM_scos(cM_rad2s(pi*moveFrame/moveEnd))| )
>      / (1 + 0x7C * getSwimTimerRate())
> ```
> with mSwim `field_0x60 = 0.4` (so `af_drag = 0.6*v + 0.4*v*|cM_scos(pi*anim/23)|`,
> moveEnd=23), and the ESS->neutral EXIT release applies JUST this numerator (no air
> denominator). **The cosine is the GAME'S `cM_scos`, NOT `math.cos`:** a 4096-entry
> table indexed by the s16 angle with the low 4 bits TRUNCATED (`index >> 4`, no interp);
> values = `f32(cos(i*2pi/4096))`. That truncation is a ~5e-4 error vs true cos that the
> high-speed exit amplifies to ~0.13 in potential speed. Implemented as `cM_scos` in
> `superswim_sim.py`; the exit release now matches live to **+0.000000**. **All swim math
> runs in f32** (the GameCube is single-precision; f64 drifts ~0.013 anim / 0.004 v over
> ~480 frames -> wrong exit phase). incr constants from HIO mSwim: maxNormalSpeed=18,
> 0x50/0x54/0x74 = 0.6/1.1/1.0; neutral-rate consts 0x40/0x70 = 0.5/2.5.
> **BIT-EXACT validation:** `verify_state.py` replays a plan live and compares the REAL
> state vars (potential_speed/anim_frame/air/link_state) frame-by-frame — these match
> exactly across a full 561-frame cold-start 200k swim (charge build, cruise, exit, dash).
> x/z/displacement stay wave-affected byproducts (not bit-checked). Pump anim-scramble
> oldFrame = (display anim at the trigger frame's START) + 1.0 (MOVE0 advances +1.0 on the
> swim-initiation frame); NO +incr (lands next frame). DEFERRED: the ESS->neutral EXIT
> neutral-display anim is a SEPARATE SWIMWAIT controller (total-frames dependent, not a fn
> of the SWIMING anim) — inert for v, but needed before re-enabling multi-PUMP swims.

**EMPIRICALLY VALIDATED to ~0.05%** (live, holding cardinal ESS, comparing
measured position delta sqrt(dx²+dz²) to the formula):

| f | vel | anim | air | measured | predicted | ratio |
|---|-----|------|-----|----------|-----------|-------|
| 1 | -233.84 | 3.54 | 790 | 214.12 | 213.98 | 1.0007 |
| 2 | -233.67 |10.75 | 789 | 143.65 | 143.52 | 1.0009 |
| 3 | -233.51 |17.97 | 788 | 203.43 | 203.43 | 1.0000 |
| 4 | -233.34 | 2.18 | 787 | 219.71 | 219.59 | 1.0005 |

Displacement oscillates 214→144→203→220… as anim cycles — that's the head-bob
`|cos(π·anim/23)|` term modulating true speed. Confirmed simultaneously:
- **anim increment ≈7.2/frame** = `|v|/36 + 3/5 + (1−(air+1)/900)` (6.50+0.60+0.12).
- **mod-23 wrap**: 17.97+7.22 = 25.17 → 2.17 ✓.
- **air −1/frame** ✓.
The ~0.05% residual is the in-game cos lookup table vs exact cos — negligible.
(Validated 2026-06-26 via dolphin_mem.py.)

### Speed gain while charging (and arrow swimming)
Decomp `setSpeedAndAngleSwim` (`d_a_player_swim.inc:41,66`):
```
delta = mStickDistance * 3.0 * cM_scos(shape_angle.y - oldAngleY)
```
- Full back/forth, on-axis → **+3** potential speed/frame (max charge rate).
- Holding at an **angle** (arrow swimming) → cos(angleΔ) < 1, so you gain
  *less* speed but Link drifts toward the destination. Link forms the "tip of
  an arrow" pointing at the target.

---

## 2b. Stick values (TAS input window) — what ESS physically is

Stick range is 0..255 per axis; **neutral = (128,128)** with a dead zone around
it. ESS = the *minimum* input just outside the dead zone that the game still
registers — smallest non-neutral `mStickDistance`, so smallest head-bob/anim
drag while still on the swimming-input path (−1/6 potential decay).

Cardinal ESS (potential decay −1/6 ≈ −0.1667), 18 units off one axis:
- ESS Down (128,110), Up (128,146), Left (110,128), Right (146,128)

Diagonal ESS (slightly more efficient → tool's `diagEss` = −0.1571), 17 units
off each axis (magnitude ~24, but smaller per-frame potential-speed loss):
- DL (111,111), DR (145,111), UR (145,145), UL (111,145)

So the tool's −1/6 vs −0.1571 constants are **grounded in stick geometry**, not
arbitrary fits. Neutral (128,128) is inside the dead zone → no swim input →
drag-free −2 regime. (Source: user, TAS practitioner.)

## 3. Speed-loss regimes (per frame)

From `SwimEnvironment.perform_step` + community docs:

| State            | Potential-speed change | Notes |
|------------------|------------------------|-------|
| Charging         | +3 (×cos if angled)    | fastest growth |
| ESS (perfect)    | −1/6 (~0.11 w/ doc's perfect pos) | stick at min non-neutral value |
| ESS (diagonal)   | −0.1571 (`diagEss`)    | ~5% less efficient option in tool |
| Neutral          | first frame fractional, then −2 | true speed == potential speed (no anim/air drag) |
| Targeting toward travel dir | speed → 0 | instant kill, avoid |

### Decay is CONTINUOUS in stick distance (key insight)
Potential-speed decay for any *registered* (non-dead-zone) input is a continuous
function of distance from neutral, NOT three discrete states:
- 18 units off (ESS minimum, e.g. 128,110): lose **1/6** /frame
- 128,60 (~68 units): lose **2.94446** /frame
- ~128,61 and beyond: saturates to a flat **−3** /frame
So the tool's "+3 charge" and "−1/6 ESS" are just two sampled points on ONE
curve — charge = full alternating deflection, ESS = the minimum. (Source: user.)

**Neutral's −2 is a SEPARATE code path** (dead zone → no swim input → flat,
drag-free −2), not a point on this curve. That's why neutral loses *less* than
full deflection (−2 < −3) yet *more* than ESS — different rules.

Implication: **arrow swimming lives on this continuum.** Partial deflection
toward the destination = intermediate decay + simultaneous movement = the
unmodeled "arrow charge" phase. Modeling the stick→decay curve directly (instead
of 3 discrete states) would let the optimizer represent arrow swimming and find
intermediate optima.

### Exact decay curve (derived from decomp)
Traced the full chain raw stick → speed delta:
- `PADClamp` (GC SDK): subtracts origin (128) and removes radial **dead zone
  15**, octagonal clamp → signed `stickX/stickY`.
- `JUTGamePad::CStick::update` (JUTGamePad.cpp:303-310): `mPosX=x/54`,
  `mPosY=y/54`, `mValue=sqrt(PosX²+PosY²)`, capped at 1. (main-stick divisor=54)
- `setStickData` (d_a_player_main.cpp:10569): `mStickDistance = mMainStickValue`.
- `setSpeedAndAngleSwim` (d_a_player_swim.inc:41,66):
  `delta = mStickDistance * 3.0 * cos(angleΔ)`.

**Cardinal axis (x or y = 0):**
```
mStickDistance = clamp((|raw - 128| - 15) / 54, 0, 1)
speed delta magnitude = mStickDistance * 3
```
Verified exactly against measured values:
- 128,110 (off 18): (18-15)/54·3 = 1/6 ✓
- 128,60  (off 68): (68-15)/54·3 = 2.94444 ✓ (measured 2.94446)
- 128,59  (off 69): caps at 1.0 → flat 3.0 (saturation starts here)
So decay is **piecewise-linear in stick distance, saturating at 3**. (Note:
saturation begins at 128,59 — the "128,61+" community note was off by ~1 unit.)

**Diagonal:** same magnitude pipeline; octagonal dead-zone geometry removes
slightly more, giving effective magnitude 0.0524 vs cardinal 0.0556 → diagonal
ESS decay 0.1571 = 0.0524·3 < 1/6. That's *why* diagonal ESS is more efficient.

Constants nailed: **deadzone = 15, main-stick divisor = 54**, delta = dist·3.

### EMPIRICAL VALIDATION (live Dolphin, slot-10 origin slate)
Measured per-frame potential-speed decay by holding steady stick values from a
charged state (state 55), reading `potential_speed` each frame:

| stickY | off | measured |decay| | linear (off-15)/54·3 |
|--------|-----|----------------|----------------------|
| 110    | 18  | 0.16667        | 0.16667 ✓ exact      |
| 90     | 38  | 1.27777        | 1.27778 ✓            |
| 75     | 53  | 2.11111        | 2.11111 ✓            |
| 70     | 58  | 2.38889        | 2.38889 ✓            |
| 65     | 63  | 2.66667        | 2.66667 ✓            |
| 63     | 65  | 2.72223        | 2.77778 (−1 unit)    |
| 60     | 68  | 2.88889        | 2.94444 (−1 unit)    |
| 58     | 70  | 3.00000        | 3.00000 ✓ (sat)      |
| 128    | 0   | 2.00000        | neutral path = 2 ✓   |

**Result:** linear law is EXACT across the whole ESS + arrow-swim regime
(off ≤ 63, decay ≤ 2.667 ≈ 89% of max). A ~1-stick-unit shortfall appears only
in the narrow off 65–68 band (PADClampCircle integer/radial top-end compression),
then saturates to exactly 3.0 by off ≥ 70. Neutral (128,128) confirmed exactly
−2. ESS steady-state confirmed exactly −1/6 (note: the FIRST frame after
switching from charge to a steady hold shows a −3.0 transient as Link's facing
flips; decay settles to 1/6 from frame 2 on).

So for any practical superswim modeling, decay = clamp((|raw−128|−15)/54,0,1)·3
is exact. (Method/constants validated 2026-06-26 via dolphin_mem.py pipe.)

Key tradeoff: **ESS** preserves potential speed (decay only ~1/6 vs 2), but
because the stick is non-neutral, **animation-frame + air-meter drag penalties
apply** to true speed. **Neutral** loses potential speed fast (−2) but true
speed equals potential speed (no drag). The optimizer finds where to switch.

---

## 4. Stroboscopic effect

At speeds around **−850 and −1650**, the per-frame animation increment makes
the animation frame land at ~the same phase each frame (aliasing/strobing), so
the cos drag term stabilizes. If it stabilizes at a *good* spot, ESS true speed
closely tracks potential speed. This is why those speed bands are valuable
targets. **Not explicitly modeled** as a special case — it emerges from the
increment formula, but the tool doesn't actively seek these bands.

**Strategy in a strobo window (user guidance):** at the strobo bands do a **full
sustained ESS** (not pumping) — the anim frame self-stabilizes at a good phase,
so sustained ESS maximizes the minimal-drag benefit. Pumping is the opposite,
low-speed regime (see §6 ESS pump). Do not confuse the two.

**Reboost tech (undocumented until now, user-confirmed to save frames):** ESS
decays potential speed by 1/6 each frame, so you slowly drift *out* of the strobo
band toward 0. A quick **up/down charge alternation ("reboost")** bumps potential
speed back UP into the band, then you resume ESS. Repeating this (ESS → drift out
→ short reboost → ESS) keeps you in the favorable strobo window longer. NOT
modeled by the predictor.

**EMPIRICAL (live, slot built at flat water, charged ~-783, air 597):**
- Strobo CONFIRMED: anim crawled **~-0.25/frame** (vs +8.8/frame at low speed)
  because increment 22.70 sits just under 23 → tiny per-frame phase shift. So
  |cos| (true-speed efficiency) stays roughly stable for many frames instead of
  cycling every frame.
- Band location: increment = `|v|/36 + 0.6 + (1-(air+1)/900)` ≈ 23·k. At air 597:
  k=1 → |v|≈794, k=2 → |v|≈1630. **Air-dependent** — as air depletes the band
  speed shifts, so the band moves under you during a long ESS.
- Drift direction: increment <23 → anim decreases; >23 → increases. At -783
  (incr 22.7) anim drifted from |cos|=0.72 toward mid-cycle (|cos|→0.18 over 18
  frames), i.e. true speed degrading as you fall just below the band.
- **Reboost is COUNTERPRODUCTIVE while in-band:** pure ESS 30fr = 15677 disp;
  (8 ESS + 2 up/dn)×3 = 30fr = 13673 disp (worse) despite ending faster (-797 vs
  -781). Charge frames move Link almost nil, so they waste frames when ESS is
  already efficient. (Confirmed below: a *blind fixed-cadence* boost like this one
  loses; the win comes from PHASE-TRIGGERING the boost to re-aim the anim drift —
  see "reboost SAVES time" below.)
**RESOLVED — reboost SAVES time, but ONLY when phase-triggered, not on a fixed
cadence.** (Supersedes an earlier draft that called reboost net-negative — that
was an artifact of testing blind fixed cadences only. User flagged it: the real
tech is timing the boost, and it is NOT a constant period.) Quantified live with
a one-process batch helper (`dolphin_mem.py seq`) and a closed-loop phase-triggered
controller (`dolphin_mem.py essloop`, reads anim each frame, fires a boost only
when anim enters a target window — see helpers below). All numbers measure **net**
Euclidean displacement (TAS-relevant progress), not raw path length.

### The mechanism (why timing is everything)
ESS true speed = `(0.6 + 0.4·|cos(π·anim/23)|)·|potential|`, so efficiency runs
1.0 at anim 0/23 down to 0.6 at anim 11.5. In a strobo band the anim increment is
near 23·k, so anim barely advances — it **slowly drifts** in one direction set by
`sign(increment − 23k)`. If it drifts toward 11.5 (the trough), ESS efficiency
**decays frame after frame** (our band-2 slate: anim 17.8→9.5, step 1476→925).
A boost adds potential → raises the increment above 23k → **flips the drift
direction**, sending anim climbing back up toward the |cos|=1 peak, and true speed
**rises monotonically** afterward. THAT is the win — not the +speed itself, but
re-aiming the strobo drift at the efficiency peak. A fixed cadence can't do this:
it fires at arbitrary anim phases, sometimes kicking the drift the wrong way, and
eats the turnaround tax for nothing.

### Measured (band 2, −1630, air 900; closed-loop `essloop`)
| config | window | net/fr | vs baseline | boosts |
|--------|--------|--------|-------------|--------|
| pure ESS (baseline) | 150 fr | 1295 | — | 0 |
| boost 4 @ anim∈[13,16] | 150 fr | **1438** | **+11%** | 1 |
| boost 6 @ anim∈[10,13] | 150 fr | 1359 | +5% | 1 |
| pure ESS (baseline) | 220 fr | 1295 | — | 0 |
| boost 4 @ anim∈[13,16] | 220 fr | **1360** | **+5%** | 3 |
| boost 4 @ [13,16], **no cooldown** | 220 fr | 902 | **−30%** | 16 |
| anim parked at peak, baseline | 120 fr | 1376 | — | 0 |
| **up-down maintenance @[20,23] from peak** | 120 fr | **1493** | **+8.5%** | 3 |
| boost 4 @[20,23] from peak (overshoots) | 120 fr | 1123 | −18% | 1 |

Frame-by-frame of the winner: anim drifts 17.8→15.8 (step decaying), a 4-frame
boost at anim≈15.8 lifts potential −1628→−1640, anim reverses and climbs
15.6→21.5 over the next ~40 frames while step rises 1316→1578 (toward the peak).

### Boost SIZE is coupled to anim phase — minimal up-down is the optimal steady state
Boost just enough to **land anim at the peak (0/23)**. How big that is depends on
how far anim is from the peak when you fire:

| anim when fired | right boost | what happens | measured (band 2) |
|-----------------|-------------|--------------|-------------------|
| near peak (~20–23/0–2) | **2 (one up-down)** — MAINTENANCE | re-parks anim at peak | **+8.5%** (1493 vs 1376) |
| deep mid-cycle (~13–16) | ~4 — RECOVERY | drives anim back UP to peak | +11% (1438 vs 1295) |
| near peak | 4+ | OVERSHOOTS past peak down far side | −18% (1123) |
| deep mid-cycle | 2 | only nudges increment to ~46.05 → **parks at the mediocre phase**, no climb | ≈ baseline |

Why a single up-down isn't always enough: +6 potential moves the increment only
+0.17 (6/36), barely past 23k, so anim drifts up at ~+0.05/fr — it **freezes
wherever it currently is**. From mid-cycle that's a mediocre |cos| (parked at anim
15.9, step stuck ~1329 ≈ baseline). From near the peak that same freeze lands you
ON the peak (|cos|≈1) — which is exactly what you want. A +12 (4-frame) kick moves
increment +0.33 → anim climbs ~+0.21/fr, enough to *travel* from mid-cycle up to
the peak before the 1/6 decay stalls the climb; but fired AT the peak it overshoots.

**The genuinely optimal line: keep anim pinned at the peak with minimal up-down
maintenance boosts, and never let it drift far enough to need a big recovery kick.**
Peak-maintenance up-down (1493) beats every recovery scenario. The big 4-frame
recovery boost is only the rescue move for when you've already let anim slide deep.

### Practical rules
1. **Boost is phase-triggered, sparse, and sized to the phase.** Steady state =
   minimal up-down (2 frames) fired when anim drifts off the top of the peak, to
   re-park it at 0/23. Use a bigger (~4) kick ONLY to recover anim that has already
   slid deep toward the 11.5 trough. Trigger phase and boost length are the knobs.
2. **Never boost on a timer, and never boost every eligible frame.** `cooldown=0`
   (16 boosts) ran speed away to −1788 and crashed net/fr to 902 (−30%). Over-
   boosting is far worse than not boosting. The right count is a handful per swim.
3. **The gain is front-loaded.** A boost launches an anim-climb that eventually
   overshoots the peak and starts descending the far side, so a single boost helps
   more per-frame on a short window (+11% / 150 fr) than amortized over a long one
   (+5% / 220 fr). Re-time the next boost for when anim is again descending toward
   the trough.
4. **Cost per boost ≈ a few frames of forward progress** (the path−net gap): full-
   deflection charging snaps Link 180° via the instant-turnaround (one ~dead frame
   + a brief reversed frame, facing flips +0x8000). Timing the kick onto lower-|cos|
   anim phases (slower frames) minimizes this. The +efficiency from re-aiming the
   drift must, and here does, outrun this tax — but only with sparse, aimed boosts.

**Earlier wrong conclusion, for the record:** blind fixed cadence (20 ESS + 2
charge, repeated) measured −2% (band 2) / −8% (band 1) and the naive reading was
"never reboost." That cadence loses because its boosts land at random anim phases
and pay the turnaround tax without aiming the drift at the peak. Reboost done
*right* (phase-triggered) is a real, measured time-save. (Validated 2026-06-26 via
`dolphin_mem.py seq` + `essloop`.)

Still open: optimal trigger/length as a function of (speed, air) — the band drifts
as air depletes, so the ideal trigger phase shifts during a long swim; and whether
a second boost can re-park anim to a true standing lock at 0/23 rather than a
climb-and-overshoot. Worth a finer essloop sweep with a (trig,len) search per
air-decade.

### Batch helper: `dolphin_mem.py seq` (added 2026-06-26)
The per-frame pipe spends ~all its cost on python startup + `attach()` (MEM1
region scan) per call. `seq` does the whole run in ONE process: attach once, then
advance frame-by-frame over a scripted stick sequence, reading memory natively
each frame and accumulating XZ path/net displacement.
```
python dolphin_mem.py seq "<sx,sy,n;sx,sy,n;...>" [loops=K] [read=a,b,c] [every=N]
```
- Segments are `stickX,stickY,frameCount`, `;`-separated; `loops=K` repeats the
  whole sequence. `substickY=0` (free-cam) is forced every frame so the auto-cam
  never flips. `every=N` prints every Nth frame (0/omitted = summary only).
- Summary line: `frames path net path/fr net/fr` + final read values. **net** =
  start→end Euclidean (TAS progress); **path** = summed per-frame |Δ| (diverges
  from net when heading wiggles, e.g. reboost reversals).
- Examples: pure ESS `seq "128,110,150"`; reboost `seq "128,110,20;128,255,1;128,0,1" loops=7`.

### Closed-loop helper: `dolphin_mem.py essloop` (added 2026-06-26)
`seq` is open-loop (blind script); it can't express phase-triggered reboost.
`essloop` holds ESS, reads `anim_frame` every frame, and fires a boost (full
up/down charge burst) ONLY when anim enters a target window — the actual reboost
tech.
```
python dolphin_mem.py essloop frames=N trig=LO,HI [boost=B] [cooldown=1] [every=0]
```
- `trig=LO,HI`: anim window (0..23) that triggers a boost; wraps if LO>HI
  (`trig=21,2` = near the 0/23 |cos|=1 peak). `boost=B`: charge frames per fire
  (0 = pure-ESS baseline). `cooldown=1`: anim must LEAVE the window before it can
  re-fire (set 0 to over-boost — DON'T, it runs speed away). `every=N` prints
  every Nth frame with an ESS/BOOST tag.
- Best band-2 result: `essloop frames=150 trig=13,16 boost=4` → +11% net/fr vs
  `boost=0`. Sweep `trig` and `boost` to tune; see reboost findings in §4.

### SOLVED — optimal reboost schedule via beam search (`superswim_optimize.py`)
With the frame-exact sim, the optimal ESS/charge schedule is now *searched*, not
guessed. `superswim_optimize.py` beam-searches the full per-frame {ESS, charge}
decision space maximizing net forward displacement (−x), keeping anim-phase
diversity so post-boost states aren't pruned. Band-2, 200-frame window (−1630, air
900): **converged** (beam 2000=4000=8000, identical) to:
```
optimal = 3 minimal up-downs (length-2 boosts) at frames 2, 44, 110
seq: ess,1; chg,2; ess,40; chg,2; ess,64; chg,2; ess,89
```
- **+15% net/fr** over pure sustained ESS. The search independently rediscovered
  that the **minimal up-down (length 2) is the optimal boost** — it never chose a
  longer kick — confirming the maintenance-regime finding.
- **Boosts fire as anim approaches the peak**: anim_before = 18.0 → 20.3 → 0.2
  across the three, and the **target phase + spacing shift as air depletes** (the
  band slides under you). So the optimal is air-aware peak-maintenance, automatic.
- **Verified live (Dolphin):** optimal net/fr **1485** vs baseline **1283** =
  **+15.7%** measured; sim predicted +15.1%. The predicted *gain* matches to ~0.6pp
  (the ~1% absolute sim↔Dolphin offset is the f18–19 camera-glitch frames and
  cancels in the ratio). Both stayed in valid water (net 297k < the ~320k wall).
- Run: `python superswim_optimize.py frames=N v=-1630 air=900 anim=18.148 [beam=K]
  [viz=opt.html]` → prints schedule + a seq string; convert chg→alternating
  255/0 for `dolphin_mem.py seq` to confirm live. Workflow: search in sim (ms),
  verify the one winner in Dolphin. (2026-06-26)

**ROBUSTNESS (sensitivity sweep, 2026-06-26):** the optimal boost *frame numbers*
are NOT transferable — they shift with the seed:
- Fine tweaks (anim ±0.3, speed ±a few) → small, smooth shifts (e.g. middle boost
  42→45), gain steady ~15%. Locally robust.
- Larger changes → big shifts: anim phase 2/16/21 → boosts 24·64·107 / 2·26·115 /
  2·63·107; speed −1620/−1630/−1640 → 10/6/4 charge frames; air 900→600 → 6→2
  boosts, gain +15%→+5%.
- STABLE across all: minimal up-downs (length 2) near the peak, ~3 per 200fr, with
  ONE bigger recovery kick (len 4–6) when starting far from the peak (trough phase /
  below-band speed). Gain always positive (+3.7% above-band … +15.6% band-centre).
- Implication: re-solve per exact (speed, anim, air); a fixed frame list won't carry
  over. (Caveat: beam pruning is myopic — trust only at beam ≥2000; harden with a
  future-value heuristic before longer windows / full-swim search.)

**SCOPE / NEXT (the real objective is not max-distance) — user note 2026-06-26:**
1. **Optimize frames-to-DESTINATION, not distance-over-window.** The TAS objective
   is *minimum frames to reach a fixed target distance D*, not max net over a fixed
   N. Change the optimizer to a min-frames search (run each beam path until forward
   ≥ D, minimize frame count / DP on frames-to-reach-D). This changes the endgame:
   near D you should NOT boost (no frames to recoup the turnaround tax), and the
   optimum naturally wants to finish in **neutral** (true speed == potential, no
   anim/air drag) for the last stretch.
2. **Include strategic ESS PUMPS + the neutral phase.** The optimizer currently only
   covers state-55 ESS+charge. A real full-swim route is charge → arrow → ESS/reboost
   → neutral boost → ESS pumps (§5). To search it, the sim must first model+validate:
   neutral (state 54) decay −2 / drag-free move / mod-26 anim; the neutral↔ESS
   transitions (1-frame pump entry tax §5.6, the ×598 anim scramble, release_ess_speed
   exit with the +2-increment phase); and arrow-swim heading (cos-penalised charge,
   45° snap). Those are documented but NOT yet in superswim_sim.py — validate each
   live (as we did for charge) before extending the optimizer to the whole swim.

### Offline sim + visualizer: `superswim_sim.py` (added 2026-06-26)
Pure-python reproduction of the swim physics (no Dolphin) for screening theories in
ms before confirming the winner live. Mirrors the `seq`/`essloop` command shapes so
results are directly A/B-comparable.
```
python superswim_sim.py seq "ess,20;chg,1;chg,1" v=-1630 air=900 anim=17.9 [every=N]
python superswim_sim.py essloop frames=150 trig=13,16 boost=4 v=-1630 air=900 anim=17.9
python superswim_sim.py compare frames=150 trig=13,16 boost=4 viz=out.html   # animated viewer
```
- Actions: `ess` (stick 110, −1/6), `ess:<rawY>`, `chg` (+3), `neu` (−2). Tracks 2D
  position + heading so movement can be drawn. `viz=out.html` emits a self-contained
  animated top-down viewer (play/scrub, efficiency-colored trail, boost markers,
  speed/anim/air gauges); `compare` overlays baseline vs reboost.
- **Charge/turnaround model (Phase B, live-calibrated to full f32 precision):**
  four separate 1-frame lags, each measured against unrounded RAM:
  1. **Anim-rate lag** — the swim-move anim controller advances using the PREVIOUS
     frame's speed, not the current one. (For ESS this is a 0.0046/fr nothing; for
     charge it's the whole ballgame.) So advance anim BEFORE applying the speed change.
  2. **Charge +3 lag** — a `chg` frame's +3 lands on the NEXT frame, *replacing that
     frame's decay*, even if the next frame is ESS. So an N-frame burst deposits its
     last +3 on the first post-burst ESS frame.
  3. **First-charge decay** — the first `chg` frame of a burst still applies the
     normal ESS decay (+1/6); the +3 only engages from the 2nd frame.
  4. **Facing flip** — each `chg` toggles a 180° (+0x8000) facing flip applied the
     next frame; even-length bursts return to the original heading (reversed frames
     land at burst positions 2,4,… → the net-vs-path reboost penalty).
  Charge frames also move **0.9466×** the ESS displacement at the same (v,anim,air)
  (`CHARGE_DISP_FACTOR`, band-2 only — revalidate far from −1630). The one-time
  **−3 facing-flip entry transient** (writename-speed-then-hold, frame 1) is modeled
  via `entry_tax` (default on in the runners).
- **Neutral (state 54) + pump model — live-validated 2026-06-26 (clean camera-aligned
  slate).** Now in the sim (1-frame state-transition lag both ways):
  - **Neutral decay = −2.000/fr exactly; displacement = |v| exactly** (drag-free,
    step/|v| = 1.0000); **anim wraps at 26** at rate
    `0.5 + 2.5·(1−(air+1)/900)`/fr (≡ 0.49722 + 2.5·(1−air/900); same (air+1)
    convention as ESS_increment). **Speed-independent** (live: −280 and −1630 give
    identical deltas) and rises as air depletes. Re-measured 2026-06-27 on the
    CURRENT slot-10 slate — matches to 5 decimals across air 891..899. (The old
    `0.49` intercept carried a −0.0072/fr bias = 4.3 anim-units of oldFrame error/fr
    after ×598. The old-slate "0.83→0.92 swim-wait rate" was a DIFFERENT
    position/depth/swim-timer regime and does NOT apply to the rebuilt slate.)
  - **ESS→neutral exit:** on the 54 transition frame (1-frame lag), v is set to
    `release_ess_speed = af_drag(v, anim + 1·ESS_increment)` and the −2 decay
    resumes the next frame. Validated to ~0.27 (0.02%).
  - **PLANNING PRINCIPLE — exit-phase penalty (the endgame tradeoff).** Because the
    ESS→neutral exit applies `af_drag` at the release anim, the speed you carry into
    a neutral dash depends on WHEN you exit: exit near anim 0/23 (|cos|≈1) keeps
    ~100%; exit near anim 11.5 (|cos|≈0) keeps only 60% (−40%). Neutral itself moves
    full |v| (drag-free) but decays −2/fr, so a neutral dash to a destination is
    fastest only if you exit at a GOOD phase. The min-frames optimizer discovers this
    automatically: at a good exit phase it dashes immediately; at a bad one it HOLDS
    ESS a few frames to advance anim to a better exit phase, then dashes — balancing
    frames-spent-waiting against speed-kept. (Live-confirmed 2026-06-27: anim-20 start
    → dash now = 13 fr; anim-11.5 start → hold-then-dash = 18 fr, vs 20 fr if you
    exited immediately at the bad phase.) Any full-swim planner must price this in.
  - **Neutral→ESS pump:** the first ESS-input frame stays state 54 (pure neutral —
    the 1-frame entry tax), then state 55 with ESS −1/6. Pot/state/decay reproduce
    **exactly**. The post-pump **anim start is scrambled** (×598 frame-controller
    math) — still APPROX in the sim (sim 21.3 vs measured ~3.0); the landed phase is
    hypersensitive and needs a calibration sweep before trusting it.
  - **CAMERA MATTERS:** the control stick is camera-relative, so cSAngle must equal
    the travel direction or ESS results skew. Aligning it (new slot 10) removed the
    old wall-clip glitch frames AND gave clean drag-free neutral (ratio exactly 1.0).
- **Validation status — now frame-exact.** Against a full-precision RAM capture the
  per-frame anim matches to **0.00002** and v to **0.0003**. On a 150-frame pure-ESS
  run vs Dolphin, cumulative path error is **−0.02%** and mean per-frame step error
  **0.15%** *after excluding 2 Dolphin-side auto-camera glitch frames* (f18–19, where
  the camera corrupts the position read → step ~160 vs ~1380; a measurement artifact,
  not physics). Closed-loop `essloop` now fires the **same boost count** as Dolphin
  and lands at **+0.86%** net/fr (the rest is Dolphin's own ±2% run-to-run variance +
  the camera-glitch frames + net-vs-path Euclidean accounting). The earlier "1–3%"
  gap was: the charge anim-rate lag, the +3-onto-next-frame lag, the entry transient,
  and those camera frames — all now resolved.

---

## 4b. Forward drift while charging (head-bob-phased charging)

You can net **progress toward the destination during the speed-build**, not just build
speed in place. This is a real (small) effect the optimizer discovered — documented here so
it isn't mistaken for "just up/down charging."

**Why plain continuous charging nets ~zero.** A turnaround charge flips facing 180° every
frame and moves Link **backward along facing**, so consecutive frames move in opposite world
directions (toward / away from target). Continuous up/down charging samples the head-bob
`|cos(pi*anim/23)|` roughly evenly on the toward and away frames, so they nearly cancel:
**272 continuous charges from a cold start net only ~390 units of progress** (≈ the
cancellation residual).

**Why the phased structure nets a lot more.** Break the charge into bursts separated by
single **ESS frames** (`128,110`) and tune the burst lengths, and two things stack up
(measured on the 200k cold-start plan: **~4948 progress by the same frame, same speed**):

1. **Head-bob phase alignment.** The ESS inserts + burst lengths shift the anim phase
   relative to the charge parity so the **toward-target** charge frames land on the head-bob
   **peak** (big displacement, e.g. ~376) while the **away** frames land on the **trough**
   (small, ~235). Each up/down pair then nets ~+140 forward instead of cancelling. (Source:
   per-frame capture, f140-150 of `coldstart200k.txt`.)
2. **Uncanceled ESS forward steps.** An ESS frame does NOT flip facing, so it's a
   full-displacement step toward the target with no backward counterpart (saw +379, +477).
   Placed when facing is toward the target, each is pure progress.

Both are driven by *where the ESS frames and burst boundaries fall* — i.e. **timing the
charge to the head-bob animation**, plus the interleaved forward ESS steps. The drift is
small at low speed (and can even wobble the wrong way — the `|cos|` swings dominate the small
speed gap), then becomes a consistent, accelerating creep as speed builds (the −3/frame speed
growth makes the later frame of each pair systematically bigger).

**Caveats.** This lives entirely in **position/displacement** — the wave-affected byproduct
(NOT bit-validated per frame; only v/anim/air/state are exact). It is well-modeled in
aggregate: the full-swim displacement matched live to **0.05%** over 200k. It was
**optimizer-discovered** (the min-frames DP, not a hand-tech), and it buys part of the ~20
frames that the reboost/strobo structure saves over no-reboost swims at 200k. To trust it as
a standalone TAS tech, bit-validate `link_x/z` per frame during the charge (confirm the drift
is the head-bob mechanism, not wave noise). See §4 (stroboscopic) and §2 head-bob drag.

---

## 5. Optimal swim phase ordering (** = NOT in predictor)

1. **Charge** at +3/frame (fastest growth).
2. **Air refill** if possible — every frame air −1 (max 900). Lower air → head
   deeper → slower ESS true speed (stacks on anim-frame penalty). Tool models
   refill as `env.air = 900`.
3. **\*\*Arrow charge** — start arrow-swimming toward destination while still
   charging at the reduced (cos-penalized) rate; trades charge speed for early
   progress. NOT modeled.
   **EMPIRICALLY CONFIRMED (flat-water slate, alternating (Xbias,255)/(Xbias,0),
   12 frames):**

   | X-bias | off | charge rate | net disp | regime |
   |--------|-----|-------------|----------|--------|
   | 128-135| ≤7  | -3.0/fr     | ~0       | dead zone (no effect) |
   | 145    | 17  | -3.0/fr     | 44       | arrow onset |
   | 160    | 32  | -2.90/fr 97%| 387      | arrow charge |
   | 180    | 52  | -2.52/fr 84%| 845      | arrow charge (sweet spot) |
   | 200    | 72  | +2.0/fr LOSS| 2290     | tipped into pure release |

   Charge efficiency tracks `cos(angle of stick vector off the vertical charge
   axis)`: at X-bias 180 each alternating vector sits ~34° off vertical →
   cos(34°)≈0.83 ≈ measured 84% charge retention. So arrow swimming = the
   `cos(angleΔ)` term in `setSpeedAndAngleSwim` (`delta = stickDist·3·cos`):
   tilting the alternation axis trades charge rate for sideways displacement.
   Dead zone reconfirmed (X≤135 → no effect). Tip-over to net speed LOSS ≈X=200.
   (Validated 2026-06-26; flat-water spot 24763,1,-197306.)

   **CLOSED-FORM ARROW MODEL (live-validated 2026-06-27, current slot-10 slate, in
   `superswim_sim.py`).** Re-captured per-frame on the rebuilt slate reading facing
   (0x803EA3D2), potential_speed, and x/z (`capture_arrow.py`). The decomp
   `delta = stickDist·3·cos(facing_after−facing_before)` is FRAME-EXACT. Parameterize
   by **tilt α** = move-direction offset from the pure-back axis toward the target:
   each alternation rotates facing by **(180°−2α)**, so
   ```
   charge_rate(α)  = −3·dist·cos(2α)            # α=0 → −3 (pure back)
   cross_drift(α)  = disp·sin(α)  per frame     # toward target, ACCUMULATES
   along_move(α)   = disp·cos(α),  sign alternates (net ~cancels, like pure charge)
   disp = CHARGE_DISP_FACTOR · true_disp(v,anim,air)
   ```
   Live match: α = 0/8/18° (Xbias 128/160/180) → rate −3.00/−2.88/−2.44 vs model
   −3.00/−2.88/−2.43; dz/|move| = sin α to <0.004 (`validate_arrow.py`). Usable
   **α ∈ [0°, ~20°]**; past Xbias≈190 the backward-snap dies (the two alternation
   targets fall within 135° of each other) → **tip-over**: facing stops snapping,
   the stick drives a FORWARD release (+speed LOSS, huge fwd displacement). So arrow
   swimming trades charge rate (cos 2α) for steady cross-track drift (sin α). The u16
   facing→world-move mapping is a reflection (move_bearing = K − facing); K is
   camera-frame-dependent but irrelevant to the planner (rotation-invariant — only
   relative Δfacing/drift matter). NEXT: wire α-gears into the planner as `frontend`
   actions (charge → arrow → cruise hand-off).

   **2-D STEPPER BUILT + LIVE-VALIDATED (2026-06-27, `superswim_sim.py` `ArrowState`).**
   Decoded the full 2-D geometry from a slot-9 capture (reorient east→N–S, arrow-swim
   west, 20 frames). The reflection constant is solved: **K = camAngle** exactly →
   `move_bearing = camAngle − facing` (cam 270 west, face east → bearing 180 west = the
   slate). Stick→angle: `stickAngle = atan2(ax, −ay)` (0=down,90=right,180=up,270=left)
   AFTER a **per-axis dead-zone of 15** (same constant as the decay curve) — the
   dead-zone is what makes a partial-Y arrow stick read the correct tilt: (0,96)→α≈8°
   (raw atan2 gave ~14° → −2.65/fr; dead-zoned → −2.86 vs live −2.88). `m34E8 =
   stickAngle + 180 + camAngle`; snap iff `|angdiff(m34E8,facing)|>135`, speed delta =
   `stickDist·3·cos(Δfacing)`, both lagging 1 frame. The 2-frame arrow SPIN-UP is
   non-snap frames (Δ≈7°, cos≈+1 → **+3 LOSS** each) before the 0↔180 swing locks in.
   Validation (`validate_arrow.py check_slot9`): facing chain reproduced to ≤0.6°, net
   drift bearing sim 224° vs live 223°. `reorient_chain()` is a facing-BFS (15° gates,
   synthesized snap sticks) that generalizes to any start/target axis — not hardcoded.
   The state-54→55 ENTRY RELEASE (live f1 −300→−24) is NOT in the stepper; it's the
   arrow↔cruise hand-off, priced separately by the planner.

   **CRUISE-TAIL POLISH (2026-06-27 pt 7) — full route 98.9% → 99.4% live.** Three
   results, all live:
   - **Displacement used a 1-frame-stale anim (FIXED).** `SwimState` (cruise) advances
     anim THEN computes `true_disp(anim)`; `ArrowState` did it in the wrong order
     (displacement off the pre-advance anim). Pinned on the first prefix frame: live
     disp **70**, stale-anim model 88, advanced-anim model **67**. Fix = advance anim
     before `mag` in `ArrowState.step`. Gain: +0.6% distance and **5× smaller cross-axis
     z error** (−137 → −25 over the prefix). Facing is untouched (validate_arrow still OK).
   - **Charge gain is EXACT, dist clamp is RIGHT (`fixed_alpha.py`).** Holding a constant
     on-axis arrow and measuring steady Δv: implied stick distance = **1.0000 at
     α=0/10/20**, gain = `3·cos(180−2α)` to the decimal. Tilt changes the COS (snap angle),
     NOT mStickDistance — so capping `stick_dist` at 1 is correct (unclamping a diagonal
     >1 over-charges). The `incr(v,air)` anim rate is also exact (live Δanim 4.332@f10,
     7.521@f50 to the decimal).
   - **Cruise + neutral-dash model is already EXACT (`debug_cruise.py`).** Seeding a
     SwimState from the LIVE hand-off and replaying the planned cruise → **99.9%** (v
     tracks live to the decimal through the whole neutral dash). The full-route residual
     is ENTIRELY the prefix anim drift corrupting the cruise seed, not the cruise model.
   - **Residual root = ~0.6–1° stick-angle quantization in the ramp** (sim snap delta ~1°
     small → tiny under-charge × ~60 frames → 0.71 anim seed error). This is the stated
     noise floor (stick model game-exact, mean 0.012° vs the 11k-row INPUT_DUMP); not
     pursued further to avoid overfitting.

   **REORIENTING THE CHARGE AXIS via turnaround chains (live-validated 2026-06-27,
   slot 9, camera fixed west).** Arrow DRIFT is ⊥ the charge axis, so to arrow-swim a
   given world direction the charge axis must be perpendicular to it → Link rotates his
   facing onto that axis. This is done with **instant-turnaround snaps, NOT a gradual
   turn** (and every snap CHARGES, −2.3…−2.9/fr, so reorienting gains speed). A single
   snap only fires for targets >135° (0x6000) off current facing, so a ~90° reorient
   can't be one snap — you **walk facing through intermediate diagonal snaps**. Verified
   example (face east 90° → N–S axis): inputs `(35,255)→(255,80)→(0,128)→(0,128)` snap
   facing 90°→305°→164°→**0°** (each Δ≈145–165°, all charging). Once on the N–S axis,
   alternating **Left(0,128)/Right(255,128)** charges cleanly (facing snaps 0°↔180°,
   −3.00/fr, pure N/S motion); adding a **Y-bias DOWN** (e.g. 96) tilts the drift **WEST**
   (Y-up → east) at the same α-model (off 32 → α 8° → −2.88/fr, dx≈−4/fr). **DO NOT
   hardcode the input chain** — model it as a small BFS over facing (nodes=facings,
   edges=valid >135° snaps to reachable m34E8 gates) so it generalizes to any
   start/target axis. m34E8 = stickAngle + 0x8000 + camAngle (camera fixed → stick→world
   mapping fixed; only Link's facing changes). Tooling: `capture_arrow.py seq=… slot=9`.

   **Instant-turnaround (charge snap) angular budget — from decomp
   `getDirectionFromAngle` (d_a_player_main.cpp:2278):**
   ```
   abs(m34E8 - facing) > 0x6000  -> DIR_BACKWARD  (snap shape_angle instantly = the charge)
   >= 0x2000 -> LEFT ; <= -0x2000 -> RIGHT ; else FORWARD
   ```
   0x6000 = 135°, 0x2000 = 45° (units: 0x10000 = 360°). So the BACKWARD snap is a
   90°-wide cone around straight-back (180°), i.e. valid only when the stick is
   **< 45° off directly-behind** (strictly: >135° from facing). This 45° is the
   ENTIRE angular budget for arrow swimming while keeping full charge snaps —
   crossing it is exactly the X≈200 tip-over above (snap stops → speed lost).

   **EMPIRICALLY CONFIRMED (live): max 1-frame heading turn vs tilt β off
   straight-back (facing addr 0x803EA3D2; snap appears 1 frame after input):**

   | β    | 0   | 35   | 42   | 44   | 46  | 50  | 70  |
   |------|-----|------|------|------|-----|-----|-----|
   | turn |180  |147.5 |138.6 |136.5 | 7.8 | 7.5 | 6.6 |

   Instant snap fires for β ≤ 44°, dies between 44–46° → boundary = exactly 45°.
   When it snaps, Link rotates exactly (180°−β) to face the stick; the snap stops
   the instant that required turn falls below 135° (0x6000) — i.e. when
   `getDirectionFromAngle` stops returning DIR_BACKWARD. Beyond it: gradual
   `cLib_addCalcAngleS` turn (~7°/frame). The snap shows one frame after the input
   changes (target-angle update lag). (Validated 2026-06-26.)
4. **ESS** toward destination — preserve potential speed via −1/6 decay.
5. **Neutral boost** — once ESS drag penalties outweigh the −2 neutral loss,
   go neutral (true speed == potential speed).
6. **\*\*ESS pump** — while neutral, occasionally ESS for one frame when the
   animation frame is favorable, to preserve speed cheaply. NOT modeled.

   **EMPIRICAL FINDINGS (live, low-speed ~-280 regime, slot-10 flat water):**
   - Neutral swimming = **state 54 (swim-wait, ANM_SWIMWAIT)**, distinct from ESS
     state 55 (move, ANM_SWIMING). Anim frame advances **~0.83/frame** in neutral
     (rises slowly as air depletes → swimTimerRate-driven, NOT speed-driven),
     vs ~7.2/frame in ESS.
   - **1-frame pump entry cost:** the FIRST ESS-input frame out of neutral stays
     in state 54 and behaves as **pure neutral** — decay −2, drag-free neutral
     displacement, anim +0.83. The stick input only QUEUES the 54→55 transition.
     The −1/6 ESS decay starts only on the 2nd frame (state 55).

     | pump frame | state | speed decay | behaves as |
     |------------|-------|-------------|------------|
     | 1          | 54    | −2          | neutral (no benefit) |
     | 2+         | 55    | −1/6        | real ESS   |

   - So a pump of length L = 1 frame@−2 + (L−1)@−1/6. Speed saved vs L neutral
     frames: L=1 → 0 (useless), L=2 → 1.83, L=3 → 3.67. **Minimum effective pump
     is 2 frames**; each pump pays a fixed 1-frame entry tax.
   - Anim across the transition: frame 1 carries the neutral anim; frame 2 the
     controller re-inits/rescales (ANM_SWIMWAIT→ANM_SWIMING have different
     lengths → transient garbage observed, e.g. 4705); from frame 3 anim advances
     at the ESS 7.2 rate (mod 23) from the re-init value.

   **When pumping matters (user guidance):** ESS pumping is a **LOW-SPEED** tech.
   The point is opportunistic — pump only when the timing happens to land an ESS
   frame on a *good animation frame* (low |cos| drag), so you preserve speed
   (−1/6) on a frame whose true displacement stays near neutral's. Given the
   1-frame entry tax above, a pump must be ≥2 frames AND land good anim phases to
   beat neutral. This is exactly why predicting the neutral→ESS anim phase matters.
   At HIGH speed / stroboscopic bands, do NOT pump — see strobo below.

   **PLANNING WARNING — mid-swim pumps are a SIM TRAP, do NOT plan with them
   (live-proven 2026-06-27).** A full-swim planner (`superswim_plan.py`) that's free
   to insert `neu,1` pumps mid-cruise produces plans that FAIL catastrophically live:
   a band-1 (v=-806) 200k-unit run planned at 266 fr bled speed to ZERO by f252 and
   reached only 58k/200k (**71% short**). Cause: every pump re-enters ESS → re-scrambles
   the ESS-start anim ×598 (above) → the sim can't predict the landed phase → it
   under-prices the exit `af_drag` cut → the optimizer mines phantom-cheap pumps that
   drain all potential speed. The reboost+ESS-cruise portion tracks live frame-exact;
   the divergence is ENTIRELY the pumps. **Fix:** plan neutral as a ONE-WAY TERMINAL
   DASH only (`allow_pump=False`, the planner default) — a single predictable exit from
   sustained ESS. That replanned to 275 fr and validated plan=sim=live frame-exact
   (0.0186% net error, +42 fr vs pure ESS). Re-enable mid-swim pumps only after the
   pump ess_start anim is validated live per entry-frame (the ×598 search dim). The
   pump exit being mispredicted is the SAME mechanism as the §"TOOL BUG" 2-increment
   phase error, amplified by repetition.

   **SOLVED — neutral→ESS anim phase is scrambled by a multiply-and-wrap.**
   `setSwimMoveAnime` (d_a_player_swim.inc:264) does, with J3DFrameCtrl getFrame()
   = raw frame, getEnd() = raw end:
   ```
   endFrame = oldFrame * oldEnd;            // oldEnd = ANM_SWIMWAIT length
   <load ANM_SWIMING, getEnd() now = newEnd>
   setFrame(endFrame * newEnd);             // newFrame = oldFrame*oldEnd*newEnd
   ```
   So the ESS-phase starting anim = `(oldFrame · oldEnd · newEnd + ESS_incr) mod 23`.
   Empirically oldEnd·newEnd ≈ 600 (transition value rose ~503 per entry frame,
   /0.84 anim-per-frame = 599). Confirmed: ess3 = (transition_raw mod 23) + r with
   r = the ESS increment `|v|/36 + 3/5 + (1-(air+1)/900)` (~8.4, shrinking with
   speed). Measured ESS-start across consecutive entries: 7.08, 2.68, 22.94,
   21.87, 22.45, 1.70, 5.60, 11.17 — jumps chaotically, NOT smooth.

   **Implication:** the ×600 factor makes anim_ESS_start hypersensitive to exact
   entry frame (1 entry-frame ≈ 0.84 anim → ×600 ≈ near-full 23-wrap). It is
   DETERMINISTIC but effectively scrambled. A predictor cannot use a smooth
   approximation — it must replicate the frame-controller math exactly, or treat
   the ESS-start phase as a per-entry-frame search/lookup.

   **CLOSED-FORM (constants measured + verified live):**
   - End_swim (ANM_SWIMING length) = **23** (ESS anim wraps at 22.9965; matches the
     cos(πx/23) drag period exactly).
   - End_wait (ANM_SWIMWAIT length) = **26** (neutral anim wraps at 25.997; it
     climbs past 23 to ~26 — harmless, neutral is drag-free).
   ```
   anim_ESS_start = (swimwait_frame * 598 + ESS_increment) mod 23   [598 = 26*23]
   ESS_increment  = |v|/36 + 3/5 + (1 - (air+1)/900)
   ```
   where swimwait_frame = the swim-wait controller frame ON the transition frame
   (entry anim advanced one swim-wait step = oldFrame; on the CURRENT slate that
   step is the neutral rate `0.5 + 2.5·(1−(air+1)/900)`, NOT the old-slate
   0.83→0.92 — confirmed live 2026-06-27: oldFrame = ess1(s54) + one neutral step,
   ×598 confirmed by raw-rise/rate ≈ 598. ESS_increment offset re-validated on the
   current slate too: implied increment drifts −0.0544/fr = −2/36+1/900 exactly
   across K=2..9, so the offset IS incr(v,air), not a constant). Verified:
   K=2 → 5.344*598 = 3195.7
   (measured transition raw 3195.57); (3195.57 mod 23)+8.5 = 7.07 (measured 7.08).
   Subsequent ESS frames: +ESS_increment mod 23 each (already validated).

   **Key insight:** 598 ≡ 0 (mod 23), so the INTEGER part of swimwait_frame is
   irrelevant — only its FRACTIONAL (sub-frame) phase sets anim_ESS_start, scaled
   ×598. 1/26 frame of entry jitter = a full 23-cycle swing → why it looks
   scrambled. Deterministic and now fully computable for a predictor.

   **EXIT (ESS→neutral) — this is the animation-frame drag, ALREADY MODELED by the
   tool as `release_ess_speed`.** On release the neutral speed becomes the
   af_drag'd (true) speed at the release frame:
   ```
   exit_speed = af_drag(potential, anim) = (2v/5)|cos(π·anim/23)| + 3v/5
   ```
   = SwimEnvironment.release_ess_speed (calc_animation_frame_drag). Applied as a
   one-time set on the state55→54 transition (lands 2nd neutral frame, 1-frame
   lag), then normal −2 decay resumes (verified persistent: −293→−186 then −2/fr).
   **Verified live to ~0.2:** exit_speed = af_drag(potential, anim_release + 1
   ESS_increment) — note the frame is the read release-frame anim advanced by one
   ESS increment.

   | effective anim | |cos| | speed kept |
   |----------------|-------|------------|
   | ~0 / 23 (ends) | ~1    | ~100% (af_drag ≈ v) |
   | ~11.5 (middle) | ~0    | ~60% (af_drag = 3v/5) |

   **Practical rule: release ESS when the (effective) animation position is near
   0/23; releasing mid-cycle (~11.5) costs up to ~40% (down to 3v/5).** This is the
   normal af_drag pattern (NOT inverted) — the loss is the same head-bob drag that
   modulates ESS true speed, now baked into the carried-over neutral speed.
   No separate "exit tax" beyond release_ess_speed; the tool has it. (2026-06-26)

   **TOOL BUG (verified): release_ess_speed uses the WRONG frame — 2-increment
   phase error.** SwimEnvironment.release_ess_speed = af_drag(velocity,
   animation_frame) reads the last-ESS-frame anim. But the game applies af_drag at
   `animation_frame + 2·ESS_increment` (the release frame still runs ESS physics +
   the 1-frame exit lag). Verified live to ~0.2 in two cases:
   - exit = af_drag(potential, (anim_lastESS + 2·incr) mod 23).
   Error depends on where the +2 incr (~17 anim units) lands on |cos|:
   small when both frames near the cos extremes, **up to ~40% when it moves a
   mid-cos frame onto a near-zero-cos frame** (e.g. tool 260 vs game 186).
   **Fix:** before computing release speed, advance 2 more ESS-physics frames
   (anim += incr, velocity -= 1/6, air -= 1 each), THEN af_drag. (2026-06-26)

---

## 6. How the prediction tool solves it

- **State machine**: `enum State { Charging, EssSwimming, NeutralSwimming }`,
  stepped frame-by-frame in `SwimEnvironment.perform_step`.
- **Optimizer**: Particle Swarm (`ParticleSwarmOptimizer.cs`). Decision vars are
  typically `[chargeTime, essTime]` (and an animation-frame variant adds
  `animationFrame` in `[0,23]`). Neutral time is then *computed analytically*
  (`time_to_travel_distance(remainingDist, releaseEssSpeed, -2)`) rather than
  searched. Fitness = total frames; infeasible (overshoot / charge+ess>air)
  returns `double.MaxValue`.
- **PSO params used**: `Omega=0.7627, Phi_G=1, Phi_P=3` (others commented out).
- **Balloon swim** option: project at current velocity for N frames, then 0.75×
  speed on landing + 27-frame resurface (−3/frame), forced air refill after.
  Decomp confirms the 0.75 landing multiplier (`mNormalSpeed *= 0.75f`,
  `d_a_player_swim.inc:137`) and 900 air reset (line 126).
- **Closed-form helpers** (kinematics, `a` = accel): `time_to_travel_distance`
  = `(sqrt(2*c*d + v²) − v)/c`; `ess_normal_minima(_new)` solve the optimal
  ESS↔neutral switch distance analytically (derivative-zero from WolframAlpha,
  comments lines 762-810). `avg_ess_rate = (4+3π)/(5π)` is the average
  fraction of speed retained as displacement while ESSing.

### Critiques / expansion opportunities
- PSO may be overkill: the feasible space is low-dimensional (`chargeTime`,
  `essTime`), monotonic-ish, and bounded by air. Grid/ternary search or the
  existing closed-form minima could be more reliable & deterministic.
- **Arrow charge** and **ESS pump** phases are unmodeled — both are real
  optimizations. Modeling ESS pump needs per-frame animation-frame tracking in
  the neutral phase (currently neutral is a closed-form kinematic, drag-free).
- Stroboscopic speed bands (−850/−1650) aren't targeted explicitly; an objective
  that rewards landing in a stable-animation band could help.
- Tool has heavy dead/commented code (`SwimEnvironmentOld`, old estimators).
  The live model is `SwimEnvironment` + `CalculateTotalTime`.

---

## 7. Decomp map (where things live)

`tww/src/d/actor/d_a_player_swim.inc` (included into `d_a_player_main.cpp`):
- `setSpeedAndAngleSwim` — speed gain, arrow-angle cos penalty, stick handling.
- `changeSwimProc` — entry to swim: air=900, `mNormalSpeed *= 0.75`.
- `getSwimTimerRate` — `1 - air/900`, the air term feeding animation rate.
- `setSwimTimerStartStop` / `setSwimMoveAnime` — animation frame-controller rate
  (speed + air dependent).
- `procSwimUp / procSwimWait / procSwimMove` — the swim state procs.
- HIO tunables (`m_HIO->mSwim.m.field_0x..`) hold the magic constants
  (max speed, rates); not all are resolved to names in the decomp yet.

---

## Open questions to resolve with the user
- Exact source of the −2 neutral / −1/6 ESS constants (HIO field mapping?).
- Confirm stick "minimum non-neutral value" for ESS in raw stick units.
- Whether −850/−1650 strobe bands are exact or approximate, and their derivation.
