"""Stage 7a runner: snapshot EV hosting capacity (LE = winter weekday evening median, non-EV load).
Writes results/stage7_ev_hc.csv, results/stage7_hand_check.csv and the EV-HC part of results/stage7_summary.md.
Simulated; IEEE feeder; NZ-parameterised synthetic load; ratings and VUF limit assumed."""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hc import ev_hosting as E, hosting as h, l2, profiles as P, yearly as Y  # noqa: E402

LABEL = "simulated; IEEE feeder; NZ-parameterised synthetic load; ratings and VUF limit assumed"
OUT = ROOT / "results"
N_SEEDS = 50
DIV_SEEDS = (2022, 1, 2, 3, 4)
t0 = time.perf_counter()
house_kw, _pv, _t = Y.load_year_inputs()
idx_utc = P.time_index_utc()
LE2022, N_LE = E.le_kw(house_kw, idx_utc)
rows = []


def make_model(pu=1.0, rating_scale=1.0, le=LE2022):
    m = h.Model(pu, True, rating_scale=rating_scale)
    m.cases["LE"] = dict(zip(m.loads, le))
    return m


LE_P90, P90_TS, P90_TOTAL, _n = E.le_p90_kw(house_kw, idx_utc)


def phase_mix(m, idxs):
    ph = np.array(m.phase)
    return "/".join(str(int(sum(ph[i] == p for i in idxs))) for p in (1, 2, 3))


def run2(m, name, order, ev_kw, tag, load_case="LE", seed="", pu=1.0, rs=1.0, div_seed=""):
    """name: P1_direct (place_p1(k) re-picked each k), P1_nested_order (ordering artefact), P2, P3."""
    pick = (lambda k: h.place_p1(m, k)) if name == "P1_direct" else (lambda k: order[:k])
    r = E.find_ev_hc(m, order, ev_kw, pick)
    n = len(m.loads)
    thermal = r["binding_limit"].replace("baseline-", "") in ("line", "transformer")
    hc = r["hc"]
    row = {"placement": name, "load_case": load_case, "seed": seed, "div_seed": div_seed, "model": tag,
           "source_pu": pu, "ev_kw": ev_kw, "rating_scale": rs, "EV_HC_count": hc,
           "pct_of_55_houses": round(100 * hc / n, 1),
           "ph1": r["per_phase"][0], "ph2": r["per_phase"][1], "ph3": r["per_phase"][2],
           "phase_mix_at_first_fail": phase_mix(m, pick(hc + 1)) if hc < n else "",
           "binding_limit": r["binding_limit"], "binding_element": r["binding_element"],
           "binding_linecode": r["line_linecode"], "binding_phase": r["line_phase"],
           "rating_status": "assumed" if thermal else "n/a",
           "vuf_max_pct_at_HC": None if r["info"]["vuf_max_pct"] is None else round(r["info"]["vuf_max_pct"], 3),
           "xfmr_kva_at_HC": None if r["info"]["xfmr_kva"] is None else round(r["info"]["xfmr_kva"], 1),
           "min_cust_v_at_HC": None if r["info"]["vmin_v"] is None else round(r["info"]["vmin_v"], 2),
           "line1_rating_a": round(m.line_rating_a[m.line_names.index("line1")], 2)}
    for key, tagk in (("line1_i_hc", "hc"), ("line1_i_fail", "fail")):
        i = r["info"][key]
        ha, hk = E.headroom(m, i) if i is not None else (np.full(3, np.nan),) * 2
        for p in range(3):
            row[f"line1_I_A_ph{p+1}_{tagk}"] = None if i is None else round(float(i[p]), 2)
            row[f"line1_headroom_A_ph{p+1}_{tagk}"] = None if i is None else round(float(ha[p]), 2)
            row[f"line1_headroom_kW230_ph{p+1}_{tagk}"] = None if i is None else round(float(hk[p]), 2)
    row["label"] = LABEL
    rows.append(row)


# main grid at source 1.00, 7.4 kW, both load cases
m = make_model()
o1, n_nested = E.order_p1(m)
for lc, le in (("LE", LE2022), ("LE_P90", LE_P90)):
    m.cases["LE"] = dict(zip(m.loads, le))
    run2(m, "P1_direct", o1, 7.4, "main", lc)
    run2(m, "P1_nested_order", o1, 7.4, "main", lc)
    run2(m, "P2", E.order_p2(m), 7.4, "main", lc)
    for sd in range(N_SEEDS):
        run2(m, "P3", E.order_p3(m, sd), 7.4, "main", lc, seed=sd)
m.cases["LE"] = dict(zip(m.loads, LE2022))


for evk in (3.7, 7.4):
    for pl in ("P1_direct", "P1_nested_order"):
        run2(m, pl, o1, evk, "sens_ev_kw")
for pu in (0.98, 1.00, 1.025, 1.05):
    mm = make_model(pu)
    for pl in ("P1_direct", "P1_nested_order"):
        run2(mm, pl, o1, 7.4, "sens_source_pu", pu=pu)
