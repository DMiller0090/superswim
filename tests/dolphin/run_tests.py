"""Regression suite for the Dolphin superswim runner + physics sim.

Replays each baseline action sequence LIVE via `advanceseq` (race-free, ONE pipe
call per test) from the slot-10 cold start, then compares the FINAL game state
(potential_speed, anim_frame, air, link_state) against a `superswim_sim.SwimState`
seeded identically. One compact line per test, no per-frame dump -> token-cheap.

Why end-state and not per-frame: the game is deterministic, so any per-frame
physics regression propagates into the final speed/anim. A single advanceseq is
race-free (DOLPHIN_CONTROL.md), unlike a per-frame advancewith loop which can drop
inputs under dense charge density. To locate WHERE a failing test diverges, fall
back to verify_state.py (it prints the per-frame table around the first mismatch).

Requires Dolphin running with twwgz.iso booted. The cold-start slate is the vendored
fixtures/savestate/superswim_coldstart_slate.s10, loaded by PATH via the pipe's `loadfile`
(no dependence on Dolphin's own StateSaves / slot 10). See DOLPHIN_CONTROL.md.

Usage:
  python run_tests.py                      # full suite (loads the vendored slate)
  python run_tests.py quick=1              # skip the long 200k target
  python run_tests.py only=pump_seq.txt    # one seq
  python run_tests.py tol=0.02 slot=10     # override: load Dolphin save slot 10 instead

Exit code 0 iff every non-xfail baseline matches (xfail mismatches don't fail the run).
"""
import struct, math
import os, sys  # >>> repo bootstrap: locate superswim/ package + ../tools/ (dolphin_mem)
_rb = os.path.dirname(os.path.abspath(__file__))
while _rb != os.path.dirname(_rb) and not os.path.exists(os.path.join(_rb, 'pyproject.toml')):
    _rb = os.path.dirname(_rb)
if _rb not in sys.path: sys.path.insert(0, _rb)
_tb = os.path.join(os.path.dirname(_rb), 'tools')
if _tb not in sys.path: sys.path.append(_tb)
import dolphin_mem as D
from superswim import sim as S
from superswim.coldstart import ColdStartSwimState
from superswim.actions import expand, acts_to_seq, animdiff
from harness.live import wnamed

FIXTURES = os.path.join(_rb, 'fixtures')  # code-referenced baseline seqs live here
# Cold-start slate, loaded BY PATH via `loadfile`. It dumps copyrighted game RAM so is NOT shipped:
# set TWWGZ_SLATE to your own slate file, or pass slot=<n>. See tests/dolphin/README.
SLATE = os.environ.get('TWWGZ_SLATE',
                       os.path.join(FIXTURES, 'savestate', 'superswim_coldstart_slate.s10'))

# (seqfile, label, xfail, note). xfail = currently-known-broken target, not a regression.
# A bug-fixture xfail flips to PASS when its bug is fixed -- that IS the fix's gate.
SUITE = [
    ("plan3k_exact_seq.txt",   "cold-start 3k", False, ""),
    ("pump_seq.txt",           "4-pump",        False, ""),
    ("pump_seq8.txt",          "8-pump",        False, ""),
    ("plan200k_seq.txt",       "200k target",   True,
     "swim v/air/state bit-exact; residual = post-death anim tail"),
    # BUG #1: v crosses 0 (forward swim) -> sim adds full ess_decay 0.1667, live runs
    # setNormalSpeedF target-chase (~0.1). Diverges at f40 (v>0). Fix in step() state-55 gain.
    ("test_lowspeed_seq.txt",  "bug1 v>=0 tail", True,
     "v>=0 forward-swim gain (setNormalSpeedF chase)"),
    # BUG #2: advanceseq gives a FALSE pass here (sim -65 matches the jittery pipe; clean DTM
    # truth is v=-775). NOT fixed -- validate via run_dtm. See history/open-questions.md#bug2.
    ("test_pumptrans_seq.txt", "bug2 neu-pump", True,
     "FALSE advanceseq pass; clean DTM v=-775 vs sim -65 -- still broken, validate via run_dtm"),
    # BUG #3 (FIXED 2026-06-30): partial hold mid-charge; uniform swim-gain lag (sim.py step()).
    # Baseline guard now. See history/resolved-bugs.md#bug3.
    ("partial_hold77_seq.txt",  "bug3 partial hold", False,
     ""),
]

# expand / acts_to_seq / animdiff now live in superswim.actions; wnamed in harness.live
# (both imported above) so the ~30 scripts that reused them no longer depend on this harness.


