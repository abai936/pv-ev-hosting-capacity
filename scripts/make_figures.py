"""Make Stage 2 checkpoint figures from results/stage2_toy_checks.csv.

All numbers are read from the CSV. Nothing is typed in by hand.
Data is simulated (synthetic, NZ-parameterised), not measured.
"""
import csv
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "results" / "stage2_toy_checks.csv"
OUT_DIR = ROOT / "checkpoints" / "img"
DPI = 150


def read_rows():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fig_transformer_noload(rows):
    """Bar chart of transformer no-load phase voltage. Needs transformer rows in the CSV."""
    picked = [r for r in rows if r["case"].startswith("3 xfmr") and r["quantity"].endswith("[V]")]
    if not picked:
        print("SKIP cp02_transformer_noload.png: no transformer rows in CSV.")
        return None
    labels = [r["case"] for r in picked]
    values = [float(r["opendss_value"]) for r in picked]
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, values, color="steelblue")
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.3, f"{v:.1f} V", ha="center")
    ax.axhline(253, color="red", linestyle="--", label="NZ upper limit 253 V")
    ax.axhline(230, color="grey", linestyle=":", label="230 V nominal")
    ax.set_ylim(220, 260)
    ax.set_ylabel("Phase voltage (V)")
    ax.set_title("No-load LV voltage vs source setting (simulated)")
    ax.legend(loc="lower right")
    out = OUT_DIR / "cp02_transformer_noload.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return out


def fig_single_phase(rows):
    """Grouped bars: hand calc vs OpenDSS for phases a, b, c, for both 1ph cases."""
    picked = [r for r in rows if r["case"].startswith("2 1ph")]
    if not picked:
        print("SKIP cp02_single_phase.png: no case 2 rows in CSV.")
        return None
    labels = [r["case"].replace("2 1ph ", "") + "\n" + r["quantity"].replace("V phase ", "phase ").split(" [")[0]
              for r in picked]
    hand = [float(r["hand_value"]) for r in picked]
    ods = [float(r["opendss_value"]) for r in picked]
    x = list(range(len(picked)))
    w = 0.38
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar([i - w / 2 for i in x], hand, w, label="Hand calculation", color="tab:orange")
    ax.bar([i + w / 2 for i in x], ods, w, label="OpenDSS", color="tab:blue")
    ax.axhline(230, color="grey", linestyle=":", label="230 V nominal")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylim(220, 240)
    ax.set_ylabel("Phase voltage (V)")
    ax.set_title("Single-phase 7.4 kW on a 3-phase line: hand calc vs OpenDSS")
    ax.legend(loc="upper right")
    out = OUT_DIR / "cp02_single_phase.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return out


BASE_CASE_CSV = ROOT / "results" / "stage3_base_case.csv"
INVCONTROL_CSV = ROOT / "results" / "stage3_invcontrol_spike.csv"


def read_csv_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fig_base_case(_rows=None):
    """Vertical range bars (min to max customer voltage) per source pu. Reads stage3_base_case.csv."""
    picked = read_csv_rows(BASE_CASE_CSV)
    labels = [r["source_pu"] for r in picked]
    vmin = [float(r["v_min_V"]) for r in picked]
    vmax = [float(r["v_max_V"]) for r in picked]
    x = list(range(len(picked)))
    fig, ax = plt.subplots(figsize=(8, 5))
    for i in x:
        ax.vlines(i, vmin[i], vmax[i], color="steelblue", linewidth=8)
        ax.text(i + 0.1, vmax[i], f"{vmax[i]:.1f} V", va="bottom", ha="left", fontsize=9)
    ax.axhline(253, color="red", linestyle="--", label="NZ upper limit 253 V")
    ax.axhline(207, color="red", linestyle="--", label="NZ lower limit 207 V")
    ax.axhline(230, color="grey", linestyle=":", label="230 V nominal")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlim(-0.5, len(picked) - 0.5)
    ax.set_ylim(200, 260)
    ax.set_xlabel("Source setting (pu)")
    ax.set_ylabel("Customer voltage (V)")
    ax.set_title("907-bus feeder, no PV: voltage range over one day vs source setting (simulated)")
    ax.legend(loc="lower right")
    out = OUT_DIR / "cp03_base_case.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return out


