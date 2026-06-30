# Camera steering (csangle)

**Answers:** How does the camera yaw affect movement? What's the per-frame camera-rate law? How do
you steer finely with the C-stick? Is omega speed-dependent?
**Status:** validated (live RE + exact integer recurrence in `superswim/predict/camera_exact.py`).
F32-precision of the internal ω and the auto-flip envelope are open.
**Source:** live RE 2026-06-28; decomp symbols below. Research log: [history/camera-predict-history](../history/camera-predict-history.md).

---

## Why the camera matters

The stick is camera-relative, so rotating the camera rotates Link's entire travel axis:

```
world_travel_angle = stick_angle + csangle + 0x8000          (halfword, 0x10000 = 360°)
```

`csangle` is the camera yaw. It is a **fine lateral-steering lever** — [ESS](ess.md) gives only
coarse ~45° [snap](turnaround.md) control; the camera gives sub-degree control. Live chain:
`0x803AD380 → +0x34 → +0x2B0` (u16); named `csangle` in `dolphin_mem`.

## The per-frame law (k = 0.5)

The C-stick X commands an angular **velocity** (not a target angle), first-order smoothed with
factor **0.5**, integrated into the yaw, with a **1-frame input→camera lag**:

```
omega_t   = omega_{t-1} + (omega_cmd(substickX) − omega_{t-1}) · 0.5
csangle_t = csangle_{t-1} + omega_t
```

Steady state for a full deflection = **±3.0°/frame** (±546 hw). Evidence (full-right hold, successive
gaps halve → k = 0.5): `272, 409, 478, 512, 529, 537, 542 → 546`.

### Exact integer recurrence (bit-exact)

`camera_exact.py` models the stored s16 yaw exactly (the smoothing above is the float view of this):

```
target += omega_cmd(csx, csy)            # 1-frame input lag
yaw    += int((s16)(target − yaw) / 2)   # C integer divide, truncates toward 0
csangle = (yaw + 0x8000) & 0xFFFF
```
- `omega_cmd` is a **live 65536-cell lookup** of (csx, csy), **speed-independent** (verified). The
  integer truncating divide reproduces both the build ramp and the release tail — a `round(omega)`
  model cannot.
- **Rest state:** with neutral C-stick, `target == yaw − 1` (a fixed −1 offset holds yaw still, since
  `int(−1/2) == 0`).
- `omega_cmd` is **asymmetric**: deadzone `+d ≤ 20` / `−d ≤ 19` → 0; saturation `csx ≥ 175 → +546`,
  `csx ≤ 81 → −547` (= ±3.0°/frame, |d| ≥ 47). E.g. csx 160 (+32) → +18 but csx 96 (−32) → −19.

## omega_cmd(substickX) — the steering band

| substickX | Δ from 128 | omega_cmd (hw/fr) | deg/fr |
|-----------|-----------|-------------------|--------|
| ≤ 149 | ≤ 21 | 0 (deadzone) | 0 |
| 154 | 26 | 6 | 0.033 |
| 162 | 34 | 26 | 0.143 |
| 170 | 42 | 105 | 0.577 |
| ≥ 176 | ≥ 48 | 546 (saturated) | 3.0 |

**Fine-control band = substickX ~150–170** (0.01–0.58°/frame) — where deliberate steering lives.
Wide deadzone to ~149, then a steep ~doubling-every-4-units ramp, fully saturated by ~176.

## The steering primitive

Tap the C-stick a few frames, then return to neutral: net axis rotation = **∫ω**, and there is **no
snapback** — Link locks onto the rotated axis and continues with steady lateral drift. The release
tail adds ≈ (last ω) of extra rotation (Σ ω·0.5ⁿ). A 5-frame `sx=166` tap then neutral → +253 hw =
+1.39°, locked. This holds *during* a swim (rotation law identical standing or moving); Link's
facing follows csangle with a lag.

## Plugging into planning

To move ΔZ laterally over a cruise, apply a tap of size X at frame F; lateral displacement is the
time-integral of `speed·sin(Δheading)`. **Frozen-camera plans stay bit-exact**: they hold
substickY = 0 (freeze) ⇒ omega_cmd = 0 ⇒ csangle constant ⇒ zero regression. The sim hard-codes
`csangle` constant today; replacing it with the evolving `(csangle, omega)` state is gated on a live
baseline.

## Decomp grounding (JP/GZLJ01)

`dCamera_c::Run` @ 0x80160260 (writer at +0x7ac, a Write16 = s16 — our u16 reads are exact);
`dCamera_c::CalcSubjectAngle` @ 0x8016cf54; `dCamera_c::subjectCamera` @ 0x8016d3a4;
`dCamMath::rationalBezierRatio` @ 0x800aca94 (the omega_cmd S-curve, Nonmatching in the decomp — hence
RE'd live, not decompiled). Full address list: [reference/addresses](../reference/addresses.md).

## Open

- **F32 precision** of the internal ω velocity (we read the s16 *output* exactly; ω is upstream).
- **Auto-flip envelope** — the speed/hold-length that triggers the auto-camera flip (the "hold
  C-stick down" convention guards against it); steering must stay in a non-flipping band.
- Negative fine-band symmetry sweep.

See [history/camera-predict-history](../history/camera-predict-history.md) for the full RE log and
the omega-grid coarseness fix.

## See also

- [Turnaround](turnaround.md) (`m34E8 = stick_angle + 0x8000 + csangle`) · [Arrow](arrow.md)
  (`move_bearing = camAngle − facing`) · [model/predictors](../model/predictors.md).
