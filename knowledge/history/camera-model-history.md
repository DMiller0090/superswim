# Camera steering model — empirical probe (2026-06-28)

> **status: historical** — research log / provenance, NOT current truth. The current camera
> steering law lives in [mechanics/camera.md](../mechanics/camera.md). This page is kept for the
> derivation, the live decomp watchpoint work, the omega-grid coarseness fix, and reproduce steps.

Goal: predict the camera yaw (`csangle`) frame-to-frame so it can be used as a **fine
lateral-steering lever** for superswims (ESS gives only coarse ~45° snap control; the
camera gives sub-degree control). The offline sim (`superswim_sim.py`) currently treats
`csangle` as a fixed constant (49152 / west) — this model is what would replace that.

Status: **probe-first complete.** The per-frame law is derived and live-confirmed, static
AND during a swim. Sim integration not yet done. F32-precision capture + full safe-envelope
sweep are the remaining validation steps (see "Open / next").

## Why the camera matters
Stick→world mapping is camera-relative:
```
world_travel_angle = stick_angle + csangle + 0x8000          (halfword, 0x10000 = 360°)
```
So rotating `csangle` by Δ rotates Link's entire travel axis by Δ. Live read:
`csangle` chain `0x803AD380 → +0x34 → +0x2B0` (u16). Named addr `csangle` in dolphin_mem.

## The per-frame law (live-derived, k = 0.5 exact)
The C-stick X commands an angular **velocity** (NOT a target angle). That velocity is
first-order smoothed with factor **0.5**, then integrated into the yaw. There is a **1-frame
input→camera lag** (an input applied on frame f first affects the yaw on f+1).

```
omega_t   = omega_{t-1} + (omega_cmd(substickX) - omega_{t-1}) * 0.5     # k = 0.5 (gaps halve)
csangle_t = csangle_{t-1} + omega_t
```

Evidence (full-right hold from slate 10, reading csangle each frame; deltas):
`272, 409, 478, 512, 529, 537, 542 → 546` — successive *gaps* 137,69,34,17,8,5 halve →
k=0.5; steady state +546 hw/frame = **exactly 3.0°/frame**. Full-left is symmetric.
Release to neutral: ω chases 0 with the same k=0.5 (`537→269→134→67→34→17`).

## omega_cmd(substickX): deadzone + steep ramp + saturation
Center = 128. Steady-state ω for a held deflection (slate 10, static Link):

| substickX | Δ from 128 | omega_cmd (hw/frame) | deg/frame |
|-----------|-----------|----------------------|-----------|
| ≤ 149     | ≤ 21      | 0  (deadzone)        | 0         |
| 150       | 22        | 2                    | 0.011     |
| 154       | 26        | 6                    | 0.033     |
| 158       | 30        | 13                   | 0.071     |
| 162       | 34        | 26                   | 0.143     |
| 166       | 38        | 51                   | 0.280     |
| 170       | 42        | 105                  | 0.577     |
| 174       | 46        | 325                  | 1.79      |
| ≥ 176     | ≥ 48      | 546 (saturated)      | 3.0       |

- **Wide deadzone** to sx≈149, then a steep ~doubling-every-4-units ramp, fully **saturated
  by sx≈176**. Half deflection (192) == full (255) exactly.
- **Fine-control band = sx ~150–170** (ω 2–105 hw/frame, 0.01–0.58°/frame). This is where
  deliberate steering lives. Curve shape ≈ a rational-bezier S-curve (per decomp; not yet
  pinned analytically — currently a lookup table).
- Negative side (sx<128) assumed symmetric (full-deflection symmetry confirmed; fine band
  not yet swept — TODO).

## Regime independence — holds DURING a swim
Placed Link at cruise (`potential_speed=-700, air=900`), applied ESS (`128,110`) + steer
`substickX=160`, substickY **neutral**:
- csangle deltas converged to **~18 hw/frame — identical to the static sx=160 measurement.**
  The rotation law is the same swimming as standing still.
- **No auto-camera flip** occurred at -700 with substickY neutral (the flip the
  "hold C-stick down" convention guards against did NOT trigger here — but verify across the
  full speed range / longer holds; see Open).
- Link's **facing (shape_angle.y) follows csangle** during ESS (with a lag) — rotating the
  camera also rotates Link's body/charge axis.
- `link_z` (the lateral axis here) went from flat to a growing drift as the camera rotated:
  the steering effect is real and measurable in world position.

## The steering primitive (live-confirmed)
Tap the C-stick for a few frames, then return it to neutral:
- 5-frame `sx=166` tap then neutral → csangle ramped +155 during the tap, coasted **+98 more**
  on release (the ω-decay tail), then **LOCKED at +253 hw = +1.39°. No snapback.**
- Link's facing locked; he continues on the rotated axis (steady lateral drift).
- So: **net axis rotation = ∫ω**, fully predictable from the law. The release tail adds
  ≈ (last ω) of extra rotation (Σ ω·0.5ⁿ). Choose tap magnitude × duration to dial in an
  arbitrary small heading offset — much finer than ESS's 45°-budget snaps.

## How this plugs into planning
- **Steering as a costed primitive**: "to move ΔZ laterally over the cruise, apply a tap of
  size X at frame F" — e.g. to reach an off-axis air-refill spot. Lateral displacement is the
  time-integral of speed·sin(Δheading); with the heading law above this is computable.
