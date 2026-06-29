"""stick_angle.py - EXACT mMainStickAngle(sx,sy) (s16) for the superswim predictor.

The game's main-stick -> angle is NOT a simple atan2 + per-axis dead-zone (that closed form,
superswim_sim.stick_angle_deg, is only good to ~0.86deg / 156 s16 because the game applies the
GC radial gate normalization). The exact angle is sampled live and cached in
stick_angle_table.csv (see stick_angle_capture.py); the shipped INPUT_DUMP_MAIN.csv is a
sparse cross-check (matches the live captures with 0 error).

angle_s16(sx,sy) returns the exact s16 angle from the cache, or None for a neutral stick.
If a stick is NOT cached it raises KeyError -- run stick_angle_capture.py on the capture first
(so a missing cell is loud, never silently approximated). This is the `stickAngle` term in
    m34E8 = stickAngle + 0x8000 + camAngle.
"""
from __future__ import annotations
import os, csv
from .. import sim as S

_HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tables")
# Complete live grid (all 65536 cells) of the game's MAIN_STICK_ANGLE (0x80398314), dumped via
# tww-python-scripts/stick_angle_grid_dump.py — the authoritative mMainStickAngle for any (sx,sy).
_TABLE_PATH = os.path.join(_HERE, "stick_angle_table.csv")
# NOTE: this grid also carries a live `stick_dist` magnitude column, currently UNUSED — it disagrees
# with the closed-form S.stick_dist off-axis (e.g. (200,60): live 1.0 vs 0.69); wiring it in is TODO.

_TABLE: dict[tuple[int, int], int] = {}
if os.path.exists(_TABLE_PATH):
    for _r in csv.DictReader(open(_TABLE_PATH)):
        _TABLE[(int(_r["sx"]), int(_r["sy"]))] = int(_r["angle"]) & 0xFFFF

_COMPLETE = len(_TABLE) >= 256 * 256


def is_neutral(sx: int, sy: int) -> bool:
    """A stick reads as neutral (no swim input) exactly when the closed-form dead-zone kills
    both axes -- same gate the game uses to decide 'stick deflected'."""
    return S.stick_angle_deg(sx, sy) is None


def angle_s16(sx: int, sy: int) -> int | None:
    """Exact s16 stick angle, or None for neutral. Resolution order:
      1. neutral gate (closed-form dead-zone) -> None (no swim input this frame);
      2. the COMPLETE live grid (stick_angle_table.csv): exact for every (sx,sy);
      3. for an ON-AXIS stick (sx == 128) the closed form is exact (covers anything the grid
         might somehow lack);
      4. otherwise KeyError -- never silently approximated."""
    sx, sy = int(sx), int(sy)
    if is_neutral(sx, sy):
        return None
    if (sx, sy) in _TABLE:
        return _TABLE[(sx, sy)]
    if sx == 128:                                   # on-axis: closed form is exact
        return S.deg_to_s16(S.stick_angle_deg(sx, sy))
    raise KeyError(f"stick ({sx},{sy}) missing (table complete={_COMPLETE}); "
                   f"re-run tww-python-scripts/stick_angle_grid_dump.py to rebuild the full grid")


def has(sx: int, sy: int) -> bool:
    return (int(sx), int(sy)) in _TABLE
