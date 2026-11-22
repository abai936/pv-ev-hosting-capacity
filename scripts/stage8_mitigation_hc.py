"""Stage 8a runner: snapshot PV hosting capacity with inverter control and transformer tap (L2, seed 2022).
Modes M0..M3 x tap 1.000/0.975 (inverter kVA = kW), plus a kVA = 1.1 x kW sensitivity for M2/M3 (P1/P2 only).
P1/P2 at 30/60/100 %, P3 = 50 random placements. Also the EV tap table (LE, P1_direct, tap 1.000 vs 0.975).
Writes results/stage8_hc.csv, results/stage8_ev_tap.csv and the HC part of results/stage8_summary.md
(the year part is added by stage8_year_control.py summary). Runs one process per (mode, tap, kva) combination.
Simulated; IEEE feeder; NZ-parameterised synthetic load; ratings assumed."""
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hc import ev_hosting as E, hosting as h, l2, mitigation as M, profiles as P, yearly as Y  # noqa: E402

LABEL = "simulated; IEEE feeder; NZ-parameterised synthetic load; modelled inverter control; ratings assumed"
OUT = ROOT / "results"
CACHE = OUT / "cache"
PENS = (0.30, 0.60, 1.00)
N_SEEDS = 50
COMBOS = [(m, t, 1.0) for m in ("M0", "M1", "M2", "M3") for t in (1.0, 0.975)] + \
         [(m, t, 1.1) for m in ("M2", "M3") for t in (1.0, 0.975)]


def run_combo(args):
    mode, tap, kva = args
    t0 = time.perf_counter()
    house_kw, _pv, _t = Y.load_year_inputs()
    l2_kw, _n = l2.l2_kw(house_kw, P.time_index_utc())
    m = M.CtlModel(mode, tap, kva)
    m.cases["L2"] = dict(zip(m.loads, l2_kw))
    rows = []
    for pen in PENS:
        n_pv = h.n_pv_for(pen, len(m.loads))
        places = [("P1", None), ("P2", None)] + ([("P3", s) for s in range(N_SEEDS)] if kva == 1.0 else [])
        for pl, seed in places:
            idx = h.place_p1(m, n_pv) if pl == "P1" else h.place_p2(m, n_pv) if pl == "P2" else h.place_p3(m, n_pv, seed)
            m.set_case("L2", idx)
            o = M.hc_with_control(m)
            hc_v = cv = None
            if pl != "P3":
                ov = M.hc_with_control(m, ignore=("line",))
                hc_v, cv = ov["hc_kw"], ov["curtailed_pct"]
            info = o["info"]
            hc = o["hc_kw"]
            rows.append({
                "mode": mode, "tap": tap, "kva_ratio": kva, "placement": pl, "seed": "" if seed is None else seed,
                "penetration": pen, "n_pv": n_pv, "status": o["status"],
                "HC_kW": "nonconverged" if hc is None else round(hc, 3),
                "Orion_capped_HC_kW": "" if hc is None else round(min(hc, h.ORION_CAP_KW), 3),
                "binding_limit": o["binding_limit"], "binding_element": o["binding_element"],
                "binding_linecode": info.get("line_linecode", ""), "binding_phase": info.get("line_phase", ""),
                "rating_status": "assumed" if o["binding_limit"].replace("baseline-", "") in ("line", "transformer") else "n/a",
                "p_dispatched_kw_at_HC": None if hc is None else round(o["p_disp_kw"], 3),
                "p_available_kw_at_HC": None if hc is None else round(o["p_avail_kw"], 3),
                "curtailed_pct_at_HC": None if hc is None else round(max(o["curtailed_pct"], 0.0), 3),
                "q_kvar_at_HC": None if hc is None else round(o["q_kvar"], 3),
                "vmax_v_at_HC": None if hc is None else round(o["vmax_v"], 2),
                "HC_voltage_only_kW": "" if pl == "P3" else ("nonconverged" if hc_v is None else round(hc_v, 3)),
                "curtailed_pct_at_HC_voltage_only": "" if cv is None else round(max(cv, 0.0), 3),
                "label": LABEL})
    df = pd.DataFrame(rows)
    CACHE.mkdir(parents=True, exist_ok=True)
    df.to_csv(CACHE / f"stage8_hc_{mode}_{tap}_{kva}.csv", index=False)
    return mode, tap, kva, len(df), round(time.perf_counter() - t0, 1)


