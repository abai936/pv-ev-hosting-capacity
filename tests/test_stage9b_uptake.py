"""Stage 9b tests: data loaders against the saved files, share bounds, back-test code against a hand-computed naive
forecast, scenario ordering, hosting-capacity read-off. Modelled / national data, not the feeder."""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hc import uptake as U  # noqa: E402

RES = ROOT / "results"


def test_pv_loader_rows_and_dates_match_file():
    n_file = sum(1 for ln in U.F_PV.read_text(encoding="utf-8-sig").splitlines() if re.match(r"\d\d/\d\d/\d{4},NZ,", ln))
    pv = U.load_pv()
    assert len(pv) == n_file == 159
    assert pv.index[0] == pd.Timestamp("2013-08-31") and pv.index[-1] == pd.Timestamp("2026-10-31")
    assert pv.index.is_monotonic_increasing and pv.index.is_unique
    assert pv["icp"].iloc[-1] == 87766                        # R11: Oct 2026
    # denominator derived from the file: ICPs / rate; 87,766 / 4.32009 % about 2.03 million residential ICPs
    assert pv["res_icp"].iloc[-1] == pytest.approx(87766 / 0.0432009, rel=1e-6)


def test_bev_loader_rows_and_dates_match_file():
    raw = pd.read_csv(U.F_EV, encoding="utf-8-sig")
    n_file = int(((raw["Variable view"] == "Battery Electric") & (raw["Vehicle Class"] == "Total")).sum())
    bev = U.load_bev()
    assert len(bev) == n_file == 122
    assert bev.index[0] == pd.Timestamp("2016-01-31") and bev.index[-1] == pd.Timestamp("2026-02-28")
    assert bev.loc["2025-12-31"] == 92560 and bev.loc["2016-12-31"] == 1911      # R11 values read from the same file


def test_driver_files():
    pa = U.load_pop_annual()
    assert len(pa) == 35 and pa.index[0] == 1991 and pa.index[-1] == 2025 and pa.loc[2025] == 5324700
    cq = U.load_cpi_quarterly()
    assert cq[pd.Period("2026Q2", "Q")] == 4.1 and cq[pd.Period("2025Q3", "Q")] == 3.0
    pq = U.load_price_quarterly()
    assert len(pq) == 48 and pq.index[0] == pd.Timestamp("2013-06-30") and pq.index[-1] == pd.Timestamp("2025-03-31")


def test_shares_between_0_and_1_and_a30():
    S = U.build_series()
    for s in (S["pv"]["share"], S["ev"]["share"]):
        assert ((s > 0) & (s < 1)).all()
    # A30: BEV per residential ICP = BEV stock / EA residential ICPs of the same month (hand check at Dec 2025)
    ev, pv = S["ev"], S["pv"]
    d = pd.Timestamp("2025-12-31")
    assert ev.loc[d, "share"] == pytest.approx(92560 / pv.loc[d, "res_icp"], rel=1e-12)
    assert len(ev) == 122 and ev["res_icp"].notna().all()               # the EA ICP count covers every BEV month
    assert 0.03 < ev["share"].iloc[-1] < 0.07                            # sanity: about 4-5 % in Feb 2026
    assert S["ev"]["pop_extrapolated"].iloc[-1] and not S["ev"]["pop_extrapolated"].iloc[0]


def test_bev_stock_never_fell():
    # justifies the floor at the last observed share: BEV stock rose or held in all 121 monthly steps
    assert (U.load_bev().diff().dropna() >= 0).all()


def test_scenario_floor():
    pts = {"a": 0.03, "b": 0.02}
    lo, mid, hi = U.scenario_from_models(pts, (0.01, 0.05), "a", ["a", "b"], floor=0.04)
    assert (lo, mid) == (0.04, 0.04) and hi == 0.05


def test_no_look_ahead_in_drivers():
    idx = pd.date_range("2014-01-31", "2026-10-31", freq="ME")
    d = U.drivers_monthly(idx)
    # 2026 Q2 CPI (period ends 30 Jun) may not be visible before the lag has passed (1 month -> from 31 Jul)
    assert d.loc["2026-06-30", "cpi_yoy"] == 3.1 and d.loc["2026-07-31", "cpi_yoy"] == 4.1
    assert d["price_yoy"].isna().loc["2026-10-31"] and d["price_yoy"].notna().loc["2024-12-31"]


def _tiny_frame():
    t = np.arange(40)
    idx = pd.date_range("2020-01-31", periods=40, freq="ME")
    return pd.DataFrame({"share": t ** 2 / 10000.0}, index=idx), \
        pd.DataFrame({c: np.nan for c in ("cpi_yoy", "price_yoy", "pop_g")}, index=idx)


def test_backtest_reproduces_hand_naive_forecast():
    # y_t = t^2/10000. Origin T=24: y=0.0576, y(T-12)=0.0144 -> slope 0.0432/12 = 0.0036 per month.
    # Naive at h=12: 0.0576 + 12 x 0.0036 = 0.1008; truth y_36 = 0.1296; error = -0.0288 = -2.88 pp.
    df, dr = _tiny_frame()
    bt = U.backtest(df, "PV", dr, [df.index[24]], horizons=(12,))
    r = bt[(bt.model == "naive")].iloc[0]
    assert r["me_h_pp"] == pytest.approx(-2.88, abs=1e-9) and r["mae_h_pp"] == pytest.approx(2.88, abs=1e-9)
    # mean error over months 1..12: forecast 0.0576+0.0036 j vs truth (24+j)^2/1e4 ; computed by hand with numpy here
    j = np.arange(1, 13)
    assert r["me_steps_pp"] == pytest.approx(np.mean((0.0576 + 0.0036 * j) - (24 + j) ** 2 / 1e4) * 100, abs=1e-9)
    # driver models have no data here, so they must be reported unusable instead of invented
    assert not bt[bt.model == "drv_cpi"]["usable"].iloc[0]


