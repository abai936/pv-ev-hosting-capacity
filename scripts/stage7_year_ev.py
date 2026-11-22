"""Stage 7b runner: 2022 year, 30-min steps, source 1.00 pu, NO PV. Y0 = no EV; E30 / E60 = EVs at 30 % (17) and
60 % (33) of the 55 houses, P1 placement (ceil rule), 7.4 kW charger profile from data/processed/ev_kw.npz.
Diversity seed 2022, plus E60 for seeds 1 to 4. Same metrics as stage6_year.csv.
Simulated; IEEE feeder; NZ-parameterised synthetic load and EV sessions; ratings and VUF limit assumed.

Usage (.venv python): stage7_year_ev.py augment (add EV peak + Y0 baseline columns to the CSV, no load flow)
                       stage7_year_ev.py all   (7 runs, sequential, writes results/stage7_year_ev.csv + _linecodes.csv)
                      stage7_year_ev.py summary   (rewrite the year section of results/stage7_summary.md)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hc import hosting as h, l2, yearly as Y  # noqa: E402

LABEL = "simulated; IEEE feeder; NZ-parameterised synthetic load and EV sessions; ratings and VUF limit assumed"
OUT = ROOT / "results"
VUF_LIMIT_PCT = 2.0
RUNS = [(2022, "Y0", 0.0), (2022, "E30", 0.3), (2022, "E60", 0.6)] + [(s, "E60", 0.6) for s in (1, 2, 3, 4)]


EV_KW_RATED = 7.4


def ev_peak_columns(evs, has_ev):
    """EV simultaneity from the EV kW profile of the EV houses (n_steps x n_ev).
    n_ev_active_max_any_nonzero_half_hour = most EVs with a non-zero kW in the same half-hour (a count of
    charging EVs; any non-zero step counts, even a partial one). Peak coincident EV kW is the largest total EV kW
    in one half-hour; EV-equivalents = that kW / 7.4 kW."""
    if not has_ev:
        return {"n_ev_active_max_any_nonzero_half_hour": 0, "peak_coincident_ev_kw": 0.0, "peak_ev_equivalents": 0.0}
    pk = float(evs.sum(axis=1).max())
    return {"n_ev_active_max_any_nonzero_half_hour": int((evs > 0).sum(axis=1).max()),
            "peak_coincident_ev_kw": round(pk, 1), "peak_ev_equivalents": round(pk / EV_KW_RATED, 2)}


def y0_baseline_columns(df):
    """Add the matching Stage 6 Y0 seed baseline (no EV, no PV, same house-load seed) next to each E60 row
    and EV effect = E60 minus Y0. Seed 2022 uses this file's own Y0 row. Stage 6 Y0 is NOT re-run."""
    s6 = pd.read_csv(OUT / "stage6_year_seeds.csv")
    s6 = s6[s6.case == "Y0"].set_index("seed")
    s6lc = pd.read_csv(OUT / "stage6_year_seeds_linecodes.csv")
    own = df[(df.case == "Y0") & (df.seed == 2022)].iloc[0]
    def y0(seed):
        if seed == 2022:
            return {"v": own.v_min_V, "ch": own.cust_hours_below_207V, "dh": own.distinct_hours_below_207V,
                    "ld": own.distinct_hours_line_above_100pct, "ls": own.line_hours_above_100pct_sum_over_lines}
        r = s6.loc[seed]
        return {"v": r.v_min_V, "ch": r.cust_hours_below_207V, "dh": r.distinct_hours_below_207V,
                "ld": r.distinct_hours_line_above_100pct, "ls": r.line_hours_above_100pct_sum_over_lines}
    cols = {k: [] for k in ("y0_v_min_V", "y0_cust_hours_below_207V", "y0_distinct_hours_below_207V",
                            "y0_distinct_hours_line_above_100pct", "y0_line_hours_sum",
                            "delta_v_min_V", "delta_distinct_hours_below_207V", "delta_distinct_hours_line_above_100pct")}
    for r in df.itertuples():
        if r.case != "E60":
            for k in cols:
                cols[k].append(np.nan)
            continue
        b = y0(int(r.seed))
        for k, v in zip(list(cols)[:5], (b["v"], b["ch"], b["dh"], b["ld"], b["ls"])):
            cols[k].append(v)
        cols["delta_v_min_V"].append(round(r.v_min_V - b["v"], 2))
        cols["delta_distinct_hours_below_207V"].append(r.distinct_hours_below_207V - b["dh"])
        cols["delta_distinct_hours_line_above_100pct"].append(r.distinct_hours_line_above_100pct - b["ld"])
    for k, v in cols.items():
        df[k] = v
    return df


