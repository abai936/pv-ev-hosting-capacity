"""Australia A curves on a stiff source: one PV, bus voltage forced by the source (no feeder impedance to speak of).
Hand calcs (S = kVA rating):
  265 V -> 1.152 pu: Q = -0.60 S (flat end point), P <= 0.2 S and never negative.
  196 V -> 0.852 pu: Q = +0.44 S.
  Volt-watt y-axis: the line runs 1.100 to 1.1304 pu
  (253.0 to 260.0 V), so 256.5 V is half way: limit = 0.6 x S_rated = 3.0 kW for S = 5 kVA (not 0.6 x Pmpp = 3.6 kW).
"""
import opendssdirect as dss
import pytest

from hc import inverter as inv


def _run(v_target_v, kva=5.0, pmpp=5.0, with_vv=True):
    dss.Basic.ClearAll()
    dss.Command("New Circuit.stiff basekv=0.23 phases=1 pu=1.0 bus1=a")
    dss.Command("New Line.l phases=1 bus1=a bus2=b r1=0.0001 x1=0 length=1")
    dss.Command(f"New PVSystem.pv phases=1 bus1=b kV=0.23 kVA={kva} Pmpp={pmpp} irradiance=1 temperature=25 "
                "pf=1 %cutin=0.1 %cutout=0.1 vminpu=0.5 vmaxpu=1.6 varFollowInverter=Yes")
    inv.add_invcontrol(["pv"])
    dss.Command("Set maxcontroliter=100")
    # Calibrate source pu so the PV bus sits at v_target_v (stiff source: voltage barely moves with PV output).
    pu = v_target_v / 230.0
    for _ in range(5):
        dss.Command(f"Edit Vsource.Source pu={pu}")
        dss.Command("Set mode=snap")
        dss.Solution.Solve()
        dss.Circuit.SetActiveElement("PVSystem.pv")
        v = dss.CktElement.VoltagesMagAng()[0]
        pu *= v_target_v / v
    p = dss.CktElement.Powers()
    return v, -p[0], -p[1]


def test_high_voltage_265v():
    v, p_kw, q_kvar = _run(265.0)
    assert abs(v - 265) < 1.0
    assert abs(q_kvar - (-0.60 * 5)) < 0.02 * 5
    assert -0.02 * 5 <= p_kw <= 0.2 * 5 + 0.02 * 5      # never negative, capped at 0.2 S


def test_low_voltage_196v():
    v, p_kw, q_kvar = _run(196.0)
    assert abs(q_kvar - 0.44 * 5) < 0.02 * 5


def test_volt_watt_y_axis_is_fraction_of_kva_not_pmpp():
    v, p_kw, _ = _run(256.5, kva=5.0, pmpp=6.0)
    print(f"V={v:.2f} V, P={p_kw:.3f} kW (expect 3.0 if base is S_rated, 3.6 if Pmpp)")
    assert abs(p_kw - 3.0) < 0.02 * 5