for rs in (0.8, 0.9, 1.0, 1.05, 1.1, 1.2):
    mm = make_model(1.0, rs)
    for pl in ("P1_direct", "P1_nested_order"):
        run2(mm, pl, o1, 7.4, "sens_rating_scale", rs=rs)
for ds in DIV_SEEDS:
    kw = LE2022 if ds == 2022 else E.le_kw(l2.default_house_kw(ds), idx_utc)[0]
    mm = make_model(1.0, 1.0, kw)
    for pl in ("P1_direct", "P1_nested_order"):
        run2(mm, pl, o1, 7.4, "sens_diversity_seed", div_seed=ds)

# voltage margin of P1_direct at the HC point, 15 and 30 EVs (LE, 7.4 kW, 1.00 pu)
m = make_model()          # the OpenDSS circuit is global: rebuild so it matches `m` again
hc_direct = [r for r in rows if r["placement"] == "P1_direct" and r["model"] == "main" and r["load_case"] == "LE"][0]["EV_HC_count"]
vrows, volt_before_30 = [], 0
for k in sorted({hc_direct, 15, 30}):
    vmin, viol, i1 = E.snapshot(m, h.place_p1(m, k))
    vrows.append({"n_ev": k, "min_cust_v": round(vmin, 2), "voltage_violations": sum(x[0].startswith("voltage") for x in viol),
                  "binding_limits": ",".join(sorted({x[0] for x in viol}))})
for k in range(1, 31):
    volt_before_30 += sum(x[0].startswith("voltage") for x in E.snapshot(m, h.place_p1(m, k))[1])
pd.DataFrame(vrows).to_csv(OUT / "stage7_voltage_margin.csv", index=False)
df = pd.DataFrame(rows)
df.to_csv(OUT / "stage7_ev_hc.csv", index=False)

# hand check
pred, sim, name, n_lines, i_nom = E.hand_check()
pd.DataFrame([{"customer": name, "ev_kw": 7.4, "I_at_230V_A": round(i_nom, 2), "lines_on_path": n_lines,
               "predicted_V": pred, "opendss_V": sim, "error_pct": 100 * (sim - pred) / pred,
               "note": "all other loads off, source 1.00 pu; current = P / solved customer voltage"}]
             ).to_csv(OUT / "stage7_hand_check.csv", index=False)
print(f"hand check pred {pred:.4f} V sim {sim:.4f} V err {100*(sim-pred)/pred:.3f} %")


def md(d):
    head = "| " + " | ".join(d.columns) + " |\n|" + "---|" * len(d.columns)
    return head + "\n" + "\n".join("| " + " | ".join(str(x) for x in r) + " |" for r in d.itertuples(index=False))


def bind(r):
    s = r.binding_limit
    if s.replace("baseline-", "") == "line":
        s += f" (assumed rating) {r.binding_element}, linecode {r.binding_linecode}, ph {r.binding_phase}"
    elif r.binding_element:
        s += f" {r.binding_element}"
    return s


def trip(r, pre, tag):
    """'a/b/c' string of a per-phase line1 column group."""
    return "/".join(str(r[f"line1_{pre}_ph{p}_{tag}"]) for p in (1, 2, 3))


df["binding"] = df.apply(bind, axis=1)
df["line1_headroom_A_hc"] = df.apply(lambda r: trip(r, "headroom_A", "hc"), axis=1)
df["line1_headroom_kW230_hc"] = df.apply(lambda r: trip(r, "headroom_kW230", "hc"), axis=1)
df["line1_headroom_A_fail"] = df.apply(lambda r: trip(r, "headroom_A", "fail"), axis=1)
df["line1_headroom_kW230_fail"] = df.apply(lambda r: trip(r, "headroom_kW230", "fail"), axis=1)
HR = ["line1_headroom_A_hc", "line1_headroom_kW230_hc", "line1_headroom_A_fail", "line1_headroom_kW230_fail"]
main = df[df.model == "main"]
L = ["# Stage 7 summary: EV hosting capacity", "",
     f"**{LABEL}. Simulated, not measured.** Source 1.00 pu, 7.4 kW single-phase EV (assumed, A18) at unity PF, "
     "constant power, at the customer's own node and phase. Limits: 207 to 253 V at customers, line ratings "
     "(assumed), transformer 800 kVA, VUF 2 % (assumed). EV HC = largest number of EVs charging at the same time "
     "with no violation; the first failing count ends it.", "",
     "Placements. **P1_direct (headline)** = place_p1(k) re-picked for each k, so every count is phase-balanced "
     "(e.g. 2/2/2 at 6 EVs). **P1_nested_order** = one list built by appending the new picks of place_p1(1..55); "
     f"it is an ordering artefact (only {n_nested} of 55 counts equal place_p1(k)) and can be phase-unbalanced "
     "(see phase_mix_at_first_fail); kept as a secondary column. P2 = highest path resistance first. "
     "P3 = 50 random orderings (seeds 0 to 49).", "",
     f"**LE = median weekday evening, typical not design peak.** Per house, median non-EV 30-min load over weekday "
     f"steps starting 19:00, 19:30, 20:00, 20:30 local (Pacific/Auckland) in Jun/Jul/Aug 2022 ({N_LE} steps = 66 weekdays "
     f"x 4; public holidays count as weekdays). Total LE load {LE2022.sum():.1f} kW.", "",
     f"**LE_P90** = the single evening step (of the {N_LE}) whose total feeder load is closest to the 90th percentile of the "
     f"step totals, each house at its own load at that step: {P90_TS} UTC, total {P90_TOTAL:.1f} kW.", ""]
