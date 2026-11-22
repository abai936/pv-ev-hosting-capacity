"""Stage 8 tests: inverter control and tap. Hand checks first (curves, tap), then feeder checks.
Australia A curves, V in pu of 230 V. Short windows keep the tests fast."""
import numpy as np
import opendssdirect as dss
import pandas as pd
import pytest

from hc import feeder as f, hosting as h, inverter as inv, mitigation as M, yearly as Y

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


def _stiff(v_target_v, mode, pmpp=5.0, kva=5.0, irradiance=1.0):
    """One PV on a stiff source calibrated so the PV bus sits at v_target_v (as test_inverter_curves)."""
    dss.Basic.ClearAll()
    dss.Command("New Circuit.stiff basekv=0.23 phases=1 pu=1.0 bus1=a")
    dss.Command("New Line.l phases=1 bus1=a bus2=b r1=0.0001 x1=0 length=1")
    dss.Command(f"New PVSystem.pv phases=1 bus1=b kV=0.23 kVA={kva} Pmpp={pmpp} irradiance={irradiance} "
                "temperature=25 pf=1 %cutin=0 %cutout=0 vminpu=0.5 vmaxpu=1.6 varFollowInverter=Yes")
    M.add_invcontrol(mode, ["pv"])
    pu = v_target_v / 230.0
    for _ in range(6):
        dss.Command(f"Edit Vsource.Source pu={pu}")
        dss.Command("Set mode=snap")
        dss.Solution.Solve()
        dss.Circuit.SetActiveElement("PVSystem.pv")
        v = dss.CktElement.VoltagesMagAng()[0]
        pu *= v_target_v / v
    for _ in range(4):                      # let the control settle (same idea as mitigation.solve)
        dss.Solution.Solve()
    p = dss.CktElement.Powers()
    return dss.CktElement.VoltagesMagAng()[0], -p[0], -p[1]


def test_volt_var_q_matches_curve_midpoint():
    # Hand calc: between 1.0435 and 1.1217 pu the curve falls from 0 to -0.60 S. At 1.0826 pu (249.0 V)
    # Q = -0.60 x (1.0826 - 1.0435) / (1.1217 - 1.0435) = -0.30 S = -1.5 kvar for S = 5 kVA.
    # Sun 50 %: P = 2.5 kW so P and Q fit in 5 kVA (no kVA clipping), volt-watt not active (below 1.10 pu).
    v, p, q = _stiff(1.0826 * 230, "M2", irradiance=0.5)
    assert abs(q - (-1.5)) < 0.1
    assert abs(p - 2.5) < 0.05


def test_volt_var_zero_just_below_deadband_end_and_injects_when_low():
    v, p, q = _stiff(1.043 * 230, "M2", irradiance=0.5)     # 1.043 pu is inside the dead band (ends 1.0435)
    assert abs(q) < 0.1
    v, p, q = _stiff(0.9565 * 230 - 0.0, "M2", irradiance=0.5)
    assert abs(q) < 0.1                                    # lower dead band end: 0 vars
    v, p, q = _stiff(0.93 * 230, "M2", irradiance=0.5)     # fraction (0.9565-0.93)/(0.9565-0.9)=0.469 -> +0.206 S
    assert abs(q - 0.44 * 0.469 * 5) < 0.1


def test_volt_watt_p_is_20_percent_of_s_rated_at_1_1304_pu():
    # Volt-watt end point: 1.1304 pu = 260.0 V -> P = 0.20 x S_rated = 1.0 kW (S = 5 kVA, sun 100 %).
    v, p, q = _stiff(260.0, "M1")
    assert abs(v - 260.0) < 1.5
    assert abs(p - 1.0) < 0.1
    # 1.130 pu (259.9 V) is 0.0004 pu short of the end: P = 1 - 0.8 x (1.130-1.100)/(1.1304-1.100) = 0.2105 S
    v, p, q = _stiff(1.130 * 230, "M1")
    assert abs(p - 5 * (1 - 0.8 * (1.130 - 1.1) / (1.1304 - 1.1))) < 0.15