def fig_invcontrol(_rows=None):
    """Bars of max customer voltage per scenario, labelled with minutes above 253 V. Reads stage3_invcontrol_spike.csv."""
    picked = read_csv_rows(INVCONTROL_CSV)
    labels = [r["scenario"] for r in picked]
    vmax = [float(r["v_max_V"]) for r in picked]
    mins = [r["minutes_above_253V"] for r in picked]
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, vmax, color="steelblue")
    for b, v, m in zip(bars, vmax, mins):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.3, f"{v:.1f} V\n{m} min above 253 V",
                ha="center", va="bottom", fontsize=9)
    ax.axhline(253, color="red", linestyle="--", label="NZ upper limit 253 V")
    ax.set_ylim(230, 270)
    ax.set_ylabel("Max customer voltage (V)")
    ax.set_title("55 x 5 kVA PV, one synthetic clear day: Australia A volt-var + volt-watt (simulated)")
    ax.legend(loc="lower right")
    out = OUT_DIR / "cp03_invcontrol.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return out


HC4_CSV = ROOT / "results" / "stage4_hc.csv"


def fig_cp04_hc_vs_penetration(_rows=None):
    """HC per customer vs penetration, base model, L1, source 1.0. Reads stage4_hc.csv."""
    base = [r for r in read_csv_rows(HC4_CSV)
            if r["source_pu"] == "1.0" and r["model"] == "neutral_return" and r["load_case"] == "L1"]
    p1 = sorted([r for r in base if r["placement"] == "P1"], key=lambda r: float(r["penetration"]))
    p2 = sorted([r for r in base if r["placement"] == "P2"], key=lambda r: float(r["penetration"]))
    p3 = [r for r in base if r["placement"] == "P3"]
    pens = sorted({float(r["penetration"]) for r in p3})
    p5, p50, p95 = [], [], []
    for pen in pens:
        vals = [float(r["HC_kW"]) for r in p3 if float(r["penetration"]) == pen]
        a, b, c = np.percentile(vals, [5, 50, 95])
        p5.append(a)
        p50.append(b)
        p95.append(c)
    x_pct = [pen * 100 for pen in pens]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.fill_between(x_pct, p5, p95, color="steelblue", alpha=0.2, label="P3 random seeds: P5 to P95")
    ax.plot(x_pct, p50, color="steelblue", linestyle="--", label="P3 random seeds: P50")
    x1 = [float(r["penetration"]) * 100 for r in p1]
    y1 = [float(r["HC_kW"]) for r in p1]
    ax.plot(x1, y1, color="tab:orange", marker="o", label="P1 balanced")
    for x, y, r in zip(x1, y1, p1):
        ax.annotate(r["binding_limit"], (x, y), textcoords="offset points", xytext=(0, 7),
                    ha="center", fontsize=8)
    x2 = [float(r["penetration"]) * 100 for r in p2]
    y2 = [float(r["HC_kW"]) for r in p2]
    ax.plot(x2, y2, color="tab:green", marker="s", label="P2 end-clustered")
    ax.axhline(10, color="grey", linestyle=":", label="Orion cap 10 kW")
    ax.text(x_pct[0], 10, "Orion cap 10 kW", va="bottom", ha="left", fontsize=8, color="grey")
    ax.set_xlabel("PV penetration (%)")
    ax.set_ylabel("HC per customer (kW)")
    ax.set_xticks(x_pct)
    ax.set_title("PV hosting capacity per customer, midday snapshot (simulated; load not NZ; ratings assumed)",
                 fontsize=10)
    ax.legend(loc="upper right", fontsize=8)
    out = OUT_DIR / "cp04_hc_vs_penetration.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return out


SENS_LABELS = {
    "sens_no_neutral_return": "no neutral return",
    "sens_ratings_x0.8": "ratings x0.8",
    "sens_ratings_x1.2": "ratings x1.2",
}


def fig_cp04_sensitivity(_rows=None):
    """Horizontal bars of HC for P1, L1, 60% sensitivity rows (model starts with sens_). Reads stage4_hc.csv."""
    picked = [r for r in read_csv_rows(HC4_CSV)
              if r["model"].startswith("sens_") and r["placement"] == "P1"
              and r["load_case"] == "L1" and float(r["penetration"]) == 0.6]
    if not picked:
        print("SKIP cp04_sensitivity.png: no sensitivity rows in CSV.")
        return None
    labels = []
    for r in picked:
        if r["model"] == "sens_source_pu":
            labels.append(f"source {r['source_pu']} pu")
        else:
            labels.append(SENS_LABELS[r["model"]])
    vals = [float(r["HC_kW"]) for r in picked]
    fig, ax = plt.subplots(figsize=(8, 5))
    y = list(range(len(picked)))
    bars = ax.barh(y, vals, color="steelblue")
    xmax = max(vals)
    for b, v, r in zip(bars, vals, picked):
        ax.text(v + xmax * 0.01, b.get_y() + b.get_height() / 2, f"{v:.2f} kW, {r['binding_limit']}",
                va="center", fontsize=9)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlim(0, xmax * 1.35)
    ax.set_xlabel("HC per customer (kW)")
    ax.set_title("What moves hosting capacity (P1, 60%, simulated)")
    out = OUT_DIR / "cp04_sensitivity.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return out


