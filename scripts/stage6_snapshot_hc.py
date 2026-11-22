"""Stage 6a runner: NZ headline snapshot HC with the L2 load (summer weekday midday median). Writes
results/stage6_snapshot_hc.csv and results/stage6_snapshot_summary.md (same format as Stage 4).
Simulated; IEEE feeder; NZ-parameterised synthetic load; ratings assumed."""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hc import hosting as h, l2, profiles as P, yearly as Y  # noqa: E402

LABEL = "simulated; IEEE feeder; NZ-parameterised synthetic load; ratings assumed"
PENS = (0.30, 0.60, 1.00)
N_SEEDS = 50
DIV_SEEDS = (2022, 1, 2, 3, 4)     # house-diversity seeds (per-day profile picks), not the P3 placement seeds
t_start = time.perf_counter()
house_kw, _pv, _t = Y.load_year_inputs()
idx_utc = P.time_index_utc()
L2_KW, N_L2_STEPS = l2.l2_kw(house_kw, idx_utc)
L2B_KW, _ = l2.l2_kw(l2.appliance_house_kw(), idx_utc)
rows = []
seen = {"vuf": 0.0, "kva": 0.0}


def make_model(pu):
    m = h.Model(pu, True)
    m.cases["L2"] = dict(zip(m.loads, L2_KW))
    m.cases["L2b"] = dict(zip(m.loads, L2B_KW))
    return m


def run_case(m, placement, seed, pen, load_case, source_pu, model_label, track=False, div_seed=""):
    n_pv = h.n_pv_for(pen, len(m.loads))
    idx = h.place_p1(m, n_pv) if placement == "P1" else h.place_p2(m, n_pv) if placement == "P2" \
        else h.place_p3(m, n_pv, seed)
    m.set_case(load_case, idx)
    hc, lim, el, info = h.find_hc(m)
    hc_v = h.find_hc(m, ignore=("line",))[0]
    if track:
        seen["vuf"] = max(seen["vuf"], info["vuf_max_pct"])
        seen["kva"] = max(seen["kva"], info["xfmr_kva"])
    thermal = lim.replace("baseline-", "") in ("line", "transformer")
    rows.append({"placement": placement, "seed": seed if placement == "P3" else "", "penetration": pen,
                 "n_pv": n_pv, "div_seed": div_seed, "load_case": load_case, "source_pu": source_pu, "model": model_label,
                 "HC_kW": round(hc, 2), "binding_limit": lim, "binding_element": el,
                 "binding_linecode": info.get("line_linecode", ""), "binding_phase": info.get("line_phase", ""),
                 "binding_chain_len": info.get("binding_chain_len", ""),
                 "rating_status": "assumed" if thermal else "n/a",
                 "HC_voltage_only_kW": round(hc_v, 2), "Orion_capped_HC_kW": round(min(hc, h.ORION_CAP_KW), 2),
                 "vuf_max_pct_at_HC": round(info["vuf_max_pct"], 3), "xfmr_kva_at_HC": round(info["xfmr_kva"], 1),
                 "label": LABEL})


m = make_model(1.0)
ph = np.array(m.phase)
per_phase = {n: [float(np.sum(np.asarray(v)[ph == p])) for p in (1, 2, 3)]
             for n, v in (("L1", m.kw_l1), ("L2", L2_KW), ("L2b", L2B_KW))}
for pen in PENS:
    for pl in ("P1", "P2"):
        run_case(m, pl, None, pen, "L2", 1.0, "neutral_return", track=True)
    for seed in range(N_SEEDS):
        run_case(m, "P3", seed, pen, "L2", 1.0, "neutral_return", track=True)
    run_case(m, "P1", None, pen, "L2b", 1.0, "sens_L2b_appliances_only")
print(f"main grid done {time.perf_counter() - t_start:.0f} s", flush=True)
for pu in (0.98, 1.00, 1.025, 1.05):
    run_case(make_model(pu), "P1", None, 0.60, "L2", pu, "sens_source_pu")

