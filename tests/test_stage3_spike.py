"""InvControl check: at solar noon each PV's reactive power follows the Australia A volt-var curve with
V in pu of 230 V (this confirms the pu base InvControl uses). Hand calc: Q = 5 kVA x interp(V/230, curve)."""
import sys

import numpy as np
import opendssdirect as dss

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "scripts"))
import stage3_invcontrol_spike as s  # noqa: E402
from hc import feeder as f  # noqa: E402
from hc import inverter as inv  # noqa: E402


def test_volt_var_follows_curve_on_230v_base():
    f.load_feeder(1.0)
    dss.Command("Set maxcontroliter=100")
    s.add_pv(s.synthetic_irradiance())
    s.add_invcontrol()
    f.solve_minutes(n_minutes=780, collect=False)     # minute 780 = 13:00, near peak irradiance
    for n in dss.PVsystems.AllNames():
        dss.Circuit.SetActiveElement(f"PVSystem.{n}")
        p = dss.CktElement.Powers()
        v_pu = dss.CktElement.VoltagesMagAng()[0] / 230.0
        q_expected = 5 * np.interp(v_pu, inv.VV_X, inv.VV_Y)
        assert abs(-p[1] - q_expected) < 0.1, (n, v_pu, -p[1], q_expected)