def fig_cp05_profiles(rows):
    """One January and one July week: average house load, PV per kWp, one EV (Auckland time).
    Data are synthetic, NZ-parameterised (load, EV) and modelled (PV, PVGIS-ERA5)."""
    import pandas as pd
    base = ROOT / "data" / "processed"
    f1, f2 = base / "avg_house_and_pv_30min.csv", base / "ev_kw.npz"
    if not (f1.exists() and f2.exists()):
        print("SKIP cp05_profiles.png: run scripts/stage5_build_profiles.py first.")
        return None
    df = pd.read_csv(f1, index_col=0, parse_dates=True)
    z = np.load(f2)
    df["ev_kw"] = z["kw"][:, 0]
    df.index = df.index.tz_convert("Pacific/Auckland")  # labels only; data stay on the UTC grid
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharey=True)
    for ax, (start, name) in zip(axes, [("2022-01-10", "January"), ("2022-07-11", "July")]):
        t0 = pd.Timestamp(start, tz="Pacific/Auckland")
        w = df[(df.index >= t0) & (df.index < t0 + pd.Timedelta(days=7))]
        ax.plot(w.index, w["avg_house_kw"], label="average house load (kW)")
        ax.plot(w.index, w["pv_kw_per_kwp"], label="PV (kW per kWp)")
        ax.plot(w.index, w["ev_kw"], label="one EV (kW)", alpha=0.7)
        ax.set_title(f"{name} week, Auckland local time")
        ax.set_ylabel("kW")
        ax.legend(loc="upper right", fontsize=8)
    axes[1].set_xlabel("Auckland local time (UTC data converted for labels)")
    fig.suptitle("Stage 5 profiles: synthetic, NZ-parameterised (load, EV); modelled (PV)")
    out = OUT_DIR / "cp05_profiles.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return out


HC6_CSV = ROOT / "results" / "stage6_snapshot_hc.csv"
YEAR6_CSV = ROOT / "results" / "stage6_year.csv"


def fig_cp06_hc_nz_vs_feeder(_rows=None):
    """P1 and P2 HC vs penetration: L2 (NZ midday) next to L1 (Stage 4 feeder profile), P3 band for L2."""
    l2 = [r for r in read_csv_rows(HC6_CSV) if r["model"] == "neutral_return" and r["load_case"] == "L2"]
    l1 = [r for r in read_csv_rows(HC4_CSV) if r["model"] == "neutral_return" and r["load_case"] == "L1"
          and r["source_pu"] == "1.0"]

    def line(rows, pl):
        rr = sorted([r for r in rows if r["placement"] == pl], key=lambda r: float(r["penetration"]))
        return [float(r["penetration"]) * 100 for r in rr], [float(r["HC_kW"]) for r in rr]
    p3 = [r for r in l2 if r["placement"] == "P3"]
    pens = sorted({float(r["penetration"]) for r in p3})
    q = np.array([np.percentile([float(r["HC_kW"]) for r in p3 if float(r["penetration"]) == pen], [5, 50, 95])
                  for pen in pens])
    x = [p * 100 for p in pens]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.fill_between(x, q[:, 0], q[:, 2], color="steelblue", alpha=0.2, label="L2 P3 random: P5 to P95")
    ax.plot(x, q[:, 1], color="steelblue", linestyle="--", label="L2 P3 random: P50")
    for rows, tag, ls in ((l2, "L2 NZ", "-"), (l1, "L1 feeder profile", ":")):
        for pl, col, mk in (("P1", "tab:orange", "o"), ("P2", "tab:green", "s")):
            xs, ys = line(rows, pl)
            ax.plot(xs, ys, color=col, marker=mk, linestyle=ls, label=f"{tag} {pl}")
    ax.set_xticks(x)
    ax.set_xlabel("PV penetration (%)")
    ax.set_ylabel("HC per customer (kW)")
    ax.set_title("PV hosting capacity, midday snapshot: NZ load L2 vs feeder load L1\n"
                 "(simulated; IEEE feeder; NZ-parameterised synthetic load; ratings assumed)", fontsize=9)
    ax.legend(fontsize=8)
    out = OUT_DIR / "cp06_hc_nz_vs_feeder.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return out


