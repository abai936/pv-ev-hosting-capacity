"""Stage 9: re-run three earlier hand checks against the FINAL code and write results/stage9_recheck.csv.
(a) Stage 4 far-end voltage rise at 5 kW (hosting.hand_check), tolerance 3%.
(b) Stage 7 EV 7.4 kW far-end drop and 32.2 A (ev_hosting.hand_check), tolerance 3%, 0.01 A.
(c) Stage 8 volt-var Q at 1.0826 pu = -0.30 S = -1.5 kvar for 5 kVA, tolerance 0.1 kvar (same function as the test).
(d) Stage 3 benchmark vs published OpenDSS and GridLAB-D snapshots (constant-P, tol 0.05 V; default loads, tol 1.0 V).
All values are simulated; (a) and (b) share the model's path resistance, so they are not fully independent."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
from hc import ev_hosting as E, hosting as h  # noqa: E402


def row(check, quantity, expected, got, tol, unit, how):
    err = got - expected
    return {"check": check, "quantity": quantity, "expected": expected, "got": got, "error": err,
            "tolerance": tol, "unit": unit, "pass": bool(abs(err) <= tol), "how_expected": how}


def main():
    rows = []
    skipped = False
    pred, sim, name, n = h.hand_check(5.0)
    rows.append(row("S4 far-end rise 5 kW", f"rise at {name}", pred, sim, 0.03 * pred, "V",
                    "Re(sum Z)*P/V_solved (shares path_r with model)"))
    pred, sim, name, n, i_nom = E.hand_check()
    rows.append(row("S7 EV nominal current", "I = 7400/230", 7400 / 230, i_nom, 0.01, "A", "P/V"))
    rows.append(row("S7 EV far-end drop 7.4 kW", f"drop at {name}", pred, sim, 0.03 * pred, "V",
                    "Re(sum Z)*P/V_solved (shares path_r with model)"))
    import test_stage8 as t8
    v, p, q = t8._stiff(1.0826 * 230, "M2", irradiance=0.5)
    rows.append(row("S8 volt-var Q at 1.0826 pu", "Q", -1.5, q, 0.1, "kvar", "-0.60*(1.0826-1.0435)/(1.1217-1.0435)*5 kVA"))
    rows.append(row("S8 volt-var P at 50% sun", "P", 2.5, p, 0.05, "kW", "0.5 x 5 kW, no clipping"))
    import stage3_benchmark as b
    if (b.SOL / "OpenDSS" / "Snapshots").exists():
        for case, cp, tol in (("constant_P", True, 0.05), ("default_loads", False, 1.0)):
            for minute in b.FILES:
                ours, nodes = b.our_voltages(minute, cp)
                for ref, tab in (("OpenDSS", b.published_opendss(minute)), ("GridLAB-D", b.published_gridlabd(minute))):
                    e = np.abs(ours - np.array([tab[k] for k in nodes])).max()
                    rows.append(row(f"S3 benchmark {case}", f"max |dV| min {minute} vs {ref}", 0.0, float(e), tol, "V",
                                    "published solution, 55 load nodes"))
    else:
        # Never look like a pass: a SKIPPED row goes into the CSV and the script exits non-zero.
        print("*** SKIPPED: published snapshots not downloaded; S3 benchmark NOT checked ***")
        rows.append({"check": "S3 benchmark", "quantity": "published snapshots", "expected": float("nan"),
                     "got": float("nan"), "error": float("nan"), "tolerance": float("nan"), "unit": "",
                     "pass": False, "status": "SKIPPED", "how_expected": "snapshots missing (scripts/download_data.py)"})
        skipped = True
    df = pd.DataFrame(rows)
    if "status" not in df:
        df["status"] = ""
    df["status"] = df["status"].where(df["status"].notna() & (df["status"] != ""), df["pass"].map({True: "PASS", False: "FAIL"}))
    df.to_csv(ROOT / "results" / "stage9_recheck.csv", index=False)
    print(df[["check", "quantity", "expected", "got", "error", "tolerance", "status"]].to_string())
    return 0 if df["pass"].all() else 1


if __name__ == "__main__":
    sys.exit(main())
