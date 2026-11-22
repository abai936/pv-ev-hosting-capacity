"""Stage 5 hand checks (a)-(e). Needs data/raw/steidl/Data.zip and data/raw/pvgis/*.csv."""
import numpy as np
import pytest

from hc import profiles as P


@pytest.fixture(scope="module")
def r(tmp_path_factory):
    # Write to a pytest temp folder so the test never overwrites data/processed.
    return P.build_all(n_ev=20, out_dir=tmp_path_factory.mktemp("proc"))


def test_f_house_mean_is_7048_and_days_differ(r):
    # Mean of the 55 houses' annual kWh is exactly the average-house energy (one common scale factor).
    kwh = (r["houses"] * P.STEP_H).sum(axis=0)
    assert kwh.mean() == pytest.approx(7048.0, rel=1e-6)


def test_g_appliances_shape_has_same_scale_factor_as_default(r):
    # Same factor => the appliances-only shape carries less than 7,048 kWh (no heating, no hot water).
    app_kwh = r["avg_house_appliances"].sum() * P.STEP_H
    assert 0 < app_kwh < 0.9 * 7048.0


def test_h_pick_differs_between_days_for_same_house():
    pick = P.daily_profile_picks(2022, P.N_HOUSES, 365)
    for i in range(P.N_HOUSES):
        assert len(np.unique(pick[i])) > 50                # a house does not reuse one profile all year
    assert (pick[0, 1:] != pick[0, :-1]).mean() > 0.9     # day-to-day picks change
    assert not np.array_equal(pick, P.daily_profile_picks(1, P.N_HOUSES, 365))   # seed matters


def test_a_average_house_sums_to_7048(r):
    kwh = r["avg_house"].sum() * P.STEP_H
    assert kwh == pytest.approx(7048.0, rel=0.001)


def test_b_pv_capacity_factor_and_orientation(r):
    assert r["cf_north"] == pytest.approx(P.PV_CF_REFERENCE, rel=0.15)
    assert r["cf_north"] > r["cf_south"]


def _peak_hour(series_utc):
    loc = series_utc.tz_convert(P.LOCAL_TZ)
    return loc.groupby(loc.index.hour + loc.index.minute / 60).mean().idxmax()


def test_c_pv_peak_january_local(r):
    pv = r["pv"]
    assert 12 <= _peak_hour(pv[pv.index.month == 1]) <= 15


def test_c_appliance_shape_peak_july_local(r):
    # Occupancy-driven appliance shape: July daily peak at 17:00-21:00 Auckland time.
    a = r["avg_house_appliances"]
    assert 17 <= _peak_hour(a[a.index.month == 7]) <= 21


def test_c_total_shape_peak_july_info(r):
    # Informational only, no assert: the heating components (heat pump, electric heating)
    # peak at 11:00 in winter in the Steidl data, so their timing is suspect.
    a = r["avg_house"]
    print(f"July total-shape (total - EV) peak hour, Auckland time: {_peak_hour(a[a.index.month == 7])}")
    print(f"January total-shape peak hour: {_peak_hour(a[a.index.month == 1])}")


def test_d_ev_energy_and_start_hours():
    s = P.ev_sessions(n_ev=30, seed=1, n_days=366)          # 10,980 sessions
    expected = np.exp(np.log(6.9) + 0.5 ** 2 / 2)           # 7.82 kWh
    assert s["energy_kwh"].mean() == pytest.approx(expected, rel=0.05)
    share = P.EV_PARAMS["start_hour_share"][0]
    want = np.full(24, (1 - sum(share.values())) / 17)
    want[17:] = [share[h] for h in range(17, 24)]
    got = np.bincount(s["start_hour_local"], minlength=24) / len(s)
    assert np.abs(got - want).max() < 0.02


def test_d_ev_series_energy_matches_sessions(r):
    # Energy in the 30-min series equals session energy, except the few cut at the year ends.
    kwh = r["ev"].sum() * P.STEP_H
    assert kwh == pytest.approx(r["sessions"]["energy_kwh"].sum(), rel=0.02)
    assert r["ev"].max() <= 7.4 + 1e-9


def test_e_no_nan_and_17520_steps(r):
    for x in (r["avg_house"], r["pv"], r["houses"], r["ev"]):
        assert len(x) == 17520
        assert not np.isnan(np.asarray(x)).any()
    assert r["avg_house"].index.is_unique and r["avg_house"].index.is_monotonic_increasing