def ev_tap_table():
    """EV evening case LE, P1_direct, 7.4 kW: EV HC count and min customer voltage, tap 1.000 vs 0.975.
    Plain h.Model (EV = negative generator, as Stage 7) with the tap applied."""
    house_kw, _pv, _t = Y.load_year_inputs()
    le, _n = E.le_kw(house_kw, P.time_index_utc())
    rows = []
    for tap in (1.0, 0.975):
        m = h.Model(1.0, True)
        if tap != 1.0:
            M.apply_tap(tap)
        m.cases["LE"] = dict(zip(m.loads, le))
        order, _ = E.order_p1(m)
        r = E.find_ev_hc(m, order, E.EV_KW, lambda k: h.place_p1(m, k))
        v0, viol0, _ = E.snapshot(m, [])
        v30, viol30, _ = E.snapshot(m, h.place_p1(m, 30))
        rows.append({"tap": tap, "EV_HC_count": r["hc"], "binding_limit": r["binding_limit"],
                     "binding_element": r["binding_element"], "min_cust_V_no_EV": round(v0, 2),
                     "min_cust_V_at_HC": round(r["info"]["vmin_v"], 2) if r["info"]["vmin_v"] is not None else None,
                     "min_cust_V_at_30_EVs": round(v30, 2),
                     "low_voltage_violations_no_EV": sum(x[0] == "voltage-low" for x in viol0),
                     "low_voltage_violations_30_EVs": sum(x[0] == "voltage-low" for x in viol30),
                     "label": "simulated; LE = winter weekday evening median, 7.4 kW EV (assumed); ratings assumed"})
    return pd.DataFrame(rows)


def md(d):
    head = "| " + " | ".join(d.columns) + " |\n|" + "---|" * len(d.columns)
    return head + "\n" + "\n".join("| " + " | ".join(str(x) for x in r) + " |" for r in d.itertuples(index=False))


def desc(r):
    s = r.binding_limit
    if str(s).replace("baseline-", "") == "line":
        return f"line (assumed) {r.binding_linecode} ph{int(float(r.binding_phase))}"
    return str(s)


def write_summary(df, ev, runtime_s):
    num = lambda s: pd.to_numeric(s, errors="coerce")
    df = df.assign(hc=num(df.HC_kW), cv=num(df.curtailed_pct_at_HC), cap=num(df.Orion_capped_HC_kW))
    base = df[df.kva_ratio == 1.0]
    L = ["# Stage 8 summary: mitigation (inverter control, transformer tap)", "",
         f"**{LABEL}. Simulated, not measured.** Source 1.00 pu, L2 load (summer weekday midday median, diversity seed 2022). "
         "Single-phase PV on the customer's own phase. Modes: M0 unity PF no control, M1 volt-watt only, M2 volt-var only, "
         "M3 Australia A volt-var + volt-watt (curves in pu of 230 V, y-axes in fraction of S_rated). Inverter kVA = PV kW "
         "rating (kva_ratio 1.0, no spare kVA, var priority) unless stated. Tap 0.975 = TR1 secondary lowered 2.5 % "
         "(no-load LV 240.18 V x tap = 234.2 V). HC = largest PV kW per customer (sweep 1 to 20 kW then bisection 0.01 kW; quoted here to 0.1 kW because the inverter control only settles to its tolerance; the CSV keeps 0.01 kW) with no "
         "violation after the control has settled (207 to 253 V at customers, line ratings and 800 kVA transformer "
         "assumed, VUF 2 % assumed). Orion-capped = min(HC, 10 kW). Curtailed % = 1 - P_dispatched / P_available at the "
         "HC point (P_available = n_pv x HC). 'cap' means no violation up to 20 kW.", "",
         "Reading note: Australia A volt-watt starts curtailing at 1.10 pu = 253.0 V, which is the NZ upper limit, so the "
         "steady state under curtailment sits at or above 253 V. Volt-watt alone therefore cannot lift the 253 V "
         "limit; its effect shows in curtailed %, not in HC. This is a property of the setting, not a model fault.", "",
         "Snapshot inverter size: the PV rating swept is the full-sun output, and kVA = kW, so there is no spare kVA. "
         "OpenDSS then gives the vars priority (WattPriority=No, the OpenDSS default) and cuts P to make room; this is an "
         "ASSUMPTION: no source found says Australia A requires var priority. That is why M2/M3 show curtailed % even below "
         "253 V. In the year runs kVA = kWp, but the PV profile peaks at 0.8915 kW per kWp, so the spare kVA at peak is "
         "sqrt(1 - 0.8915^2) = 0.45 S, which is less than the 0.6 S volt-var maximum: 'there is spare kVA' is only partly true. "
         "Volt-watt on the S_rated basis only cuts output above about 254 V at peak sun (the curve reaches 0.8915 S at "
         "1.1041 pu), which is why M1 curtails little and does not lower the over-253 V hours.", "",
         "Settling: after each solve the control is solved again until two successive solves agree to 0.02 V and 0.2 % of P, "
         "starting every point from a fixed cold state (src/hc/mitigation.py, cold_start). Result file stage8_hc.csv: 1272 rows, "
         "0 nonconverged, HC run time 494 s (results/stage8_hc_run.log).", ""]
    for pl in ("P1", "P2"):
        d = base[base.placement == pl]
        t = []
        for pen in PENS:
            for (mo, tp), g in d[d.penetration == pen].groupby(["mode", "tap"]):
                r = g.iloc[0]
                t.append({"penetration": pen, "mode": mo, "tap": tp, "HC_kW": r.HC_kW if r.status == "nonconverged" else f"{r.hc:.1f}",
                          "Orion_capped": f"{r.cap:.1f}" if r.status != "nonconverged" else "",
                          "HC_voltage_only": r.HC_voltage_only_kW if r.HC_voltage_only_kW == "nonconverged" else f"{float(r.HC_voltage_only_kW):.1f}",
                          "curtailed_pct_at_HC": "" if pd.isna(r.cv) else f"{r.cv:.2f}",
                          "curtailed_pct_at_HC_V_only": "" if r.curtailed_pct_at_HC_voltage_only in ("", None) or pd.isna(r.curtailed_pct_at_HC_voltage_only) else f"{float(r.curtailed_pct_at_HC_voltage_only):.2f}",
                          "binding": desc(r) + (f" {r.binding_element}" if str(r.binding_limit).startswith("voltage") else "")})
        L += [f"## {pl} {'(balanced)' if pl == 'P1' else '(end-clustered)'}", "", md(pd.DataFrame(t)), ""]
    L += [f"## P3 random placement ({N_SEEDS} seeds): HC percentiles (kW) and median curtailed %", ""]
    t = []
    for (pen, mo, tp), g in base[base.placement == "P3"].groupby(["penetration", "mode", "tap"]):
        ok = g[g.status != "nonconverged"]
        p5, p50, p95 = (np.percentile(ok.hc, q) for q in (5, 50, 95))
        t.append({"penetration": pen, "mode": mo, "tap": tp, "P5": f"{p5:.1f}", "P50": f"{p50:.1f}", "P95": f"{p95:.1f}",
                  "median_curtailed_pct": f"{ok.cv.median():.2f}", "nonconverged": int((g.status == 'nonconverged').sum()),
                  "binding": ", ".join(f"{k}:{v}" for k, v in g.binding_limit.value_counts().items())})
    L += [md(pd.DataFrame(t)), ""]
    s = df[(df.kva_ratio == 1.1) & df.placement.isin(["P1", "P2"])]
    L += ["## Sensitivity: inverter kVA = 1.1 x kW (P1, P2; compare with the kva_ratio 1.0 rows above)", ""]
    t = [{"placement": r.placement, "penetration": r.penetration, "mode": r.mode, "tap": r.tap,
          "HC_kW": "nonconverged" if pd.isna(r.hc) else f"{r.hc:.1f}",
          "curtailed_pct_at_HC": "" if pd.isna(r.cv) else f"{r.cv:.2f}", "binding": desc(r)} for r in s.itertuples()]
    L += [md(pd.DataFrame(t)), ""]
    nc = df[df.status == "nonconverged"]
    L += [f"Nonconverged evaluations: {len(nc)} of {len(df)} rows.", "",
          "## EV evening case LE: effect of the tap (P1_direct, 7.4 kW EV)", "", md(ev.drop(columns="label")), "",
          f"Runtime {runtime_s:.0f} s."]
    sm = OUT / "stage8_summary.md"
    old = sm.read_text(encoding="utf-8") if sm.exists() else ""
    year = ("\n## Year with control" + old.split("\n## Year with control")[1]) if "\n## Year with control" in old else ""
    sm.write_text("\n".join(L) + "\n" + year, encoding="utf-8")
    return len(df), len(nc)