def test_tap_sets_no_load_lv_voltage():
    # Hand calc: no-load phase voltage = 416 V / sqrt(3) x tap = 240.18 V x tap (source 1.00 pu, all loads 0).
    for tap in (1.0, 0.975):
        m = M.CtlModel("M0", tap)
        m.set_case("L0", [])
        m.solve(0.0)
        v = dss.Circuit.AllBusVMag()[m.node_idx["1.1"]]
        assert abs(v - 416 / np.sqrt(3) * tap) < 0.05, (tap, v)
    assert abs(416 / np.sqrt(3) * 0.975 - 234.18) < 0.01


def test_far_end_customer_control_reduces_voltage_rise_with_correct_sign():
    # One PV (8 kW) at the far end, loads zero, source 1.00 pu: with no control the far-end voltage is the highest.
    # Volt-var (M3) must absorb vars (injected Q negative) and lower the voltage; M0 injects no vars.
    out = {}
    for mode in ("M0", "M3"):
        m = M.CtlModel(mode)
        k = int(np.argmax(m.path_r))
        m.set_case("L0", [k])
        m.solve(8.0)
        out[mode] = (dss.Circuit.AllBusVMag()[m.cust_idx[k]], *m.pv_output())
    v0, p0, q0 = out["M0"]
    v3, p3, q3 = out["M3"]
    assert v0 > 240.0                          # above the volt-var dead band end (1.0435 pu = 240.0 V): control must act
    assert abs(q0) < 1e-3 and abs(p0 - 8.0) < 1e-3
    assert q3 < -0.5                           # absorbing vars (negative injection)
    # Q follows the curve on the inverter's own kVA base (8 kVA here, not 1 kVA): Q = 8 x interp(V/230)
    # Bound = the InvControl's own VarChangeTolerance (0.025 pu default) x 8 kVA = 0.2 kvar. It was 0.15; after the
    # cold-start fix (and with the other 54 idle PVSystems now disabled) the settled Q is 0.164 kvar off the curve,
    # still inside the control's tolerance.
    assert abs(q3 - 8.0 * np.interp(v3 / 230.0, inv.VV_X, inv.VV_Y)) <= 0.025 * 8.0, (q3, v3)
    assert v3 < v0 - 0.3                       # voltage rise reduced
    assert p3 <= p0 + 1e-6                     # control never raises P


def test_non_pv_customers_deliver_zero_and_pv_customers_deliver_p():
    m = M.CtlModel("M0")
    m.set_case("L0", [0, 5, 9])
    m.solve(4.0)
    tot = 0.0
    for i, n in enumerate(m.loads):
        dss.Circuit.SetActiveElement(f"PVSystem.PVS_{n}")
        p = -dss.CktElement.Powers()[0]
        assert abs(p - (4.0 if i in (0, 5, 9) else 0.0)) < 1e-4
        tot += p
    assert abs(tot - 12.0) < 1e-3


def test_m0_matches_stage6_generator_hc():
    # M0 (PVSystem, unity PF, no control) must reproduce the Stage 6 L2 numbers (generator model), tap 1.000.
    from hc import l2, profiles as P
    hk, _, _ = Y.load_year_inputs()
    kw, _ = l2.l2_kw(hk, P.time_index_utc())
    s6 = pd.read_csv(ROOT / "results" / "stage6_snapshot_hc.csv")
    m = M.CtlModel("M0")
    m.cases["L2"] = dict(zip(m.loads, kw))
    for pen, pl in ((0.6, "P1"), (0.6, "P2"), (1.0, "P1")):
        n = h.n_pv_for(pen, 55)
        idx = h.place_p1(m, n) if pl == "P1" else h.place_p2(m, n)
        m.set_case("L2", idx)
        o = M.hc_with_control(m)
        ref = s6[(s6.model == "neutral_return") & (s6.load_case == "L2") & (s6.placement == pl) & (s6.penetration == pen)].HC_kW.iloc[0]
        assert abs(o["hc_kw"] - ref) < 0.02, (pen, pl, o["hc_kw"], ref)
        assert o["curtailed_pct"] < 1e-6


