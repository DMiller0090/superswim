# Live Dolphin tests

These validate the sim against a running Dolphin instance, so they need an emulator + the game,
neither of which is shipped here. The pure-offline gate (`pytest` at the repo root) covers
logic regressions without any of this.

## Locked tests are immutable (HARD RULE)

Once a test here is locked to a clean-DTM sync — its expected values confirmed against **movie
playback** (`run_dtm.py`, the trustworthy path) — it is **frozen**. Do NOT edit the test, its
input sequence, its expected values, or its golden to make a later run pass. A synced test is
ground truth about the game; the sim is what's under test, not the other way around.

If a locked test later shows the sim "wrong", the fault is, in order of likelihood:
1. **Methodology** (almost always). The sim was seeded or compared incorrectly. The classic trap:
   seeding the sim with a *different* cold start's controller mRate than the one the test's anchor
   was captured on. Two cold starts can share a display anim yet differ in `move0_mrate` (this
   anchor is **0.5**, the slot-10 slate is **0.5472**); the ×598 scramble amplifies that into a
   ~700 `v` gap. Seed with the EXACT anchor's logged mRate and compare against the SAME savestate.
2. **The playback/harness** (rare) — DTM authoring or the read.
3. **The sim physics** — only after 1 and 2 are ruled out on the clean-DTM path.

Never "fix" a synced test by regenerating its expected. That inverts the trust.

## Requirements

- A running Dolphin (the TAS-edition fork used for development) with `twwgz.iso` (GZLJ01) booted.
- `dolphin_mem` from the sibling `../tools/` workspace (these scripts reach it via a path bootstrap;
  a standalone clone of this repo won't have it).
- A **cold-start slate** to load. The slate is a dump of copyrighted game RAM, so it is **not**
  distributed here — supply your own:
  - `TWWGZ_SLATE=/path/to/your/slate.s10 python tests/dolphin/run_tests.py`, or
  - `python tests/dolphin/run_tests.py slot=10` to load a Dolphin save slot instead.

  A valid slate is an uncharged neutral float in open water (state 54). The suite seeds air/speed
  and the cold-start animation from the live state, so any equivalent cold-start float works.

## Running

```bash
python tests/dolphin/run_tests.py            # full suite
python tests/dolphin/run_tests.py dtm=1      # re-run the clean-DTM baselines LIVE (relaunches Dolphin)
python tests/dolphin/run_tests.py quick=1    # skip the long 200k case
python tests/dolphin/verify_state.py seq=... # per-frame divergence locator
```

The PASS baselines (cold-start 3k, 4/8-pump, pump-transition, bug3 partial hold) are **clean-DTM
syncs**: `run_tests.py` compares the sim to each recorded DTM truth offline (no emulator), seeded at
the anchor `cruise_cold@twwgz.sav`'s cold start with its own mRate. `dtm=1` re-plays each movie live
to re-confirm the truth still holds. These are LOCKED — see the immutability rule above. Only the
two XFAILs (200k, bug1) still run over the advanceseq pipe from the slate.

## Which path: pipe vs clean DTM

- `run_tests.py` / `verify_state.py` drive inputs over the **advanceseq pipe** — fast, no reboot.
  The pipe jitters SI polls on dense charge dips and can slip inputs (bug#2), so a failure on a
  dense charge/pump/arrow plan may be a delivery artifact.
- `harness/dtm/run_dtm.py` plays a **clean DTM** through the movie system — the trustworthy check
  for dense plans. Use it to gate dense charge/pump/arrow plans or when the pipe disagrees.

## `run_dtm.py` — inputs + expected

```bash
python harness/dtm/run_dtm.py seq=plan3k_exact_seq.txt \
    expect_v=-80.6842 expect_anim=3.44164 expect_air=832 expect_state=54
```

Authors a clean DTM → stops any running Dolphin and relaunches it (the game list closes) → plays
the movie → compares v/anim/air/state/**facing**. Position (x/z) is wave-affected and never
asserted. The iso is read from the anchor name, so no `game=` needed. `seq=NAME` resolves `NAME`
under `fixtures/`; pass a path for files elsewhere, or raw sticks with `sticks=<csv>`.

## Anchors

The starting slate is a test-owned savestate `tests/dolphin/anchors/<test>@<isokey>.sav`; the
`<isokey>` resolves to `$TWW_ISOS_DIR/<isokey>.iso`. Mint one from the current slate:

```bash
python harness/dtm/capture_anchor.py name=arrow_charged iso=twwgz
```

`.sav` are gitignored (copyrighted RAM); convention in `anchors/README.md`. Don't use save slots.
