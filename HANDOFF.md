# Superswim session handoff — 2026-06-29

Read `SUPERSWIM_KNOWLEDGE.md` (source of truth) and `../tools/DOLPHIN_CONTROL.md` first.
This file is the short "where we are / what's next" for the next session.

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
