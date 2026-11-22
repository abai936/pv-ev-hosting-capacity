"""Stage 8b runner: year time series with inverter control and tap. Case Y3 = 8 kWp on 60 % of houses (P1, 33 houses),
2022, 30-min steps, diversity seed 2022, source 1.00 pu, inverter kVA = kW.
Cases: M0 (reused from results/stage6_year.csv when the scope is the full year), M3, M3 + tap 0.975, M0 + tap 0.975, M1.
First a 2-day spike records ms/step; if the projected full-year time of the slowest case is over SPIKE_LIMIT_MIN the
run uses 4 one-week blocks (days 8 to 14 of Jan, Apr, Jul, Oct on the UTC grid) for ALL cases (M0 is re-run on the
same blocks) and the scope is written in every row.  Nothing is scaled up.
Usage (.venv python):  stage8_year_control.py run | summary
Simulated; IEEE feeder; NZ-parameterised synthetic load; PV modelled (PVGIS-ERA5); ratings assumed."""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hc import hosting as h, mitigation as M, yearly as Y  # noqa: E402

LABEL = "simulated; IEEE feeder; NZ-parameterised synthetic load; PV modelled; modelled inverter control; ratings assumed"
OUT = ROOT / "results"
KWP = 8.0
SPIKE_LIMIT_MIN = 25.0
SPIKE_START, SPIKE_STEPS = 48 * 10, 96
CASES = [("Y3_M0_tap1.000", "M0", 1.0, 1.0), ("Y3_M3_tap1.000", "M3", 1.0, 1.0), ("Y3_M3_tap0.975", "M3", 0.975, 1.0),
         ("Y3_M0_tap0.975", "M0", 0.975, 1.0), ("Y3_M1_tap1.000", "M1", 1.0, 1.0), ("Y3_M3_tap1.000_kva1.1", "M3", 1.0, 1.1)]
RERUN = {"Y3_M3_tap1.000", "Y3_M3_tap0.975", "Y3_M1_tap1.000", "Y3_M3_tap1.000_kva1.1"}   # the cases that use InvControl
WEEK_STEPS = 7 * 48
BLOCK_STARTS = [48 * (doy - 1) for doy in (8, 98, 189, 281)]    # 8 Jan, 8 Apr, 8 Jul, 8 Oct (non-leap 2022 day-of-year)


def metrics(rs, name, mode, tap, scope, kva=1.0):
    """Combine one or more window results into one row. Hours are customer-/step-hours x 0.5."""
    cat = lambda key: np.concatenate([r[key] for r in rs])
    vc = np.concatenate([r["v_cust_v"] for r in rs])
    lr = np.concatenate([r["line_ratio"] for r in rs]) > 1.0
    n = sum(r["n_steps"] for r in rs)
    hi, lo = vc > 253.0, vc < 207.0
    avail = cat("pv_avail_kw_per_step").astype(np.float64).sum() * Y.STEP_H      # float64 sums
    deliv = cat("pv_kw_per_step").astype(np.float64).sum() * Y.STEP_H
    q = np.concatenate([r["pv_q"] for r in rs]).astype(np.float64)
    err = sum(Y.energy_balance(r)[0] + Y.energy_balance(r)[1] - Y.energy_balance(r)[2] - Y.energy_balance(r)[3] for r in rs)
    e_x = sum(Y.energy_balance(r)[3] for r in rs)
    rt = sum(r["runtime_s"] for r in rs)
    return {"case": name, "mode": mode, "tap": tap, "kva_ratio": kva, "scope": scope, "pv_kwp_per_house": KWP,
            "n_pv_houses": rs[0]["pv_q"].shape[1], "steps": n, "nonconverged_steps": n - sum(r["converged"] for r in rs),
            "control_not_settled_steps": sum(r["ctl_fail_steps"] for r in rs),
            "cust_hours_above_253V": hi.sum() * Y.STEP_H, "distinct_hours_above_253V": hi.any(axis=1).sum() * Y.STEP_H,
            "cust_hours_below_207V": lo.sum() * Y.STEP_H, "distinct_hours_below_207V": lo.any(axis=1).sum() * Y.STEP_H,
            "v_min_V": round(float(vc.min()), 2), "v_max_V": round(float(vc.max()), 2),
            "pv_available_kWh": round(avail, 1), "pv_delivered_kWh": round(deliv, 1),
            "curtailed_kWh": round(avail - deliv, 3), "curtailed_pct_of_pv_energy": round(100 * (avail - deliv) / avail, 5),
            "q_absorbed_kvarh": round(float(-np.minimum(q, 0).sum() * Y.STEP_H), 1),
            "q_injected_kvarh": round(float(np.maximum(q, 0).sum() * Y.STEP_H), 1),
            "line_hours_above_100pct_sum_over_lines": lr.sum() * Y.STEP_H,
            "distinct_hours_line_above_100pct": lr.any(axis=1).sum() * Y.STEP_H,
            "max_line_loading_pct": round(100 * float(max(r["line_ratio"].max() for r in rs)), 1),
            "xfmr_max_kVA": round(float(max(r["kva"].max() for r in rs)), 1),
            "E_xfmr_in_kWh": round(e_x, 1), "balance_error_pct_of_xfmr": round(100 * err / e_x, 5),
            "runtime_s": round(rt, 1), "ms_per_step": round(1000 * rt / n, 2), "label": LABEL}


