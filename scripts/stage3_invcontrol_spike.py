"""Stage 3a InvControl speed spike: 55 x 5 kVA single-phase PV, one InvControl (VV_VW, AS/NZS 4777.2 Australia A).
One day, 1-minute steps, source 1.00 pu. Irradiance is a SYNTHETIC clear-sky half-sine 06:00-20:00.
Writes results/stage3_invcontrol_spike.csv. Synthetic, NZ-parameterised data."""
import sys
from pathlib import Path

import numpy as np
import opendssdirect as dss
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hc import feeder as f  # noqa: E402
from hc import inverter as inv  # noqa: E402

PV_KVA = 5.0
# ASSUMPTION: varFollowInverter=Yes, residential inverters exchange no vars when not producing (night Q = 0).
MAXITER = 100   # raised from default 15; see note in CSV / report


def synthetic_irradiance(n=1440):
    """Half-sine, 0 outside 06:00 (min 360) to 20:00 (min 1200), peak 1.0 pu (clear-sky shape, synthetic)."""
    t = np.arange(1, n + 1)
    return np.where((t >= 360) & (t <= 1200), np.sin(np.pi * (t - 360) / 840), 0.0)


def add_pv(irr):
    dss.Command(f"New Loadshape.SynthClearSky npts=1440 minterval=1 mult=({','.join(f'{x:.5f}' for x in irr)})")
    for name in dss.Loads.AllNames():
        dss.Circuit.SetActiveElement(f"Load.{name}")
        bus = dss.CktElement.BusNames()[0]          # e.g. '34.1': same bus AND phase as the load
        dss.Command(f"New PVSystem.PV_{name} phases=1 bus1={bus} kV=0.23 kVA={PV_KVA} Pmpp={PV_KVA} "
                    f"irradiance=1 temperature=25 pf=1 %cutin=0.1 %cutout=0.1 varFollowInverter=Yes vminpu=0.7 vmaxpu=1.3 yearly=SynthClearSky daily=SynthClearSky")


def add_invcontrol():
    inv.add_invcontrol(dss.PVsystems.AllNames())


def run(label, pv, ctl, irr):
    f.load_feeder(1.00, True)
    dss.Command(f"Set maxcontroliter={MAXITER}")
    if pv:
        add_pv(irr)
    if ctl:
        add_invcontrol()
    pvn = list(dss.PVsystems.AllNames())
    p_pv = []

    def grab(out):
        tot = 0.0
        for n in pvn:
            dss.Circuit.SetActiveElement(f"PVSystem.{n}")
            tot += -sum(dss.CktElement.Powers()[0::2])   # kW delivered (generation is negative)
        p_pv.append(tot)

    r = f.solve_minutes(on_step=grab if pv else None)
    v = np.array(r["v_cust"])
    p_pv = np.array(p_pv) if pv else np.zeros(1440)
    avail_kwh = len(pvn) * PV_KVA * irr.sum() / 60 if pv else 0.0
    return {
        "scenario": label, "pv_count": len(pvn),
        "solve_ms_per_step": round(1000 * r["solve_s"] / 1440, 3),
        "nonconverged_steps": sum(not c for c in r["converged"]),
        "v_max_V": round(v.max(), 2), "minutes_above_253V": int((v.max(axis=1) > f.V_HIGH_V).sum()),
        "pv_energy_kWh": round(p_pv.sum() / 60, 1), "pv_available_kWh": round(avail_kwh, 1),
        "curtailed_kWh_volt_watt_plus_var_priority_kVA_limit": round(avail_kwh - p_pv.sum() / 60, 1) if ctl else float("nan"),
        "maxcontroliter": MAXITER,
        "irradiance_note": "SYNTHETIC clear-sky half-sine 06:00-20:00; synthetic NZ-parameterised feeder",
    }


if __name__ == "__main__":
    irr = synthetic_irradiance()
    rows = [run("no_pv", False, False, irr), run("pv_no_control", True, False, irr), run("pv_vv_vw", True, True, irr)]
    df = pd.DataFrame(rows)
    (ROOT / "results").mkdir(exist_ok=True)
    df.to_csv(ROOT / "results" / "stage3_invcontrol_spike.csv", index=False)
    print(df.drop(columns="irradiance_note").to_string(index=False))
