"""Stage 9b: NZ rooftop-PV and EV uptake scenarios for 2027-2028 (national data, NOT this feeder).

Everything here is MODELLED / FORECAST from saved public files in data/raw/uptake (sources in research/R11-uptake-data.md).
Nothing is measured on the feeder, no causal claim is made: drivers are only tested for forecast skill.

Units: shares are fractions 0..1 in the code (reported as % in the outputs). Months are month-end timestamps.
Plain numpy/pandas only (scipy and statsmodels are not installed in the project .venv).
"""
import csv
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
UP = ROOT / "data" / "raw" / "uptake"
F_PV = UP / "EA_DG_solar_all_Res_NZ_monthly.csv"
F_EV = UP / "FigureNZ_MoT_EV_hybrid_fleet_by_engine_monthly_Feb2017-Feb2026.csv"
F_POP = UP / "FigureNZ_StatsNZ_ERP_by_age_sex_annual_Jun_1991-2025.csv"
F_CPI = UP / "FigureNZ_StatsNZ_CPI_all_groups_pct_change_qtrly_to_Jun2026.csv"
F_PRICE = UP / "FigureNZ_MBIE_residential_sales_based_electricity_cost_quarterly_2013Q2-2025Q1.xlsx"

CEILINGS = {"PV": (0.15, 0.30, 0.60), "EV": (0.20, 0.40, 0.70)}   # ASSUMED scenario parameters, never fitted
DRIVER_AVAIL_LAG_MONTHS = {"cpi": 1, "price": 6, "pop": 3}   # ASSUMED publication lags, so no look-ahead


def month_end(ts):
    return pd.Timestamp(ts) + pd.offsets.MonthEnd(0)


# ---------------------------------------------------------------- loaders
def load_pv():
    """EA residential solar, monthly, Sep 2013 to Oct 2026 (159 rows). Columns: icp, rate_pct, avg_new_kw, n_new, cap_mw.
    The file carries the uptake rate = ICPs with solar / all residential ICPs, so the denominator is in the file
    (denominator = icp / (rate/100))."""
    raw = F_PV.read_text(encoding="utf-8-sig").splitlines()
    start = next(i for i, ln in enumerate(raw) if ln.startswith("Month end,"))
    df = pd.read_csv(F_PV, skiprows=start, encoding="utf-8-sig")
    df.columns = ["date", "reg", "name", "cap", "fuel", "icp", "rate_pct", "mw", "avg_kw", "n_new", "avg_new_kw"]
    df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y")
    out = df.set_index("date")[["icp", "rate_pct", "mw", "n_new", "avg_new_kw"]].astype(float)
    out["res_icp"] = out["icp"] / (out["rate_pct"] / 100.0)
    out["share"] = out["rate_pct"] / 100.0
    out.index = out.index.map(month_end)
    return out


def load_bev():
    """MoT fleet via Figure.NZ: Battery Electric, all vehicle classes, monthly stock Jan 2016 to Feb 2026 (122 rows).
    BEV only. PHEV (plug-in hybrid) and hybrids are EXCLUDED from every number here."""
    df = pd.read_csv(F_EV, encoding="utf-8-sig")
    b = df[(df["Variable view"] == "Battery Electric") & (df["Vehicle Class"] == "Total")].copy()
    b["date"] = pd.to_datetime(b["Month Year"], format="%B %Y").map(month_end)
    return b.set_index("date")["Number of vehicles"].astype(float).rename("bev").sort_index()


def bev_light_ratio_feb2026():
    """Light (passenger + commercial) BEV / all-class BEV at Feb 2026 from the MoT file; used only for the EVDB cross-check."""
    df = pd.read_csv(F_EV, encoding="utf-8-sig")
    d = df[(df["Variable view"] == "Battery Electric") & (df["Month Year"] == "February 2026")].set_index("Vehicle Class")["Number of vehicles"]
    return float((d["Light passenger"] + d["Light commercial"]) / d["Total"])