def fig_cp06_year_violations(_rows=None):
    """Bars: customer-hours above 253 V and distinct hours with any line above 100% of assumed rating, Y0 to Y3."""
    if not YEAR6_CSV.exists():
        print("SKIP cp06_year_violations.png: run scripts/stage6_year.py first.")
        return None
    rows = read_csv_rows(YEAR6_CSV)
    names = [f"{r['case']}\n{float(r['pv_kwp_per_house']):.0f} kWp" for r in rows]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    for ax, key, ttl, col in ((axes[0], "cust_hours_above_253V", "Customer-hours above 253 V", "tab:red"),
                              (axes[1], "distinct_hours_line_above_100pct",
                               "Hours with any line above 100% of assumed rating\n(a step counts once)", "tab:purple")):
        vals = [float(r[key]) for r in rows]
        bars = ax.bar(names, vals, color=col)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v, f"{v:,.0f}", ha="center", va="bottom", fontsize=9)
        ax.set_title(ttl, fontsize=10)
        ax.set_ylabel("customer-hours" if "cust" in key else "hours")
    fig.suptitle("2022, 30-min steps, P1 60% PV, unity PF (simulated; NZ-parameterised synthetic; ratings assumed)",
                 fontsize=9, y=1.04)
    out = OUT_DIR / "cp06_year_violations.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return out


EV_HC_CSV = ROOT / "results" / "stage7_ev_hc.csv"
YEAR7_CSV = ROOT / "results" / "stage7_year_ev.csv"
YEAR7_LC_CSV = ROOT / "results" / "stage7_year_ev_linecodes.csv"


def fig_cp07_ev_hc_vs_placement(_rows=None):
    """Bars: EVs supported (count) per placement, 7.4 kW, source 1.00 pu, two load cases (LE median evening, LE_P90).
    Headline P1_direct; P1_nested_order hatched (ordering artefact); P3 = median with P5 to P95 bar."""
    if not EV_HC_CSV.exists():
        print("SKIP cp07_ev_hc_vs_placement.png: run scripts/stage7_ev_hc.py first.")
        return None
    allrows = [r for r in read_csv_rows(EV_HC_CSV) if r["model"] == "main"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), sharey=True)
    ymax = 0
    for ax, lc, ttl in ((axes[0], "LE", "LE: median weekday evening (typical, not design peak)"),
                        (axes[1], "LE_P90", "LE_P90: one evening step at the 90th percentile of feeder load")):
        rows = [r for r in allrows if r["load_case"] == lc]
        pick = lambda pl: [r for r in rows if r["placement"] == pl]
        p3 = np.array([float(r["EV_HC_count"]) for r in pick("P3")])
        p1, p2, pn = pick("P1_direct")[0], pick("P2")[0], pick("P1_nested_order")[0]
        p5, p50, p95 = (np.percentile(p3, q) for q in (5, 50, 95))
        vals = [float(p1["EV_HC_count"]), float(p2["EV_HC_count"]), p50, float(pn["EV_HC_count"])]
        kinds = {}
        for r in pick("P3"):
            k = r["binding_limit"] + "/" + r["binding_linecode"]
            kinds[k] = kinds.get(k, 0) + 1
        lab = lambda r: f"{r['binding_limit']}\n{r['binding_linecode']} (assumed)"
        notes = [lab(p1), lab(p2), "; ".join(f"{k} x{v}" for k, v in kinds.items()) + "\n(assumed)",
                 "ordering artefact\nphase mix " + pn["phase_mix_at_first_fail"] + " at first fail"]
        bars = ax.bar(["P1_direct\n(headline,\nphase-balanced)", "P2\nfar end\nfirst", "P3 random\n(median,\nP5-P95)",
                       "P1_nested\n_order\n(artefact)"], vals,
                      color=["tab:blue", "tab:orange", "tab:green", "lightsteelblue"],
                      yerr=[[0, 0, p50 - p5, 0], [0, 0, p95 - p50, 0]], capsize=6)
        bars[3].set_hatch("//")
        for bb, v, n in zip(bars, vals, notes):
            ax.text(bb.get_x() + bb.get_width() / 2, v + (p95 - p50 if v == p50 else 0) + 0.2, f"{v:.0f} EVs\n{n}",
                    ha="center", va="bottom", fontsize=7)
        ax.set_title(ttl, fontsize=9)
        ymax = max(ymax, max(vals + [p95]))
    axes[0].set_ylabel("EVs charging at once, no violation (count, of 55 houses)")
    axes[0].set_ylim(0, ymax * 1.6)
    fig.suptitle("EV hosting capacity, 7.4 kW EVs, source 1.00 pu "
                 "(simulated; synthetic NZ-parameterised load; line ratings assumed)", fontsize=9, y=1.0)
    out = OUT_DIR / "cp07_ev_hc_vs_placement.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return out