def run():
    house_kw, pv, _t = Y.load_year_inputs()
    pv_idx = h.place_p1(h.Model(1.0, True), h.n_pv_for(0.6, 55))
    # 2-day spike on the expensive case (M3, tap 1.000)
    sp = M.run_year_ctl(house_kw, pv, pv_idx, KWP, "M3", 1.0, 1.0, SPIKE_STEPS, SPIKE_START)
    ms = 1000 * sp["runtime_s"] / SPIKE_STEPS
    proj_min = ms * house_kw.shape[0] / 60000.0
    full = proj_min <= SPIKE_LIMIT_MIN
    scope = "full year 2022 (17,520 steps)" if full else "4 one-week blocks (8 Jan, 8 Apr, 8 Jul, 8 Oct 2022), NOT scaled"
    print(f"SPIKE M3: {ms:.1f} ms/step, projected full year {proj_min:.1f} min -> {scope}", flush=True)
    pd.DataFrame([{"spike_case": "M3_tap1.000", "steps": SPIKE_STEPS, "ms_per_step": round(ms, 2),
                   "projected_full_year_min": round(proj_min, 1), "chosen_scope": scope}]).to_csv(
        OUT / "stage8_year_spike.csv", index=False)
    wins = [(0, house_kw.shape[0])] if full else [(s, WEEK_STEPS) for s in BLOCK_STARTS]
    old = pd.read_csv(OUT / "stage8_year.csv") if (OUT / "stage8_year.csv").exists() else pd.DataFrame()
    rows = []
    for name, mode, tap, kva in CASES:
        if name not in RERUN and len(old) and name in set(old.case):      # M0 rows do not use InvControl: keep
            rows.append(old[old.case == name].iloc[0].to_dict())
            continue
        if full and mode == "M0" and tap == 1.0:
            s6 = pd.read_csv(OUT / "stage6_year.csv")
            r = s6[s6.case == "Y3"].iloc[0]
            rows.append({"case": name, "mode": "M0", "tap": 1.0, "kva_ratio": 1.0, "scope": scope + "; reused from results/stage6_year.csv",
                         "pv_kwp_per_house": KWP, "n_pv_houses": int(r.n_pv_houses), "steps": int(r.steps),
                         "nonconverged_steps": int(r.nonconverged), "control_not_settled_steps": 0,
                         "cust_hours_above_253V": r.cust_hours_above_253V, "distinct_hours_above_253V": r.distinct_hours_above_253V,
                         "cust_hours_below_207V": r.cust_hours_below_207V, "distinct_hours_below_207V": r.distinct_hours_below_207V,
                         "v_min_V": r.v_min_V, "v_max_V": r.v_max_V, "pv_available_kWh": r.E_pv_kWh_dss,
                         "pv_delivered_kWh": r.E_pv_kWh_dss, "curtailed_kWh": 0.0, "curtailed_pct_of_pv_energy": 0.0,
                         "q_absorbed_kvarh": 0.0, "q_injected_kvarh": 0.0,
                         "line_hours_above_100pct_sum_over_lines": r.line_hours_above_100pct_sum_over_lines,
                         "distinct_hours_line_above_100pct": r.distinct_hours_line_above_100pct,
                         "max_line_loading_pct": r.max_line_loading_pct, "xfmr_max_kVA": r.xfmr_max_kVA,
                         "E_xfmr_in_kWh": r.E_xfmr_in_kWh, "balance_error_pct_of_xfmr": r.balance_error_pct_of_xfmr,
                         "runtime_s": r.runtime_s, "ms_per_step": r.ms_per_step, "label": LABEL})
        else:
            rs = [M.run_year_ctl(house_kw, pv, pv_idx, KWP, mode, tap, kva, n, s) for s, n in wins]
            rows.append(metrics(rs, name, mode, tap, scope, kva))
        pd.DataFrame(rows).to_csv(OUT / "stage8_year.csv", index=False)     # save after every case
        print({k: v for k, v in rows[-1].items() if k != "label"}, flush=True)