def run_one(seqfile, slot, tol):
    """Replay seqfile live + sim, compare final state. Returns a result dict.
    Loads the vendored slate by path, or a Dolphin save slot if `slot` is not None."""
    path = seqfile if os.path.exists(seqfile) else os.path.join(FIXTURES, seqfile)
    acts = expand(open(path).read())
    seq = acts_to_seq(acts)

    load = {"action": "load", "slot": slot} if slot is not None else {"action": "load", "path": SLATE}
    D.control_pipe_quiet("savestate", load)
    h, m = D.attach()
    D.control_pipe_quiet("advancewith", {"stickX": 128, "stickY": 128,
                                         "substickY": 0, "frames": 1})
    h, m = D.attach()
    wnamed(h, m, "air", 900); wnamed(h, m, "potential_speed", 0.0)
    v0 = D.read_named(h, m, "potential_speed"); anim0 = D.read_named(h, m, "anim_frame")
    air0 = D.read_named(h, m, "air"); st0 = D.read_named(h, m, "link_state")
    mr0 = D.read_named(h, m, "move0_mrate")  # LOGGED controller rate -> bit-exact cold start

    # Seed the cold-start scramble from the LIVE-LOGGED seed mRate, not the slate-phase-wrong
    # f32(anim+1.0) the base SwimState assumes. The cold-start x598 scramble amplifies a sub-ULP
    # oldframe error ~600x, so anim-only seeding fails the v/anim compare at any slate whose
    # controller phase isn't the canonical 0.0639 (see superswim-554-resolved). ColdStartSwimState
    # corrects ONLY the cold-start oldframe; all other physics are inherited verbatim.
    sim = ColdStartSwimState(v=v0, anim=anim0, air=air0, mrate=mr0); sim.state = st0
    sim._entry_tax = False
    for a in acts:
        sim.step(a)

    D.control_pipe_quiet("advanceseq", {"port": 0, "seq": seq})
    vl = D.read_named(h, m, "potential_speed"); anl = D.read_named(h, m, "anim_frame")
    airl = D.read_named(h, m, "air"); stl = D.read_named(h, m, "link_state")

    cyc = 26.0 if stl == 54 else 23.0
    dv = vl - sim.v
    dan = animdiff(anl, sim.anim, cyc)
    air_ok = (airl == sim.air)
    passed = abs(dv) <= tol and dan <= tol and stl == sim.state and air_ok
    return {
        "frames": len(acts), "passed": passed, "air_ok": air_ok,
        "vl": vl, "vs": sim.v, "dv": dv, "anl": anl, "ans": sim.anim, "dan": dan,
        "airl": airl, "airs": sim.air, "stl": stl, "sts": sim.state,
    }


def main():
    opts = {}
    for tok in sys.argv[1:]:
        k, _, v = tok.partition('='); opts[k] = v
    slot = int(opts['slot']) if 'slot' in opts else None  # None => load the slate by path
    tol = float(opts.get('tol', '0.02'))
    only = opts.get('only')
    quick = opts.get('quick') in ('1', 'true', 'yes')

    suite = [t for t in SUITE if (only is None or t[0] == only)
             and not (quick and t[2])]
    if not suite:
        print(f"no matching tests (only={only!r})"); sys.exit(2)
    if slot is None and not os.path.exists(SLATE):
        print(f"slate not found: {SLATE}\n"
              "The cold-start slate is not shipped (it dumps copyrighted game RAM). Set TWWGZ_SLATE "
              "to your own slate file, or pass slot=<n> to load a Dolphin save slot.")
        sys.exit(2)

    src = f"slot {slot}" if slot is not None else os.path.basename(SLATE)
    print(f"SUPERSWIM RUNNER REGRESSION  ({src}, tol {tol})")
    n_pass = n_fail = n_xfail = 0
    for seqfile, label, xfail, note in suite:
        try:
            r = run_one(seqfile, slot, tol)
        except Exception as e:
            print(f"ERROR {label:<14} {seqfile}: {e}"); n_fail += 1; continue
        f = r["frames"]
        if r["passed"]:
            tag = "PASS "; n_pass += 1
            print(f"{tag} {label:<14} {f:>4}f  v={r['vl']:.2f} "
                  f"anim={r['anl']:.2f} air={r['airl']} st={r['stl']}")
        elif xfail:
            tag = "XFAIL"; n_xfail += 1
            print(f"{tag} {label:<14} {f:>4}f  dv={r['dv']:+.3f} dan={r['dan']:.3f} "
                  f"air {r['airl']}/{r['airs']} st {r['stl']}/{r['sts']}  ({note})")
        else:
            tag = "FAIL "; n_fail += 1
            hint = "" if r["air_ok"] else " [air desync = dropped frame; re-run]"
            print(f"{tag} {label:<14} {f:>4}f  dv={r['dv']:+.3f} dan={r['dan']:.3f} "
                  f"air {r['airl']}/{r['airs']} st {r['stl']}/{r['sts']}{hint}")
            print(f"      -> locate: python verify_state.py seq={seqfile}")
    D.control_pipe_quiet("clearinput")

    base = n_pass + n_fail
    print(f"---\n{n_pass}/{base} baselines pass"
          + (f"; {n_xfail} xfail" if n_xfail else ""))
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
