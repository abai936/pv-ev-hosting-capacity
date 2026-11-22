"""Stage 9b runner: back-test uptake models, make 2027-2028 PV/EV scenarios, link them to the simulated hosting capacity.
NATIONAL data, MODELLED / FORECAST. The feeder part is a 'what if this feeder looked like NZ' reading, not a prediction.
Usage: python scripts/stage9b_uptake.py [--skip-hc]   (--skip-hc reuses results/stage9b_hc_curve.csv)
Writes results/stage9b_backtest.csv, stage9b_scenarios.csv, stage9b_hc_curve.csv, stage9b_summary.md
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hc import uptake as U  # noqa: E402

RES = ROOT / "results"
ORIGINS = ["2021-12-31", "2022-12-31", "2023-12-31"]
PENS = (0.05, 0.10, 0.15, 0.20, 0.30, 0.45, 0.60, 0.80, 1.00)
TARGETS = ("2027-12-31", "2028-12-31")
EVDB_BEV_LIGHT_OCT2026 = 107200      # EVDB web snippet in R11 (third party, NOT data, cross-check only)
LABEL_NAT = "modelled forecast; national data (EA, MoT, Stats NZ, MBIE), not this feeder; synthetic feeder link is 'what if'"
LABEL_HC = "simulated; IEEE feeder; NZ-parameterised synthetic load; ratings assumed"


# ------------------------------------------------------------------ hosting-capacity curve (OpenDSS)
def hc_curve():
    """P1 PV hosting capacity, L2 load (house-diversity seed 2022), source 1.00 pu, assumed ratings, fresh model per
    penetration (cold start, same find_hc as Stage 6). Returns DataFrame pen, n_pv, HC_kW, binding_limit."""
    from hc import hosting as h, l2, profiles as P, yearly as Y
    house_kw, _pv, _t = Y.load_year_inputs()
    l2_kw, _ = l2.l2_kw(house_kw, P.time_index_utc())
    rows = []
    for pen in PENS:
        m = h.Model(1.0, True)
        m.cases["L2"] = dict(zip(m.loads, l2_kw))
        n_pv = h.n_pv_for(pen, len(m.loads))
        m.set_case("L2", h.place_p1(m, n_pv))
        hc, lim, el, _info = h.find_hc(m)
        rows.append({"penetration": pen, "n_pv": n_pv, "n_customers": len(m.loads), "HC_kW": round(hc, 2),
                     "binding_limit": lim, "binding_element": el, "source_pu": 1.0, "load_case": "L2", "placement": "P1",
                     "rating_status": "assumed", "label": LABEL_HC})
        print(f"HC {pen:.2f} n={n_pv} HC={hc:.2f} kW ({lim})", flush=True)
    return pd.DataFrame(rows)


def hc_for_n(ns):
    """Direct find_hc for N single-phase PV houses (P1, L2 seed 2022, source 1.00 pu, assumed ratings, cold-start model per N).
    Used for the scenarios instead of interpolating the 9-point curve (which has a 5 % point and a 10 % point only)."""
    from hc import hosting as h, l2, profiles as P, yearly as Y
    house_kw, _pv, _t = Y.load_year_inputs()
    l2_kw, _ = l2.l2_kw(house_kw, P.time_index_utc())
    rows = []
    for n in ns:
        m = h.Model(1.0, True)
        m.cases["L2"] = dict(zip(m.loads, l2_kw))
        m.set_case("L2", h.place_p1(m, int(n)))
        hc, lim, el, _info = h.find_hc(m)
        rows.append({"n_pv": int(n), "n_customers": len(m.loads), "HC_kW": round(hc, 2), "binding_limit": lim,
                     "binding_element": el, "source_pu": 1.0, "load_case": "L2", "placement": "P1",
                     "rating_status": "assumed", "label": LABEL_HC})
        print(f"HC direct N={n} HC={hc:.2f} kW ({lim})", flush=True)
    return pd.DataFrame(rows)


def hc_display(hc_kw, limit):
    """Text for a HC value. The sweep stops at 20 kW, so 'none (>= 20 kW)' means 'at least 20', not exactly 20."""
    if str(limit).startswith("none"):
        return ">= 20 kW (sweep cap, no limit hit)"
    return f"{hc_kw:.1f} kW"


def ev_counts():
    """Stage 7 P1_direct 7.4 kW EV counts: typical evening (LE) and busy evening (LE_P90), source 1.00 pu, rating scale 1."""
    e = pd.read_csv(RES / "stage7_ev_hc.csv")
    e = e[(e.placement == "P1_direct") & (e.ev_kw == 7.4) & (e.rating_scale == 1.0) & (e.source_pu == 1.0)]
    return {c: (int(g.EV_HC_count.iloc[0]), float(g.pct_of_55_houses.iloc[0])) for c, g in e.groupby("load_case")}


# ------------------------------------------------------------------ forecasts
def final_forecasts(series_df, kind, ctx_df, best, keep):
    """Forecast all kept models from the last observed month to each target month; best model gets its 80 % band."""
    y = series_df["share"].to_numpy()
    last = series_df.index[-1]
    ctx = {c: ctx_df[c].to_numpy() for c in ctx_df.columns}
    models = U.model_set(kind)
    out = {}
    for tg in TARGETS:
        h = U.months_to(last, tg)
        pts = {m: models[m](y, h, ctx)[-1] for m in keep}
        fn = models[best]
        pt = fn(y, h, ctx)
        lo, hi = U.band(pt, U.internal_errors(fn, y, h, ctx), y[-1])
        out[tg] = {"h": h, "points": pts, "mid": pt[-1], "band": (lo[-1], hi[-1])}
    return out


def main():
    skip_hc = "--skip-hc" in sys.argv
    t0 = time.perf_counter()
    S = U.build_series()
    pv, ev = S["pv"], S["ev"]
    drv_pv, drv_ev = U.drivers_monthly(pv.index), U.drivers_monthly(ev.index)
    frames = {"PV": (pv, drv_pv), "EV": (ev, drv_ev)}

    # ---- back-test
    bts, best, rank = [], {}, {}
    for kind, (df, dr) in frames.items():
        bts.append(U.backtest(df, kind, dr, ORIGINS))
    bt = pd.concat(bts, ignore_index=True)
    summ = U.summarise_backtest(bt)
    for kind in frames:
        rank[kind] = U.best_model(summ, kind)
        best[kind] = rank[kind].index[0]
    s_out = summ.copy()
    s_out["origin"] = "mean_of_3_origins"
    s_out["label"] = "modelled; error = forecast - actual in percentage points of share; coverage = share of months with truth inside the 80% band"
    b_out = bt.copy()
    b_out["label"] = s_out["label"].iloc[0]
    pd.concat([b_out, s_out], ignore_index=True).to_csv(RES / "stage9b_backtest.csv", index=False, float_format="%.4f")

    # ---- scenarios: mid = best back-tested model; spread = models within 2x of best MAE and usable now
    scen_rows, raw = [], {}
    for kind, (df, dr) in frames.items():
        keep = [m for m, v in rank[kind].items() if v <= 2.0 * rank[kind].iloc[0]]
        ff = final_forecasts(df, kind, dr, best[kind], keep)
        usable = {tg: {m: v for m, v in d["points"].items() if not np.isnan(v)} for tg, d in ff.items()}
        raw[kind] = {"ff": ff, "keep": keep}
        for tg, d in ff.items():
            # floor at the last observed share: BEV stock never fell in the 122 months, so no scenario may sit below today
            lo, mid, hi = U.scenario_from_models(d["points"], d["band"], best[kind], keep, floor=df["share"].iloc[-1])
            raw[kind][tg] = (lo, mid, hi)
            raw[kind][tg + "_models"] = usable[tg]

    # PV system size (kW), volume-weighted mean of new systems over 12 months; flat / damped Holt / linear 36 m
    size_series = U.rolling_size_series(pv)
    size_now = U.avg_new_system_kw(pv)
    size = {}
    for tg in TARGETS:
        h = U.months_to(pv.index[-1], tg)
        v = sorted([float(size_series.iloc[-1]), float(U.f_holt(size_series.to_numpy(), h)[-1]),
                    float(U.f_linear(size_series.to_numpy(), h)[-1])])
        size[tg] = tuple(v)                       # low, mid, high = min / median / max of the three simple methods

    # ---- hosting capacity link
    if skip_hc and (RES / "stage9b_hc_curve.csv").exists():
        hc = pd.read_csv(RES / "stage9b_hc_curve.csv")
    else:
        hc = hc_curve()
        hc.to_csv(RES / "stage9b_hc_curve.csv", index=False)
    pg, hk = hc["penetration"].to_numpy(), hc["HC_kW"].to_numpy()
    n_need = sorted({U.n_houses(raw["PV"][tg][i]) for tg in TARGETS for i in range(3)})
    p_n = RES / "stage9b_hc_n_direct.csv"
    hcn = pd.read_csv(p_n) if (skip_hc and p_n.exists() and set(n_need) <= set(pd.read_csv(p_n).n_pv)) else hc_for_n(n_need)
    hcn.to_csv(p_n, index=False)
    evc = ev_counts()
    typ_pct, busy_pct = evc["LE"][1], evc["LE_P90"][1]

    ICP_PP = S["icp_per_person"]
    for tg in TARGETS:
        for i, sc in enumerate(("low", "mid", "high")):
            pv_sh, ev_sh = raw["PV"][tg][i], raw["EV"][tg][i]
            sz = size[tg][i]
            hc_at = U.read_off(pg, hk, pv_sh)
            n_pv = U.n_houses(pv_sh)
            hd = hcn.set_index("n_pv").loc[n_pv]      # exact simulated HC for N houses, not an interpolation
            hc_at = float(hd["HC_kW"])
            scen_rows.append({
                "target": tg, "scenario": sc,
                "pv_share_of_houses_pct": pv_sh * 100, "pv_new_system_kw": sz,
                "feeder_pv_houses_of_55": n_pv, "feeder_hc_kw_at_that_penetration": hc_at,
                "feeder_hc_binding_limit": hd["binding_limit"], "feeder_hc_display": hc_display(hc_at, hd["binding_limit"]),
                "new_system_minus_hc_kw": sz - hc_at,
                "bev_per_res_icp_pct": ev_sh * 100, "ev_per_1000_people": ev_sh * 1000.0 * ICP_PP,
                "feeder_ev_houses_of_55": U.n_houses(ev_sh),
                "ev_pct_vs_typical_evening_limit": ev_sh * 100 / typ_pct, "ev_pct_vs_busy_evening_limit": ev_sh * 100 / busy_pct,
                "label": LABEL_NAT})
    sc = pd.DataFrame(scen_rows)
    sc.to_csv(RES / "stage9b_scenarios.csv", index=False, float_format="%.4f")

    # ---- cross-check: EV models fitted to Feb 2026, run to Oct 2026, vs EVDB snippet (light BEV, third party)
    evd = raw["EV"]
    models = U.model_set("EV")
    y_ev = ev["share"].to_numpy()
    ctx_ev = {c: drv_ev[c].to_numpy() for c in drv_ev.columns}
    h8 = U.months_to(ev.index[-1], "2026-10-31")
    icp_oct = float(pv.res_icp.loc["2026-10-31"])    # residential ICPs at Oct 2026: EA data, no persons-per-household guess
    light_ratio = U.bev_light_ratio_feb2026()     # light passenger+commercial / all-class BEV at Feb 2026, MoT file
    xc = {m: models[m](y_ev, h8, ctx_ev)[-1] * icp_oct * light_ratio for m in ("naive", "linear36", "holt_damped", best["EV"])}

    write_summary(S, bt, summ, rank, best, raw, size, size_now, sc, hc, hcn, evc, xc, h8, time.perf_counter() - t0)
    print(f"done in {time.perf_counter() - t0:.0f} s")


# ------------------------------------------------------------------ summary text
def pct(x):
    return f"{x * 100:.1f} %"


def write_summary(S, bt, summ, rank, best, raw, size, size_now, sc, hc, hcn, evc, xc, h8, secs):
    pv, ev = S["pv"], S["ev"]

    def m(kind, model, h):
        r = summ[(summ.series == kind) & (summ.model == model) & (summ.h == h)].iloc[0]
        return r

    def line_cmp(kind):
        lg = min((n for n in rank[kind].index if n.startswith("logistic")), key=lambda n: rank[kind][n])
        dr = min((n for n in ("drv_cpi", "drv_all") if n in rank[kind].index), key=lambda n: rank[kind][n])
        a = lambda n: f"{rank[kind][n]:.2f}"
        return lg, dr, (f"{kind}: mean MAE over h=12 and 24 (pp of share): naive {a('naive')}, linear36 {a('linear36')}, "
                        f"Holt {a('holt_damped')}, best logistic ({lg}) {a(lg)}, momentum-only regression {a('drv_mom')}, "
                        f"driver regression ({dr}) {a(dr)}")

    lgp, drp, cmp_pv = line_cmp("PV")
    lge, dre, cmp_ev = line_cmp("EV")
    nl_beats = {k: rank[k][lg] < rank[k]["linear36"] for k, lg in (("PV", lgp), ("EV", lge))}
    dr_beats = {k: rank[k][d] < min(rank[k]["linear36"], rank[k]["naive"]) for k, d in (("PV", drp), ("EV", dre))}
    drv_vs_mom = {k: rank[k][d] < rank[k]["drv_mom"] for k, d in (("PV", drp), ("EV", dre))}
    yn = lambda b: "yes" if b else "no"

    g = lambda kind, col: sc[col].round(2).tolist()
    t27 = sc[sc.target == TARGETS[0]].set_index("scenario")
    t28 = sc[sc.target == TARGETS[1]].set_index("scenario")
    cov = summ.groupby(["series"]).coverage80.mean()

    def trip(t, col, f="{:.1f}"):
        return "/".join(f.format(t.loc[s, col]) for s in ("low", "mid", "high"))

    # penetration at which the average new system first exceeds the HC curve, today's and mid-2028 size
    pg, hk = hc.penetration.to_numpy(), hc.HC_kW.to_numpy()
    fe_now = U.first_exceeded(pg, hk, size_now)
    fe_mid28 = U.first_exceeded(pg, hk, size[TARGETS[1]][1])
    fe_txt = lambda x: "already at the first curve point (5 %)" if x is not None and x <= pg[0] + 1e-9 else \
        ("not within the curve" if x is None else f"about {x * 100:.0f} %")
    hc_lines = "; ".join(f"{p * 100:.0f} % -> {k:.2f} kW" for p, k in zip(pg, hk))
    typ_n, typ_pct = evc["LE"]
    busy_n, busy_pct = evc["LE_P90"]

    # --- facts used in the headline, all computed from the files
    def lg_names(k):
        return [n for n in rank[k].index if n.startswith("logistic")]
    naive_beats_lg = {k: all(rank[k]["naive"] < rank[k][n] for n in lg_names(k)) for k in ("PV", "EV")}
    assert all(naive_beats_lg.values()), "headline 2 wording assumes naive beat every logistic"
    nv = {k: f"{rank[k]['naive']:.2f}" for k in ("PV", "EV")}
    pvs = summ[summ.series == "PV"]
    n_pv_models = pvs[pvs.h == 12].shape[0]
    under12 = int((pvs[pvs.h == 12].me_h_pp < 0).sum())
    under24 = int((pvs[pvs.h == 24].me_h_pp < 0).sum())
    light_ratio = U.bev_light_ratio_feb2026()
    icp_oct = float(pv.res_icp.loc["2026-10-31"])
    icp_oct_txt = f"{icp_oct:,.0f}"
    evdb_pct = EVDB_BEV_LIGHT_OCT2026 / light_ratio / icp_oct * 100        # snippet-implied BEV per residential ICP, Oct 2026
    mid27 = t27.loc["mid", "bev_per_res_icp_pct"]
    below_txt = "below" if mid27 < evdb_pct else "NOT below"
    hcd = lambda t: "/".join(t.loc[s_, "feeder_hc_display"].replace(" (sweep cap, no limit hit)", "") for s_ in ("low", "mid", "high"))
    ncp = lambda t: "/".join(str(int(t.loc[s_, "feeder_pv_houses_of_55"])) for s_ in ("low", "mid", "high"))

    L = ["# Stage 9b summary: 2027-2028 PV and EV uptake scenarios and the hosting-capacity reading", "",
         "## HEADLINE",
         f"1. All numbers are MODELLED forecasts from national NZ data (EA residential solar, MoT battery-electric fleet, Stats NZ, MBIE); "
         f"they are not measured, not about this feeder, and not causal. PV: {len(pv)} monthly points; EV (BEV only, PHEV excluded): {len(ev)} monthly points.",
         f"2. Did the non-linear or driver model beat a straight line? Logistic (assumed ceilings) beats the 36-month linear fit: PV {yn(nl_beats['PV'])}, EV {yn(nl_beats['EV'])}, "
         f"but the naive forecast (PV {nv['PV']}, EV {nv['EV']}) beat every logistic. "
         f"Driver regression beats both naive and linear: PV {yn(dr_beats['PV'])}, EV {yn(dr_beats['EV'])}; driver beats momentum-only regression: PV {yn(drv_vs_mom['PV'])}, EV {yn(drv_vs_mom['EV'])}. "
         f"{cmp_pv}. {cmp_ev}. Best model: PV {best['PV']}, EV {best['EV']}.",
         f"3. PV share of residential ICPs (low/mid/high), Dec 2027: {trip(t27, 'pv_share_of_houses_pct')} %; Dec 2028: {trip(t28, 'pv_share_of_houses_pct')} % (now {pv.share.iloc[-1] * 100:.1f} %, Oct 2026). "
         f"Average new system (kW): Dec 2027 {trip(t27, 'pv_new_system_kw')}; Dec 2028 {trip(t28, 'pv_new_system_kw')} (last 12 months: {size_now:.2f} kW, EA).",
         f"4. BEV per residential ICP (A30: BEV stock / the EA monthly residential ICP count; an UPPER BOUND on the share of houses with an EV) low/mid/high, Dec 2027: {trip(t27, 'bev_per_res_icp_pct')} %; Dec 2028: {trip(t28, 'bev_per_res_icp_pct')} % "
         f"(now {ev.share.iloc[-1] * 100:.1f} %, Feb 2026). Every scenario is floored at the last observed share, because BEV stock never fell in any of the {len(ev)} months. "
         f"The 2027 mid ({mid27:.1f} %) is {below_txt} the level the Oct 2026 EVDB snippet implies (about {evdb_pct:.2f} % BEV per residential ICP, using the file's light ratio {light_ratio:.3f}; snippet, third-party, NOT data); "
         f"MoT Mar-Oct 2026 data need a manual download. EV horizons are beyond the 24 months that were back-tested, and the 2026 fuel-price turn is not in the history.",
         f"5. Hosting-capacity reading (P1, L2, source 1.00 pu, ratings assumed): the 9-point curve starts at 'at least {hk[0]:.0f} kW' at 5 % (that point is the 20 kW sweep cap, binding 'none (>= 20 kW)'), is {hk[1]:.1f} kW at 10 % and falls to {hk[-1]:.1f} kW at 100 %. "
         f"The scenarios use N = ceil(share x 55) PV houses simulated directly (N = {ncp(t27)} in 2027, {ncp(t28)} in 2028, low/mid/high), giving HC {hcd(t27)} (Dec 2027) and {hcd(t28)} (Dec 2028), against average new systems of "
         f"{trip(t27, 'pv_new_system_kw')} and {trip(t28, 'pv_new_system_kw')} kW. A system of today's size ({size_now:.1f} kW) first exceeds the HC at {fe_txt(fe_now)} penetration, several times the forecast national share. "
         f"The average new system is {'ABOVE' if (sc.new_system_minus_hc_kw > 0).any() else 'below'} the HC in every scenario. Caveat: the HC is kW per single-phase PV customer (one phase), while the EA size is a whole-house system, which may be split over three phases; "
         f"the size-versus-HC comparison is rough, and a value shown '>= 20 kW' means the sweep stopped at its 20 kW cap.",
         f"6. EV reading: Stage 7 gives {typ_n} of 55 EVs ({typ_pct:.1f} %) on a typical evening and {busy_n} of 55 ({busy_pct:.1f} %) on a busy evening (7.4 kW chargers, assumed ratings). "
         f"The forecast BEV per residential ICP, {trip(t27, 'bev_per_res_icp_pct')} % (2027) and {trip(t28, 'bev_per_res_icp_pct')} % (2028), is an UPPER BOUND on the share of houses with an EV (some homes have two BEVs, some BEVs are fleet), and it is compared here with the Stage 7 'EVs of 55' counts: it sits "
         f"{'above' if t27.loc['low', 'bev_per_res_icp_pct'] > busy_pct else 'not clearly above'} the busy-evening count from the low 2027 case and "
         f"{'below the typical-evening count even in the high 2028 case' if t28.loc['high', 'bev_per_res_icp_pct'] < typ_pct else 'at or above the typical-evening count only in the high 2028 case (mid stays between the two counts)'}. "
         "A feeder is not the national average: this is a 'what if this feeder looked like NZ' reading, with every BEV assumed to charge at 7.4 kW at the evening peak (an upper bound).",
         f"7. Back-test warning: 80 % bands held the truth in only {cov['PV'] * 100:.0f} % (PV) / {cov['EV'] * 100:.0f} % (EV) of cases: the ranges are too narrow; PV models were biased low "
         f"(under-forecast in {under12} of {n_pv_models} models at 12 months, {under24} of {n_pv_models} at 24 months; mean over 3 origins).",
         "", "## Method and data (all inputs from saved files in data/raw/uptake, sources in research/R11-uptake-data.md)",
         f"- PV: EA 'Installed distributed generation trends', residential solar, {pv.index[0].date()} to {pv.index[-1].date()}. Share = ICPs with solar / residential ICPs; the EA file carries the uptake rate, so the denominator is in the file (about {pv.res_icp.iloc[-1] / 1e6:.2f} million at Oct 2026). CC BY 4.0.",
         f"- EV: MoT fleet via Figure.NZ, Battery Electric, all vehicle classes, stock {ev.index[0].date()} to {ev.index[-1].date()}. BEV only; PHEV and hybrids are excluded. Per 1,000 people = BEV / ERP x 1000 (ERP is annual at 30 June, straight-line interpolated by month; after Jun 2025 extended with the last year's growth, so the 2025-26 population is an EXTRAPOLATION). Now: {ev.bev_per_1000_people.iloc[-1]:.1f} BEV per 1,000 people.",
         "- A30 (assumption): BEV per residential ICP = BEV stock / the monthly residential ICP count of the same month from the EA file (data; the EA file spans Aug 2013 to Oct 2026, so it covers every BEV month Jan 2016 to Feb 2026 and no month is filled). No persons-per-household figure is used any more. It is an UPPER BOUND on the share of houses with an EV: some homes have two BEVs and some BEVs are fleet or business vehicles, while ICPs include holiday homes and so on (BELIEVED, not checked). The earlier +/-15 % persons-per-household sensitivity is dropped because it no longer drives the number. 'Per 1,000 people' = share x ICPs per person (EA ICPs / ERP at Feb 2026, ERP extrapolated).",
         "- Ceilings of the logistic curve are ASSUMED scenario parameters (PV 15/30/60 % of houses, EV 20/40/70 % of residential ICPs), never fitted; no source was found for them.",
         f"- Drivers: CPI annual change (Stats NZ, quarterly to 2026 Q2), population growth (ERP to Jun 2025), residential electricity price (MBIE, quarterly to 2025 Q1; STALE). Release lags (CPI 1 month, price 6, population 3) are ASSUMED so no forecast uses unreleased data. Price growth is blank after 2026-03 and population growth only after 2026-09. At the EV origin (Feb 2026) both exist, so the full driver model (drv_all) was usable for the EV forecast; it was not kept because its error was more than twice the best ({rank['EV']['drv_all']:.2f} vs {rank['EV'][best['EV']]:.2f} pp). At the PV origin (Oct 2026) both are blank, so drv_all is unusable for PV (and it was also more than twice the best, {rank['PV']['drv_all']:.2f} vs {rank['PV'][best['PV']]:.2f} pp). Unusable inputs: OCR (blocked file), GDP (saved but not used in the model), household income (no file).",
         "- Models (monthly): naive (last value + last 12-month change), linear (36 months), damped Holt (grid-fitted), logistic with an assumed ceiling (logit-line on 36 months), direct ridge regression of the h-month change on 12-month momentum (drv_mom) and on momentum + CPI (drv_cpi) or + price + population growth (drv_all), ridge strength by forward-chaining cross-validation. Bands: 80 % from bootstrapped relative errors of each model's own pseudo-forecasts inside its training window.",
         f"- Back-test: rolling origins Dec 2021, Dec 2022, Dec 2023, horizons 12 and 24 months, PV truth runs to {pv.index[-1].date()} and EV truth to {ev.index[-1].date()}, but scoring stops at Dec 2025 (Dec 2023 + 24 months): 2026 is never scored. Only 3 origins, heavily overlapping, so differences of a few tenths of a point are not statistically meaningful. The three origins also share one policy regime (EV feebate end in 2024, flat 2024-25).",
         "", "## Back-test result (mean over 3 origins; error = forecast - actual, percentage points of share)", ""]
    t = summ.copy()
    t = t.sort_values(["series", "h", "mae_h_pp"])
    L.append("| series | h | model | MAE at h (pp) | mean error at h (pp) | MAE over months 1..h (pp) | 80 % coverage |")
    L.append("|---|---|---|---|---|---|---|")
    for r in t.itertuples():
        L.append(f"| {r.series} | {r.h} | {r.model} | {r.mae_h_pp:.2f} | {r.me_h_pp:+.2f} | {r.mae_steps_pp:.2f} | {r.coverage80:.2f} |")
    L += ["", f"Mean 80 % coverage over all models: PV {cov['PV']:.2f}, EV {cov['EV']:.2f}. The nominal level is 0.80, so the bands are too narrow: the 2024-25 EV slowdown and the 2023-26 PV acceleration are bigger than the errors seen inside each training window. Treat the low/high as a lower bound on the real uncertainty.",
          "", "## Scenarios (modelled forecast; low = lowest of the best model's 80 % band and the kept models, mid = best model, high = highest)", "",
          "| target | scenario | PV share of houses (%) | avg new PV system (kW) | BEV per residential ICP (%) | BEV per 1,000 people | PV houses of 55 | EV houses of 55 | HC at N PV houses (kW, direct) |", "|---|---|---|---|---|---|---|---|---|"]
    for r in sc.itertuples():
        L.append(f"| {r.target} | {r.scenario} | {r.pv_share_of_houses_pct:.2f} | {r.pv_new_system_kw:.2f} | {r.bev_per_res_icp_pct:.2f} | {r.ev_per_1000_people:.1f} | {r.feeder_pv_houses_of_55} | {r.feeder_ev_houses_of_55} | {r.feeder_hc_display} |")
    L += ["", f"Kept models (back-test MAE within 2x of best and usable now): PV {', '.join(raw['PV']['keep'])}; EV {', '.join(raw['EV']['keep'])}.",
          f"PV forecast horizons from Oct 2026: {raw['PV']['ff'][TARGETS[0]]['h']} and {raw['PV']['ff'][TARGETS[1]]['h']} months; EV from Feb 2026: {raw['EV']['ff'][TARGETS[0]]['h']} and {raw['EV']['ff'][TARGETS[1]]['h']} months (the last is beyond the tested 24).",
          "System size: low / mid / high are the minimum / median / maximum of three simple methods (rolling 12-month volume-weighted average held flat, damped Holt, 36-month linear) on EA 'Avg. capacity - new installations (kW)' weighted by 'ICP count - new installations'.",
          "", "## Hosting-capacity link (simulated; IEEE feeder; NZ-parameterised synthetic load; ratings assumed)", "",
          "Method: national share is used as the feeder penetration (assumes this 55-house feeder equals the national average, which it does not); N = ceil(share x 55), and the HC for that N is simulated directly (find_hc, results/stage9b_hc_n_direct.csv), not interpolated. HC curve = P1 placement, L2 load (seed 2022), source 1.00 pu, fresh model per point as in Stage 6. HC is per single-phase PV customer and the EA system size is a whole-house system, so the comparison is a rough 'size versus per-phase limit' reading.",
          f"HC curve: {hc_lines} (5 % is 'at least 20', the sweep cap).",
          "Direct N values: " + "; ".join(f"N={int(r.n_pv)} -> {hc_display(r.HC_kW, r.binding_limit)} ({r.binding_limit})" for r in hcn.itertuples()) + ". The HC need not fall smoothly with N because P1 puts PV on a different set of houses for each N (believed), so N=4 can sit below the 10 % point (N=6).",
          f"Penetration at which the HC first falls below the average new system size: today's {size_now:.2f} kW -> {fe_txt(fe_now)}; Dec 2028 mid size {size[TARGETS[1]][1]:.2f} kW -> {fe_txt(fe_mid28)}.",
          f"EV: Stage 7 P1 direct counts at 7.4 kW and source 1.00 pu: typical evening {typ_n} of 55 ({typ_pct:.1f} %), busy evening {busy_n} of 55 ({busy_pct:.1f} %) (assumed ratings).",
          "", "## EV cross-check against a third-party snippet (not data)",
          f"R11 records an EVDB web snippet: about 107,200 fully electric light vehicles at 31 Oct 2026. Models fitted to MoT data to Feb 2026 and run {h8} months (light share of BEV stock at Feb 2026 = {U.bev_light_ratio_feb2026():.3f} from the MoT file, assumed constant; residential ICPs at Oct 2026 from the EA file, {icp_oct_txt}): "
          + "; ".join(f"{k} {v:,.0f}" for k, v in xc.items()) + ". Gap to 107,200: " + "; ".join(f"{k} {(v / EVDB_BEV_LIGHT_OCT2026 - 1) * 100:+.0f} %" for k, v in xc.items())
          + ". A negative gap means the models miss the 2026 rebound (no fuel-price shock in the history). Labelled snippet cross-check only; the snippet is light vehicles, the models are scaled to light with a constant ratio.",
          "", "## Not done / limits",
          "- No fit to registrations or new-BEV share (flow data not in saved files). EV data stop in Feb 2026; MoT Mar-Oct 2026 need a manual download.",
          "- Drivers are tested for forecast skill only; a driver that helps in the back-test is not a cause. Population growth is almost constant, so it can carry little signal.",
          "- No ceiling source found; the ceilings only set the shape of the S-curve.",
          f"- Runtime {secs:.0f} s. Label: {LABEL_NAT}."]
    (RES / "stage9b_summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