def load_pop_annual():
    """Estimated resident population, total all ages, at 30 June, 1991 to 2025 (35 values). Stats NZ via Figure.NZ."""
    rows = list(csv.reader(F_POP.open(encoding="utf-8-sig")))
    col = [i for i, c in enumerate(rows[3]) if c == "Total All Ages"][-1]     # third block = both sexes
    d = {int(r[0]): float(r[col]) for r in rows if r and r[0].isdigit() and len(r) > col and r[col]}
    return pd.Series(d, name="erp").sort_index()


def load_cpi_quarterly():
    """CPI all groups, % change on same quarter a year earlier. Quarter label YYYYQn. '..' = not available."""
    out = {}
    for r in csv.reader(F_CPI.open(encoding="utf-8-sig")):
        if r and len(r[0]) == 6 and r[0][4] == "Q" and r[0][:4].isdigit():
            try:
                v = float(r[1])
            except ValueError:
                continue
            out[pd.Period(r[0], "Q")] = v
    return pd.Series(out, name="cpi_yoy_pct").sort_index()


def load_price_quarterly():
    """MBIE sales-based residential cost, c/kWh incl GST, quarter ended Jun 2013 to Mar 2025 (48 values). STALE after 2025 Q1."""
    d = pd.read_excel(F_PRICE, sheet_name="Quarterly Residential Elec Cost", header=None)
    body = d.iloc[14:, [0, 3]].copy()
    body[0] = pd.to_datetime(body[0], errors="coerce")
    body = body.dropna()
    body.columns = ["q", "c_kwh"]
    body["q"] = body["q"].map(month_end)
    return body.set_index("q")["c_kwh"].astype(float).rename("price_c_kwh")


# ---------------------------------------------------------------- monthly drivers and shares
def monthly_index(start, end):
    return pd.date_range(month_end(start), month_end(end), freq="ME")


def pop_monthly(idx, pop_annual=None):
    """Monthly population: straight line between 30 June points; after the last June (2025) the log growth of the
    last year is carried forward (EXTRAPOLATED, not data; the Jun 2026 provisional figure in R11 is a web snippet,
    not used)."""
    pa = load_pop_annual() if pop_annual is None else pop_annual
    t_pts = pd.to_datetime([f"{y}-06-30" for y in pa.index])
    t = idx.values.astype("datetime64[D]").astype(float)
    tp = t_pts.values.astype("datetime64[D]").astype(float)
    v = np.interp(t, tp, pa.values)
    g = math.log(pa.iloc[-1] / pa.iloc[-2]) / 365.25                  # log growth per day, last year
    after = t > tp[-1]
    v[after] = pa.iloc[-1] * np.exp(g * (t[after] - tp[-1]))
    extrapolated = pd.Series(after, index=idx)
    return pd.Series(v, index=idx, name="pop"), extrapolated


def _step_driver(values_by_end, idx, lag_months):
    """Carry a low-frequency series forward month by month, visible only lag_months after its period ends."""
    avail = pd.Series(values_by_end.values, index=[month_end(i) + pd.offsets.MonthEnd(lag_months) for i in values_by_end.index])
    s = avail.reindex(avail.index.union(idx)).sort_index().ffill()
    return s.reindex(idx)


