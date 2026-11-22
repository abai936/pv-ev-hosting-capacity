"""Stage 5: NZ-parameterised 30-minute profiles for calendar year 2022 (17,520 steps).

Everything is indexed in UTC. Pacific/Auckland is used only to pick time of day, so NZ
daylight saving can never create a duplicate or missing step.
Labels: load and EV are "synthetic, NZ-parameterised"; PV is "modelled" (PVGIS-ERA5).
"""
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ZIP_PATH = ROOT / "data" / "raw" / "steidl" / "Data.zip"
PVGIS_DIR = ROOT / "data" / "raw" / "pvgis"
PROFILE_DIR = ROOT / "data" / "feeders" / "LVTestCase" / "Daily_1min_100profiles"
OUT_DIR = ROOT / "data" / "processed"

LOCAL_TZ = "Pacific/Auckland"
N_STEPS = 17520
STEP_H = 0.5
N_HOUSES = 55
ANNUAL_KWH_PER_HOUSE = 7048.0  # MBIE via Figure.NZ, year to Mar 2025, national (not Auckland)
ZIP_BASE = "Data/New-Zealand/Auckland/Reference/"
ZIP_TOTAL = ZIP_BASE + "Totals/Total_electricity_load.csv"
ZIP_EV = ZIP_BASE + "Electric-vehicles.csv"
ZIP_APPLIANCES = ZIP_BASE + "Totals/Total_electric_appliances.csv"
PV_CF_REFERENCE = 0.151  # EECA/AMCL App. 7 Table 1, Auckland north 30 deg ILR 1.0 (row inferred)

# Every EV parameter with its source label.
EV_PARAMS = {
    "charger_kw": (7.4, "assumption"),
    "sessions_per_ev_per_day": (1, "assumption"),
    "energy_median_kwh": (6.9, "Vector trial summary, search snippet only, INFERRED"),
    "energy_sigma": (0.5, "assumption"),
    "energy_cap_kwh": (40.0, "assumption"),
    # EECA 2023 survey start hours, VERIFIED in R4
    "start_hour_share": ({17: 0.04, 18: 0.07, 19: 0.05, 20: 0.07, 21: 0.34, 22: 0.08, 23: 0.12},
                         "EECA 2023 survey, VERIFIED in R4"),
    "other_hours_note": ("remaining 23% spread uniformly over 00:00-16:59", "assumption"),
}


def time_index_utc():
    """The one 30-min UTC grid for 2022."""
    idx = pd.date_range("2022-01-01", periods=N_STEPS, freq="30min", tz="UTC")
    assert idx[-1] == pd.Timestamp("2022-12-31 23:30", tz="UTC")
    return idx