S6_SEEDS_CSV = ROOT / "results" / "stage6_year_seeds.csv"
S6_SEEDS_LC_CSV = ROOT / "results" / "stage6_year_seeds_linecodes.csv"


def fig_cp07_year_ev_lowvoltage(_rows=None):
    """Y0 vs +30% vs +60% EV (seed 2022 bars); seeds 1 to 4 as points: hollow = Y0 for that seed (Stage 6 file),
    filled = E60 for that seed, so EV effect = E60 minus Y0 for the same seed. Left: distinct hours below 207 V.
    Right: hours with a 4c_70 trunk line above 100% (assumed rating)."""
    if not (YEAR7_CSV.exists() and YEAR7_LC_CSV.exists() and S6_SEEDS_CSV.exists()):
        print("SKIP cp07_year_ev_lowvoltage.png: run scripts/stage7_year_ev.py first.")
        return None
    rows, lcs = read_csv_rows(YEAR7_CSV), read_csv_rows(YEAR7_LC_CSV)
    s6, s6lc = read_csv_rows(S6_SEEDS_CSV), read_csv_rows(S6_SEEDS_LC_CSV)
    trunk = "4c_70"        # trunk linecode that binds the EV snapshot HC (stage7_ev_hc.csv)
    def trunk_h(r):
        return float([l for l in lcs if l["seed"] == r["seed"] and l["case"] == r["case"]
                      and l["linecode"] == trunk][0]["distinct_hours_above_100pct"])
    def y0_trunk(seed):
        return float([l for l in s6lc if l["seed"] == seed and l["case"] == "Y0"
                      and l["linecode"] == trunk][0]["distinct_hours_above_100pct"])
    def y0_low(seed):
        return float([r for r in s6 if r["seed"] == seed and r["case"] == "Y0"][0]["distinct_hours_below_207V"])
    main = {r["case"]: r for r in rows if r["seed"] == "2022"}
    e60s = [r for r in rows if r["case"] == "E60" and r["seed"] != "2022"]
    names = ["Y0\nno EV", "E30\n+30% EV", "E60\n+60% EV"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 5.4))
    for ax, f_, y0f, ttl, col in ((axes[0], lambda r: float(r["distinct_hours_below_207V"]), y0_low,
                                   "Distinct hours with any customer below 207 V", "tab:red"),
                                  (axes[1], trunk_h, y0_trunk,
                                   f"Distinct hours with a {trunk} line above 100%\n(assumed rating)", "tab:purple")):
        vals = [f_(main[c]) for c in ("Y0", "E30", "E60")]
        bars = ax.bar(names, vals, color=col)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v, f"{v:,.1f}", ha="center", va="bottom", fontsize=9)
        ax.scatter([0.3] * len(e60s), [y0f(r["seed"]) for r in e60s], facecolors="none", edgecolors="k",
                   zorder=3, s=26, label="Y0 seeds 1 to 4 (Stage 6)")
        ax.scatter([2.3] * len(e60s), [f_(r) for r in e60s], color="k", zorder=3, s=22,
                   label="E60 seeds 1 to 4 (+60% EV)")
        ax.set_ylabel("hours in 2022"); ax.set_xlim(-0.6, 2.7)
        ax.set_title(ttl, fontsize=10)
        ax.legend(fontsize=8, loc="upper left")
    dv = "; ".join(f"seed {r['seed']}: {float(r['delta_v_min_V']):+.2f} V" for r in e60s)
    fig.text(0.5, -0.02, "EV effect (E60 minus Y0, same seed) on lowest customer voltage: " + dv +
             ".\nBars = seed 2022; hollow = Y0 for that seed, filled = E60 for that seed.", ha="center", va="top", fontsize=8)
    fig.suptitle("2022, 30-min steps, P1 EV placement, no PV (simulated; synthetic NZ-parameterised; ratings assumed)",
                 fontsize=9, y=1.0)
    out = OUT_DIR / "cp07_year_ev_lowvoltage.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return out