def drivers_monthly(idx):
    """Monthly driver frame on idx: cpi_yoy (%), price_yoy (%), pop_g (% per year). NaN where the data do not cover.
    Lags in DRIVER_AVAIL_LAG_MONTHS are ASSUMED publication delays, so a forecast never uses a number not yet released."""
    cq = load_cpi_quarterly()
    cpi = _step_driver(pd.Series(cq.values, index=[p.end_time.normalize() for p in cq.index]), idx, DRIVER_AVAIL_LAG_MONTHS["cpi"])
    pq = load_price_quarterly()
    yoy = (pq / pq.shift(4) - 1.0) * 100.0
    price = _step_driver(yoy.dropna(), idx, DRIVER_AVAIL_LAG_MONTHS["price"])
    # price series ends at 2025 Q1: carrying it forward would fake data, so blank it 6 months after its last release
    last_ok = month_end(pq.index[-1]) + pd.offsets.MonthEnd(DRIVER_AVAIL_LAG_MONTHS["price"] + 6)
    price[price.index > last_ok] = np.nan
    pa = load_pop_annual()
    g = (pa / pa.shift(1) - 1.0).dropna() * 100.0
    pop = _step_driver(pd.Series(g.values, index=[pd.Timestamp(f"{y}-06-30") for y in g.index]), idx, DRIVER_AVAIL_LAG_MONTHS["pop"])
    last_pop = pd.Timestamp("2025-06-30") + pd.offsets.MonthEnd(12 + DRIVER_AVAIL_LAG_MONTHS["pop"])   # no ERP after Jun 2025
    pop[pop.index > last_pop] = np.nan
    return pd.DataFrame({"cpi_yoy": cpi, "price_yoy": price, "pop_g": pop})


def build_series():
    """Return dict with monthly PV and EV frames (share columns in 0..1) plus the A30 numbers."""
    pv = load_pv()
    bev = load_bev()
    pop_pv, _ = pop_monthly(pv.index)
    ev_idx = bev.index
    pop_ev, extrap = pop_monthly(ev_idx)
    ev = pd.DataFrame({"bev": bev, "pop": pop_ev, "pop_extrapolated": extrap})
    ev["bev_per_1000_people"] = ev["bev"] / ev["pop"] * 1000.0
    # A30: denominator = residential ICPs of the SAME month from the EA file (data). The EA file covers Aug 2013 to Oct 2026,
    # so it spans the whole BEV file (Jan 2016 to Feb 2026) and no month needs filling.
    ev["res_icp"] = pv["res_icp"].reindex(ev.index)
    assert not ev["res_icp"].isna().any()
    ev["share"] = ev["bev"] / ev["res_icp"]       # BEV per residential ICP: an UPPER BOUND on the share of houses with an EV
    # residential ICPs per person at the last BEV month, only to express a share as 'per 1,000 people' in the outputs
    icp_per_person = float(ev["res_icp"].iloc[-1] / ev["pop"].iloc[-1])
    return {"pv": pv, "ev": ev, "icp_per_person": icp_per_person, "pop_pv": pop_pv}


# ---------------------------------------------------------------- forecast models (monthly steps)
# Every model: f(y, h, ctx) -> np.array of h forecasts for months T+1..T+h, using only y[0..T] and ctx[..T].
def f_naive(y, h, ctx=None):
    """Last value + last 12-month change, spread evenly per month (a straight line with the last year's slope)."""
    slope = (y[-1] - y[-13]) / 12.0
    return y[-1] + slope * np.arange(1, h + 1)


def f_linear(y, h, ctx=None, window=36):
    """Straight-line least squares on the last `window` months."""
    yy = y[-window:]
    t = np.arange(len(yy))
    b, a = np.polyfit(t, yy, 1)
    return np.maximum(a + b * (len(yy) - 1 + np.arange(1, h + 1)), 0.0)


def holt_filter(y, alpha, beta, phi):
    """Damped-trend Holt recursion; returns level, trend and one-step SSE."""
    lvl, tr = y[0], y[1] - y[0]
    sse = 0.0
    for v in y[1:]:
        pred = lvl + phi * tr
        sse += (v - pred) ** 2
        new = alpha * v + (1 - alpha) * pred
        tr = beta * (new - lvl) + (1 - beta) * phi * tr
        lvl = new
    return lvl, tr, sse