hc_rows = []
for lc in ("LE", "LE_P90"):
    mm_ = main[main.load_case == lc]
    for pl in ("P1_direct", "P2", "P1_nested_order"):
        r = mm_[mm_.placement == pl].iloc[0]
        hc_rows.append({"load_case": lc, "placement": pl, "EV_HC": r.EV_HC_count, "pct_of_55": r.pct_of_55_houses,
                        "per_phase": f"{r.ph1}/{r.ph2}/{r.ph3}", "mix_at_first_fail": r.phase_mix_at_first_fail,
                        "binding": bind(r), **{c: r[c] for c in HR}})
    p3 = mm_[mm_.placement == "P3"]
    p5, p50, p95 = (np.percentile(p3.EV_HC_count, q) for q in (5, 50, 95))
    kinds = p3.apply(lambda r: r.binding_limit + (f"/{r.binding_linecode}" if r.binding_linecode else ""), axis=1)
    hc_rows.append({"load_case": lc, "placement": "P3 (P5/P50/P95 of 50)", "EV_HC": f"{p5:.0f}/{p50:.0f}/{p95:.0f}",
                    "pct_of_55": f"{100*p5/55:.1f}/{100*p50/55:.1f}/{100*p95/55:.1f}", "per_phase": "",
                    "mix_at_first_fail": "", "binding": ", ".join(f"{k}:{v}" for k, v in kinds.value_counts().items()),
                    **{c: "" for c in HR}})
L += ["## Main result (7.4 kW, source 1.00 pu)", "",
      "Headroom columns = line1 (rating minus current) per phase 1/2/3, in A and in kW at 230 V, at the HC point and "
      "at the first failing count (negative = over the assumed rating).", "", md(pd.DataFrame(hc_rows)), ""]
rs = df[(df.model == "sens_rating_scale")]
d = rs[rs.placement == "P1_direct"]
vm = pd.read_csv(OUT / "stage7_voltage_margin.csv").fillna("none")
L += ["**The EV count is a step function of the ASSUMED 195 A rating of the 4c_70 trunk (data/line_ratings.csv); a few % "
      "change moves it by whole EVs.** Rating-scale P1_direct HC: " +
      ", ".join(f"{r.rating_scale}->{r.EV_HC_count}" for r in d.itertuples()) + ". "
      + ("Voltage never binds before 30 EVs" if volt_before_30 == 0 else
         f"WARNING: {volt_before_30} voltage violations were seen at some count up to 30 EVs")
      + " (P1_direct, LE; min customer voltage: " +
      ", ".join(f"{r.min_cust_v} V at {r.n_ev} EVs" for r in vm.itertuples()) + ").", "",
      "### Voltage margin (P1_direct, LE, 7.4 kW)", "", md(vm), ""]


def sens(title, key, col):
    d_ = df[(df.model == key) & (df.placement == "P1_direct")].reset_index(drop=True)
    n_ = df[(df.model == key) & (df.placement == "P1_nested_order")].reset_index(drop=True)
    t_ = d_[[col, "EV_HC_count", "pct_of_55_houses", "ph1", "ph2", "ph3", "binding"] + HR].copy()
    t_["nested_order_HC (secondary)"] = n_.EV_HC_count
    t_["nested_mix_at_first_fail"] = n_.phase_mix_at_first_fail
    return [f"## {title}", "", md(t_), ""]


L += sens("Source voltage (P1_direct headline)", "sens_source_pu", "source_pu")
L += sens("EV power (P1_direct, source 1.00 pu)", "sens_ev_kw", "ev_kw")
L += sens("Rating scale (P1_direct, 7.4 kW; 1.0 = main)", "sens_rating_scale", "rating_scale")
L += sens("Diversity seed of the LE load (P1_direct, 7.4 kW)", "sens_diversity_seed", "div_seed")
h_ = pd.read_csv(OUT / "stage7_hand_check.csv")
L += ["## Hand check", "", "Checks the (2R1+R0)/3 loop model; it shares path_r with the model code (independent of the "
      "OpenDSS solve only).", "", md(h_), "", f"Runtime {time.perf_counter() - t0:.0f} s."]
sm = OUT / "stage7_summary.md"
txt = sm.read_text(encoding="utf-8") if sm.exists() else ""
old = txt.split("\n## Year with EV")[1] if "\n## Year with EV" in txt else None
sm.write_text("\n".join(L) + ("\n\n## Year with EV" + old if old else ""), encoding="utf-8")
print("\n".join(L))