S8_HC_CSV = ROOT / "results" / "stage8_hc.csv"
S8_YEAR_CSV = ROOT / "results" / "stage8_year.csv"


def fig_cp08_hc_mitigation(_rows=None):
    """Grouped bars: P1 snapshot HC (kW per PV customer) at 30/60/100 % for M0, M3, M0+tap 0.975, M3+tap 0.975
    (L2 load, inverter kVA = kW). Orion cap 10 kW dashed; the binding limit is printed above each bar."""
    if not S8_HC_CSV.exists():
        print("SKIP cp08_hc_mitigation.png: run scripts/stage8_mitigation_hc.py first.")
        return None
    rows = [r for r in read_csv_rows(S8_HC_CSV) if r["placement"] == "P1" and float(r["kva_ratio"]) == 1.0]
    series = [("M0", 1.0, "M0 unity PF, tap 1.000", "tab:gray"), ("M3", 1.0, "M3 Aus A volt-var+volt-watt, tap 1.000", "tab:blue"),
              ("M0", 0.975, "M0 unity PF, tap 0.975", "tab:orange"), ("M3", 0.975, "M3 Aus A, tap 0.975", "tab:green")]
    pens = [0.3, 0.6, 1.0]
    fig, ax = plt.subplots(figsize=(10, 5.4))
    w = 0.2
    for j, (mo, tp, lab, col) in enumerate(series):
        for i, pen in enumerate(pens):
            r = [x for x in rows if x["mode"] == mo and float(x["tap"]) == tp and float(x["penetration"]) == pen][0]
            if r["status"] == "nonconverged":
                ax.text(i + (j - 1.5) * w, 0.2, "nonconv.", rotation=90, ha="center", fontsize=7)
                continue
            v = float(r["HC_kW"])
            xb = i + (j - 1.5) * w
            ax.bar(xb, v, w * 0.95, color=col, label=lab if i == 0 else None)
            b = r["binding_limit"]
            tag = "line" if b.startswith("line") else "volt" if b.startswith("voltage") else b[:6]
            ax.text(xb, v + 0.1, f"{v:.1f}\n{tag}", ha="center", va="bottom", fontsize=7)
    ax.axhline(10.0, color="k", ls="--", lw=1)
    ax.text(1.0, 10.1, "Orion cap 10 kW", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(range(3)); ax.set_xticklabels(["30 % of customers\n(17 PV)","60 % (33 PV)", "100 % (55 PV)"])
    ax.set_ylabel("PV hosting capacity, kW per PV customer (= per phase)")
    ax.set_ylim(0, 12.5)
    ax.legend(fontsize=8, loc="upper right", bbox_to_anchor=(1.0, 0.8))
    ax.set_title("Snapshot PV hosting capacity with control and tap, P1 balanced placement, L2 summer midday load\n"
                 "'line' = assumed line rating binds (4c_70 trunk), 'volt' = 253 V binds. Inverter kVA = PV kW. "
                 "Simulated; synthetic NZ-parameterised load; ratings assumed", fontsize=8)
    out = OUT_DIR / "cp08_hc_mitigation.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return out


def fig_cp08_year_curtailment(_rows=None):
    """Y3 (8 kWp, 60 % P1, kVA = kW): voltage cost, curtailment, and thermal cost per mode/tap.
    Panel 1 customer-hours above 253 V; panel 2 curtailed kWh (about zero, so a small panel); panel 3 distinct hours any
    line is above 100 % of its ASSUMED rating (bars) and transformer max kVA (labels, 800 kVA assumed rating)."""
    if not S8_YEAR_CSV.exists():
        print("SKIP cp08_year_curtailment.png: run scripts/stage8_year_control.py first.")
        return None
    rows = [r for r in read_csv_rows(S8_YEAR_CSV) if float(r["kva_ratio"]) == 1.0]
    names = [f"{r['mode']}\ntap {float(r['tap']):.3f}" for r in rows]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), gridspec_kw={"width_ratios": [1.2, 0.7, 1.3]})
    vals = [float(r["cust_hours_above_253V"]) for r in rows]
    bars = axes[0].bar(names, vals, color="tab:red")
    for b, v in zip(bars, vals):
        axes[0].text(b.get_x() + b.get_width() / 2, v, f"{v:,.1f}", ha="center", va="bottom", fontsize=8)
    axes[0].set_title("Customer-hours above 253 V", fontsize=10)
    axes[0].set_ylabel("customer-hours")
    # curtailment: small panel, values as text (all near zero next to the PV energy)
    cur = [float(r["curtailed_kWh"]) for r in rows]
    axes[1].bar(names, [max(c, 0.0) for c in cur], color="tab:blue")
    for k, c in enumerate(cur):
        axes[1].text(k, max(c, 0.0), "below 1 kWh" if abs(c) < 1.0 else f"{c:,.1f} kWh", ha="center", va="bottom", fontsize=7, rotation=90)
    axes[1].set_title("Curtailed PV energy\n(available minus delivered)", fontsize=10)
    axes[1].set_ylabel(f"kWh per year (PV available {float(rows[0]['pv_available_kWh']) / 1000:,.0f} MWh)")
    axes[1].set_ylim(0, max(max(cur), 1.0) * 1.8)
    axes[1].tick_params(axis="x", labelsize=7, labelrotation=90)
    # thermal cost
    hrs = [float(r["distinct_hours_line_above_100pct"]) for r in rows]
    bars = axes[2].bar(names, hrs, color="tab:orange")
    for b, v, r in zip(bars, hrs, rows):
        axes[2].text(b.get_x() + b.get_width() / 2, v, f"{v:,.1f} h\nxfmr max {float(r['xfmr_max_kVA']):,.0f} kVA", ha="center", va="bottom", fontsize=7)
    axes[2].set_title("Thermal cost: hours any line above 100 %\n(assumed ratings) and transformer peak kVA", fontsize=10)
    axes[2].set_ylabel("distinct hours in the year")
    axes[2].set_ylim(0, max(hrs) * 1.25)
    fig.suptitle(f"Y3: 8 kWp on 60 % of houses (P1), inverter kVA = kW. Scope: {rows[1]['scope'].split(';')[0]}. "
                 "Simulated; synthetic NZ-parameterised; ratings assumed", fontsize=8, y=1.02)
    out = OUT_DIR / "cp08_year_curtailment.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return out