def test_naive_function_direct():
    y = np.arange(0, 20, dtype=float)             # slope 1 per month
    assert np.allclose(U.f_naive(y, 3), [20, 21, 22])


def test_logistic_respects_ceiling_and_linear_exact():
    t = np.arange(48)
    k = 0.3
    y = k / (1 + np.exp(-(0.1 * t - 5)))          # an exact logistic: the fit must recover it
    f = U.f_logistic(y, 12, ceiling=k)
    truth = k / (1 + np.exp(-(0.1 * (47 + np.arange(1, 13)) - 5)))
    assert np.allclose(f, truth, rtol=1e-6) and (f < k).all()
    yl = 0.01 + 0.002 * np.arange(50)
    assert np.allclose(U.f_linear(yl, 2), [0.01 + 0.002 * 50, 0.01 + 0.002 * 51])


def test_scenario_ordering_function():
    pts = {"a": 0.08, "b": 0.05, "c": 0.12}
    lo, mid, hi = U.scenario_from_models(pts, (0.06, 0.10), "a", ["a", "b", "c"])
    assert lo <= mid <= hi and (lo, mid, hi) == (0.05, 0.08, 0.12)
    lo, mid, hi = U.scenario_from_models({"a": 0.08}, (np.nan, np.nan), "a", ["a"])
    assert lo == mid == hi == 0.08


def test_scenario_file_ordering():
    p = RES / "stage9b_scenarios.csv"
    if not p.exists():
        pytest.skip("run scripts/stage9b_uptake.py first")
    sc = pd.read_csv(p)
    assert len(sc) == 6
    for tg, g in sc.groupby("target"):
        g = g.set_index("scenario")
        for col in ("pv_share_of_houses_pct", "pv_new_system_kw", "bev_per_res_icp_pct"):
            assert g.loc["low", col] <= g.loc["mid", col] <= g.loc["high", col], (tg, col)
    # 2028 not below 2027 at the mid scenario (the models all grow; a drop would flag a bug)
    mid = sc[sc.scenario == "mid"].set_index("target")
    assert (mid.loc["2028-12-31", ["pv_share_of_houses_pct", "bev_per_res_icp_pct"]] >=
            mid.loc["2027-12-31", ["pv_share_of_houses_pct", "bev_per_res_icp_pct"]]).all()


def test_hc_readoff_monotonic_and_first_exceeded():
    pen = [0.05, 0.1, 0.3, 1.0]
    hc = [10.0, 8.0, 5.0, 2.0]
    grid = np.linspace(0.05, 1.0, 40)
    vals = [U.read_off(pen, hc, g) for g in grid]
    assert all(a >= b - 1e-12 for a, b in zip(vals, vals[1:]))          # more PV never raises the HC
    assert U.read_off(pen, hc, 0.2) == pytest.approx(6.5)               # hand: halfway between 8 (10 %) and 5 (30 %)
    assert U.first_exceeded(pen, hc, 6.5) == pytest.approx(0.2)         # HC drops below 6.5 kW at 20 %
    assert U.first_exceeded(pen, hc, 11.0) == 0.05 and U.first_exceeded(pen, hc, 1.0) is None
    assert U.n_houses(0.30) == 17 and U.n_houses(0.60) == 33            # same ceil rule as hosting.n_pv_for


def test_hc_curve_file_monotonic_and_matches_stage6():
    p = RES / "stage9b_hc_curve.csv"
    if not p.exists():
        pytest.skip("run scripts/stage9b_uptake.py first")
    c = pd.read_csv(p).sort_values("penetration")
    assert len(c) == 9 and (np.diff(c["HC_kW"]) <= 1e-9).all()
    s6 = pd.read_csv(RES / "stage6_snapshot_hc.csv")
    s6 = s6[(s6.placement == "P1") & (s6.load_case == "L2") & (s6.model == "neutral_return")].set_index("penetration")["HC_kW"]
    for pen in (0.3, 0.6, 1.0):                                         # same feeder, same case: must reproduce Stage 6
        assert c.set_index("penetration").loc[pen, "HC_kW"] == pytest.approx(s6.loc[pen], abs=0.011)


def test_scenarios_floor_and_direct_hc():
    ps, pn = RES / "stage9b_scenarios.csv", RES / "stage9b_hc_n_direct.csv"
    if not (ps.exists() and pn.exists()):
        pytest.skip("run scripts/stage9b_uptake.py first")
    sc, hn = pd.read_csv(ps), pd.read_csv(pn).set_index("n_pv")
    last = U.build_series()["ev"]["share"].iloc[-1] * 100
    assert (sc["bev_per_res_icp_pct"] >= last - 1e-3).all()                 # floored at the last observed share
    assert "ev_share_of_households_pct" not in sc.columns
    for r in sc.itertuples():                                               # HC in the scenarios = the direct find_hc value
        assert r.feeder_hc_kw_at_that_penetration == pytest.approx(hn.loc[r.feeder_pv_houses_of_55, "HC_kW"])
    assert hn.loc[3, "binding_limit"].startswith("none")                    # N = 3 hits the 20 kW sweep cap: 'at least 20'
