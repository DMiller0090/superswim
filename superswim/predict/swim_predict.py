"""swim_predict.py — validate the POSITION (world x/z) prediction during a swim.

Direction law (live-derived 2026-06-28): the per-frame world move bearing, measured as
atan2(dx, dz), tracks the camera yaw csangle (+ a main-stick-relative offset, ~0 for ESS)
and is INDEPENDENT of Link's facing. So:

    heading_deg = csangle_deg + stick_offset(main stick)
    dx = mag * sin(heading);  dz = mag * cos(heading)

where mag is the per-frame displacement magnitude (the existing bit-exact swim physics,
|v|*(0.6+0.4|cos(pi*anim/23)|)). This script isolates the DIRECTION law by integrating the
LIVE per-frame magnitude along the PREDICTED camera heading and comparing to live x/z.

Usage: python swim_predict.py <capture.csv> [offset_deg=0]
"""
from __future__ import annotations
import sys, csv, math
from .camera_predict import CameraState, HW
from ..sim import SwimState


def hw_to_deg(hw):
    return hw * 360.0 / HW


def stick_to_action(sx, sy):
    """Map a raw main-stick (sx, sy) to a SwimState action token."""
    if sx == 128 and sy == 128:
        return 'neu'
    if sx == 128 and sy in (0, 255):
        return 'chg'
    if sy < 128:                      # down-ish = ESS (rawY = sy); 110 is the canonical ESS
        return 'ess' if sy == 110 else f'ess:{sy}'
    return 'ess'


def stick_offset_deg(sx, sy):
    """World move-bearing offset (deg) relative to the camera, set by the main stick.
    For ESS/neutral cruise this is ~0 (heading == camera). Charge up/down differ by 180
    (handled by SwimState's own facing flips for magnitude; the heading sign for charge
    is not yet calibrated here -- cruise/steer only)."""
    return 0.0


def predict_full(frames, v0, anim0, air0, cam0, entry_tax=True):
    """Predict per-frame (cam, x, z, v, anim, air, state) from raw (sx,sy,csx,csy) inputs
    alone. Physics from SwimState (bit-exact), camera from CameraState, heading = the
    START-of-frame camera (1-frame lag), magnitude = |SwimState step|."""
    s = SwimState(v=v0, anim=anim0, air=air0)
    s._entry_tax = entry_tax
    cs = CameraState(cam=cam0)
    x = z = 0.0
    out = []
    for (sx, sy, csx, csy) in frames:
        cam_start = cs.cam                       # cam[f-1] drives this frame's heading
        d, tag = s.step(stick_to_action(sx, sy))
        cs.step(csx, csy)
        hdg = math.radians(hw_to_deg(cam_start) + stick_offset_deg(sx, sy))
        mag = abs(d)
        x += mag * math.sin(hdg)
        z += mag * math.cos(hdg)
        out.append({"cam": cs.cam, "x": x, "z": z, "v": s.v, "anim": s.anim,
                    "air": s.air, "state": s.state, "tag": tag})
    return out


def validate_full(csv_path):
    """End-to-end: seed from the capture's frame 0, predict from inputs only, compare."""
    rows = list(csv.DictReader(open(csv_path)))
    f0 = rows[0]
    frames = [(int(r["sx"]), int(r["sy"]), int(r["csx"]), int(r["csy"])) for r in rows[1:]]
    pred = predict_full(frames, v0=float(f0["potential_speed"]),
                        anim0=float(f0["anim_frame"]), air0=int(f0["air"]),
                        cam0=int(f0["csangle"]))
    x0, z0 = float(f0["link_x"]), float(f0["link_z"])
    wv = wa = wpos = wcam = 0.0
    print(f"{'f':>3} {'v_err':>7} {'anim_err':>8} {'cam_err':>7} {'pos_err':>8}")
    for r, p in zip(rows[1:], pred):
        ve = p["v"] - float(r["potential_speed"])
        ae = p["anim"] - float(r["anim_frame"])
        ce = ((p["cam"] - int(r["csangle"]) + 0x8000) & 0xFFFF) - 0x8000
        xe = (x0 + p["x"]) - float(r["link_x"])
        ze = (z0 + p["z"]) - float(r["link_z"])
        pe = math.hypot(xe, ze)
        wv, wa, wcam, wpos = max(wv, abs(ve)), max(wa, abs(ae)), max(wcam, abs(ce)), max(wpos, pe)
        f = int(r["f"])
        if f <= 3 or f % 5 == 0:
            print(f"{f:>3} {ve:>7.3f} {ae:>8.4f} {ce:>7} {pe:>8.2f}")
    travel = math.hypot(float(rows[-1]["link_x"]) - x0, float(rows[-1]["link_z"]) - z0)
    print(f"WORST  v={wv:.3f}  anim={wa:.4f}  cam={wcam}hw  pos={wpos:.2f} "
          f"({100*wpos/max(travel,1):.3f}% of {travel:.0f} travel)")
    return wv, wa, wcam, wpos


