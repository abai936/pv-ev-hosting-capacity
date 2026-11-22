"""Website chart data: every JSON value must equal its source CSV value, and the headline
numbers must equal those printed in results/stage8_summary.md. Simulated data only."""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "site" / "src" / "data"
R = ROOT / "results"


def load(name):
    p = DATA / name
    if not p.exists():
        pytest.fail(f"{p} missing: run python site/scripts/build_chart_data.py")
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def hc():
    return load("chart_hc_vs_penetration.json")


@pytest.fixture(scope="module")
def tr():
    return load("chart_tradeoff.json")


def test_labels_and_sources(hc, tr):
    assert hc["label"] == "simulated" and tr["label"] == "simulated"
    assert (ROOT / hc["source_file"]).exists()
    for f in tr["source_files"]:
        assert (ROOT / f).exists()


def test_hc_matches_stage6_csv(hc):
    d = pd.read_csv(R / "stage6_snapshot_hc.csv")
    b = d[(d.load_case == "L2") & (d.source_pu == 1.0) & (d.model == "neutral_return")]
    for name in ("P1", "P2"):
        assert len(hc[name]) == 3
        for pt in hc[name]:
            row = b[(b.placement == name) & (np.isclose(b.penetration, pt["penetration_pct"] / 100))]
            assert len(row) == 1
            assert pt["hc_kw"] == float(row.HC_kW.iloc[0])
            assert pt["binding_limit"] == row.binding_limit.iloc[0]
    for pt in hc["P3"]:
        s = b[(b.placement == "P3") & np.isclose(b.penetration, pt["penetration_pct"] / 100)].HC_kW.astype(float)
        assert pt["n_orders"] == len(s) == 50
        p5, p50, p95 = np.percentile(s, [5, 50, 95])
        assert (pt["p5_kw"], pt["p50_kw"], pt["p95_kw"]) == (float(p5), float(p50), float(p95))
        assert sum(pt["binding_counts"].values()) == len(s)


def test_tradeoff_matches_stage8_csvs(tr):
    y = pd.read_csv(R / "stage8_year.csv")
    for pt in tr["year"]:
        row = y[y.case == pt["case"]]
        assert len(row) == 1
        assert pt["cust_hours_above_253v"] == float(row.cust_hours_above_253V.iloc[0])
        assert pt["hours_line_above_rating"] == float(row.distinct_hours_line_above_100pct.iloc[0])
    h = pd.read_csv(R / "stage8_hc.csv")
    assert len(tr["hc"]) == 6
    for pt in tr["hc"]:
        row = h[(h.placement == "P1") & (h["mode"] == pt["mode"]) & (h.tap == 1.0) & (h.kva_ratio == 1.0)
                & np.isclose(h.penetration, pt["penetration_pct"] / 100)]
        assert len(row) == 1
        assert pt["hc_kw"] == float(row.HC_kW.iloc[0])
        assert pt["binding_limit"] == row.binding_limit.iloc[0]


def test_headlines_match_stage8_summary(tr, hc):
    md = (R / "stage8_summary.md").read_text(encoding="utf-8")
    y = {p["mode"]: p for p in tr["year"]}
    # "from 1330.0 to 38.5" customer-hours above 253 V
    assert f"from {y['M0']['cust_hours_above_253v']:.1f} to {y['M3']['cust_hours_above_253v']:.1f}" in md
    # "go from 326.5 (M0) to 582.5 (M3)"
    assert f"from {y['M0']['hours_line_above_rating']:.1f} (M0) to {y['M3']['hours_line_above_rating']:.1f} (M3)" in md
    # "M0 9.5 / 5.0 / 2.7 kW vs M3 9.3 / 4.9 / 2.7 kW" (summary rounds to 0.1 kW)
    def trio(mode):
        return " / ".join(f"{p['hc_kw']:.1f}" for p in tr["hc"] if p["mode"] == mode)
    assert f"M0 {trio('M0')} kW vs M3 {trio('M3')} kW" in md
    # the flagship chart's balanced P1 points are the same M0 numbers (to 0.1 kW)
    assert " / ".join(f"{p['hc_kw']:.1f}" for p in hc["P1"]) == trio("M0")