# House-diversity seed sweep: P1 at 30/60/100 %, L2 rebuilt from each seed's per-day profile picks.
m = make_model(1.0)     # fresh model: the source-voltage sweep above recompiled the global OpenDSS circuit
for dseed in DIV_SEEDS:
    kw_seed = L2_KW if dseed == 2022 else l2.l2_kw(l2.default_house_kw(dseed), idx_utc)[0]
    m.cases["L2"] = dict(zip(m.loads, kw_seed))
    for pen in PENS:
        run_case(m, "P1", None, pen, "L2", 1.0, "sens_diversity_seed", div_seed=dseed)
m.cases["L2"] = dict(zip(m.loads, L2_KW))

df = pd.DataFrame(rows)
out = ROOT / "results"
df.to_csv(out / "stage6_snapshot_hc.csv", index=False)
runtime_s = time.perf_counter() - t_start


def desc(r):
    lim = r.binding_limit
    if lim.replace("baseline-", "") == "line":
        return (f"{lim} (assumed rating): linecode {r.binding_linecode}, phase {int(float(r.binding_phase))}, nearest "
                f"line {r.binding_element}, chain of {int(float(r.binding_chain_len))} lines")
    if lim.replace("baseline-", "") == "transformer":
        return f"{lim} (assumed rating)"
    return f"{lim} {r.binding_element}".strip()


def f1(x):
    return f"{x:.1f}"


def md(d):
    head = "| " + " | ".join(d.columns) + " |\n|" + "---|" * len(d.columns)
    return head + "\n" + "\n".join("| " + " | ".join(str(x) for x in r) + " |" for r in d.itertuples(index=False))


main = df[df.model == "neutral_return"]
s4 = pd.read_csv(out / "stage4_hc.csv")
s4 = s4[(s4.model == "neutral_return") & (s4.load_case == "L1")]
L = ["# Stage 6 summary: NZ headline snapshot PV hosting capacity (L2)", "",
     f"**{LABEL}. Simulated, not measured.** Source 1.00 pu, PV single-phase at unity PF, no inverter control. "
     "HC = kW per PV customer (= kW per phase), 1 decimal (bisection step 0.01 kW). Penetration N = ceil(pen x 55) "
     "= 17, 33, 55. Orion cap = min(HC, 10). HC_V = HC ignoring line ratings. Thermal limits (lines, transformer "
     "800 kVA nameplate) use **assumed ratings** (data/line_ratings.csv, R10).", "",
     f"L2 = per house, the median of its 30-minute load over steps starting 12:00 and 12:30 NZDT on weekdays of "
     f"Dec, Jan and Feb 2022 ({N_L2_STEPS} steps = 63 weekdays x 2). L2b = the same from the appliances-only "
     "shape (sensitivity, no heating). L1 = Stage 4 (one random minute of non-NZ profiles).", "",
     "## Per-phase load totals (kW, 55 customers)", "",
     md(pd.DataFrame([{"case": n, "phase_1": f"{v[0]:.2f}", "phase_2": f"{v[1]:.2f}", "phase_3": f"{v[2]:.2f}",
                       "total": f"{sum(v):.2f}"} for n, v in per_phase.items()])), "",
     "Each house picks one of the feeder's 100 daily profiles at random per local day (diversity seed 2022 here; "
     "other seeds below). More midday load on a phase means more headroom for PV on that phase.", ""]
L += ["## P1 (balanced) and P2 (end-clustered), L2 next to L1 (Stage 4)", ""]
d = main[main.placement.isin(["P1", "P2"])].assign(source="L2")
d1 = s4[s4.placement.isin(["P1", "P2"])].assign(source="L1")
dd = pd.concat([d, d1]).copy()
dd["binding"] = dd.apply(desc, axis=1)
dd = dd.sort_values(["penetration", "placement", "source"])
dd = dd.assign(HC=dd.HC_kW.map(f1), Orion_capped=dd.Orion_capped_HC_kW.map(f1), HC_V=dd.HC_voltage_only_kW.map(f1))
L += [md(dd[["placement", "penetration", "n_pv", "source", "HC", "Orion_capped", "HC_V", "binding"]]), ""]

