# Test-owned DTM anchors

Savestate anchors for the live DTM validators (`harness/dtm/run_dtm.py`). Each test (or test
group) owns its starting slate here, so a run never depends on Dolphin savestate **slot 9** —
which other processes (and the editor) silently overwrite, and which we learned had quietly
drifted from its documented facing.

## Naming convention (load-bearing)

```
<test-or-group>@<isokey>.sav
```

- `<isokey>` is the iso basename without extension. The runner resolves it to
  `$TWW_ISOS_DIR/<isokey>.iso` (default `C:\Users\pinhi\Documents\ISOs`), so the image to
  boot is baked into the anchor name — no more `TWW-JP.iso` vs `twwgz.iso` confusion.
- Example: `cruise_cold@twwgz.sav` → boots `…/ISOs/twwgz.iso`.

`run_dtm` parses the `@<isokey>` tag automatically; you never pass `game=` unless overriding.

## These files are NOT committed

They are dumps of copyrighted game RAM (~27 MB), so `.gitignore` excludes `*.sav`. Only this
README is tracked. Regenerate an anchor locally:

```
# set up the slate (loadstate / writename / charge / reorient ...), then:
python harness/dtm/capture_anchor.py name=arrow_charged iso=twwgz
```

It prints the captured controllable values (v / anim / air / state / facing) — record those
as the test's expected endpoint.

## Anchors

| anchor | slate | notes |
|--------|-------|-------|
| `cruise_cold@twwgz.sav` | cold start, v=0, state 54, COLD_ANIM | shared cruise baseline (was `cruise_pump300k_rec.dtm.sav`) |