def half_hour_of_local_day(idx_utc):
    """0..47 index of each UTC step within the Auckland local day (for time-of-day logic only)."""
    loc = idx_utc.tz_convert(LOCAL_TZ)
    return (loc.hour * 2 + loc.minute // 30).to_numpy()


# ---------------------------------------------------------------- load
# Steidl timestamp labels. The files say "+00:00" (UTC) but that is wrong. Evidence (checked
# 19 Nov 2026): grouped by month and label hour, Total_electric_appliances.csv (occupancy
# driven) has its minimum at 03:00 and maximum at 19:00 in EVERY month, with no shift at the
# April or September NZ daylight-saving changes. So the labels are local clock time with no
# daylight saving, i.e. NZ standard time, fixed UTC+12. We drop the "+00:00" and subtract
# 12 h to get true UTC. The total load's winter max at 11:00 comes from the heating components
# (heat pump, electric heating), whose timing is suspect.
STEIDL_UTC_OFFSET_H = 12


def _read_zip_30min(member, chunksize=100_000):
    """Read a 1-min city CSV straight from the zip in chunks; return 30-min mean kW (UTC index)."""
    sums, counts = None, None
    with zipfile.ZipFile(ZIP_PATH) as z, z.open(member) as f:
        for ch in pd.read_csv(f, chunksize=chunksize):
            # Parse, drop the wrong "+00:00", treat the label as NZST (UTC+12), convert to UTC.
            label = pd.to_datetime(ch["time"], utc=True).dt.tz_localize(None)
            t = (label - pd.Timedelta(hours=STEIDL_UTC_OFFSET_H)).dt.tz_localize("UTC").dt.floor("30min")
            g = ch["load_kW"].groupby(t)
            s, c = g.sum(), g.count()
            sums = s if sums is None else sums.add(s, fill_value=0.0)
            counts = c if counts is None else counts.add(c, fill_value=0.0)
    return (sums / counts).sort_index()


def _to_year_grid(kw):
    """Put a shifted series on the 2022 UTC grid. The last 12 h of UTC 2022 would need label
    times in 2023, which do not exist; fill them with the previous day's values (24 h earlier)."""
    kw = kw.reindex(time_index_utc())
    kw = kw.fillna(kw.shift(48))
    return kw


def city_shape_30min_kw(option="total_minus_ev"):
    """City load shape in kW on the UTC grid.
    'total_minus_ev' (default): Total_electricity_load - Electric-vehicles (our own EVs are added later).
    'appliances' (sensitivity): Total_electric_appliances only (no heating components)."""
    if option == "total_minus_ev":
        kw = _read_zip_30min(ZIP_TOTAL) - _read_zip_30min(ZIP_EV)
    elif option == "appliances":
        kw = _read_zip_30min(ZIP_APPLIANCES)
    else:
        raise ValueError(option)
    return _to_year_grid(kw)


def city_non_ev_30min_kw():
    return city_shape_30min_kw("total_minus_ev")


def average_house_kw(city_kw=None, option="total_minus_ev", ref_city_kw=None):
    """Average household kW: city shape scaled so the DEFAULT shape (total - EV) sums to 7,048 kWh/yr.

    The scale factor is 7,048 / sum(raw total_minus_ev). Other options (appliances only) use the SAME
    factor, so they are a true "no electric heating, no electric hot water" shape that carries less
    than 7,048 kWh/yr (the Steidl appliances file drops electric hot water too). ref_city_kw lets the
    caller pass the raw total_minus_ev series to avoid reading it twice."""
    if city_kw is None:
        city_kw = city_shape_30min_kw(option)
    if ref_city_kw is None:
        ref_city_kw = city_kw if option == "total_minus_ev" else city_shape_30min_kw("total_minus_ev")
    kwh_per_raw_kw = ANNUAL_KWH_PER_HOUSE / ref_city_kw.sum()   # kWh per step per raw kW unit
    return city_kw * kwh_per_raw_kw / STEP_H                    # kW


def feeder_profiles_30min():
    """The feeder's 100 daily 1-min profiles averaged to 48 half-hour bins -> shape (100, 48)."""
    arr = np.empty((100, 48))
    for i in range(100):
        v = np.loadtxt(PROFILE_DIR / f"load_profile_{i + 1}.txt")
        assert v.size == 1440
        arr[i] = v.reshape(48, 30).mean(axis=1)
    return arr


def diversity_factors(seed=2022, n_houses=N_HOUSES):
    """d_i(tod) = profile_i / mean of all 100 profiles, per half hour; one profile per house (seeded)."""
    prof = feeder_profiles_30min()
    d_all = prof / prof.mean(axis=0)
    pick = np.random.default_rng(seed).choice(100, size=n_houses, replace=False)
    return d_all[pick], pick


def daily_profile_picks(seed, n_houses, n_days):
    """Which of the 100 feeder profiles each house uses on each local day: (houses, days) ints, seeded."""
    return np.random.default_rng(seed).integers(0, 100, size=(n_houses, n_days))


def house_loads_kw(a_kw, seed=2022, n_houses=N_HOUSES):
    """House load_i(t) = A(t) * d_pick(i, local day)(local time of day). Returns (steps, houses) kW.

    Each house, each Auckland local day, draws one of the 100 feeder profiles at random (with
    replacement, seeded), so houses do not peak together every day. Afterwards all loads are
    scaled by one factor so the mean house has the same annual kWh as a_kw (7,048 for the default
    shape). House-to-house yearly differences are removed (see ASSUMPTIONS A15)."""
    prof = feeder_profiles_30min()
    d_all = prof / prof.mean(axis=0)                              # (100, 48)
    loc = a_kw.index.tz_convert(LOCAL_TZ)
    day = pd.factorize(loc.normalize())[0]                        # local day number of each step
    tod = (loc.hour * 2 + loc.minute // 30).to_numpy()
    pick = daily_profile_picks(seed, n_houses, day.max() + 1)     # (houses, days)
    d = d_all[pick[:, day], tod[None, :]]                         # (houses, steps)
    kw = a_kw.to_numpy()[:, None] * d.T
    kw *= a_kw.sum() / kw.sum(axis=0).mean()                      # mean house annual kWh = a_kw annual kWh
    return kw


# ---------------------------------------------------------------- PV
def read_pvgis_kw_per_kwp(path):
    """PVGIS hourly (UTC, HH:30) -> 30-min kW per kWp on the common grid (AC, after 14% loss)."""
    df = pd.read_csv(path, skiprows=10, usecols=["time", "P"]).dropna()
    df = df[df["time"].str.match(r"^\d{8}:\d{4}$")]
    t = pd.to_datetime(df["time"], format="%Y%m%d:%H%M", utc=True)
    s = pd.Series(df["P"].astype(float).to_numpy() / 1000.0, index=t)       # W -> kW (peakpower = 1 kWp)
    grid = time_index_utc()
    # Interpolate linearly in time between the hourly points; edges take the nearest value.
    s = s.reindex(s.index.union(grid)).interpolate("time").ffill().bfill()
    return s.reindex(grid)


def pv_capacity_factor(kw_per_kwp):
    return float(kw_per_kwp.mean())  # mean kW per kWp = energy / (kWp * hours)


def pv_north_south():
    """Return (series_north, cf_north, cf_south, aspect_north).
    PVGIS aspect convention is 0 = SOUTH, 180 = north (not hemisphere-aware), so the
    higher-yield file is chosen by test, not by label."""
    a0 = read_pvgis_kw_per_kwp(PVGIS_DIR / "pvgis_era5_2022_akl_aspect0.csv")
    a180 = read_pvgis_kw_per_kwp(PVGIS_DIR / "pvgis_era5_2022_akl_aspect180.csv")
    if a180.sum() > a0.sum():
        return a180, pv_capacity_factor(a180), pv_capacity_factor(a0), 180
    return a0, pv_capacity_factor(a0), pv_capacity_factor(a180), 0


# ---------------------------------------------------------------- EV
def ev_sessions(n_ev, seed=2022, n_days=366):
    """One session per EV per Auckland local day, local days from 2021-12-31 (so the early
    hours of local 1 Jan, which are 31 Dec UTC, are covered). Returns UTC start and kWh."""
    p = {k: v[0] for k, v in EV_PARAMS.items()}
    rng = np.random.default_rng(seed)
    n = n_ev * n_days
    energy = np.minimum(rng.lognormal(np.log(p["energy_median_kwh"]), p["energy_sigma"], n),
                        p["energy_cap_kwh"])
    shares = p["start_hour_share"]
    probs = np.zeros(24)
    for h, s in shares.items():
        probs[h] = s
    probs[:17] = (1.0 - sum(shares.values())) / 17           # remaining 23% over hours 0..16
    hour = rng.choice(24, size=n, p=probs)
    start_h_local = hour + rng.random(n)                    # uniform inside the hour
    day = np.tile(np.arange(n_days), n_ev)
    ev_id = np.repeat(np.arange(n_ev), n_days)
    local = pd.Timestamp("2021-12-31") + pd.to_timedelta(day, unit="D") \
        + pd.to_timedelta(start_h_local, unit="h")
    start_utc = pd.DatetimeIndex(local).tz_localize(
        LOCAL_TZ, ambiguous=True, nonexistent="shift_forward").tz_convert("UTC")
    # One charger cannot deliver two sessions at once: a session that would start while the
    # previous one is still charging waits until it finishes (assumption, queue per EV).
    t_h = ((start_utc - pd.Timestamp("2022-01-01", tz="UTC")).total_seconds() / 3600.0).to_numpy()
    t_h = t_h.reshape(n_ev, n_days).copy()
    dur = (energy / p["charger_kw"]).reshape(n_ev, n_days)
    for d in range(1, n_days):
        t_h[:, d] = np.maximum(t_h[:, d], t_h[:, d - 1] + dur[:, d - 1])
    start_utc = pd.Timestamp("2022-01-01", tz="UTC") + pd.to_timedelta(t_h.ravel(), unit="h")
    return pd.DataFrame({"ev": ev_id, "start_utc": start_utc, "energy_kwh": energy,
                         "start_hour_local": hour})


def ev_series_kw(sessions, n_ev):
    """Constant 7.4 kW until the energy is delivered, split exactly over 30-min bins.
    Returns (steps, n_ev) kW (average power in each step)."""
    kw = EV_PARAMS["charger_kw"][0]
    grid0 = time_index_utc()[0]
    start_h = ((sessions["start_utc"] - grid0).dt.total_seconds() / 3600.0).to_numpy()
    end_h = start_h + sessions["energy_kwh"].to_numpy() / kw
    ev = sessions["ev"].to_numpy()
    out = np.zeros((N_STEPS, n_ev))
    first = np.floor(start_h / STEP_H).astype(int)
    for k in range(int(np.ceil(40.0 / kw / STEP_H)) + 2):
        b = first + k
        lo = np.maximum(start_h, b * STEP_H)
        hi = np.minimum(end_h, (b + 1) * STEP_H)
        ov = np.clip(hi - lo, 0, None)
        ok = (b >= 0) & (b < N_STEPS) & (ov > 0)
        np.add.at(out, (b[ok], ev[ok]), kw * ov[ok] / STEP_H)
    return out


# ---------------------------------------------------------------- build all
def build_all(n_ev=55, seed=2022, out_dir=OUT_DIR, write=True):
    """Build all profiles. write=False skips every file write; otherwise files go to out_dir."""
    out_dir = Path(out_dir)
    idx = time_index_utc()
    raw = city_shape_30min_kw("total_minus_ev")
    a = average_house_kw(raw, "total_minus_ev", raw)         # default: total - EV, 7,048 kWh/yr
    a_app = average_house_kw(city_shape_30min_kw("appliances"), "appliances", raw)  # same factor, no heating/hot water
    houses = house_loads_kw(a, seed)
    pv, cf_n, cf_s, asp = pv_north_south()
    sess = ev_sessions(n_ev, seed)
    ev = ev_series_kw(sess, n_ev)
    result = {"avg_house": a, "avg_house_appliances": a_app, "houses": houses, "pv": pv, "cf_north": cf_n,
              "cf_south": cf_s, "north_aspect": asp, "ev": ev, "sessions": sess}
    if not write:
        return result
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"avg_house_kw": a, "pv_kw_per_kwp": pv}).rename_axis("time_utc").to_csv(
        out_dir / "avg_house_and_pv_30min.csv")
    pd.DataFrame({"avg_house_kw": a}).rename_axis("time_utc").to_csv(
        out_dir / "avg_house_shape_total_minus_ev_30min.csv")
    pd.DataFrame({"avg_house_kw": a_app}).rename_axis("time_utc").to_csv(
        out_dir / "avg_house_shape_appliances_only_30min.csv")
    np.savez_compressed(out_dir / "house_load_kw.npz", time_utc=idx.astype(str).to_numpy().astype("U25"),
                        kw=houses.astype("float32"))
    np.savez_compressed(out_dir / "ev_kw.npz", time_utc=idx.astype(str).to_numpy().astype("U25"),
                        kw=ev.astype("float32"))
    return result
