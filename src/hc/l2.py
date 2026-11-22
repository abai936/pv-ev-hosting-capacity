"""Stage 6a: the NZ headline snapshot load "L2" (and L2b) built from the Stage 5 per-house series.

L2 per house = the median of that house's 30-minute load over the steps that start at 12:00 and 12:30 Auckland
local time, on weekdays (Mon to Fri, local date) of Dec, Jan and Feb of 2022. Those months are NZDT (UTC+13),
so local 12:00 is 23:00 UTC the day before; the Stage 5 grid is UTC, so convert with tz_convert (time of day
and weekday only, as in profiles.py). The median, not the mean, so a few EV-free evening-heating outliers
cannot move the midday point. Synthetic, NZ-parameterised load; not measured.
"""
import numpy as np
import pandas as pd

from . import profiles as P

SUMMER_MONTHS = (12, 1, 2)       # Dec 2022, Jan 2022, Feb 2022 (calendar 2022 only)
LOCAL_HALF_HOURS = (24, 25)      # 12:00 and 12:30 local, as half-hour-of-day indices


def summer_midday_mask(idx_utc):
    """Boolean mask over the UTC grid: local weekday, summer month, step starting 12:00 or 12:30 local."""
    loc = idx_utc.tz_convert(P.LOCAL_TZ)
    hh = loc.hour * 2 + loc.minute // 30
    return np.asarray(np.isin(hh, LOCAL_HALF_HOURS) & (loc.day_of_week < 5) & np.isin(loc.month, SUMMER_MONTHS))


def l2_kw(house_kw, idx_utc):
    """Per-house median kW over the L2 steps. house_kw is (steps, houses). Returns (kw[houses], n_steps)."""
    mask = summer_midday_mask(idx_utc)
    return np.median(house_kw[mask], axis=0), int(mask.sum())


def appliance_house_kw(seed=2022):
    """Per-house series from the appliances-only shape (L2b: no electric heating or hot water), same
    diversity picks as the default for the same seed. Scaled by the same factor as the default shape."""
    a = pd.read_csv(P.OUT_DIR / "avg_house_shape_appliances_only_30min.csv", index_col=0, parse_dates=True)
    return P.house_loads_kw(a["avg_house_kw"], seed)


def default_house_kw(seed=2022):
    """Per-house series (steps, houses) from the saved default shape (total - EV) for any diversity seed."""
    a = pd.read_csv(P.OUT_DIR / "avg_house_shape_total_minus_ev_30min.csv", index_col=0, parse_dates=True)
    return P.house_loads_kw(a["avg_house_kw"], seed)
