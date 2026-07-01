"""test_stick_table_integrity.py — offline guard on superswim/tables/stick_angle_table.csv.

The table is a live gold capture (harness/capture/stick_grid_redump.py: settle+verify, 4-instance,
2026-07). Its predecessor was corrupt: a 1-frame-pipeline dump recorded ~2600 angle cells and the
whole stick_dist column from latency-lagged frames (worst: exact-diagonal cells like (160,160) read
24260 instead of 24576 — a real sim-vs-live facing desync). See knowledge/history.

This test locks the table's INTERNAL bit-consistency without needing Dolphin: by construction
(JUTGamePad::CStick::update) the recorded angle must equal (s16)(10430.379f * atan2f(x, -y)) of the
recorded stick vector — the exact relationship a latency-mismatched cell violates. Plus:
value == hypot(x,y) capped, stick_dist == value, and every exact-diagonal cell lands on the 45deg
grid. Bit-exact against the atan2f closed form (CSV stores x/y to 7 sig figs, so a 2-s16 slack
absorbs that rounding; a real latency mismatch is off by tens–thousands).
"""
import os, csv, math
import pytest

from superswim import sim as S

TABLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "superswim", "tables", "stick_angle_table.csv")
RAD2S = 10430.3779296875     # 0x8000/pi (the f32 constant 10430.379f)
TOL = 2                      # s16 slack for the CSV's 7-sig-fig x/y rounding


def _s16(v):
    return ((int(v) + 0x8000) & 0xFFFF) - 0x8000


def _s16diff(a, b):
    return abs(((a - b + 0x8000) & 0xFFFF) - 0x8000)


def _angle_from_xy(x, y):
    if y == 0.0:
        return 0x4000 if x > 0.0 else -0x4000
    return _s16(S.f32(RAD2S * S.f32(math.atan2(x, -y))))


@pytest.fixture(scope="module")
def rows():
    return list(csv.DictReader(open(TABLE)))


def test_table_complete(rows):
    assert len(rows) == 256 * 256, f"expected 65536 cells, got {len(rows)}"


def test_angle_consistent_with_stick_vector(rows):
    """No latency-mismatched cells: recorded angle == atan2f of recorded (x,y)."""
    bad = []
    for r in rows:
        x, y, ang = float(r["x"]), float(r["y"]), int(r["angle"])
        if x == 0.0 and y == 0.0:
            continue
        if _s16diff(ang, _angle_from_xy(x, y)) > TOL:
            bad.append((int(r["sx"]), int(r["sy"]), ang, _angle_from_xy(x, y)))
    assert not bad, f"{len(bad)} cells' angle disagrees with atan2f(x,-y): {bad[:15]}"


def test_magnitude_columns_consistent(rows):
    """value == hypot(x,y) capped at 1; stick_dist == value (mMainStickValue)."""
    bad_v = bad_sd = 0
    for r in rows:
        x, y, val, sd = float(r["x"]), float(r["y"]), float(r["value"]), float(r["stick_dist"])
        if abs(val - min(math.hypot(x, y), 1.0)) > 5e-4:
            bad_v += 1
        if abs(sd - val) > 5e-4:
            bad_sd += 1
    assert bad_v == 0, f"{bad_v} cells: value != hypot(x,y) capped"
    assert bad_sd == 0, f"{bad_sd} cells: stick_dist != value"


def test_exact_diagonals_on_45deg_grid(rows):
    """|x|==|y| cells must resolve to an exact multiple of 0x2000 (45 deg) — the tell-tale the old
    latency dump failed (e.g. (160,160) 24260 instead of 24576)."""
    bad = []
    for r in rows:
        x, y, ang = float(r["x"]), float(r["y"]), int(r["angle"])
        if x != 0.0 and y != 0.0 and abs(abs(x) - abs(y)) < 1e-6:
            if _s16diff(ang, round(ang / 0x2000) * 0x2000) > TOL:
                bad.append((int(r["sx"]), int(r["sy"]), ang))
    assert not bad, f"{len(bad)} exact-diagonal cells off the 45deg grid: {bad[:15]}"