def f_holt(y, h, ctx=None, window=60):
    """Damped-trend Holt, parameters picked on a small grid by one-step SSE over the last `window` months."""
    yy = y[-window:]
    best = None
    for a in (0.2, 0.4, 0.6, 0.8, 1.0):
        for b in (0.05, 0.1, 0.2, 0.4):
            for p in (0.8, 0.9, 0.95, 0.98):
                lvl, tr, sse = holt_filter(yy, a, b, p)
                if best is None or sse < best[0]:
                    best = (sse, lvl, tr, p)
    _, lvl, tr, p = best
    damp = np.cumsum(p ** np.arange(1, h + 1))
    return np.maximum(lvl + damp * tr, 0.0)


def f_logistic(y, h, ctx=None, ceiling=0.3, window=36):
    """S-curve y = K / (1 + exp(-(a + b t))). K (ceiling) is a SCENARIO PARAMETER, never fitted. a,b by least squares on
    ln(y / (K - y)) over the last `window` months (the straight line in logit space)."""
    yy = np.clip(y[-window:], 1e-9, ceiling * 0.999)
    t = np.arange(len(yy))
    b, a = np.polyfit(t, np.log(yy / (ceiling - yy)), 1)
    z = a + b * (len(yy) - 1 + np.arange(1, h + 1))
    return ceiling / (1.0 + np.exp(-z))


def _features(y, ctx, t_idx, names):
    """Feature rows at month indices t_idx: 12-month momentum of the share (+ requested drivers)."""
    cols = []
    for n in names:
        if n == "mom12":
            v = np.full(len(t_idx), np.nan)
            ok = t_idx >= 12
            v[ok] = y[t_idx[ok]] - y[t_idx[ok] - 12]
        else:
            v = ctx[n][t_idx]
        cols.append(v)
    return np.column_stack(cols)


def _ridge(X, z, lam):
    mu, sd = X.mean(0), X.std(0) + 1e-12
    Xs = (X - mu) / sd
    zm = z.mean()
    beta = np.linalg.solve(Xs.T @ Xs + lam * np.eye(X.shape[1]), Xs.T @ (z - zm))
    return lambda Xn: zm + ((Xn - mu) / sd) @ beta