L += [f"## P3 random placement ({N_SEEDS} seeds, 0 to {N_SEEDS - 1}), L2", ""]
t = []
for pen, g in main[main.placement == "P3"].groupby("penetration"):
    p5, p50, p95 = (np.percentile(g.HC_kW, q) for q in (5, 50, 95))
    p1 = main[(main.placement == "P1") & (main.penetration == pen)].HC_kW.iloc[0]
    p2 = main[(main.placement == "P2") & (main.penetration == pen)].HC_kW.iloc[0]
    kinds = g.apply(lambda r: f"{r.binding_limit}" + (f"/{r.binding_linecode}/ph{r.binding_phase}"
                                                      if r.binding_linecode else ""), axis=1)
    t.append({"load_case": "L2", "penetration": pen, "P1_HC": f1(p1), "P2_HC": f1(p2), "P3_P5": f1(p5),
              "P3_P50": f1(p50), "P3_P95": f1(p95), "P2_below_P3_P5": "yes" if p2 < p5 else "no",
              "binding (assumed rating if line/transformer)": ", ".join(f"{k}:{v}" for k, v in kinds.value_counts().items())})
L += [md(pd.DataFrame(t)), ""]

L += ["## Source-voltage sweep (P1, L2, 60 %)", ""]
sw = df[df.model == "sens_source_pu"]
sw = sw.assign(binding=sw.apply(desc, axis=1), HC=sw.HC_kW.map(f1), HC_voltage_only=sw.HC_voltage_only_kW.map(f1))
L += [md(sw[["source_pu", "HC", "HC_voltage_only", "binding"]]), ""]

L += ["## House-diversity seed sweep (P1, L2)", "",
      "Same feeder, same P1 placement; only the per-day profile picks change with the seed. min / median / max "
      "over the 5 seeds (2022, 1, 2, 3, 4).", ""]
dv = df[df.model == "sens_diversity_seed"]
t = []
for pen, g in dv.groupby("penetration"):
    kinds = g.apply(lambda r: f"seed {r.div_seed}: " + desc(r), axis=1)
    t.append({"penetration": pen, "HC_min": f1(g.HC_kW.min()), "HC_median": f1(g.HC_kW.median()),
              "HC_max": f1(g.HC_kW.max()), "HC_per_seed": ", ".join(f1(x) for x in g.HC_kW),
              "binding": "; ".join(kinds)})
L += [md(pd.DataFrame(t)), ""]

L += ["## L2b (no electric heating or hot water, appliances-only shape, same scale factor as L2) next to L2, P1", ""]
b = pd.concat([main[main.placement == "P1"], df[df.model == "sens_L2b_appliances_only"]])
b = b.assign(binding=b.apply(desc, axis=1), HC=b.HC_kW.map(f1), HC_voltage_only=b.HC_voltage_only_kW.map(f1))
b = b.sort_values(["penetration", "load_case"])
L += [md(b[["load_case", "penetration", "n_pv", "HC", "HC_voltage_only", "binding"]]), ""]

L += ["## Limits seen", "",
      f"- Max VUF at the HC points of the main grid: {seen['vuf']:.2f} % (limit 2 %, assumed, EN 50160 basis).",
      f"- Transformer max kVA at the HC points of the main grid: {seen['kva']:.1f} kVA (800 kVA nameplate, assumed).",
      "", f"Runtime {runtime_s:.0f} s."]
(out / "stage6_snapshot_summary.md").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))
print(f"\nRUNTIME_S {runtime_s:.1f}")