def augment_csv():
    """Post-hoc update of results/stage7_year_ev.csv WITHOUT re-running the year: EV peak columns from the EV
    profile (needs only the placement, no load flow) and the Y0 seed baselines."""
    df = pd.read_csv(OUT / "stage7_year_ev.csv")
    ev = np.load(ROOT / "data" / "processed" / "ev_kw.npz")["kw"].astype(float)
    m0 = h.Model(1.0, True)
    pk = []
    for r in df.itertuples():
        idx = h.place_p1(m0, h.n_pv_for(r.ev_penetration, 55)) if r.ev_penetration > 0 else []
        pk.append(ev_peak_columns(ev[:r.steps, idx] if idx else None, bool(idx)))
    df = df.drop(columns=[c for c in ("max_simultaneous_EVs",) if c in df.columns])
    for k in pk[0]:
        df[k] = [p[k] for p in pk]
    df = df.drop(columns=[c for c in df.columns if c.startswith(("y0_", "delta_"))])
    y0_baseline_columns(df).to_csv(OUT / "stage7_year_ev.csv", index=False)


def one_run(seed, name, pen, house_kw, ev_kw, n_steps=None):
    m0 = h.Model(1.0, True)
    idx = h.place_p1(m0, h.n_pv_for(pen, 55)) if pen > 0 else []
    r = Y.run_year(house_kw, np.zeros(house_kw.shape[0]), (), 0.0, n_steps=n_steps, ev_kw=ev_kw, ev_idx=idx)
    m, vc, n = r["model"], r["v_cust_v"], r["n_steps"]
    lo, hi, lr = vc < 207.0, vc > 253.0, r["line_ratio"] > 1.0
    e_load, e_ev, e_loss, _e_pv, e_x, err = Y.energy_balance_ev(r)
    evs = ev_kw[:n, idx] if len(idx) else np.zeros((n, 1))
    row = {"seed": seed, "case": name, "ev_penetration": pen, "n_ev_houses": len(idx), "steps": n,
           "nonconverged": n - r["converged"],
           "cust_hours_above_253V": hi.sum() * Y.STEP_H,
           "cust_hours_below_207V": lo.sum() * Y.STEP_H, "distinct_hours_below_207V": lo.any(axis=1).sum() * Y.STEP_H,
           "v_min_V": round(float(vc.min()), 2), "v_max_V": round(float(vc.max()), 2),
           "line_hours_above_100pct_sum_over_lines": lr.sum() * Y.STEP_H,
           "distinct_hours_line_above_100pct": lr.any(axis=1).sum() * Y.STEP_H,
           "max_line_loading_pct": round(100 * float(r["line_ratio"].max()), 1),
           "xfmr_max_kVA": round(float(r["kva"].max()), 1),
           "vuf_max_pct": round(float(r["vuf_pct"].max()), 3),
           "vuf_hours_above_2pct": float((r["vuf_pct"] > VUF_LIMIT_PCT).sum() * Y.STEP_H),
           **ev_peak_columns(evs, bool(len(idx))),
           "E_load_kWh_dss": round(e_load, 1), "E_ev_kWh_dss": round(e_ev, 1),
           "E_ev_kWh_profile": round(float(evs.sum() * Y.STEP_H), 1) if len(idx) else 0.0,
           "E_loss_kWh": round(e_loss, 1), "E_xfmr_in_kWh": round(e_x, 1),
           "balance_error_pct_of_xfmr": round(err, 5),
           "runtime_s": round(r["runtime_s"], 1), "label": LABEL}
    codes = np.array(m.line_code)
    lcs = [{"seed": seed, "case": name, "linecode": c, "n_lines": int((codes == c).sum()),
            "distinct_hours_above_100pct": lr[:, codes == c].any(axis=1).sum() * Y.STEP_H,
            "line_hours_sum_over_lines": lr[:, codes == c].sum() * Y.STEP_H,
            "max_loading_pct": round(100 * float(r["line_ratio"][:, codes == c].max()), 1)} for c in sorted(set(codes))]
    return row, lcs