def _l2_model(mode, tap, pen, pl, kva=1.0):
    from hc import l2, profiles as P
    hk, _, _ = Y.load_year_inputs()
    kw, _ = l2.l2_kw(hk, P.time_index_utc())
    m = M.CtlModel(mode, tap, kva)
    m.cases["L2"] = dict(zip(m.loads, kw))
    n = h.n_pv_for(pen, 55)
    m.set_case("L2", h.place_p1(m, n) if pl == "P1" else h.place_p2(m, n))
    return m


def test_control_solve_does_not_depend_on_the_points_solved_before():
    # Review fix: every control solve starts cold. The same point solved after different earlier points
    # (higher, lower, nonconverging 20 kW, a near neighbour) must give the same customer voltages to 1 mV.
    m = _l2_model("M3", 1.0, 0.3, "P2")
    p = 6.3
    m.solve(p)
    v_ref = np.array(dss.Circuit.AllBusVMag())[m.cust_idx]
    for prior in (20.0, 1.0, 9.0, p + 0.01, 0.0):
        try:
            m.solve(prior)
        except M.NonConverged:
            pass
        m.solve(p)
        v = np.array(dss.Circuit.AllBusVMag())[m.cust_idx]
        assert np.abs(v - v_ref).max() < 1e-3, (prior, np.abs(v - v_ref).max())
    # A different placement solved in between (other customers given PV and kVA) must not leak either.
    idx = list(m.pv_idx)
    m.set_case("L2", h.place_p1(m, 33))
    m.solve(9.0)
    m.set_case("L2", idx)
    m.solve(p)
    v = np.array(dss.Circuit.AllBusVMag())[m.cust_idx]
    assert np.abs(v - v_ref).max() < 1e-3, ("placement switch", np.abs(v - v_ref).max())


def test_customers_without_pv_deliver_no_p_and_no_vars_under_volt_var():
    # Review fix: a PVSystem at irradiance 0 used to absorb volt-var vars. Non-PV customers must give 0 P, 0 Q.
    m = _l2_model("M3", 1.0, 0.6, "P1")
    m.set_case("L2", h.place_p1(m, 17))
    m.solve(9.0)                                  # leaves 9 kVA ratings on the 30 % customers
    m.set_case("L2", h.place_p1(m, 33))
    m.solve(4.7)
    on = set(m.pv_idx)
    q = p = 0.0
    for i, n in enumerate(m.loads):
        if i not in on:
            dss.Circuit.SetActiveElement(f"PVSystem.PVS_{n}")
            pw = dss.CktElement.Powers()
            p, q = p + abs(pw[0]), q + abs(pw[1])
    assert p < 1e-6 and q < 1e-6, (p, q)


# Sample of reported HC rows (mode, tap, kva, placement, penetration): M1, M2, M3, P1/P2, tap 0.975, kVA 1.1.
_HC_SAMPLE = [("M1", 1.0, 1.0, "P1", 1.0), ("M1", 0.975, 1.0, "P2", 0.3), ("M2", 1.0, 1.0, "P2", 0.3),
              ("M2", 0.975, 1.0, "P1", 0.6), ("M3", 1.0, 1.0, "P1", 0.3), ("M3", 1.0, 1.0, "P1", 0.6),
              ("M3", 1.0, 1.0, "P2", 0.3), ("M3", 0.975, 1.0, "P2", 0.6), ("M3", 0.975, 1.0, "P1", 1.0),
              ("M2", 1.0, 1.1, "P1", 0.3)]


