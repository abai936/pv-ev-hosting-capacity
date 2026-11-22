"""Stage 3a: IEEE European LV Test Feeder, NZ base case (230 V base), helpers and day runner.

The downloaded files in data/feeders/ are never edited. Every change is an OpenDSS command
issued after Master.dss has compiled. Voltages are in volts (phase to neutral), power in kVA.
"""
import time
from pathlib import Path

import numpy as np
import opendssdirect as dss

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "data" / "feeders" / "LVTestCase" / "Master.dss"
V_LOW_V, V_HIGH_V = 207.0, 253.0          # NZ limits, 230 V +/-10 % (the project notes fixed facts)
A_OP = np.exp(2j * np.pi / 3)              # 120 degree rotation operator for symmetrical components


def load_feeder(source_pu=1.00, nz_base=True, constant_p=True):
    """Compile the feeder. nz_base=True re-bases to 400/230 V; False keeps the published settings
    (source 1.05 pu, 0.416 kV base). constant_p=True widens load vminpu/vmaxpu to 0.7/1.3;
    False leaves the loads exactly as published. nz_base=False, constant_p=False is the true original. Returns the list of load names."""
    dss.Basic.ClearAll()
    # Master.dss uses relative Redirects, so compile from its own folder, then return.
    dss.Command(f'compile "{MASTER}"')
    if nz_base:
        dss.Command(f"Edit Vsource.Source pu={source_pu}")
        # 1 pu = 230 V phase (400 V line), so pu values line up with the 207-253 V limits.
        # The 11/0.416 kV transformer ratio is kept on purpose: it acts as a realistic no-load tap (PLAN b2).
        dss.Command("Set voltagebases=[11 0.4]")
        dss.Command("Calcvoltagebases")
    # Loads switch from constant power to constant impedance outside vminpu..vmaxpu. The defaults
    # (0.95 / 1.05 pu of the 0.23 kV load base) put that switch at 241.5 V, which is inside our 207-253 V
    # study range and would hide high-voltage behaviour (a load that stops drawing power as voltage
    # rises). Widening to 0.7-1.3 pu keeps loads constant-power over the whole range we study.
    if constant_p:
        dss.Command("batchedit load..* vminpu=0.7 vmaxpu=1.3")
    return list(dss.Loads.AllNames())


def _node_index():
    names = [n.lower() for n in dss.Circuit.AllNodeNames()]
    return {n: i for i, n in enumerate(names)}


def customer_nodes():
    """Node name ('34.1') for each load, in load order."""
    out = []
    for name in dss.Loads.AllNames():
        dss.Circuit.SetActiveElement(f"Load.{name}")
        out.append(dss.CktElement.BusNames()[0].lower())
    return out


def customer_voltages_v():
    """Phase-to-neutral voltage magnitude (V) at every load bus, in load order."""
    idx = _node_index()
    v = np.array(dss.Circuit.AllBusVMag())
    return v[[idx[n] for n in customer_nodes()]]


def transformer_kva(name="TR1"):
    """Apparent power (kVA) entering the transformer HV terminal: |sum P + j sum Q| over its 3 phases."""
    dss.Circuit.SetActiveElement(f"Transformer.{name}")
    p = dss.CktElement.Powers()[:6]   # terminal 1, 3 phases: P,Q pairs in kW, kvar
    return float(np.hypot(sum(p[0::2]), sum(p[1::2])))


def three_phase_nodes():
    """Index triples (a, b, c) into the node-voltage vector for buses that have nodes 1, 2 and 3."""
    idx = _node_index()
    buses = {n.split(".")[0] for n in idx}
    return [(idx[f"{b}.1"], idx[f"{b}.2"], idx[f"{b}.3"]) for b in sorted(buses)
            if all(f"{b}.{k}" in idx for k in (1, 2, 3))]


def vuf_percent(triples=None):
    """Voltage unbalance factor, VUF = |V2| / |V1| x 100 (IEC definition), at three-phase buses only.

    V1 and V2 are the positive and negative sequence phase voltages from the three phase-neutral phasors.
    Single- and two-phase buses are excluded because sequence components need all three phases.
    The 2 % limit used later is an ASSUMED European value (EN 50160 basis), not an NZ limit.
    """
    if triples is None:
        triples = three_phase_nodes()
    raw = np.array(dss.Circuit.AllBusVolts())
    v = raw[0::2] + 1j * raw[1::2]
    a, b, c = (v[[t[i] for t in triples]] for i in range(3))
    v1 = (a + A_OP * b + A_OP**2 * c) / 3
    v2 = (a + A_OP**2 * b + A_OP * c) / 3
    return 100 * np.abs(v2) / np.abs(v1)


def solve_minutes(n_minutes=1440, collect=True, on_step=None):
    """Run n_minutes 1-minute steps: mode=yearly number=1 stepsize=1m, one Solve per step.
    Returns dict of per-step arrays, plus solve time and number of non-converged steps."""
    dss.Command("Set mode=yearly stepsize=1m number=1")
    dss.Command("Set year=1")        # resets time to 0; first Solve then uses load-shape point 1
    triples = three_phase_nodes()
    nodes_idx = _node_index()
    cust_idx = [nodes_idx[n] for n in customer_nodes()]
    out = {"v_cust": [], "xfmr_kva": [], "vuf": [], "converged": []}
    t_solve = 0.0
    for _ in range(n_minutes):
        t0 = time.perf_counter()
        dss.Solution.Solve()
        t_solve += time.perf_counter() - t0
        out["converged"].append(bool(dss.Solution.Converged()))
        if collect:
            out["v_cust"].append(np.array(dss.Circuit.AllBusVMag())[cust_idx])
            out["xfmr_kva"].append(transformer_kva())
            out["vuf"].append(vuf_percent(triples).max())
        if on_step:
            on_step(out)
    out["solve_s"] = t_solve
    return out


RATINGS_CSV = ROOT / "data" / "line_ratings.csv"


def line_ratings_a():
    """Assumed continuous rating (A) per linecode, from data/line_ratings.csv (Stage 3b, research/R10)."""
    import csv
    with open(RATINGS_CSV, newline="") as fh:
        return {r["linecode"].lower(): float(r["rating_A"]) for r in csv.DictReader(fh)}


def line_loading(feeder=None):
    """Per-line loading = max phase current / assumed rating, for the current solution.

    Heating in a conductor follows I^2 R, so the worst single phase sets the thermal limit; the neutral
    is ignored (the datasheet ratings are per phase conductor). `feeder` is unused (the circuit is the
    active OpenDSS one) and kept for the agreed signature. Returns {line_name: ratio}."""
    ratings = line_ratings_a()
    out = {}
    for name in dss.Lines.AllNames():
        dss.Lines.Name(name)
        n_ph = dss.Lines.Phases()
        i_a = dss.CktElement.CurrentsMagAng()[0:2 * n_ph:2]   # terminal 1, phase conductors only
        out[name] = max(i_a) / ratings[dss.Lines.LineCode().lower()]
    return out
