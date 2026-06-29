"""analyze_tables.py - validate/characterize the full omega + stick-angle grid dumps.

Checks structure (coverage, deadzone, saturation, symmetry) and cross-checks the full dumps
against the prior captured tables (which were the trusted live ground truth) so we KNOW the
full dump is bit-exact before wiring it into the predictor.
"""
import csv, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path, vk):
    t = {}
    if not os.path.exists(path):
        return t
    for r in csv.DictReader(open(path)):
        keys = list(r.keys())
        kx, ky = keys[0], keys[1]
        t[(int(r[kx]), int(r[ky]))] = int(r[vk])
    return t


def s16(x):
    x &= 0xFFFF
    return x - 0x10000 if x >= 0x8000 else x


def analyze_omega():
    full = load(os.path.join(HERE, "omega_table_full.csv"), "omega")
    old = load(os.path.join(HERE, "omega_table.csv"), "omega")
    print(f"=== OMEGA ===")
    print(f"full cells: {len(full)} / 65536")
    missing = [(x, y) for x in range(256) for y in range(256) if (x, y) not in full]
    print(f"missing: {len(missing)}", missing[:10])
    vals = set(full.values())
    print(f"distinct omega: {len(vals)}  min {min(vals)} max {max(vals)}")
    # cross-check vs old captured table
    diff = [(k, old[k], full[k]) for k in old if k in full and old[k] != full[k]]
    print(f"old-table cells: {len(old)}; disagree with full: {len(diff)}")
    for k, a, b in diff[:10]:
        print(f"   {k}: old {a} full {b}")
    # deadzone: omega==0 region
    dz = [k for k, v in full.items() if v == 0]
    if dz:
        xs = sorted(set(x for x, y in dz)); ys = sorted(set(y for x, y in dz))
        print(f"omega==0 cells: {len(dz)}  csx in [{min(xs)},{max(xs)}] csy in [{min(ys)},{max(ys)}]")
    # saturation
    sp = sum(1 for v in full.values() if v == 546)
    sn = sum(1 for v in full.values() if v == 547 or v == -547)
    print(f"omega==+546: {sum(1 for v in full.values() if v==546)}  omega==-547: {sum(1 for v in full.values() if v==-547)}")
    # left/right symmetry: omega(csx,csy) vs -omega(255-csx, csy)?  try (256-csx)
    for mir in (255, 256):
        bad = 0; n = 0
        for (x, y), v in full.items():
            mx = mir - x
            if 0 <= mx <= 255 and (mx, y) in full:
                n += 1
                if full[(mx, y)] != -v:
                    bad += 1
        if n:
            print(f"csx mirror {mir}-csx -> -omega: {bad}/{n} violate (0 = perfect antisymmetry)")


def analyze_stick():
    full = load(os.path.join(HERE, "stick_angle_full.csv"), "angle")
    cap = load(os.path.join(HERE, "stick_angle_table.csv"), "angle")
    dump = {}
    p = os.path.join(HERE, "tww-python-scripts", "ww", "data", "INPUT_DUMP_MAIN.csv")
    for r in csv.DictReader(open(p)):
        dump[(int(r["input x"]), int(r["input y"]))] = int(r["angle"]) & 0xFFFF
    print(f"\n=== STICK ANGLE ===")
    print(f"full cells: {len(full)} / 65536")
    missing = [(x, y) for x in range(256) for y in range(256) if (x, y) not in full]
    print(f"missing: {len(missing)}", missing[:10])
    # cross-check vs captured ground truth
    diff = [(k, cap[k], full[k]) for k in cap if k in full and (cap[k] & 0xFFFF) != (full[k] & 0xFFFF)]
    print(f"captured cells: {len(cap)}; disagree with full: {len(diff)}")
    for k, a, b in diff[:10]:
        print(f"   {k}: captured {a} full {b} (d={s16(b-a)})")
    # cross-check vs INPUT_DUMP
    dd = [(k, dump[k], full[k]) for k in dump if k in full and dump[k] != (full[k] & 0xFFFF)]
    print(f"INPUT_DUMP cells: {len(dump)}; disagree with full: {len(dd)} (these were the overfit risk)")
    worst = max((abs(s16(full[k] - dump[k])), k) for k in dump if k in full)
    print(f"   worst INPUT_DUMP disagreement: {worst[0]} s16 at {worst[1]}")


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "both"
    if what in ("omega", "both"):
        analyze_omega()
    if what in ("stick", "both"):
        analyze_stick()