def validate_position(csv_path, stick_offset_deg=0.0, use_live_cam=False):
    rows = list(csv.DictReader(open(csv_path)))
    cam0 = int(rows[0]["csangle"])
    cs = CameraState(cam=cam0)
    x = float(rows[0]["link_x"]); z = float(rows[0]["link_z"])
    x0, z0 = x, z
    worst_pos = 0.0
    worst_hdg = 0.0
    prev_live_cam = cam0
    print(f"{'f':>3} {'hdg_live':>8} {'hdg_pred':>8} {'dErr':>5} "
          f"{'x_err':>7} {'z_err':>7} {'net_err':>7}")
    for r in rows[1:]:
        csx = int(r["csx"]) if r["csx"] != "" else 128
        csy = int(r["csy"]) if r["csy"] != "" else 128
        # Link moves using the START-of-frame camera (= last frame's cam): a 1-frame lag
        # between the camera yaw and the movement direction (live-pinned: hdg[f]==cam[f-1]).
        cam_pred = prev_live_cam if use_live_cam else cs.cam
        cs.step(csx, csy)
        prev_live_cam = int(r["csangle"])
        dx_live = float(r["dx"]); dz_live = float(r["dz"])
        mag = math.hypot(dx_live, dz_live)
        hdg = math.radians(hw_to_deg(cam_pred) + stick_offset_deg)
        x += mag * math.sin(hdg)
        z += mag * math.cos(hdg)
        x_live = float(r["link_x"]); z_live = float(r["link_z"])
        xe, ze = x - x_live, z - z_live
        net_err = math.hypot(xe, ze)
        worst_pos = max(worst_pos, net_err)
        hdg_live = math.degrees(math.atan2(dx_live, dz_live)) % 360.0 if mag > 1e-6 else 0.0
        hdg_pred = (hw_to_deg(cam_pred) + stick_offset_deg) % 360.0
        derr = ((hdg_pred - hdg_live + 180) % 360) - 180
        if mag > 1.0:
            worst_hdg = max(worst_hdg, abs(derr))
        f = int(r["f"])
        if f <= 4 or f % 5 == 0:
            print(f"{f:>3} {hdg_live:>8.3f} {hdg_pred:>8.3f} {derr:>5.2f} "
                  f"{xe:>7.2f} {ze:>7.2f} {net_err:>7.2f}")
    travel = math.hypot(x_live - x0, z_live - z0)
    print(f"WORST pos_err = {worst_pos:.2f} units over {len(rows)-1} frames "
          f"(net travel {travel:.0f}; {100*worst_pos/max(travel,1):.3f}% of travel)")
    print(f"WORST heading_err = {worst_hdg:.3f} deg (frames with mag>1)")
    return worst_pos, worst_hdg


if __name__ == "__main__":
    if "full" in sys.argv[2:]:
        validate_full(sys.argv[1])
    else:
        off = 0.0
        live = False
        for a in sys.argv[2:]:
            if a.startswith("offset_deg="):
                off = float(a.split("=")[1])
            if a == "livecam":
                live = True
        validate_position(sys.argv[1], off, use_live_cam=live)
