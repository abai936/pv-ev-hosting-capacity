"""Stage 4 runner: snapshot PV hosting capacity. Writes results/stage4_hc.csv, stage4_hand_check.csv and
stage4_summary.md. IEEE European LV feeder; load data synthetic/non-NZ; simulated; thermal ratings assumed."""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hc import hosting as h  # noqa: E402

PENS = (0.30, 0.60, 1.00)
N_SEEDS = 50
# Any per-customer kW dict can be added here (Stage 6: "L2" NZ case) with no change to hosting.py.
LOAD_LABEL = {"L0": "L0 zero load (minimum-load bound)",
              "L1": "L1 one stochastic minute of non-NZ feeder profiles (minute 720)"}
t_start = time.perf_counter()
rows = []
seen = {"vuf": 0.0, "kva": 0.0}


def run_case(m, placement, seed, pen, load_case, source_pu, model_label, track=False):
    n_pv = h.n_pv_for(pen, len(m.loads))
    if placement == "P1":
        idx = h.place_p1(m, n_pv)
    elif placement == "P2":
        idx = h.place_p2(m, n_pv)
    else:
        idx = h.place_p3(m, n_pv, seed)
    m.set_case(load_case, idx, load_kw=m.cases[load_case])
    hc, lim, el, info = h.find_hc(m)
    hc_v = h.find_hc(m, ignore=("line",))[0]
    if track:
        seen["vuf"] = max(seen["vuf"], info["vuf_max_pct"])
        seen["kva"] = max(seen["kva"], info["xfmr_kva"])
    thermal = lim.replace("baseline-", "") in ("line", "transformer")
    rows.append({"placement": placement, "seed": seed if placement == "P3" else "", "penetration": pen,
                 "n_pv": n_pv, "load_case": load_case, "source_pu": source_pu, "model": model_label,
                 "HC_kW": round(hc, 2), "binding_limit": lim, "binding_element": el,
                 "binding_linecode": info.get("line_linecode", ""), "binding_phase": info.get("line_phase", ""),
                 "binding_chain_len": info.get("binding_chain_len", ""),
                 "rating_status": "assumed" if thermal else "n/a",
                 "HC_voltage_only_kW": round(hc_v, 2), "Orion_capped_HC_kW": round(min(hc, h.ORION_CAP_KW), 2),
                 "vuf_max_pct_at_HC": round(info["vuf_max_pct"], 3), "xfmr_kva_at_HC": round(info["xfmr_kva"], 1)})


# Main grid: source 1.00, neutral return on, ratings as assumed.
m = h.Model(1.0, True)
for lc in ("L1", "L0"):
    for pen in PENS:
        for pl in ("P1", "P2"):
            run_case(m, pl, None, pen, lc, 1.0, "neutral_return", track=True)
        for seed in range(N_SEEDS):
            run_case(m, "P3", seed, pen, lc, 1.0, "neutral_return", track=True)
print(f"main grid done {time.perf_counter() - t_start:.0f} s", flush=True)

# Sensitivities on P1, L1, 60 %.
for pu in (0.98, 1.00, 1.025, 1.05):
    run_case(h.Model(pu, True), "P1", None, 0.60, "L1", pu, "sens_source_pu")
run_case(h.Model(1.0, False), "P1", None, 0.60, "L1", 1.0, "sens_no_neutral_return")
for sc in (0.8, 1.2):
    run_case(h.Model(1.0, True, rating_scale=sc), "P1", None, 0.60, "L1", 1.0, f"sens_ratings_x{sc}")

df = pd.DataFrame(rows)
out = ROOT / "results"
df.to_csv(out / "stage4_hc.csv", index=False)
pred, sim, name, nl = h.write_hand_check(out / "stage4_hand_check.csv", 5.0)
runtime_s = time.perf_counter() - t_start

# ---- summary ----
main = df[df.model == "neutral_return"]


def desc(r):
    """Human binding description; thermal-bound results carry 'assumed rating'."""
    lim = r.binding_limit
    if lim.replace("baseline-", "") == "line":
        return (f"{lim} (assumed rating): linecode {r.binding_linecode}, phase {r.binding_phase}, nearest "
                f"line {r.binding_element}, chain of {r.binding_chain_len} lines")
    if lim.replace("baseline-", "") == "transformer":
        return f"{lim} (assumed rating)"
    return f"{lim} {r.binding_element}".strip()


def f1(x):
    return f"{x:.1f}"


def md(d):
    head = "| " + " | ".join(d.columns) + " |\n|" + "---|" * len(d.columns)
    rows_md = ["| " + " | ".join(str(x) for x in r) + " |" for r in d.itertuples(index=False)]
    return head + "\n" + "\n".join(rows_md)


