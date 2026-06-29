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