def fig_cp09b_backtest(_rows=None):
    """Forecast vs actual at origin Dec 2023, 24 months ahead, PV and EV: naive (= best back-tested), linear, best logistic,
    with the 80 % band of the best model. Modelled forecast; national data."""
    import sys
    import pandas as pd
    sys.path.insert(0, str(ROOT / "src"))
    from hc import uptake as U
    S = U.build_series()
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.8))
    for ax, kind, df, title, ylab in ((axs[0], "PV", S["pv"], "Rooftop PV, residential", "ICPs with solar / residential ICPs (%)"),
                                      (axs[1], "EV", S["ev"], "Battery-electric vehicles (BEV only)", "BEV per residential ICP (%)")):
        dr = U.drivers_monthly(df.index)
        y = df["share"].to_numpy()
        T = int(np.where(df.index == pd.Timestamp("2023-12-31"))[0][0])
        h = 24
        ctx = {c: dr[c].to_numpy()[:T + 1] for c in dr.columns}
        ms = U.model_set(kind)
        # show the BEST back-tested logistic (lowest mean MAE over h = 12 and 24 in results/stage9b_backtest.csv), not the first
        bt = pd.read_csv(ROOT / "results" / "stage9b_backtest.csv")
        bt = bt[(bt.origin == "mean_of_3_origins") & (bt.series == kind) & bt.model.str.startswith("logistic")]
        lgn = bt.groupby("model").mae_h_pp.mean().idxmin()
        fut = df.index[T + 1:T + 1 + h]
        ax.plot(df.index[T - 36:T + 1 + h], y[T - 36:T + 1 + h] * 100, color="black", lw=2, label="actual (data)")
        for name, col, ls in (("naive", "tab:red", "-"), ("linear36", "tab:green", "--"), (lgn, "tab:blue", ":")):
            f = ms[name](y[:T + 1], h, ctx)
            ax.plot(fut, f * 100, color=col, ls=ls, label=f"forecast: {name}")
            if name == "naive":
                lo, hi = U.band(f, U.internal_errors(ms[name], y[:T + 1], h, ctx), y[T])
                ax.fill_between(fut, lo * 100, hi * 100, color=col, alpha=0.15, label="naive 80 % band")
        ax.axvline(df.index[T], color="grey", lw=0.8)
        ax.set_title(f"{title}: forecast from Dec 2023 (modelled)", fontsize=9)
        ax.set_ylabel(ylab)
        ax.set_xlabel("month (national data, not this feeder)")
        ax.legend(fontsize=7, loc="upper left")
    fig.suptitle("Back-test at one origin: modelled forecast vs actual, 24 months. Best back-tested model for both = naive. "
                 "Logistic = best logistic per series (ceiling assumed, not fitted).\n"
                 "80% bands held the truth in only 40% (PV) / 27% (EV) of cases: the ranges are too narrow; "
                 "PV models were biased low (under-forecast in 8 of 9 cases at 12 months, 9 of 9 at 24 months).", fontsize=9, y=1.04)
    out = OUT_DIR / "cp09b_backtest.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return out


