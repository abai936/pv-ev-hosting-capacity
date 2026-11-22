"""Build small JSON files for the two website charts from the results CSVs.

Every value is copied or computed from a CSV in results/ (nothing typed in by hand).
Each JSON carries source_file(s) and label 'simulated'. Run from anywhere:
    python site/scripts/build_chart_data.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "site" / "src" / "data"
LABEL = "simulated"
PENS = [0.3, 0.6, 1.0]


def hc_vs_penetration():
    """L2 NZ summer-midday rows, source 1.00 pu, base model (neutral return).
    Same selection as the PLAN b2 headline (9.5 / 5.0 / 2.7 kW); the old PNG used stage4 L1 instead."""
    d = pd.read_csv(ROOT / "results" / "stage6_snapshot_hc.csv")
    b = d[(d.load_case == "L2") & (d.source_pu == 1.0) & (d.model == "neutral_return")]
    out = {"source_file": "results/stage6_snapshot_hc.csv", "label": LABEL,
           "selection": "load_case L2, source_pu 1.0, model neutral_return",
           "x_unit": "% of houses with solar", "y_unit": "kW per solar house",
           "orion_cap_kw": 10.0, "P1": [], "P2": [], "P3": []}
    for name in ("P1", "P2"):
        for pen in PENS:
            r = b[(b.placement == name) & (b.penetration == pen)].iloc[0]
            out[name].append({"penetration_pct": round(pen * 100), "hc_kw": float(r.HC_kW),
                              "binding_limit": str(r.binding_limit)})
    for pen in PENS:
        s = b[(b.placement == "P3") & (b.penetration == pen)]
        p5, p50, p95 = np.percentile(s.HC_kW.astype(float), [5, 50, 95])
        counts = s.binding_limit.value_counts().to_dict()
        out["P3"].append({"penetration_pct": round(pen * 100), "n_orders": int(len(s)),
                          "p5_kw": float(p5), "p50_kw": float(p50), "p95_kw": float(p95),
                          "binding_counts": {k: int(v) for k, v in counts.items()}})
    return out


def tradeoff():
    y = pd.read_csv(ROOT / "results" / "stage8_year.csv")
    h = pd.read_csv(ROOT / "results" / "stage8_hc.csv")
    out = {"source_files": ["results/stage8_year.csv", "results/stage8_hc.csv"], "label": LABEL,
           "year_case": "Y3: 8 kWp on 60% of houses, P1, tap 1.000, inverter kVA = kW",
           "year": [], "hc": []}
    for mode, name in (("M0", "without control"), ("M3", "with Australia A control")):
        r = y[(y["mode"] == mode) & (y.tap == 1.0) & (y.kva_ratio == 1.0)].iloc[0]
        out["year"].append({"mode": mode, "name": name, "case": str(r.case),
                            "cust_hours_above_253v": float(r.cust_hours_above_253V),
                            "hours_line_above_rating": float(r.distinct_hours_line_above_100pct)})
    for mode, name in (("M0", "without control"), ("M3", "with Australia A control")):
        for pen in PENS:
            r = h[(h.placement == "P1") & (h["mode"] == mode) & (h.tap == 1.0)
                  & (h.kva_ratio == 1.0) & (h.penetration == pen)].iloc[0]
            out["hc"].append({"mode": mode, "name": name, "penetration_pct": round(pen * 100),
                              "hc_kw": float(r.HC_kW), "binding_limit": str(r.binding_limit)})
    return out


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for fname, data in (("chart_hc_vs_penetration.json", hc_vs_penetration()),
                        ("chart_tradeoff.json", tradeoff())):
        (OUT / fname).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print("wrote", OUT / fname)
