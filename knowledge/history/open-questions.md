# Open questions

> **status: historical/tracking** — the open research register. Each item's *current best answer*
> also lives on its truth page (linked); this page is the running list of what's unresolved.

---

- **Does arrow swimming save time?** Current verdict: probably not (offline loses ~2–4 fr at 200k;
  not validated cold — `ArrowState` doesn't model the state-54→55 entry release + ×598). Next:
  capture charged-arrow anchors, build arrow vs no-arrow plans, compare via DTM. →
  [mechanics/arrow](../mechanics/arrow.md#open-question--does-arrow-swimming-save-time).

- **Stroboscopic band exact derivation.** The bands are empirical (emerge from the increment
  formula); the exact decomp source (likely a Nonmatching `J3DFrameCtrl::update` term) and whether
  the bands are sharp or fuzzy are unpinned. → [mechanics/strobo](../mechanics/strobo.md#open--approximate).

- **Multi-pump precision floor.** Single/double pumps are bit-exact; beyond ~1.5 pump cycles the
  ×598 scramble amplifies a ~1e-4 per-entry anim oscillation past a cos-table boundary (~0.07 v per
  pump). Escape hatch: a per-entry anim ∈ [0,23] search dimension in the planner. →
  [mechanics/pumps](../mechanics/pumps.md), [model/planner](../model/planner.md).

- **Re-enable mid-swim pumps.** Currently disabled (`allow_pump=False`) because the pump ess_start
  anim is mispredicted. Re-enable only after validating the entry-anim phase live per entry-frame.

- **BUG #2 (pump transition) still broken — root cause = anim-phase drift into pump exits (an
  instance of the multi-pump precision floor above).** `test_pumptrans_seq` (chg,144 + dense
  neu↔ess tail) reaches live **v=−775 / net=111004** (clean DTM `run_dtm`, reproduced 2026-06-30 &
  2026-07-01); the sim predicts v=−65. Bisected via truncated-prefix DTMs (2026-07-01): the build
  is **bit-exact through n=267** (v=−788.5 == live); divergence begins at the **first ESS→neutral
  release (n=269)** — the sim bleeds −252 there vs live's ≈−0.001. `release_ess_speed` is **CORRECT**
  (reseeding the sim from the exact live n=268 state reproduces live's near-identity exit): the sim
  lands the exit in the |cos|≈0.2 anim trough while live is at the |cos|≈1 peak. So the defect is
  the SWIMING anim *phase* drifting through the ×598 pump-entry scrambles (the ~18 neu↔ess tail
  cycles), NOT the release formula. Fix path = the multi-pump precision floor's: a bit-exact
  per-entry anim (or a per-entry anim ∈ [0,23) search dimension). Gate: `run_tests.py bug2 neu-pump`
  now compares the sim to the recorded DTM truth (v=−775), NOT advanceseq (which gave a FALSE pass
  by matching the equally-wrong sim on the jittered tail) — XFAILs by ~700 until fixed. →
  [history/resolved-bugs#bug2](resolved-bugs.md#bug2--dense-pump-live-divergence--pipe-artifact-not-physics),
  multi-pump precision floor (above).

- **Camera: f32 ω precision + auto-flip envelope + negative fine-band symmetry.** We read the s16
  yaw output exactly; the internal ω velocity is f32 (upstream). The auto-camera *flip* trigger
  (speed/hold-length) is uncharacterized — steering must stay in a non-flipping band. →
  [mechanics/camera](../mechanics/camera.md#open).

- **Predictor consolidation.** The 4 `swim_predict*` variants form an evolution chain kept as
  separate modules; merging into one predictor is a known follow-up (each merge re-validated
  bit-exact). → [model/predictors](../model/predictors.md).

- **HIO constant provenance.** Not all `m_HIO->mSwim` magic constants are resolved to decomp names. →
  [reference/constants](../reference/constants.md), [reference/addresses](../reference/addresses.md).