L = ["# Stage 4 summary: snapshot PV hosting capacity", "",
     "**IEEE European LV feeder; load data synthetic/non-NZ. Simulated, not measured.** Source 1.00 pu, 12:00 "
     "snapshot, PV single-phase at unity PF, no inverter control. HC = kW per PV customer (= kW per phase), "
     "reported to 1 decimal (bisection step 0.01 kW; the CSV keeps 2 decimals). Penetration N = ceil(pen x 55) "
     "= 17, 33, 55. Orion cap = min(HC, 10). HC_V = HC ignoring line ratings. Thermal limits (lines, transformer "
     "800 kVA nameplate) use **assumed ratings** (data/line_ratings.csv, R10).", "",
     "Load cases: L0 = zero load, the minimum-load bound (worst case for voltage rise). L1 = one stochastic "
     "minute of non-NZ feeder profiles (minute 720); it is a single random minute, not an NZ load case. "
     "An NZ case (L2) comes in Stage 6.", "",
     "No-load LV voltage is about 240 V at 1.00 pu source (0.416 kV / sqrt(3)), because of the 11/0.416 kV "
     "ratio, so customers start close to the 253 V upper limit.", ""]

L += ["## P1 (balanced) and P2 (end-clustered), L0 next to L1", ""]
d = main[main.placement.isin(["P1", "P2"])].copy()
d["binding"] = d.apply(desc, axis=1)
d = d.sort_values(["penetration", "placement", "load_case"])
d = d.assign(HC=d.HC_kW.map(f1), Orion_capped=d.Orion_capped_HC_kW.map(f1), HC_V=d.HC_voltage_only_kW.map(f1))
L += [md(d[["placement", "penetration", "n_pv", "load_case", "HC", "Orion_capped", "HC_V", "binding"]]), ""]

L += [f"## P3 random placement ({N_SEEDS} seeds, 0 to {N_SEEDS - 1}), L0 next to L1", ""]
t, notes = [], []
for (lc, pen), g in main[main.placement == "P3"].groupby(["load_case", "penetration"]):
    p5, p50, p95 = (np.percentile(g.HC_kW, q) for q in (5, 50, 95))
    p2 = main[(main.placement == "P2") & (main.load_case == lc) & (main.penetration == pen)].HC_kW.iloc[0]
    p1 = main[(main.placement == "P1") & (main.load_case == lc) & (main.penetration == pen)].HC_kW.iloc[0]
    kinds = g.apply(lambda r: f"{r.binding_limit}" + (f"/{r.binding_linecode}/ph{r.binding_phase}"
                                                      if r.binding_linecode else ""), axis=1)
    t.append({"load_case": lc, "penetration": pen, "P1_HC": f1(p1), "P2_HC": f1(p2), "P3_P5": f1(p5),
              "P3_P50": f1(p50), "P3_P95": f1(p95), "P2_below_P3_P5": "yes" if p2 < p5 else "no",
              "binding (assumed rating if line/transformer)": ", ".join(f"{k}:{v}" for k, v in kinds.value_counts().items())})
L += [md(pd.DataFrame(t)), ""]
L += ["P2 (end-clustering) is not the worst case: where `P2_below_P3_P5` is `no`, P2 is at or above the "
      "5th-percentile random placement, so some random placements give a lower HC than P2. Use the P3 P5 as the "
      "conservative figure.", ""]

L += ["## Source-voltage sweep (P1, L1, 60 %)", ""]
base = main[(main.placement == "P1") & (main.load_case == "L1") & (main.penetration == 0.6)].assign(model="base")
sw = pd.concat([base, df[df.model == "sens_source_pu"]])
sw = sw.assign(binding=sw.apply(desc, axis=1), HC=sw.HC_kW.map(f1), HC_voltage_only=sw.HC_voltage_only_kW.map(f1))
L += [md(sw[["model", "source_pu", "HC", "HC_voltage_only", "binding"]]), ""]
L += ["A lower source voltage (for example 0.98 pu) can give a LOWER HC than 1.00 pu, even though it gives more "
      "voltage headroom: the HC is thermal-bound (assumed rating), and a lower voltage means more current for "
      "the same power. HC_voltage_only (line ratings ignored) shows the voltage-rise limit alone.", ""]

L += ["## Other sensitivities (P1, L1, 60 %)", ""]
oth = df[df.model.isin(["sens_no_neutral_return"]) | df.model.str.startswith("sens_ratings")]
oth = oth.assign(binding=oth.apply(desc, axis=1), HC=oth.HC_kW.map(f1), HC_voltage_only=oth.HC_voltage_only_kW.map(f1))
L += [md(oth[["model", "HC", "HC_voltage_only", "binding"]]), ""]

L += ["## Limits seen", "",
      f"- VUF 2 % limit is **assumed** (EN 50160 basis, ASSUMPTIONS.md A7). Max VUF seen at the HC points of "
      f"the main grid: {seen['vuf']:.2f} %.",
      f"- Transformer max kVA seen at the HC points of the main grid: {seen['kva']:.1f} kVA (800 kVA nameplate, "
      "assumed rating).",
      f"- Hand check (load53-type worst customer {name}, 5 kW, {nl} lines): predicted {pred:.4f} V, OpenDSS "
      f"{sim:.4f} V; the current uses the solved customer voltage. See results/stage4_hand_check.csv.", "",
      f"Runtime {runtime_s:.0f} s."]
(out / "stage4_summary.md").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))
print(f"\nRUNTIME_S {runtime_s:.1f}")