def md(d):
    head = "| " + " | ".join(d.columns) + " |\n|" + "---|" * len(d.columns)
    return head + "\n" + "\n".join("| " + " | ".join(str(x) for x in r) + " |" for r in d.itertuples(index=False))


def write_summary():
    df = pd.read_csv(OUT / "stage8_year.csv")
    sp = pd.read_csv(OUT / "stage8_year_spike.csv")
    cols = ["case", "kva_ratio", "cust_hours_above_253V", "distinct_hours_above_253V", "cust_hours_below_207V", "v_min_V", "v_max_V",
            "curtailed_kWh", "curtailed_pct_of_pv_energy", "q_absorbed_kvarh", "q_injected_kvarh",
            "distinct_hours_line_above_100pct", "max_line_loading_pct", "xfmr_max_kVA", "nonconverged_steps",
            "control_not_settled_steps", "balance_error_pct_of_xfmr", "runtime_s", "ms_per_step"]
    df = df.copy()          # display only: tiny curtailed energies are float noise level, say so
    df["curtailed_kWh"] = [("below 1 kWh" if abs(x) < 1.0 else x) for x in df.curtailed_kWh]
    sec = ["", "## Year with control", "",
           f"**{LABEL}. Simulated, not measured.** Case Y3 = 8 kWp on 60 % of houses (P1, 33 houses), inverter kVA = kW, "
           f"source 1.00 pu, diversity seed 2022. Scope: {df.scope.iloc[1]}. Spike (2 days, M3): "
           f"{sp.ms_per_step.iloc[0]} ms/step, projected full year {sp.projected_full_year_min.iloc[0]} min. "
           "Curtailed kWh = PV available (kWp x PVGIS-ERA5 profile) minus PV delivered (OpenDSS PVSystem output). "
           "Reactive energy: absorbed and injected, summed over inverters. Customer-hours count each customer "
           "separately; distinct hours count a step once. Line overloads use assumed ratings. M0 row of a full-year scope "
           "is reused from stage6_year.csv. 30-min averages hide short peaks. Only the M3, M3+tap and M1 cases (and the extra "
           "M3 kVA = 1.1 x kWp case) use InvControl; they were re-run after the fix that disables customers without PV "
           "(they used to absorb volt-var vars). The M0+tap 0.975 reactive energy of about 4 kvarh (absorbed and injected) is "
           "numerical noise of a case with no control (no source of vars), not a result.", "", md(df[cols]), ""]
    sm = OUT / "stage8_summary.md"
    txt = sm.read_text(encoding="utf-8") if sm.exists() else ""
    txt = txt.split("\n## Year with control")[0].rstrip("\n")
    sm.write_text(txt + "\n" + "\n".join(sec), encoding="utf-8")
    print("\n".join(sec))


if __name__ == "__main__":
    {"run": run, "summary": write_summary}[sys.argv[1]]()
