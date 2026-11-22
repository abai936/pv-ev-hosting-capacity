"""Stage 7 tests: LE mask vs an independent timestamp list, EV as Load == negative Generator, 32.2 A hand check,
2-day year energy balance with EVs, EV current on the right phase.

NOTE on test_hand_check_32A_and_drop_within_3pct: it checks the (2R1+R0)/3 loop-resistance model against the OpenDSS
solve. The prediction uses model.path_r, the same path resistance the model code uses for placement, so it is
independent of the load-flow solve but not of that helper."""
from pathlib import Path

import numpy as np
import opendssdirect as dss
import pandas as pd
import pytest

from hc import ev_hosting as E, hosting as h, profiles as P, yearly as Y

ROOT = Path(__file__).resolve().parents[1]


def test_le_mask_picks_exactly_the_independent_timestamp_list():
    idx = P.time_index_utc()
    expect = []
    for d in pd.date_range("2022-01-01", "2022-12-31", freq="D"):
        if d.month in (6, 7, 8) and d.day_of_week < 5:
            for hh, mm in ((19, 0), (19, 30), (20, 0), (20, 30)):
                expect.append(pd.Timestamp(d.year, d.month, d.day, hh, mm, tz=P.LOCAL_TZ).tz_convert("UTC"))
    got = idx[E.winter_evening_mask(idx)]
    assert list(got) == sorted(expect)
    assert len(expect) == 66 * 4                      # 22 + 21 + 23 weekdays in Jun, Jul, Aug 2022 (hand count)
    assert pd.Timestamp("2022-07-06 07:00", tz="UTC") in set(got)   # local Wed 6 Jul 19:00 NZST = 07:00 UTC


def test_le_median_hand_value():
    idx = pd.date_range("2022-07-04", periods=48 * 7, freq="30min", tz="UTC")
    mask = E.winter_evening_mask(idx)
    x = np.full((len(idx), 1), 99.0)
    pos = np.flatnonzero(mask)
    x[pos, 0] = 2.0
    x[pos[:3], 0] = [1, 50, 60]
    kw, n = E.le_kw(x, idx)
    assert n == len(pos) and n >= 8 and kw[0] == 2.0


def test_ev_as_load_equals_negative_generator():
    m = h.Model(1.0, True)
    k = int(np.argmax(m.path_r))
    m.set_case("L0", [k])
    m.solve(-7.4)
    v_gen = np.array(dss.Circuit.AllBusVMag())
    m.set_case("L0", [])                               # generator off, same circuit
    E.add_ev_load("EVTEST", m.nodes[k], 7.4)
    dss.Solution.Solve()
    v_load = np.array(dss.Circuit.AllBusVMag())
    assert np.max(np.abs(v_gen - v_load)) < 1e-3       # volts


def test_hand_check_32A_and_drop_within_3pct():
    pred, sim, _name, _n, i_nom = E.hand_check()
    assert i_nom == pytest.approx(32.17, abs=0.01)     # 7400 W / 230 V
    assert abs(sim - pred) / pred < 0.03


def test_ev_hc_baseline_prefix_and_per_phase_sum():
    m = h.Model(1.0, True)
    m.cases["LE"] = {n: 0.0 for n in m.loads}
    r = E.find_ev_hc(m, E.order_p2(m))
    assert not r["binding_limit"].startswith("baseline")
    assert sum(r["per_phase"]) == r["hc"]
    m.cases["LE"] = {n: 400.0 for n in m.loads}        # absurd load: baseline already violates
    r = E.find_ev_hc(m, E.order_p2(m))
    assert r["hc"] == 0 and r["binding_limit"].startswith("baseline-")


def test_year_energy_balance_with_ev_2_days():
    hk, pv, _ = Y.load_year_inputs()
    ev = np.load(ROOT / "data" / "processed" / "ev_kw.npz")["kw"].astype(float)
    start, n = 48 * 10, 96
    m0 = h.Model(1.0, True)
    idx = h.place_p1(m0, h.n_pv_for(0.6, 55))
    r = Y.run_year(hk, pv, (), 0.0, n_steps=n, start=start, ev_kw=ev, ev_idx=idx)
    e_load, e_ev, e_loss, e_pv, e_x, err = Y.energy_balance_ev(r)
    assert e_ev > 0 and e_pv == 0
    assert e_ev == pytest.approx(ev[start:start + n, idx].sum() * 0.5, rel=1e-4)   # EV energy = profile
    assert abs(err) < 0.01                                                           # percent


@pytest.mark.parametrize("phase", [1, 2, 3])
def test_ev_current_appears_on_its_own_phase_only(phase):
    """With every house load off, one 7.4 kW EV on phase p: the head-of-feeder line carries ~P/V on phase p and
    ~0 A on the other two phases (an EV is single-phase; the neutral, not another phase, carries the return)."""
    m = h.Model(1.0, True)
    k = next(i for i, p in enumerate(m.phase) if p == phase)
    head_line = m.path_lines[k][-1]                    # the line next to the transformer LV bus
    m.set_case("L0", [])
    m.solve(0.0)
    i0 = E.line_phase_currents_a(m, head_line)
    assert np.all(i0 < 0.05)                           # nothing connected: no current
    m.set_case("L0", [k])
    m.solve(-7.4)
    i1 = E.line_phase_currents_a(m, head_line)
    v_cust = np.array(dss.Circuit.AllBusVMag())[m.cust_idx[k]]
    assert i1[phase - 1] == pytest.approx(7400.0 / v_cust, rel=0.02)    # about 32 A
    assert all(i1[q] < 0.5 for q in range(3) if q != phase - 1)         # amperes
