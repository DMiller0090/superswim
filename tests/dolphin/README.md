# Live Dolphin tests

These validate the sim against a running Dolphin instance, so they need an emulator + the game,
neither of which is shipped here. The pure-offline gate (`pytest` at the repo root) covers
logic regressions without any of this.

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
python tests/dolphin/run_tests.py quick=1    # skip the long 200k case
python tests/dolphin/verify_state.py seq=... # per-frame divergence locator
```

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