def fig_cp09b_scenarios_vs_hc(_rows=None):
    """Left: P1 PV hosting-capacity curve with the forecast national PV share band (2027, 2028) and average new system size.
    Right: forecast BEV per household band against the Stage 7 EV counts."""
    import pandas as pd
    sc = pd.read_csv(ROOT / "results" / "stage9b_scenarios.csv")
    hc = pd.read_csv(ROOT / "results" / "stage9b_hc_curve.csv")
    fig, axs = plt.subplots(1, 2, figsize=(12.5, 4.9))
    ax = axs[0]
    ax.plot(hc["penetration"] * 100, hc["HC_kW"], "o-", color="tab:orange", label="HC, P1, L2 (simulated)")
    for tg, col in (("2027-12-31", "tab:blue"), ("2028-12-31", "tab:purple")):
        g = sc[sc.target == tg].set_index("scenario")
        ax.axvspan(g.loc["low", "pv_share_of_houses_pct"], g.loc["high", "pv_share_of_houses_pct"], color=col, alpha=0.25,
                   label=f"PV share low-high, {tg[:4]} (forecast)")
        ax.hlines([g.loc["low", "pv_new_system_kw"], g.loc["high", "pv_new_system_kw"]], 0, 100, colors=col, linestyles=":", lw=1)
    ax.set_xlabel("PV penetration of houses (%)\n(forecast = national share: 'what if this feeder looked like NZ')")
    ax.set_ylabel("kW per PV customer")
    ax.set_title("PV: HC curve vs forecast share; dotted = avg new system kW (low/high)", fontsize=9)
    ax.text(50, 20.4, "HC 20 kW = sweep cap (5 % point is 'at least 20')", fontsize=7)
    ax.legend(fontsize=7)
    ax = axs[1]
    for i, (tg, col) in enumerate((("2027-12-31", "tab:blue"), ("2028-12-31", "tab:purple"))):
        g = sc[sc.target == tg].set_index("scenario")
        ax.barh(i, g.loc["high", "bev_per_res_icp_pct"] - g.loc["low", "bev_per_res_icp_pct"],
                left=g.loc["low", "bev_per_res_icp_pct"], color=col, alpha=0.4, height=0.4)
        ax.plot(g.loc["mid", "bev_per_res_icp_pct"], i, "k|", ms=18)
    ax.axvline(100 * 2 / 55, color="tab:red", ls="--", label="Stage 7 busy evening: 2 of 55 (3.6 %)")
    ax.axvline(100 * 6 / 55, color="tab:green", ls="--", label="Stage 7 typical evening: 6 of 55 (10.9 %)")
    ax.set_yticks([0, 1], ["Dec 2027", "Dec 2028"])
    ax.set_xlabel("BEV per residential ICP (%)\n(A30: BEV stock / EA residential ICPs, an upper bound; bar = low to high, tick = mid)")
    ax.set_title("EV: forecast national BEV per residential ICP vs simulated EV counts (assumed ratings)", fontsize=9)
    ax.legend(fontsize=7)
    fig.suptitle("Modelled forecast (national data) against simulated feeder limits (IEEE feeder; NZ-parameterised synthetic load; ratings assumed)", fontsize=9)
    out = OUT_DIR / "cp09b_scenarios_vs_hc.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return out


def main():
    rows = read_rows()
    for fn in (fig_transformer_noload, fig_single_phase, fig_base_case, fig_invcontrol,
               fig_cp04_hc_vs_penetration, fig_cp04_sensitivity, fig_cp05_profiles,
               fig_cp06_hc_nz_vs_feeder, fig_cp06_year_violations,
               fig_cp07_ev_hc_vs_placement, fig_cp07_year_ev_lowvoltage,
               fig_cp08_hc_mitigation, fig_cp08_year_curtailment,
               fig_cp09b_backtest, fig_cp09b_scenarios_vs_hc):
        out = fn(rows)
        if out:
            print(f"Wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