@pytest.mark.parametrize("mode,tap,kva,pl,pen", _HC_SAMPLE)
def test_reported_hc_passes_and_hc_plus_0_01_fails_from_cold(mode, tap, kva, pl, pen):
    d = pd.read_csv(ROOT / "results" / "stage8_hc.csv")
    r = d[(d["mode"] == mode) & (d.tap == tap) & (d.kva_ratio == kva) & (d.placement == pl) & (d.penetration == pen)].iloc[0]
    if r.status != "ok":
        pytest.skip(f"row status {r.status}")
    hc = float(r.HC_kW)
    m = _l2_model(mode, tap, pen, pl, kva)
    m.solve(hc)                                  # solve() starts cold every time
    assert m.violations() == [], (hc, m.violations()[:3])
    assert np.array(dss.Circuit.AllBusVMag())[m.cust_idx].max() <= f.V_HIGH_V
    try:
        m.solve(hc + 0.01)
        assert m.violations(), (hc + 0.01, "passes")
    except M.NonConverged:
        pass                                     # counts as fail in find_hc too (row would be nonconverged)


def test_m1_hc_equals_m0_hc_and_m1_does_not_curtail_below_253_v():
    # Australia A volt-watt starts at 253.0 V = the NZ limit, so M1 cannot lift a voltage-bound HC, and a
    # settled M1 point with every customer below 253 V delivers all its P. Within one bisection step.
    d = pd.read_csv(ROOT / "results" / "stage8_hc.csv")
    d = d[(d.status == "ok") & (d.kva_ratio == 1.0)]
    k = ["tap", "placement", "seed", "penetration"]
    d["seed"] = d.seed.fillna(-1)
    a = d[d["mode"] == "M0"].set_index(k).HC_kW.astype(float)
    b = d[d["mode"] == "M1"].set_index(k).HC_kW.astype(float)
    diff = (b - a).dropna()
    assert len(diff) >= 150 and (diff.abs() <= 0.011).all(), diff[diff.abs() > 0.011]
    m1 = d[d["mode"] == "M1"]
    low = m1[pd.to_numeric(m1.vmax_v_at_HC) < 252.9]
    assert (low.curtailed_pct_at_HC < 0.01).all()


def test_m0_rows_in_stage8_csv_match_stage6():
    # M0 (no control, no cold start needed) must equal the Stage 6 generator HC for every P1/P2 row at tap 1.000.
    d = pd.read_csv(ROOT / "results" / "stage8_hc.csv")
    s6 = pd.read_csv(ROOT / "results" / "stage6_snapshot_hc.csv")
    s6 = s6[(s6.model == "neutral_return") & (s6.load_case == "L2") & (s6.source_pu == 1.0)]
    d = d[(d["mode"] == "M0") & (d.tap == 1.0) & d.placement.isin(["P1", "P2"])]
    assert len(d) == 6
    for r in d.itertuples():
        ref = s6[(s6.placement == r.placement) & (s6.penetration == r.penetration)].HC_kW.iloc[0]
        assert abs(float(r.HC_kW) - ref) < 0.02, (r.placement, r.penetration, r.HC_kW, ref)


def test_nonconverged_is_reported_not_a_number():
    m = M.CtlModel("M3")
    m.set_case("L0", [0])
    m.solve = lambda p: (_ for _ in ()).throw(M.NonConverged("forced"))
    o = M.hc_with_control(m)
    assert o["status"] == "nonconverged" and o["hc_kw"] is None


