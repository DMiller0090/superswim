# Superswim session handoff — 2026-06-29

Read `SUPERSWIM_KNOWLEDGE.md` (source of truth) and `../tools/DOLPHIN_CONTROL.md` first.
This file is the short "where we are / what's next" for the next session.

## >>> NEXT (chosen 2026-06-29): close the OFF-AXIS charge v residual (~0.0105) — the last gap in the arbitrary-stick predictor <<<
The `tests/test_complicated.py` residual (cap_randcharge/gen_charge: **v ~0.0105**, pos ~1.8) is now
ISOLATED to the **off-axis charge GAIN** — it is NOT camera and NOT magnitude:
- Injecting the TRUE live camera (instead of the predicted one) leaves the v residual **identical**
  (0.01047/0.01072) and pos barely moves → not camera-driven (the coarse-omega 1–2 hw cam error is
  a separate, near-orthogonal issue).
- Magnitude is saturated on these captures (sy∈{0,255} → md=1.0), and the magnitude model is
  live-confirmed anyway (pt23 below). So magnitude is ruled out.
- **The discriminator is purely on-axis vs off-axis main stick:** `cap_camchaos` (clean ON-axis
  charge + random camera) is **bit-exact**; `cap_randcharge` (random OFF-axis charge) is not. Same
  cold start, same camera treatment.

So the gap is how an off-axis stick's angle feeds `gain = mStickDistance*3*cM_scos(d_turn)` under
**arbitrary per-frame directions** — likely the snap-cone (`|m34E8-facing|>0x6000`) decision and the
1-frame facing-lag bookkeeping near the snap↔gradual boundary (swim_arbitrary.action_for already
notes a "snap<->non-snap boundary mis-price" history). NOTE the clean FIXED-tilt charge is already
live-validated: `sim.py:195` `charge_rate(α) = -3*cos(2α)` matched live at α=0/8/18. The residual is
specific to RANDOM per-frame direction changes.

**PLAN (mirror the pt23 magnitude method, which worked):**
1. OFFLINE FIRST — localize: per-frame v-error on cap_randcharge, correlate worst frames with the
   snap decision (`d_turn`, snap vs gradual), the stick angle, and post-snap transients. Cheap; no
   Dolphin. (Drive `ArbitrarySwimState` with the TRUE camera to fully isolate the swim model.)
2. Form a hypothesis about the mis-priced frames (boundary crossings? gradual-chase lag?).
3. Capture a CLEAN targeted live charge that isolates the suspect mechanic (fixed off-axis tilt /
   deliberate snap-cone crossings, camera frozen via csy=0) for clean per-frame ground truth — use
   `harness/capture/capture_full.py seq=… out=… slot=10` (same tool as pt23).
4. Fix in `swim_arbitrary._swim_facing` (and/or `swim_exact` snap helpers); validate: golden suite
   MUST stay bit-exact (arbitrary path is not token-driven, so goldens are untouched if done right),
   then `python tests/dolphin/run_tests.py` live, then TIGHTEN `_CHAR_BOUNDS` toward bit-exact.
CODE: `superswim/predict/swim_arbitrary.py` (`_swim_facing`, gain/d_turn, L65-90),
`superswim/predict/swim_predict_complicated.py` (`predict_full`, the per-frame loop + snap/chase),
`superswim/sim.py:195` (charge_rate model), `tests/test_partial_magnitude.py` (the pt23 method to copy).

## >>> pt 23 (2026-06-29) — the "wire the live stick magnitude" task is DISPROVEN & CLOSED. The closed-form /54 magnitude was ALREADY correct; the grid `stick_dist` column is NOT the gain input. <<<
Read memory [[superswim-stick-magnitude-todo]] (now CLOSED-as-invalid).

**What was tested (decisive, live):** captured a partial **on-axis** charge — alternate (128,84)/
(128,176), camera frozen west — so the angle is exact and ONLY the magnitude (grid vs closed /54)
differs. `harness/capture/partial_onaxis_cap.csv` (48 fr, run_tests-style seed). Then drove
`ArbitrarySwimState` two ways:
- **closed-form `hypot(_deadzone₁₅)/54`** → **bit-exact every frame** (worst |v_err| 0.000008).
- **grid `stick_dist` column** → ~0.22 too short (worst |v_err| 0.22, grows with charge).

