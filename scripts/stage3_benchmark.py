"""Stage 3a benchmark: our OpenDSS run vs published solutions of the IEEE European LV feeder.
Cases: (a) original default loads, (b) constant-P loads (vmaxpu 1.3). References: published OpenDSS and GridLAB-D
snapshots at minutes 1, 566, 1440, compared at all 55 load nodes in volts (phase to neutral).
Writes results/stage3_benchmark.csv."""
import sys
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hc import feeder as f  # noqa: E402

SOL = f.ROOT / "data" / "feeders" / "ieee_zip" / "Solutions"
FILES = {1: "Snapshot_1min_Initialization_Off Peak.xlsx", 566: "Snapshot_566min_On Peak.xlsx",
         1440: "Snapshot_1440min_End.xlsx"}


def published_opendss(minute):
    """Sheet 'Voltages': Bus, BasekV, then (Node, Magnitude, Angle, pu) x3. Returns {'bus.node': V}."""
    ws = openpyxl.load_workbook(SOL / "OpenDSS" / "Snapshots" / FILES[minute], read_only=True)["Voltages"]
    t = {}
    for row in list(ws.iter_rows(values_only=True))[1:]:
        for k in range(3):
            node, mag = row[2 + 4 * k], row[3 + 4 * k]
            if node is not None and mag is not None:
                t[f"{str(row[0]).strip().lower()}.{int(node)}"] = float(mag)
    return t


def published_gridlabd(minute):
    """Sheet 'Voltages': 1 comment row, header, then node_name, voltA_mag, angle, voltB..., voltC...
    Node 'Bus34' phase 1/2/3 -> A/B/C. Returns {'34.1': V}."""
    ws = openpyxl.load_workbook(SOL / "GridLAB-D" / "Snapshots" / FILES[minute], read_only=True)["Voltages"]
    t = {}
    for row in list(ws.iter_rows(values_only=True))[2:]:
        name = str(row[0]).strip().lower()
        name = name[3:] if name.startswith("bus") else name
        for k in range(3):
            if row[1 + 2 * k] is not None:
                t[f"{name}.{k + 1}"] = float(row[1 + 2 * k])
    return t


def our_voltages(minute, constant_p):
    f.load_feeder(nz_base=False, constant_p=constant_p)      # true original source (1.05 pu, 0.416 kV)
    f.solve_minutes(n_minutes=minute, collect=False)
    return f.customer_voltages_v(), f.customer_nodes()


def run():
    rows = []
    for case, cp in (("a_default_loads", False), ("b_constant_P", True)):
        for minute in FILES:
            ours, nodes = our_voltages(minute, cp)
            for ref, tab in (("published_OpenDSS", published_opendss(minute)),
                             ("published_GridLAB-D", published_gridlabd(minute))):
                err = np.abs(ours - np.array([tab[n] for n in nodes]))
                rows.append({"case": case, "minute": minute, "reference": ref,
                             "max_abs_err_V": round(err.max(), 4), "mean_abs_err_V": round(err.mean(), 4)})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = run()
    df.to_csv(ROOT / "results" / "stage3_benchmark.csv", index=False)
    print(df.to_string(index=False))