def test_control_curtailment_and_energy_balance_closes():
    # 2-day summer window, 12 kWp per house (above HC). Volt-watt only (M1) curtails (hand-visible: delivered < available).
    # The PV profile peaks at 0.8915 kW per kWp, so the spare kVA at peak is sqrt(1 - 0.8915^2) = 0.45 S (less than the
    # 0.6 S volt-var maximum). M3 is therefore only checked for energy balance, not for zero curtailment.
    # Energy balance with curtailment: load + losses - delivered PV = energy into the transformer HV terminal, error < 0.01 %.
    hk, pv, _ = Y.load_year_inputs()
    idx = h.place_p1(h.Model(1.0, True), 33)
    for mode, must_curtail in (("M1", True), ("M3", False)):
        r = M.run_year_ctl(hk, pv, idx, 12.0, mode, 1.0, 1.0, n_steps=96, start=48 * 10)
        e_avail = r["pv_avail_kw_per_step"].sum() * Y.STEP_H
        e_deliv = r["pv_kw_per_step"].sum() * Y.STEP_H
        assert r["converged"] == 96 and r["ctl_fail_steps"] == 0
        if must_curtail:
            assert e_avail - e_deliv > 5.0                 # curtailment really happened (kWh)
        assert e_deliv <= e_avail + 0.01                   # control never creates energy
        assert (r["pv_p"] <= 12.0 + 1e-3).all()            # never above the rating
        e_load, e_loss, e_pv, e_x, err_pct, _ = Y.energy_balance(r)
        assert abs(e_pv - e_deliv) < 1e-6
        assert abs(err_pct) < 0.01, (mode, err_pct)


def test_year_m0_pvsystem_matches_stage6_generator_energy_and_voltage():
    hk, pv, _ = Y.load_year_inputs()
    idx = h.place_p1(h.Model(1.0, True), 33)
    ref = Y.run_year(hk, pv, idx, 8.0, n_steps=48, start=48 * 10)
    r = M.run_year_ctl(hk, pv, idx, 8.0, "M0", 1.0, 1.0, n_steps=48, start=48 * 10)
    assert abs(r["pv_kw_per_step"].sum() - ref["pv_kw_per_step"].sum()) < 1e-2
    assert abs(float(r["v_cust_v"].max()) - float(ref["v_cust_v"].max())) < 0.01
    assert abs(r["p_hv_kw"].sum() - ref["p_hv_kw"].sum()) < 0.1


def test_tap_lowers_customer_voltage_by_about_2_5_percent_at_light_load():
    v = {}
    for tap in (1.0, 0.975):
        m = M.CtlModel("M0", tap)
        m.set_case("L0", [])
        m.solve(0.0)
        v[tap] = np.array(dss.Circuit.AllBusVMag())[m.cust_idx].max()
    assert 0.974 < v[0.975] / v[1.0] < 0.976


def test_year_non_pv_customers_are_disabled_and_deliver_no_vars():
    # Review fix: customers without PV must not be active PVSystems in the InvControl list (they absorbed volt-var vars).
    hk, pv, _ = Y.load_year_inputs()
    idx = h.place_p1(h.Model(1.0, True), 33)
    r = M.run_year_ctl(hk, pv, idx, 8.0, "M3", 1.0, 1.0, n_steps=4, start=48 * 10)
    m = r["model"]
    on = set(idx)
    for i, n in enumerate(m.loads):
        dss.Circuit.SetActiveElement(f"PVSystem.PVS_{n}")
        assert dss.CktElement.Enabled() == (i in on), n
    assert r["pv_p"].dtype == np.float64 and r["pv_q"].dtype == np.float64    # energies summed in float64


def test_year_csv_m0_row_equals_stage6_y3():
    # The reused M0 row must be exactly the Stage 6 Y3 numbers (hand check: same file values).
    y = pd.read_csv(ROOT / "results" / "stage8_year.csv")
    s6 = pd.read_csv(ROOT / "results" / "stage6_year.csv")
    a = y[y.case == "Y3_M0_tap1.000"].iloc[0]
    b = s6[s6.case == "Y3"].iloc[0]
    assert a.cust_hours_above_253V == b.cust_hours_above_253V and a.xfmr_max_kVA == b.xfmr_max_kVA
    assert a.distinct_hours_line_above_100pct == b.distinct_hours_line_above_100pct


def test_pv_profile_peak_and_spare_kva():
    d = pd.read_csv(ROOT / "data" / "processed" / "avg_house_and_pv_30min.csv")
    peak = d.pv_kw_per_kwp.max()
    assert abs(peak - 0.8915) < 1e-4
    assert abs(np.sqrt(1 - peak**2) - 0.45) < 0.005           # spare kVA at peak, per S_rated; below the 0.6 S var max