def _pick_lambda(X, z, tt, h, lams=(0.1, 1.0, 10.0, 100.0)):
    """Forward-chaining (time-ordered) cross-validation with a purge gap of h months, so no fold sees the future."""
    n = len(z)
    if n < 16:
        return 10.0
    cuts = [n // 2, (3 * n) // 4]
    errs = {lam: 0.0 for lam in lams}
    for k, c0 in enumerate(cuts):
        c1 = cuts[k + 1] if k + 1 < len(cuts) else n
        tr = tt <= tt[c0] - h
        va = np.arange(n) >= c0
        va &= np.arange(n) < c1
        if tr.sum() < 6 or va.sum() < 1:
            continue
        for lam in lams:
            m = _ridge(X[tr], z[tr], lam)
            errs[lam] += float(np.mean((m(X[va]) - z[va]) ** 2))
    return min(lams, key=lambda lam: errs[lam])


def f_driver(y, h, ctx, names=("mom12",)):
    """Direct regression: share(t+j) - share(t) on features known at t (12-month momentum and optionally lagged drivers),
    one ridge fit per step j = 1..h, ridge strength chosen by forward-chaining CV. Forecast for ORIGIN T uses features at T.
    Returns NaNs if a driver is not available at the origin (e.g. the stale price series)."""
    T = len(y) - 1
    out = np.full(h, np.nan)
    x_now = _features(y, ctx, np.array([T]), names)
    if np.isnan(x_now).any():
        return out
    for j in range(1, h + 1):
        tt = np.arange(0, T - j + 1)
        X = _features(y, ctx, tt, names)
        z = y[tt + j] - y[tt]
        ok = ~np.isnan(X).any(1)
        X, z, tts = X[ok], z[ok], tt[ok]
        if len(z) < 8:
            return out
        lam = _pick_lambda(X, z, tts, j)
        out[j - 1] = y[T] + float(_ridge(X, z, lam)(x_now)[0])
    return np.maximum(out, 0.0)


def model_set(kind):
    """Name -> function. Logistic has one entry per assumed ceiling."""
    ms = {"naive": f_naive, "linear36": f_linear, "holt_damped": f_holt}
    for k in CEILINGS[kind]:
        ms[f"logistic_K{int(round(k * 100))}"] = (lambda y, h, ctx=None, k=k: f_logistic(y, h, ctx, ceiling=k))
    ms["drv_mom"] = lambda y, h, ctx: f_driver(y, h, ctx, ("mom12",))
    ms["drv_cpi"] = lambda y, h, ctx: f_driver(y, h, ctx, ("mom12", "cpi_yoy"))
    ms["drv_all"] = lambda y, h, ctx: f_driver(y, h, ctx, ("mom12", "cpi_yoy", "price_yoy", "pop_g"))
    return ms


# ---------------------------------------------------------------- bands and back-test
def internal_errors(fn, y, h, ctx, step=3, span=60, min_train=24):
    """Pseudo-out-of-sample errors (actual - forecast) of the model INSIDE the training window: refit at origins every
    `step` months over the last `span` months and compare to what happened. Returns array (n_origins, h), NaN where
    the future was not yet inside the window. Errors are RELATIVE (divided by the level at that origin) because the shares
    grow several-fold, so absolute early errors would make the band far too narrow. Used to build the 80 % band."""
    T = len(y) - 1
    rows = []
    for t in range(max(min_train, T - h - span), T - h + 1, step):
        try:
            f = fn(y[: t + 1], h, ctx)
        except Exception:
            continue
        e = (y[t + 1: t + 1 + h] - f) / max(y[t], 1e-9)       # relative to the level at that origin
        if len(e) == h and not np.isnan(e).any():
            rows.append(e)
    return np.array(rows)


def band(point, errs, scale, level=0.80, n_boot=500, seed=0):
    """80 % band per step: bootstrap-resample the model's own step-j errors, take the 10th/90th percentiles, times the
    current level `scale` (last observed share), add to point.
    Falls back to NaN when there are fewer than 4 errors."""
    h = len(point)
    lo, hi = np.full(h, np.nan), np.full(h, np.nan)
    if errs.ndim != 2 or len(errs) < 4:
        return lo, hi
    rng = np.random.default_rng(seed)
    a = (1 - level) / 2 * 100
    for j in range(h):
        e = errs[:, j]
        bs = rng.choice(e, size=(n_boot, len(e)), replace=True)
        q = np.percentile(bs, [a, 100 - a], axis=1).mean(1)
        lo[j], hi[j] = point[j] + scale * q[0], point[j] + scale * q[1]
    return lo, hi


def backtest(series_df, kind, ctx_df, origins, horizons=(12, 24), truth_end=None):
    """Rolling-origin back-test. series_df['share'] is the target; ctx_df holds driver columns on the same index.
    Returns a long DataFrame: one row per (model, origin, horizon) with errors defined as forecast - actual."""
    y_all = series_df["share"].to_numpy()
    idx = series_df.index
    ctx = {c: ctx_df[c].to_numpy() for c in ctx_df.columns}
    models = model_set(kind)
    rows = []
    for o in origins:
        T = int(np.where(idx == month_end(o))[0][0])
        for h in horizons:
            if T + h >= len(y_all):
                continue
            truth = y_all[T + 1: T + 1 + h]
            for name, fn in models.items():
                y = y_all[: T + 1]
                c = {k: v[: T + 1] for k, v in ctx.items()}
                pt = fn(y, h, c)
                if np.isnan(pt).any():
                    rows.append({"series": kind, "model": name, "origin": str(month_end(o).date()), "h": h, "usable": False})
                    continue
                lo, hi = band(pt, internal_errors(fn, y, h, c), y[-1])
                err = pt - truth
                cov = float(np.mean((truth >= lo) & (truth <= hi))) if not np.isnan(lo).any() else np.nan
                rows.append({"series": kind, "model": name, "origin": str(month_end(o).date()), "h": h, "usable": True,
                             "mae_h_pp": abs(err[-1]) * 100, "me_h_pp": err[-1] * 100,
                             "mae_steps_pp": float(np.mean(np.abs(err))) * 100, "me_steps_pp": float(np.mean(err)) * 100,
                             "coverage80": cov})
    return pd.DataFrame(rows)


def summarise_backtest(bt):
    """Average over origins per (series, model, h): MAE and mean error at the horizon month, coverage over all months."""
    u = bt[bt["usable"]]
    g = u.groupby(["series", "model", "h"]).agg(n_origins=("origin", "count"), mae_h_pp=("mae_h_pp", "mean"),
                                               me_h_pp=("me_h_pp", "mean"), mae_steps_pp=("mae_steps_pp", "mean"),
                                               coverage80=("coverage80", "mean")).reset_index()
    return g


def best_model(summary, kind):
    """Lowest mean of MAE-at-horizon over h = 12 and 24, only models with results at both horizons and for 3 origins."""
    s = summary[(summary["series"] == kind)]
    p = s.pivot(index="model", columns="h", values="mae_h_pp").dropna()
    return (p.mean(1)).sort_values()


# ---------------------------------------------------------------- scenarios
def months_to(last_date, target):
    t = month_end(target)
    d = month_end(last_date)
    return (t.year - d.year) * 12 + (t.month - d.month)


def scenario_from_models(point_by_model, band_best, best, keep, floor=0.0):
    """Low / mid / high at one target month: mid = best model; low/high = widest of the best model's 80 % band and the
    point forecasts of the `keep` models (models not much worse than best in the back-test). Ordered by construction.
    Every value is floored at `floor` (the last observed share): the observed stock never fell, so a forecast below
    today's level is not a credible low case."""
    mid = point_by_model[best]
    pts = [point_by_model[m] for m in keep if not np.isnan(point_by_model[m])]
    lo_c = [mid] + pts + ([band_best[0]] if not np.isnan(band_best[0]) else [])
    hi_c = [mid] + pts + ([band_best[1]] if not np.isnan(band_best[1]) else [])
    return max(min(lo_c), floor), max(mid, floor), max(max(hi_c), floor)


def avg_new_system_kw(pv, months=12, end=None):
    """Volume-weighted mean size of NEW residential systems over the last `months` (EA: avg capacity of new installations
    x number of new installations). Returns kW."""
    d = pv if end is None else pv.loc[:end]
    d = d.iloc[-months:]
    return float((d["avg_new_kw"] * d["n_new"]).sum() / d["n_new"].sum())


def rolling_size_series(pv, months=12):
    w = pv["avg_new_kw"] * pv["n_new"]
    return (w.rolling(months).sum() / pv["n_new"].rolling(months).sum()).dropna()


# ---------------------------------------------------------------- link to hosting capacity
def read_off(pen_grid, hc_kw, pen):
    """HC at a penetration by straight-line interpolation of the simulated curve; clamps at the ends (no extrapolation)."""
    return float(np.interp(pen, pen_grid, hc_kw))


def first_exceeded(pen_grid, hc_kw, size_kw):
    """Lowest penetration (fraction) at which the hosting capacity falls below size_kw, by interpolation between curve
    points. Returns 0.0 if already below at the first point, None if never below on the curve."""
    p, hc = np.asarray(pen_grid, float), np.asarray(hc_kw, float)
    if hc[0] < size_kw:
        return float(p[0])
    for i in range(1, len(p)):
        if hc[i] < size_kw:
            return float(p[i - 1] + (hc[i - 1] - size_kw) / (hc[i - 1] - hc[i]) * (p[i] - p[i - 1]))
    return None


def n_houses(pen, n_cust=55):
    return math.ceil(round(pen * n_cust, 9))      # same ceil rule as hosting.n_pv_for