if __name__ == "__main__":
    t0 = time.perf_counter()
    log = [f"stage8_mitigation_hc.py {' '.join(sys.argv[1:])} started {time.strftime('%Y-%m-%d %H:%M:%S')}"]
    if len(sys.argv) > 1 and sys.argv[1] == "summary":
        pass
    else:
        only = sys.argv[1].split(":")[1] if len(sys.argv) > 1 and sys.argv[1].startswith("only:") else None
        with Pool(4) as pool:
            for res in pool.imap_unordered(run_combo, [c for c in COMBOS if only is None or c[0] == only]):
                print("done", res, flush=True)
                log.append(f"done mode={res[0]} tap={res[1]} kva={res[2]} rows={res[3]} runtime_s={res[4]}")
    df = pd.concat([pd.read_csv(CACHE / f"stage8_hc_{m}_{t}_{k}.csv") for m, t, k in COMBOS], ignore_index=True)
    df.to_csv(OUT / "stage8_hc.csv", index=False)
    ev = ev_tap_table()
    ev.to_csv(OUT / "stage8_ev_tap.csv", index=False)
    n_rows, n_nc = write_summary(df, ev, time.perf_counter() - t0)
    print(ev.to_string(index=False))
    nc_by = df[df.status == "nonconverged"].groupby(["mode", "tap", "kva_ratio"]).size().to_dict()
    log += [f"rows {n_rows}", f"nonconverged rows {n_nc}", f"nonconverged by (mode, tap, kva): {nc_by}",
            f"runtime_s {time.perf_counter() - t0:.0f}"]
    (OUT / "stage8_hc_run.log").write_text("\n".join(log) + "\n", encoding="utf-8")
