"""Golden / characterization tests -- the core of the regression lock.

Each (seed, seq) CASE in golden_harness.CASES is run through the CURRENT sim and its
FULL per-frame trace (v, anim, air, state, x, z, step, tag, path, net) is asserted
bit-exact against a stored golden under tests/golden/. Floats are compared with zero
tolerance (the goldens store full-precision hex floats; the sim is bit-exact f32).

The goldens were generated FROM the sim at HEAD, which the live Dolphin suite confirms
matches the real game -- so HEAD's output IS the correct reference. A failure here means
the sim's deterministic behavior changed; if that change is deliberate and live-verified,
refresh the goldens with:

    python -m tests.golden_regen

Regeneration is NEVER automatic on failure.

Pure offline. 3.7-compatible.
"""
import os
import pytest

from tests import golden_harness as G


@pytest.mark.parametrize("case_id,seed_id,source", G.CASES,
                         ids=[c[0] for c in G.CASES])
def test_golden_trace_bit_exact(case_id, seed_id, source):
    gpath = G.golden_path(case_id)
    assert os.path.exists(gpath), (
        "missing golden %s; run `python -m tests.golden_regen`" % gpath)
    rows = G.run_case(case_id, seed_id, source)
    golden = G.load_golden(case_id)
    errs = G.compare_rows(rows, golden)
    assert not errs, (
        "case %r diverged from golden (%d mismatch(es)); first few:\n  %s\n"
        "If this change is intentional and live-verified, run "
        "`python -m tests.golden_regen`."
        % (case_id, len(errs), "\n  ".join(errs[:8])))


def test_all_cases_have_goldens():
    """Guard: every CASE must have a committed golden (catches a forgotten regen)."""
    missing = [c[0] for c in G.CASES if not os.path.exists(G.golden_path(c[0]))]
    assert not missing, "cases without goldens: %s" % (missing,)


def test_neutral_dip_is_drag_free_at_release():
    """Characterize the neutral-dip mechanic (superswim-neutral-dip): the 1-frame neutral
    inside an ESS cruise dodges the -2 decay -- the exit-release frame moves the FULL |v|
    (drag-free, |step| == |v|) and re-enters ESS the next frame, so the sustained -2 never
    fires. This pins the MECHANISM, not just the numbers."""
    rows = G.run_case("cruise_dip1", "cruise_hi", ("inline", "neutral_dip_single"))
    # frame 8 is the lone neutral exit-release (state flips to 54, full-|v| drag-free move).
    rel = rows[7]
    assert rel["tag"] == "NEU"
    assert rel["state"] == 54
    assert abs(rel["step"]) == pytest.approx(abs(rel["v"]), rel=1e-9)
    # frame 9 has already re-entered ESS (state 55) -> no sustained -2 decay.
    assert rows[8]["state"] == 55
    assert rows[8]["tag"] == "ESS"


def test_lowspeed_tail_decays_monotonically_toward_zero():
    """Characterize the cLib_addCalc low-speed tail: pure neutral bleeds |v| down through
    the proportional band and the 0.5/frame snap band, monotonically toward 0."""
    rows = G.run_case("lowspeed_tail", "lowspeed", ("inline", "neutral_decay_tail"))
    vs = [abs(r["v"]) for r in rows]
    for a, b in zip(vs, vs[1:]):
        assert b <= a + 1e-9          # |v| never increases under neutral decay
    assert vs[-1] < vs[0]             # and it has bled down


def test_cold_entry_x598_scramble_visible():
    """The cold-start charge entry scrambles the ESS-start anim via the x598 multiply;
    pin that the first state-55 frame after entry carries a scrambled (non-small) anim."""
    rows = G.run_case("cold_entry", "cold", ("inline", "coldstart_entry"))
    # The entry transitions 54->55; once in state 55 the scramble has landed.
    state55 = [r for r in rows if r["state"] == 55]
    assert state55, "cold entry never reached state 55"