- **Sim integration**: replace the fixed `csangle` constant in `superswim_sim.py` with the
  evolving `(csangle, omega)` state driven by per-frame substickX. **Frozen-camera plans must
  stay bit-exact**: existing validated plans hold substickY=0 (freeze) ⇒ omega_cmd=0 ⇒
  csangle constant ⇒ zero regression. Gate on a run_tests baseline vs a live capture.

## Decomp grounding (JP/GZLJ01 symbols + live watchpoint, 2026-06-28)
From the JP/GZLJ01 `framework.map` (a local TWW decomp/extract):
- `dCamera_c::Run`            @ **0x80160260** (size 0x9e0) — per-frame camera update.
- `dCamera_c::CalcSubjectAngle(s16*,s16*)` @ **0x8016cf54** — computes subject yaw/pitch from stick.
- `dCamera_c::subjectCamera(long)` @ **0x8016d3a4** — subject (swim/free-look) mode.
- `dCamMath::rationalBezierRatio(f,f)` @ **0x800aca94** — the omega_cmd(substick) S-curve.

Live write-watch (`bp_camera.py`, bp_stick pattern) on the resolved yaw addr **0x80AD0010**
(= `[[0x803AD380]+0x34]+0x2B0` after slate 10) caught the writer:
```
MBP 80160a0c Write16 ffffc000 at 80ad0010   # 0xc000 = 49152
MBP 80160a0c Write16 ffffc110 ...            # = 49424, the full-right ramp
```
- **Writer PC 0x80160a0c is inside `dCamera_c::Run` (+0x7ac).** The yaw is a **Write16 = s16**,
  so our u16 `csangle` reads are the EXACT stored output (no hidden f32 on the output — the
  "f32 precision" concern applies only to the internal ω velocity, which is upstream in Run /
  CalcSubjectAngle). To pin ω-f32 + the literal k=0.5 and the cap: code-BP in Run/subjectCamera
  and read FPRs (event.on_codebreakpoint + registers.read_fpr; needs the non-pausing pattern).
- Tools: `bp_camera.py` (arm write-watch, resolves chain live), `bp_clear.py` (clear).
  DebugModeEnabled=True already set (persists); restart Dolphin to drop all memchecks.

## Resolved: the omega (camera-rate) grid was off by +1 (input-path corruption)

For arbitrary C-stick (csy != 128) `omega_cmd` is a 2-D lookup, not the csx-only table above.
The shipped grid `superswim/tables/omega_table_full.csv` (csx 0..15 x csy 0..255, the
deep-negative-X band) had been dumped via the in-Dolphin `controller.set_gc_buttons` (calibrated)
path. That path recorded the negative-saturation omega as **-546** where the raw-byte
`advancewith` path the swim/tests/DTM actually use gives **-547** — 1816 of 4096 cells off by +1
(a few edge cells off by more). `camera_arbitrary` loaded that grid LAST, so its -546 clobbered
the correctly-captured -547 in the fine `omega_table.csv`. This was the cam=1-2hw residual on the
random-camera charge cases (cap_randcharge / gen_charge).

Fix (2026-06-29): load the fine table last so it wins on overlap, and regenerate the full grid via
`advancewith` (`harness/capture/omega_full_redump.py`). The regenerated grid agrees with the
independently-captured fine table on 100% of overlap cells, and both charge cases go cam=0hw.

- **omega in this band is camera-STATE dependent by ±1.** A continuous neutral-settle sweep (no
  loadstate) drifts -547 → -546 as `cam_target`/`cam_yaw` accumulate; the value the swim
  experiences is the **from-rest** one. So the dump uses a fresh `loadstate 10` per cell (the
  gold method, ~1 s/cell under 3-way concurrency). Writing `cam_yaw`/`cam_target` back to rest in
  place is faster but the camera pointer chain goes null over a long run — use loadstate.
- **Parallelizable across Dolphin instances.** `dolphin_mem` is per-PID (pipe `DolphinControl-<pid>`,
  `attach()` resolves MEM1 from `DOLPHIN_PID`), so N instances dump disjoint csx ranges to shard
  CSVs concurrently (merge via `omega_full_redump.py merge shardN=...`). A savestate-load briefly
  tears the pipe down (CreateFileW error 2), so wrap pipe/mem calls in a retry.

## Open / next (to finish before trusting it for plans)
1. **F32 precision**: we read csangle as u16; the underlying yaw is a float. Capture the f32
   (and confirm k is exactly 0.5 = a >>1, ω_cmd_max exactly 3.0°) for bit-exact sim work.
2. **Analytic omega_cmd(substickX)**: map the table to the decomp normalization
   (rationalBezierRatio / the /54 stick scale) so it generalizes, vs the lookup table.
3. **Safe envelope**: find the auto-camera *flip* trigger (speed/hold-length) so steering
   stays in a non-flipping band. The "hold C-stick down" convention exists because of it.
4. **Negative fine band** symmetry sweep.
5. **Reusable probe script** (emu-thread Load script): drive a configurable C-stick pattern,
   log (substickX/Y, facing, csangle-f32, link_x/z) per frame to CSV — drop-free capture for
   (1)–(4) and for the bit-exact baseline.

## Reproduce
Slate 10 (csangle=49152 W, facing=16384 E, state 54). All probes:
`loadstate 10` → optional `writename potential_speed -700; writename air 900` →
`advancewith stickX=.. stickY=.. substickX=.. substickY=.. frames=1` loop, reading
`probe csangle,facing,link_x,link_z` each frame. (Pipe input is fine here — not dense
alternation, so the pt-21 jitter artifact doesn't apply.)
