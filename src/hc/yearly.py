"""Stage 6b: year time series (30-min steps) on the IEEE European LV feeder with NZ-parameterised profiles.

Loads are OpenDSS yearly LoadShapes (kW = 1 base, multiplier = the house's kW series), PV is one Generator per
PV house (kW = kWp base, multiplier = PV kW per kWp), one Solve per step in mode=yearly. OpenDSS then does the
time stepping in C instead of 55 Python calls per step. House i in data/processed = i-th load in OpenDSS order.
Simulated; synthetic NZ-parameterised load; modelled PV; ratings assumed.
"""
import time
from pathlib import Path

import numpy as np
import opendssdirect as dss

from . import feeder as f
from . import hosting as h

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
STEP_H = 0.5


def load_year_inputs():
    """(house_kw[steps, 55] float64, pv_kw_per_kwp[steps], time_utc strings)."""
    import pandas as pd
    z = np.load(PROC / "house_load_kw.npz")
    pv = pd.read_csv(PROC / "avg_house_and_pv_30min.csv")["pv_kw_per_kwp"].to_numpy(float)
    return z["kw"].astype(float), pv, z["time_utc"]


def _new_shape(name, mult):
    dss.LoadShape.New(name)
    dss.LoadShape.Npts(len(mult))
    dss.LoadShape.HrInterval(STEP_H)
    dss.LoadShape.UseActual(False)
    dss.LoadShape.PMult(np.ascontiguousarray(mult, dtype=float))


def run_year(house_kw, pv_per_kwp, pv_idx=(), kwp=0.0, n_steps=None, start=0, source_pu=1.0,
             collect_pv_per_step=True, ev_kw=None, ev_idx=()):
    """Build a fresh model and run n_steps 30-min steps from `start`. No inverter control, unity PF.

    house_kw: (steps, 55) kW. pv_idx: load indices with PV. kwp: PV size per house. Returns a dict of arrays
    and totals. Stage 7: ev_kw (steps, 55) kW per house and ev_idx = houses that charge; each gets an extra
    unity-PF constant-power Load "EV_<house>" at its own node, driven by its column of ev_kw. The shapes are sliced to the window so step 0 of the run is point `start` of the year."""
    t0 = time.perf_counter()
    m = h.Model(source_pu, True)
    n_steps = n_steps or house_kw.shape[0] - start
    sl = slice(start, start + n_steps)
    for i, n in enumerate(m.loads):
        _new_shape(f"nz_{n}", house_kw[sl, i])
        dss.Loads.Name(n)
        dss.Loads.kW(1.0)                       # base 1 kW, so the shape multiplier IS the kW (pf 0.95 kept)
        dss.Loads.Yearly(f"nz_{n}")
    m.set_case("L0", list(pv_idx), load_kw=m.cases["L0"])      # enables the PV generators, loads zeroed ...
    for n in m.loads:                                        # ... so restore the 1 kW base for the shapes
        dss.Loads.Name(n)
        dss.Loads.kW(1.0)
    if len(pv_idx):
        _new_shape("nz_pv", pv_per_kwp[sl])
        for i in pv_idx:
            dss.Generators.Name(f"PV_{m.loads[i]}")
            dss.Generators.kW(kwp)
            dss.Generators.kvar(0.0)             # unity PF
            dss.Generators.Yearly("nz_pv")
    for i in ev_idx:                                  # EV = extra load shape on the customer's own node/phase
        _new_shape(f"ev_{m.loads[i]}", ev_kw[sl, i])
        dss.Command(f"New Load.EV_{m.loads[i]} phases=1 bus1={m.nodes[i]} kV=0.23 kW=1 pf=1 model=1 "
                    f"vminpu=0.7 vmaxpu=1.3 yearly=ev_{m.loads[i]}")
    dss.Command(f"Set mode=yearly stepsize=30m number=1")
    dss.Command("Set year=1")

    triples, cust_idx = m.triples, m.cust_idx
    names = [x.lower() for x in dss.PDElements.AllNames()]
    line_pos = [names.index("line." + n.lower()) for n in m.line_names]
    rating = np.array(m.line_rating_a)
    v_cust = np.empty((n_steps, len(cust_idx)), np.float32)
    line_ratio = np.empty((n_steps, len(line_pos)), np.float32)
    p_hv = np.empty(n_steps)
    kva = np.empty(n_steps)
    loss_kw = np.empty(n_steps)
    vuf = np.empty(n_steps)
    pv_kw = np.zeros(n_steps)
    ev_step_kw = np.zeros(n_steps)
    load_kw = np.zeros(n_steps)
    ok = 0
    load_elems = [f"Load.{n}" for n in m.loads]
    ev_elems = [f"Load.EV_{m.loads[i]}" for i in ev_idx]
    gens = [f"Generator.PV_{m.loads[i]}" for i in pv_idx]
    for k in range(n_steps):
        dss.Solution.Solve()
        ok += bool(dss.Solution.Converged())
        v_cust[k] = np.array(dss.Circuit.AllBusVMag())[cust_idx]
        line_ratio[k] = np.array(dss.PDElements.AllMaxCurrents())[line_pos] / rating
        dss.Circuit.SetActiveElement("Transformer.tr1")
        p = dss.CktElement.Powers()[:6]               # HV terminal, 3 phases, kW and kvar
        p_hv[k] = sum(p[0::2])
        kva[k] = np.hypot(p_hv[k], sum(p[1::2]))
        loss_kw[k] = dss.Circuit.Losses()[0] / 1000.0
        vuf[k] = f.vuf_percent(triples).max()
        for e in load_elems:                          # what the loads actually drew (kW, positive = consumed)
            dss.Circuit.SetActiveElement(e)
            load_kw[k] += sum(dss.CktElement.Powers()[0::2])
        for e in ev_elems:                            # what the EVs actually drew (kW)
            dss.Circuit.SetActiveElement(e)
            ev_step_kw[k] += sum(dss.CktElement.Powers()[0::2])
        if collect_pv_per_step:
            for g in gens:
                dss.Circuit.SetActiveElement(g)
                pv_kw[k] += -sum(dss.CktElement.Powers()[0::2])    # OpenDSS reports generation as negative
    # Generator energy register (kWh): an independent OpenDSS-side total of what the PV delivered.
    pv_kwh = 0.0
    for i in pv_idx:
        dss.Generators.Name(f"PV_{m.loads[i]}")
        pv_kwh += dss.Generators.RegisterValues()[0]
    return {"model": m, "v_cust_v": v_cust, "line_ratio": line_ratio, "p_hv_kw": p_hv, "kva": kva,
            "loss_kw": loss_kw, "vuf_pct": vuf, "pv_kw_per_step": pv_kw, "ev_kw_per_step": ev_step_kw, "load_kw": load_kw,
            "converged": ok, "n_steps": n_steps, "pv_kwh_dss": pv_kwh,
            "runtime_s": time.perf_counter() - t0}


