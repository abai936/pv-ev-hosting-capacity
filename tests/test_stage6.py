"""Stage 6 tests. Short 2-day windows keep them fast; the runner reports the full-year balance."""
import numpy as np
import pandas as pd
import pytest

from hc import hosting as h, l2, profiles as P, yearly as Y

START, N = 48 * 10, 96          # 2 days from 11 Jan 2022 (UTC grid), a clear PV window


@pytest.fixture(scope="module")
def data():
    return Y.load_year_inputs()


def test_l2_mask_counts_63_weekdays_two_steps():
    # Dec + Jan + Feb 2022 weekdays: 22 + 21 + 20 = 63; steps starting 12:00 and 12:30 local = 126
    assert l2.summer_midday_mask(P.time_index_utc()).sum() == 126


def test_l2_mask_picks_exactly_the_independent_timestamp_list():
    # Build the expected UTC steps independently, day by day in local time: for every Auckland local date in
    # Dec/Jan/Feb 2022 that is Mon-Fri, the steps starting 12:00 and 12:30 local.
    idx = P.time_index_utc()
    expect = []
    for d in pd.date_range("2022-01-01", "2022-12-31", freq="D"):
        if d.month in (12, 1, 2) and d.day_of_week < 5:
            for hh, mm in ((12, 0), (12, 30)):
                local = pd.Timestamp(d.year, d.month, d.day, hh, mm, tz=P.LOCAL_TZ)
                expect.append(local.tz_convert("UTC"))
    got = idx[l2.summer_midday_mask(idx)]
    assert list(got) == sorted(expect)
    assert len(expect) == 126
    # DST check on one day: 12:00 NZDT (UTC+13) in January is 23:00 UTC the previous day.
    assert pd.Timestamp("2022-01-13 23:00", tz="UTC") in set(got)      # local Fri 14 Jan 12:00


def test_l2_median_of_toy_series_hand_value():
    # One house; the four L2 steps of the first days carry 1, 3, 2, 10 and every other L2 step is 5.
    # Median of the L2 set is therefore exactly 5 (hand value), unlike the huge value 99 elsewhere.
    idx = pd.date_range("2022-01-10", periods=48 * 7, freq="30min", tz="UTC")
    mask = l2.summer_midday_mask(idx)
    x = np.full((len(idx), 1), 99.0)
    pos = np.flatnonzero(mask)
    x[pos, 0] = 5.0
    x[pos[:4], 0] = [1, 3, 2, 10]
    kw, n = l2.l2_kw(x, idx)
    assert n == len(pos) and n >= 6
    assert kw[0] == 5.0


def test_l2b_total_not_above_l2_total_at_midday_summer(data):
    # L2b has no electric heating or hot water and uses the same scale factor, so it cannot exceed L2 in total.
    hk, _, _ = data
    kw2, _ = l2.l2_kw(hk, P.time_index_utc())
    kwb, _ = l2.l2_kw(l2.appliance_house_kw(), P.time_index_utc())
    assert kwb.sum() <= kw2.sum()


def test_l2_shape_and_positive(data):
    hk, _, _ = data
    kw, n = l2.l2_kw(hk, P.time_index_utc())
    assert n == 126 and len(kw) == 55
    kwb, _ = l2.l2_kw(l2.appliance_house_kw(), P.time_index_utc())
    assert np.all(kwb > 0)


@pytest.fixture(scope="module")
def runs(data):
    hk, pv, _ = data
    m = h.Model(1.0, True)
    idx = h.place_p1(m, h.n_pv_for(0.6, 55))
    y0 = Y.run_year(hk, pv, [], 0.0, n_steps=N, start=START)
    y2 = Y.run_year(hk, pv, idx, 5.0, n_steps=N, start=START)
    return y0, y2, idx


def test_pv_energy_matches_profile(data, runs):
    _, pv, _ = data
    _, y2, idx = runs
    expect = pv[START:START + N].sum() * Y.STEP_H * 5.0 * len(idx)
    assert expect > 500                                   # a real summer window, not a dark one
    assert len(idx) == 33
    assert y2["pv_kw_per_step"].sum() * Y.STEP_H == pytest.approx(expect, rel=0.005)
    assert y2["pv_kwh_dss"] == pytest.approx(expect, rel=0.005)   # the generators' own energy registers


def test_load_energy_matches_profile(data, runs):
    hk = data[0]
    y0 = runs[0]
    assert y0["load_kw"].sum() * Y.STEP_H == pytest.approx(hk[START:START + N].sum() * Y.STEP_H, rel=0.005)


@pytest.mark.parametrize("which", [0, 1])
def test_energy_balance_closes_y0_y2(runs, which):
    """Bookkeeping check, not a physics validation: load + losses - PV must equal the HV-terminal energy
    to 0.01 %. It would catch a missed or double-counted element, but not a wrong model."""
    r = runs[which]
    assert r["converged"] == N
    e_load, e_loss, e_pv, e_x, err_x, _ = Y.energy_balance(r)
    assert 0 < e_loss < 0.1 * e_load                      # losses are small and positive
    assert abs(err_x) < 0.01
