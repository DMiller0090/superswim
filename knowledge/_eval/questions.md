# Documentation eval — question bank (pilot slice)

Test questions for the turnaround / arrow / strobo / reboost slice. Each entry: the question, a
graded **reference answer** (the key fact a correct answer must contain), the **page** that should
own it, and a **source** (mined research thread, or `fresh`). `hazard` marks questions where an
*earlier* conclusion was later overturned — the highest-value retrieval checks, because stale docs
would give the wrong answer.

The eval runs each question in two modes:
- **Tier A (retrieval):** agent gets the question only and must *find* the answer in `knowledge/`
  within a tool-call budget. Failure = a discoverability gap (fix the index/structure).
- **Tier B (comprehension):** agent gets only the page named below and must answer from it. Failure
  = the page is wrong/incomplete (fix the content).

Restrictions for every eval agent: read only under `knowledge/`; never open `.py`; never touch
Dolphin; hard tool-call budget; if not found, report `found:false` and stop (no goose chase).

---

```yaml
- id: turn-threshold
  question: "What is the angle threshold for an instant turnaround (charge snap), and when does Link turn gradually instead?"
  answer: "Snap fires when the stick points >135° (0x6000) from current facing — i.e. within 45° of straight-back. Beyond that budget he turns gradually at ~7°/frame."
  page: mechanics/turnaround.md
  source: thread-3

- id: turn-units
  question: "In the turnaround decomp, what angles do 0x6000 and 0x2000 correspond to?"
  answer: "0x6000 = 135° (DIR_BACKWARD snap threshold); 0x2000 = 45° (left/right). Units: 0x10000 = 360°."
  page: reference/constants.md
  source: thread-3

- id: turn-reorient
  question: "Can you reorient the charge axis ~90° with a single instant snap? If not, how?"
  answer: "No — a single snap only fires for targets >135° off facing, so a ~90° reorient needs walking facing through 2–3 intermediate diagonal snaps (each charges)."
  page: mechanics/turnaround.md
  source: thread-3

- id: arrow-rate-18
  question: "Charging an arrow at 18° tilt off the back axis — what charge rate, and roughly what fraction of full?"
  answer: "charge_rate = -3·cos(2·18°) ≈ -2.43 (~81% of -3). Live measured -2.44."
  page: mechanics/arrow.md
  source: thread-4

- id: arrow-drift
  question: "What is the per-frame cross-track drift while arrow swimming at tilt α?"
  answer: "cross_drift = displacement · sin(α) per frame (accumulates toward the target)."
  page: mechanics/arrow.md
  source: thread-4

- id: arrow-tipover
  question: "What is the tilt limit before arrow swimming breaks, and what happens past it?"
  answer: "Usable to α ≈ 20° (Xbias ≈ 190). Past it the backward snap dies → forward release → speed LOSS (tip-over). Same as the 45° turnaround budget."
  page: mechanics/arrow.md
  source: thread-3,4

- id: arrow-spinup
  question: "What is the arrow spin-up cost?"
  answer: "~2 frames — the first non-snap forward frames each lose ~+3/fr before the 0↔180 swing locks in."
  page: mechanics/arrow.md
  source: thread-14

- id: arrow-stickdist
  question: "When you tilt the arrow stick, does mStickDistance change?"
  answer: "No. Tilt changes the cosine (snap angle), not the magnitude; mStickDistance stays capped at 1 / closed-form /54."
  page: mechanics/arrow.md
  source: fresh-negative

- id: arrow-pays
  question: "Does arrow swimming actually save time over a straight cruise at 200k?"
  answer: "Likely NO — offline it loses ~2–4 frames (early drift doesn't cover prefix overhead), and it is NOT yet validated from a cold start (entry-tax + x598 unmodeled). Open question."
  page: history/reboost-strobo-history.md
  source: thread-14
  hazard: true

- id: strobo-speeds
  question: "At what potential speeds do the stroboscopic bands occur?"
  answer: "≈ -794 (k=1) and ≈ -1630 (k=2), air-dependent (where the ESS anim increment ≈ 23·k)."
  page: mechanics/strobo.md
  source: thread-16

- id: strobo-legacy
  question: "Is the strobo band exactly at -1650 (the commonly cited number)?"
  answer: "No — that legacy figure ignores the air dependence. The band is ≈ -1630 at air 900 and drifts with air; -850/-1650 are the same bands, off by the air term."
  page: mechanics/strobo.md
  source: fresh-negative
  hazard: true

- id: strobo-air-drift
  question: "As air depletes during a long swim, does the strobo band move to higher or lower speed?"
  answer: "Higher speed — the air term shrinks, so reaching increment = 23·k needs a larger |v|. The band drifts up under you."
  page: mechanics/strobo.md
  source: thread-16

- id: reboost-saves
  question: "Does reboosting in a strobo band save time?"
  answer: "Yes, but ONLY when phase-triggered (fire as anim drifts off the peak) — up to +15%. A fixed cadence loses."
  page: strategy/reboost.md
  source: thread-6
  hazard: true

- id: reboost-fixed
  question: "Should you reboost on a fixed cadence (e.g. every 20 frames)?"
  answer: "No. Blind fixed cadence loses (-2% band-2, -8% band-1) — it fires at random anim phases and pays the turnaround tax without aiming the drift."
  page: strategy/reboost.md
  source: thread-6
  hazard: true

- id: reboost-size
  question: "How big should a maintenance reboost be, and when do you fire it?"
  answer: "A 2-frame up-down (minimal), fired when anim drifts off the top of the peak (anim ~20-23/0-2), to re-park it at the peak. ~4 frames only to recover an anim that slid deep."
  page: strategy/reboost.md
  source: thread-6

- id: reboost-transfer
  question: "Does an optimal reboost frame schedule transfer to a nearby seed (e.g. speed ±5)?"
  answer: "No — the frame numbers shift with the seed (band drifts with speed/air). Stable across seeds: ~3 minimal 2-frame boosts near the peak per 200 fr. Re-solve per exact state."
  page: strategy/reboost.md
  source: thread-13

- id: reboost-cost
  question: "Why does each reboost cost a few frames of forward progress?"
  answer: "The full-deflection charge triggers an instant 180° turnaround snap (one ~dead frame + a reversed frame), the per-boost turnaround tax."
  page: strategy/reboost.md
  source: fresh-crosslink

- id: const-deadzone
  question: "What is the stick radial dead-zone constant?"
  answer: "15 raw units (removed before any input registers)."
  page: reference/constants.md
  source: fresh

- id: const-divisor
  question: "What is the main-stick divisor?"
  answer: "54 (mPosX = stickX/54 after dead-zone removal)."
  page: reference/constants.md
  source: fresh

- id: const-wraps
  question: "What are the animation wrap points for ESS (swimming) and neutral (swim-wait)?"
  answer: "End_swim (ANM_SWIMING) = 23; End_wait (ANM_SWIMWAIT) = 26."
  page: reference/constants.md
  source: fresh

- id: const-x598
  question: "What is x598 and where does it come from?"
  answer: "598 = End_wait · End_swim = 26·23; the neutral→ESS anim-scramble multiplier. 598 ≡ 0 (mod 23), so only the fractional entry phase matters — which is why it's hypersensitive."
  page: reference/glossary.md
  source: thread-5

- id: afdrag-formula
  question: "What is the head-bob (animation-frame) drag formula on true speed?"
  answer: "af_drag = 0.6·v + 0.4·v·|cM_scos(π·anim/23)| (then divided by 1 + 0.35·getSwimTimerRate). Near anim 0/23 keeps ~100%, near 11.5 keeps ~60%."
  page: reference/constants.md
  source: thread-17
```

## Fresh questions to add as more topics migrate (not pilot-scoped)

Kept here so they aren't lost: cosine-table ULP count (2964/4096), neutral decay below |v|=25
(cLib_addCalc snap), DTM rows-per-frame (8), mRate non-recomputability, off-axis residual cause
(stick table dump path). These belong to model/reference pages built during the full migration.