def energy_balance(r):
    """Hand check: load + losses - PV = energy entering the transformer HV terminal (all in kWh, 30-min steps).
    Load and PV are what OpenDSS drew/delivered per step; losses are OpenDSS total circuit PD losses. Returns
    (e_load, e_loss, e_pv, e_xfmr_in, error_pct of e_xfmr_in, error_pct of e_load)."""
    e_load = r["load_kw"].sum() * STEP_H
    e_loss = r["loss_kw"].sum() * STEP_H
    e_pv = r["pv_kw_per_step"].sum() * STEP_H
    e_x = r["p_hv_kw"].sum() * STEP_H
    err = e_load + e_loss - e_pv - e_x
    return e_load, e_loss, e_pv, e_x, 100 * err / e_x, 100 * err / e_load


def energy_balance_ev(r):
    """Stage 7 hand check: house load + EV + losses - PV = energy into the transformer HV terminal (kWh).
    Returns (e_load, e_ev, e_loss, e_pv, e_xfmr_in, error_pct of e_xfmr_in)."""
    e_load, e_ev = r["load_kw"].sum() * STEP_H, r["ev_kw_per_step"].sum() * STEP_H
    e_loss, e_pv, e_x = r["loss_kw"].sum() * STEP_H, r["pv_kw_per_step"].sum() * STEP_H, r["p_hv_kw"].sum() * STEP_H
    return e_load, e_ev, e_loss, e_pv, e_x, 100 * (e_load + e_ev + e_loss - e_pv - e_x) / e_x
