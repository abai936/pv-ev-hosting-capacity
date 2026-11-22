"""Stage 6b runner: 2022 year, 30-min steps, source 1.00 pu. Y0 = no PV; Y1/Y2/Y3 = P1 at 60% (33 houses) with
3/5/8 kWp each, unity PF, no inverter control, no EV. Simulated; IEEE feeder; NZ-parameterised synthetic load;
PV modelled (PVGIS-ERA5); ratings assumed.

Usage (.venv python):
  stage6_year.py main              Y0..Y3 for diversity seed 2022 -> results/stage6_year.csv and
                                   results/stage6_year_linecodes.csv
  stage6_year.py seeds 1 2 3 4     Y0 only for the given diversity seeds -> results/stage6_year_seeds.csv
                                   and results/stage6_year_seeds_linecodes.csv
  stage6_year.py summary           rewrite the "Year time series" section of results/stage6_snapshot_summary.md
                                   from the saved CSVs (run after the snapshot script, which rewrites the file)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hc import hosting as h, l2, yearly as Y  # noqa: E402

LABEL = "simulated; IEEE feeder; NZ-parameterised synthetic load; PV modelled; ratings assumed"
CASES = [("Y0", 0.0), ("Y1", 3.0), ("Y2", 5.0), ("Y3", 8.0)]
OUT = ROOT / "results"
VUF_LIMIT_PCT = 2.0   # assumed (EN 50160 basis), same as the snapshot stages


def run_cases(seed, cases, house_kw, pv):
    n = house_kw.shape[0]
    pv_idx = h.place_p1(h.Model(1.0, True), h.n_pv_for(0.6, 55))
    rows, lc_rows = [], []
    for name, kwp in cases:
        idx = pv_idx if kwp > 0 else []
        r = Y.run_year(house_kw, pv, idx, kwp)
        m = r["model"]
        vc = r["v_cust_v"]
        hi, lo = vc > 253.0, vc < 207.0
        lr = r["line_ratio"] > 1.0
        e_load, e_loss, e_pv, e_x, err_x, err_l = Y.energy_balance(r)
        rows.append({
            "seed": seed, "case": name, "pv_kwp_per_house": kwp, "n_pv_houses": len(idx), "steps": n,
            "nonconverged": n - r["converged"],
            "cust_hours_above_253V": hi.sum() * Y.STEP_H, "distinct_hours_above_253V": hi.any(axis=1).sum() * Y.STEP_H,
            "cust_hours_below_207V": lo.sum() * Y.STEP_H, "distinct_hours_below_207V": lo.any(axis=1).sum() * Y.STEP_H,
            "v_min_V": round(float(vc.min()), 2), "v_max_V": round(float(vc.max()), 2),
            "line_hours_above_100pct_sum_over_lines": lr.sum() * Y.STEP_H,   # each line counted separately
            "distinct_hours_line_above_100pct": lr.any(axis=1).sum() * Y.STEP_H,  # a step counted once
            "max_line_loading_pct": round(100 * float(r["line_ratio"].max()), 1),
            "xfmr_max_kVA": round(float(r["kva"].max()), 1),
            "reverse_flow_hours": float((r["p_hv_kw"] < 0).sum() * Y.STEP_H),
            "vuf_max_pct": round(float(r["vuf_pct"].max()), 3),
            "vuf_hours_above_2pct": float((r["vuf_pct"] > VUF_LIMIT_PCT).sum() * Y.STEP_H),
            "E_load_kWh_dss": round(e_load, 1), "E_load_kWh_profile": round(float(house_kw.sum() * Y.STEP_H), 1),
            "E_loss_kWh": round(e_loss, 1), "E_pv_kWh_dss": round(e_pv, 1),
            "E_pv_kWh_register": round(r["pv_kwh_dss"], 1),
            "E_pv_kWh_profile": round(float(pv.sum() * Y.STEP_H * kwp * len(idx)), 1),
            "E_xfmr_in_kWh": round(e_x, 1),
            "balance_error_pct_of_xfmr": round(err_x, 4), "balance_error_pct_of_load": round(err_l, 4),
            "runtime_s": round(r["runtime_s"], 1),          # wall time of the whole case (build + 17,520 solves)
            "ms_per_step": round(1000 * r["runtime_s"] / n, 2), "label": LABEL})
        # Same overload numbers split by linecode (lines of one linecode share one assumed rating).
        codes = np.array(m.line_code)
        for c in sorted(set(codes)):
            sub = lr[:, codes == c]
            lc_rows.append({"seed": seed, "case": name, "linecode": c, "n_lines": int((codes == c).sum()),
                            "distinct_hours_above_100pct": sub.any(axis=1).sum() * Y.STEP_H,
                            "line_hours_sum_over_lines": sub.sum() * Y.STEP_H,
                            "max_loading_pct": round(100 * float(r["line_ratio"][:, codes == c].max()), 1)})
        print(seed, name, {k: v for k, v in rows[-1].items() if k != "label"}, flush=True)
    return rows, lc_rows


def md(d):
    head = "| " + " | ".join(d.columns) + " |\n|" + "---|" * len(d.columns)
    return head + "\n" + "\n".join("| " + " | ".join(str(x) for x in r) + " |" for r in d.itertuples(index=False))


def write_summary():
    df = pd.read_csv(OUT / "stage6_year.csv")
    lc = pd.read_csv(OUT / "stage6_year_linecodes.csv")
    tbl1 = df[["case", "pv_kwp_per_house", "cust_hours_above_253V", "distinct_hours_above_253V",
               "cust_hours_below_207V", "v_min_V", "v_max_V", "line_hours_above_100pct_sum_over_lines",
               "distinct_hours_line_above_100pct", "max_line_loading_pct", "xfmr_max_kVA", "reverse_flow_hours",
               "vuf_max_pct", "vuf_hours_above_2pct", "runtime_s", "ms_per_step"]]
    tbl2 = df[["case", "E_load_kWh_dss", "E_loss_kWh", "E_pv_kWh_dss", "E_xfmr_in_kWh", "balance_error_pct_of_xfmr",
               "E_pv_kWh_register", "E_pv_kWh_profile"]]
    lc_over = lc[lc.distinct_hours_above_100pct > 0]
    sec = ["", "## Year time series 2022 (Stage 6b)", "",
           f"**{LABEL}. Simulated, not measured.** 17,520 steps of 30 min, source 1.00 pu, mode=yearly, one Solve per "
           "step, house diversity seed 2022 (each house picks one of 100 feeder profiles per local day). Loads: "
           "per-house kW series as OpenDSS yearly LoadShapes. Y1 to Y3: P1 placement at 60% (33 houses), unity PF, "
           "no inverter control, no EV, PV = kWp x PVGIS-ERA5 kW-per-kWp series (Generator objects). Customer-hours "
           "count each customer separately (x 0.5 h per step); distinct hours count a step once. "
           "`line_hours_above_100pct_sum_over_lines` is the sum over lines (each overloaded line counted "
           "separately); `distinct_hours_line_above_100pct` counts a step once if any line is above 100%. Ratings "
           "are assumed. The 30-min averages hide short peaks. Run time per case is in the table (runtime_s, "
           "ms_per_step), measured on this laptop.", "", md(tbl1), "",
           "### Hours above 100 % by linecode (assumed ratings; only linecodes with overload hours)", "",
           md(lc_over) if len(lc_over) else "None.", "",
           "### Energy balance (kWh): load + losses - PV = energy into the transformer HV terminal", "", md(tbl2), ""]
    sd = OUT / "stage6_year_seeds.csv"
    if sd.exists():
        s = pd.concat([df[df.case == "Y0"], pd.read_csv(sd)]).sort_values("seed")
        sec += ["### Y0 (no PV) across house-diversity seeds", "",
                md(s[["seed", "max_line_loading_pct", "distinct_hours_line_above_100pct",
                      "line_hours_above_100pct_sum_over_lines", "xfmr_max_kVA", "distinct_hours_below_207V",
                      "v_min_V", "vuf_max_pct", "vuf_hours_above_2pct"]]), ""]
    sm = OUT / "stage6_snapshot_summary.md"
    txt = sm.read_text(encoding="utf-8").split("\n## Year time series 2022 (Stage 6b)")[0].rstrip("\n")
    sm.write_text(txt + "\n" + "\n".join(sec), encoding="utf-8")
    print("\n".join(sec))


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "main":
        house_kw, pv, _t = Y.load_year_inputs()        # data/processed, seed 2022
        rows, lc = run_cases(2022, CASES, house_kw, pv)
        pd.DataFrame(rows).to_csv(OUT / "stage6_year.csv", index=False)
        pd.DataFrame(lc).to_csv(OUT / "stage6_year_linecodes.csv", index=False)
    elif mode == "seeds":
        _hk, pv, _t = Y.load_year_inputs()
        rows, lc = [], []
        for seed in map(int, sys.argv[2:]):
            r_, l_ = run_cases(seed, CASES[:1], l2.default_house_kw(seed), pv)
            rows += r_
            lc += l_
            # save after every seed so a crash keeps finished seeds
            pd.DataFrame(rows).to_csv(OUT / "stage6_year_seeds.csv", index=False)
            pd.DataFrame(lc).to_csv(OUT / "stage6_year_seeds_linecodes.csv", index=False)
    elif mode == "summary":
        write_summary()
