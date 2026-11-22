"""Stage 3 neutral-return check: original IEEE European LV feeder vs the "neutral-return" variant
(src/hc/neutral.py). Source 1.00 pu, NZ 230 V base. Synthetic, NZ-parameterised data.

Prints the linecode facts and the service-cable hand check, runs four 1-day cases
(base no PV, and the spike PV setup 55 x 5 kVA, synthetic half-sine, no control; each original vs variant)
and writes results/stage3_neutral_check.csv."""
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import opendssdirect as dss
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from hc import feeder as f  # noqa: E402
from hc import neutral as nr  # noqa: E402
import stage3_invcontrol_spike as spike  # noqa: E402  (same PV setup as the spike)

NOTE = "synthetic NZ-parameterised feeder; SYNTHETIC half-sine irradiance; simulated, not measured"


def linecode_facts():
    f.load_feeder()
    use = Counter()
    for n in dss.Lines.AllNames():
        dss.Lines.Name(n)
        use[dss.Lines.LineCode().lower()] += 1
    rows = []
    for c in sorted(use):
        dss.LineCodes.Name(c)
        r1, r0 = dss.LineCodes.R1(), dss.LineCodes.R0()
        rows.append({"linecode": c, "nphases": dss.LineCodes.Phases(), "R1": r1, "X1": dss.LineCodes.X1(),
                     "R0": r0, "X0": dss.LineCodes.X0(), "R0/R1": round(r0 / r1, 2),
                     "Rn/Rp=(R0-R1)/3R1": round((r0 - r1) / (3 * r1), 2), "lines": use[c]})
    return pd.DataFrame(rows)


def two_core_path_lengths():
    """Length (m) of 2c/35_SAC lines on the path from the transformer to each load."""
    f.load_feeder()
    adj, info = defaultdict(list), {}
    for n in dss.Lines.AllNames():
        dss.Lines.Name(n)
        a, b = dss.Lines.Bus1().split(".")[0], dss.Lines.Bus2().split(".")[0]
        adj[a].append((b, n)); adj[b].append((a, n))
        info[n] = (dss.Lines.LineCode().lower(), dss.Lines.Length())
    par, q = {"1": None}, ["1"]
    while q:
        u = q.pop(0)
        for v, n in adj[u]:
            if v not in par:
                par[v] = (u, n); q.append(v)
    out = []
    for bus in (b.split(".")[0] for b in f.customer_nodes()):
        tot = 0.0
        while par[bus]:
            lc, length = info[par[bus][1]]
            tot += length if lc in nr.NO_RETURN_CODES else 0.0
            bus = par[bus][0]
        out.append(tot)
    return np.array(out)


def run_day(variant, pv):
    f.load_feeder(1.00, True)
    dss.Command(f"Set maxcontroliter={spike.MAXITER}")
    if variant:
        nr.apply_neutral_return(1.0)
    if pv:
        spike.add_pv(spike.synthetic_irradiance())
    ratings = f.line_ratings_a()
    names = [n.lower() for n in dss.PDElements.AllNames()]
    line_pos, rate = [], []
    for k, n in enumerate(names):
        if n.startswith("line."):
            dss.Lines.Name(n.split(".", 1)[1])
            line_pos.append(k); rate.append(ratings[dss.Lines.LineCode().lower()])
    line_pos, rate = np.array(line_pos), np.array(rate)
    load_max = []

    def grab(_):
        i = np.array(dss.PDElements.AllMaxCurrents())    # max over phase conductors, terminal 1
        load_max.append((i[line_pos] / rate).max())

    r = f.solve_minutes(on_step=grab)
    v = np.array(r["v_cust"])
    return {"case": "pv_55x5kVA_no_control" if pv else "base_no_pv",
            "model": "neutral_return_k1" if variant else "original",
            "v_min_V": round(v.min(), 2), "v_max_V": round(v.max(), 2),
            "minutes_above_253V": int((v.max(axis=1) > f.V_HIGH_V).sum()),
            "minutes_below_207V": int((v.min(axis=1) < f.V_LOW_V).sum()),
            "max_line_loading_pct_assumed_ratings": round(100 * max(load_max), 1),
            "xfmr_max_kVA": round(max(r["xfmr_kva"]), 2),
            "nonconverged_steps": sum(not c for c in r["converged"]), "note": NOTE}


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    print(linecode_facts().to_string(index=False))
    L = two_core_path_lengths()
    print(f"\n2c/35_SAC length on each customer's path (m): min {L.min():.1f}, median {np.median(L):.1f}, "
          f"max {L.max():.1f}")
    for variant in (False, True):
        f.load_feeder()
        if variant:
            nr.apply_neutral_return(1.0)
        for ld in ("load1", "load49"):
            f.load_feeder()
            if variant:
                nr.apply_neutral_return(1.0)
            h = nr.service_drop_check(ld, 5.0)
            print(f"hand check {'variant ' if variant else 'original'} {ld} {h['line']} {h['linecode']} "
                  f"{h['length_m']:.2f} m I={h['I_A']:.2f} A: OpenDSS dV={h['dV_opendss_V']:.4f} V, "
                  f"one-conductor={h['dV_one_conductor_V']:.4f} V, loop={h['dV_loop_V']:.4f} V")
    rows = [run_day(var, pv) for pv in (False, True) for var in (False, True)]
    df = pd.DataFrame(rows)
    (ROOT / "results").mkdir(exist_ok=True)
    df.to_csv(ROOT / "results" / "stage3_neutral_check.csv", index=False)
    print(df.drop(columns="note").to_string(index=False))