So the gain magnitude the game uses **IS** the closed-form `/54` already in `swim_arbitrary.py`
(and `sim.py:537`). The grid `stick_dist` (deref `0x803BD910 +0x35B4`) reads a related-but-different
value (effective deadzone ~13, off by ~2/54=0.037 per partial cell) — NOT what the swim gain
consumes, despite the dump script's comment. Wiring it in was tried and **reverted**; only
explanatory comments remain in `swim_arbitrary.py` / `stick_angle.py`. The (200,60) "live 1.0 vs
0.69" that motivated the task was a red herring: the 0.69 was `sim.stick_dist`'s `/113` gate (a
different function); the `/54` path already gives 1.0 there, matching live.

**STILL OPEN (separate, correctly-scoped):** the `tests/test_complicated.py` residual on the
random-camera off-axis charges (cap_randcharge/gen_charge: v ~0.0105, pos ~1.8, cam 1–2 hw) is
NOT a magnitude bug — those captures use saturated `sy∈{0,255}` sticks (grid==closed==1.0). The
residual lives in the **angle/snap/camera coupling** (note the residual cam 1–2 hw too). Leave
`_CHAR_BOUNDS` as-is; do NOT tighten. A genuinely-partial OFF-axis live capture is still untested
(both closed /54 and the grid column are unproven off-axis where they don't saturate).

## >>> RESOLVED (2026-06-29): the omega (camera-rate) grid was corrupt (input-path off-by-one) <<<
See memory [[superswim-omega-grid-coarse]] + knowledge/CAMERA_MODEL.md ("Resolved: the omega grid").
`omega_table_full.csv` (csx 0..15 x csy 0..255) had been dumped via `set_gc_buttons` (calibrated
path), recording the neg-saturation omega as -546 where the raw-byte `advancewith` path the swim
uses gives -547 (1816/4096 cells off by +1), and it loaded LAST so it clobbered the correct fine
`omega_table.csv`. Fix: load the fine table last + regenerate the grid via `advancewith`
(`harness/capture/omega_full_redump.py`). The two tables now agree on 100% of overlap; cap_randcharge
/ gen_charge go cam=0hw (were 1-2hw) and are promoted to bit-exact. Still NOT a complete 65536 grid
(csx 0..15 band + captured cells); off-grid (csy != 128) still raises -- capture cells on demand via
`harness/capture/omega_capture.py --sticks csx,csy` if a route needs an off-grid C-stick.

## >>> pt 22 (2026-06-29) — REPO turned into a shareable `superswim` PACKAGE + a two-gate test model. KEY LESSON: the sim cold-start seed needs the live mRate, not anim alone. <<<
Read [[superswim-repo-layout]], [[superswim-regression-suite]], [[superswim-554-resolved]] first.

**STRUCTURE (was a flat 71-file root; now a package — see README.md):**
- `superswim/` = the importable, **pure-offline** library (`sim` `plan` `optimize` `coldstart`
  `actions`, `predict/`, `tables/`); no Dolphin dep; `pip install -e .` → `from superswim import …`.
  Old flat names map: `superswim_sim.py`→`superswim/sim.py`, etc. (full map in [[superswim-repo-layout]]).
- `tests/` = OFFLINE `pytest` suite (unit + golden). `tests/dolphin/` = LIVE sim-vs-Dolphin scripts
  (`run_tests.py` `verify_state.py` `spotcheck_*`). `harness/` = live tooling. `viz/` `fixtures/`
  `docs/` (+`history/`) `archive/` (one-off probes, kept for provenance).
- The shared seq helpers `expand`/`acts_to_seq`/`animdiff` now live in `superswim/actions.py`
  (were `run_tests.R.*`); the live-write `wnamed` in `harness/live.py`.

**SAVESTATE: `loadfile` WORKS on this fork now (pt9's "ok:false" is STALE).** The cold-start slate is
vendored at `fixtures/savestate/superswim_coldstart_slate.s10` and loaded BY PATH via
`savestate loadfile` — bit-identical to slot 10, so the suite needs only Dolphin + booted ISO, no slot
dependence. `tests/dolphin/run_tests.py slot=10` still overrides with a Dolphin slot.

**⚠️ THE LESSON (cost a debugging cycle — do not relearn it): seed the cold start with the LIVE mRate.**
A plain `SwimState(v, anim, air)` hardcodes the cold-start scramble oldframe as `f32(anim + 1.0)`,
which is correct ONLY at the canonical fresh-cold-start controller phase (anim≈0.0639). At ANY other
slate phase the real entry-tax advance is the logged controller rate `mRate`, and the x598 anim
scramble amplifies the sub-ULP oldframe error ~600× → the tell-tale signature **air + link_state match
exactly, but v and anim diverge**. FIX: seed `ColdStartSwimState(v, anim, air, mrate=move0_mrate)`
(the live MOVE0 rate; named addr `move0_mrate` = anim-chain base `0x803AD860 +0x2F60` == fc_rate,
anim_frame is +0x2F64). `tests/dolphin/run_tests.py` and `harness/validate/validate_coldstart.py` do
this; mirror them for any new live seeding.

**NEW: offline regression suite (`pytest`) — the logic-regression LOCK.** 89 tests (+1 `slow`), ~3s,
no Dolphin. Two layers: unit tests on the physics primitives (decomp-grounded values) and
GOLDEN/characterization tests freezing full per-frame traces of 17 `(seed, seq)` cases as
**full-precision hex floats at 0 tolerance**. Goldens are generated from HEAD (the live-validated sim
IS the reference). GOTCHAS for whoever edits the sim next:
- A golden diff means the sim's output CHANGED. After a *deliberate, live-verified* change, refresh
  with `python -m tests.golden_regen` (never auto on failure) and re-run the Dolphin gate.
- `bug1_lowspeed` / `bug2_pumptrans` goldens freeze the sim's DETERMINISTIC output even though those
  fixtures are XFAIL vs LIVE — a change there is a real sim regression, not the live bug.
- Two unit asserts use widened tolerance ON PURPOSE (`cM_scos(pi)≈−1` proves the table-truncation
  offset *exists*; `incr(0,0)≈1.599` is a coarse air-dependence check). Don't "tighten" them; exact
  values are frozen elsewhere.
- Offline seeds (`COLD_ANIM`/`COLD_MRATE` in `tests/golden_harness.py`) are the canonical live seed;
  if the cold-start model changes they must be re-synced from a live read.

**RUN BOTH before/after any `superswim/sim.py` change:** `pytest` (offline, anywhere) AND
`python tests/dolphin/run_tests.py` (live: 3/3 baselines PASS + 2 XFAIL on the current slate). All work
is on branch `dmiller/repo-reorg` (4 commits), not yet pushed.

## >>> pt 21 (2026-06-28) — bug#2 RESOLVED: it is a PIPE INPUT-DELIVERY ARTIFACT, not game physics. The decisive clean-DTM movie test PASSED bit-exact. Dense-pump plans are VALID. <<<
Read memory [[superswim-bug2-input-delivery]] (now RESOLVED). This closes the pt-20 crux.

**THE DECISIVE TEST WAS RUN — conclusive, bit-exact:**
- Authored a CLEAN DTM (`make_dtm.py`, rewritten) for cruise_pump300k_seq.txt with the correct poll
  cadence and NO slip, played it via the movie system, read the endpoint:
  - **Clean DTM → net 300,816, v=−801.011, anim=19.4041, air 195, st 54 — BIT-EXACT to the sim**
    (`SwimState` end state identical to the decimal across all 705 frames / 44 pump cycles).
  - Recorded (jittered) DTM, SAME harness → net 127,046, v=0 (reproduced the pt-19 figure exactly).
- So the sim's dense-pump physics were CORRECT all along. The ~127k shortfall was the **external
  pipe inserting poll JITTER** on the dense-transition frames — offline `align_dtm.py` shows the
  pipe recording has +2/−2/+2 extra SI polls at runs ~f278/287/289 vs a uniform 4-polls/game-frame;
  a clean from-savestate movie polls uniformly (no FrameAdvance-listener). bug#2 = validator artifact.

**THE CORRECT DTM CADENCE (now in `make_dtm.py`):** controllers=3 (TWO GC ports — the "blank" rows
are the idle port-1, NOT padding); the game polls ~4×/30fps-frame; a working DTM is, per game frame,
4 polls × 2 ports = 8 ControllerState rows laid out port0(stick)/port1(blank) per poll (PlayController
consumes one ControllerState per port per poll, stride = active_ports×8). `getMainStickValue`
calibrates extremes 255→254 / 0→1. bFromSaveState=1 disables the tick-end → playback runs to
byte-exhaustion. We CLONE the proven-playable recorded header (patch only frameCount/inputCount/
lagCount), copy its exact port-1 blank row, reuse its `.dtm.sav` cold-start anchor. The old
make_dtm (1 row/frame, controllers=1) was unplayable garbage.

**WHAT THIS MEANS FOR THE PROJECT (direction):**
- Dense-dip plans are VALID; the planner's pump savings (6 fr @200k, 6 fr @300k, etc.) are REAL.
- The "live failures" and the [[superswim-multi-solution]] live-filter rejections were EXTERNAL-PIPE
  artifacts, not physics. The pipe (advanceseq/advancewith) is UNRELIABLE for dense back-to-back-dip
  plans. **DTM movie playback is the faithful delivery + validation path** — use it, not the pipe.
- Do NOT model the slip into `SwimState` (that would corrupt a correct sim to match a broken
  validator). `run_tests` bug#2 XFAIL (test_pumptrans via advanceseq) now documents the PIPE
  artifact — leave it XFAIL; it is not a physics regression.
**NEXT STEPS — DONE this session:**
- (a) **`validate_dtm.py` built** = the standard faithful validator: kill+relaunch Dolphin →
  `make_dtm.build_dtm` (clean cadence) → copy the cold-start `.sav` anchor → playmovie → play to
  byte-exhaustion → read endpoint → compare v/anim/air/state to the sim (seeded cold at COLD_ANIM).
  One call, fully automated, exit 0 iff bit-exact. Usage: `python validate_dtm.py seq=<file>`.
- (b) **All dense pump plans re-validated via DTM playback — ALL BIT-EXACT (dv=0, dan=0):**
  - `cruise_pump300k_seq.txt` (705 fr) → net 300,816, v=−801.011 (= sim).
  - `cruise_pump300k_f6000.txt` (704 fr, 199 dips, the DENSEST + 1 fr better) → net 300,376,
    v=−793.790 (= sim). **This is the best 300k plan — use it.**
  - `ab_pump_seq.txt` (556 fr, the A*-best 200k that pt-18 said "DIES live to 110k via bug#2") →
    net 200,330, v=−624.682 (= sim). The "death" was the pipe; the plan is valid.
  So the planner's pump savings are now LIVE-CONFIRMED faithful (200k: 556 vs 561 no-pump; 300k:
  704 vs 711 no-pump). DTM playback is the trustworthy delivery path; the advanceseq pipe is not.
- (c) NOT needed — these are min-frames-to-DEST plans; they correctly CROSS the destination at speed
  (net ≥ dest), they don't need a decel-to-0 tail. (My earlier "ends mid-cruise" note was a misread.)
- TOOLS: `validate_dtm.py` (the validator), `make_dtm.py` (clean-cadence author + `build_dtm()`),
  `align_dtm.py` (offline jitter locator), `dtm_play.py` (manual play+read; boot-detect now guards
  the `attach` SystemExit). ARTIFACTS: `*_clean.dtm` (small; the big `.dtm.sav` anchors are
  regenerated on demand by copying `cruise_pump300k_rec.dtm.sav`).
- POSSIBLE FUTURE: route the planner's full charge→arrow→cruise→dash front-end plans through
  validate_dtm (the front-end uses arrow sticks, not just ess/neu/chg — `make_dtm` sticks come from
  `run_tests.acts_to_seq` which only knows ess/neu/chg, so extend it for arrow stick rows first).


---

_Older session logs (pt 8–20) are kept locally in the gitignored `_notes/` (not in the shared repo);
full detail also remains in git history._
