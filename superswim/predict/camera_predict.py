"""camera_predict.py — predict the camera yaw (csangle) per frame from the C-stick.

Empirical law (live-derived 2026-06-28, see knowledge/mechanics/camera.md), regime-independent
(static AND mid-swim): the C-stick X commands an angular VELOCITY omega_cmd; the actual
rate chases it with factor 0.5; the yaw integrates the rate; there is a 1-frame input lag.

    omega_t   = omega_{t-1} + (omega_cmd(csx) - omega_{t-1}) * 0.5
    cam_t     = (cam_{t-1} + round(omega_t)) & 0xFFFF        # s16 yaw, written by dCamera_c::Run
    (the csx that drives frame t is the one supplied on frame t-1 — 1-frame lag)

omega_cmd(csx): deadzone to |csx-128|<=21, steep ramp, saturates at +/-546 hw/frame
(=+/-3.0 deg/frame). Measured steady-state table below; symmetric about center 128.
substickY full-down (<~64) is the free-cam FREEZE used by straight superswims -> omega_cmd=0.
"""
from __future__ import annotations

HW = 65536           # halfword units per full turn (360 deg)
SAT = 546            # saturated rate, hw/frame (= 3.0 deg/frame)
DEADZONE = 21        # |csx-128| <= this -> no rotation

# measured steady-state omega for substickX deflections (csx-128 -> hw/frame), live.
_OMEGA_TABLE = [
    (0, 0), (21, 0), (22, 2), (26, 6), (30, 13), (32, 18), (34, 26),
    (38, 51), (42, 105), (46, 325), (48, SAT),
]


def omega_cmd(csx: int, csy: int = 128) -> float:
    """Target rotation rate (hw/frame) commanded by the C-stick. +csx (right) -> +yaw."""
    # free-cam freeze: holding C-stick down pins the camera (omega target 0).
    if csy <= 64:
        return 0.0
    d = csx - 128
    s = 1.0 if d >= 0 else -1.0
    a = abs(d)
    if a >= 48:
        return s * SAT
    # piecewise-linear interp on the measured table
    for i in range(1, len(_OMEGA_TABLE)):
        x0, y0 = _OMEGA_TABLE[i - 1]
        x1, y1 = _OMEGA_TABLE[i]
        if a <= x1:
            t = 0.0 if x1 == x0 else (a - x0) / (x1 - x0)
            return s * (y0 + t * (y1 - y0))
    return s * SAT


class CameraState:
    """Per-frame camera yaw predictor. cam in halfword (0..65535, == csangle)."""
    def __init__(self, cam: int = 49152):
        self._cam_f = float(int(cam) & 0xFFFF)   # float yaw accumulator (game keeps full
                                                 # precision; the s16 store is round(_cam_f))
        self.omega = 0.0
        self._pending_cmd = 0.0   # 1-frame input lag: this frame uses last frame's cmd

    @property
    def cam(self) -> int:
        return round(self._cam_f) & 0xFFFF

    def clone(self):
        c = CameraState.__new__(CameraState)
        c._cam_f = self._cam_f
        c.omega = self.omega
        c._pending_cmd = self._pending_cmd
        return c

    def step(self, csx: int, csy: int = 128) -> int:
        """Advance one frame; the C-stick (csx,csy) takes effect with a 1-frame lag.
        Returns the new cam (halfword)."""
        cmd = self._pending_cmd
        self.omega += (cmd - self.omega) * 0.5
        self._cam_f += self.omega
        self._pending_cmd = omega_cmd(csx, csy)
        return self.cam


# ----------------------------------------------------------------------------------
# Validation against a camera_capture.py CSV
# ----------------------------------------------------------------------------------
def _validate(csv_path):
    import csv
    rows = list(csv.DictReader(open(csv_path)))
    cam0 = int(rows[0]["csangle"])
    cs = CameraState(cam=cam0)
    worst = 0
    print(f"{'f':>3} {'csx':>4} {'cam_live':>9} {'cam_pred':>9} {'err':>5}")
    for r in rows[1:]:
        csx = int(r["csx"]) if r["csx"] != "" else 128
        csy = int(r["csy"]) if r["csy"] != "" else 128
        pred = cs.step(csx, csy)
        live = int(r["csangle"])
        err = ((pred - live + 0x8000) & 0xFFFF) - 0x8000   # signed hw error
        worst = max(worst, abs(err))
        f = int(r["f"])
        if f <= 8 or f % 5 == 0 or abs(err) > 2:
            print(f"{f:>3} {csx:>4} {live:>9} {pred:>9} {err:>5}")
    print(f"WORST |err| = {worst} hw ({worst*360/HW:.3f} deg) over {len(rows)-1} frames")
    return worst


if __name__ == "__main__":
    import sys
    _validate(sys.argv[1])