def md(d):
    head = "| " + " | ".join(d.columns) + " |\n|" + "---|" * len(d.columns)
    return head + "\n" + "\n".join("| " + " | ".join(str(x) for x in r) + " |" for r in d.itertuples(index=False))


def write_summary():
    df = pd.read_csv(OUT / "stage7_year_ev.csv")
    lc = pd.read_csv(OUT / "stage7_year_ev_linecodes.csv")
    cols = ["seed", "case", "n_ev_houses", "cust_hours_below_207V", "distinct_hours_below_207V", "v_min_V",
            "distinct_hours_line_above_100pct", "line_hours_above_100pct_sum_over_lines", "max_line_loading_pct",
            "xfmr_max_kVA", "vuf_max_pct", "vuf_hours_above_2pct", "n_ev_active_max_any_nonzero_half_hour",
            "peak_coincident_ev_kw", "peak_ev_equivalents", "runtime_s"]
    sec = ["", "## Year with EV, no PV (Stage 7b)", "",
           f"**{LABEL}. Simulated, not measured.** 17,520 steps of 30 min, source 1.00 pu, no PV. Y0 = no EV (same "
           "as Stage 6 Y0). E30 / E60 = EV at 17 / 33 houses, P1 placement, one EV load per house driven by its column "
           "of data/processed/ev_kw.npz (7.4 kW charger, synthetic sessions, A18), unity PF. Rows with seed 1 to 4 "
           "change the house-load diversity picks only (the EV series stay the same). Line ratings are assumed, so "
           "line hours are indicative; Y0 already has line overload hours at these ratings.", "",
           md(df[cols]), "",
           "n_ev_active_max_any_nonzero_half_hour = most EVs with non-zero kW in the same half-hour (a partial "
           "step counts); peak_coincident_ev_kw = largest total EV kW in one half-hour; peak_ev_equivalents = that "
           "kW / 7.4 kW.", "",
           "### EV effect = E60 minus Y0 for the same house-load seed (Y0 seeds 1 to 4 from results/stage6_year_seeds.csv, "
           "not re-run; seed 2022 Y0 from this file)", "",
           md(df[df.case == "E60"][["seed", "y0_v_min_V", "v_min_V", "delta_v_min_V", "y0_cust_hours_below_207V",
                                    "cust_hours_below_207V", "y0_distinct_hours_below_207V", "distinct_hours_below_207V",
                                    "delta_distinct_hours_below_207V", "y0_distinct_hours_line_above_100pct",
                                    "distinct_hours_line_above_100pct", "delta_distinct_hours_line_above_100pct",
                                    "y0_line_hours_sum", "line_hours_above_100pct_sum_over_lines"]]), "",
           "### Hours above 100 % by linecode (only linecodes with overload hours)", "",
           md(lc[lc.distinct_hours_above_100pct > 0]), "",
           "### Energy balance (kWh): house load + EV + losses = energy into the transformer HV terminal", "",
           md(df[["seed", "case", "E_load_kWh_dss", "E_ev_kWh_dss", "E_ev_kWh_profile", "E_loss_kWh", "E_xfmr_in_kWh",
                  "balance_error_pct_of_xfmr"]]), ""]
    sm = OUT / "stage7_summary.md"
    txt = sm.read_text(encoding="utf-8").split("\n## Year with EV")[0].rstrip("\n")
    sm.write_text(txt + "\n" + "\n".join(sec), encoding="utf-8")
    print("\n".join(sec))


if __name__ == "__main__":
    if sys.argv[1] == "all":
        hk2022, _pv, _t = Y.load_year_inputs()
        ev = np.load(ROOT / "data" / "processed" / "ev_kw.npz")["kw"].astype(float)
        rows, lcs = [], []
        for seed, name, pen in RUNS:
            hk = hk2022 if seed == 2022 else l2.default_house_kw(seed)
            row, l = one_run(seed, name, pen, hk, ev)
            rows.append(row)
            lcs += l
            pd.DataFrame(rows).to_csv(OUT / "stage7_year_ev.csv", index=False)      # save after every run
            pd.DataFrame(lcs).to_csv(OUT / "stage7_year_ev_linecodes.csv", index=False)
            print({k: v for k, v in row.items() if k != "label"}, flush=True)
    elif sys.argv[1] == "augment":
        augment_csv()
    else:
        write_summary()
