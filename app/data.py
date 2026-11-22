"""Cached, read-only loaders for the dashboard.

Reads PRECOMPUTED files only: CSV and md files in results/, md files in the
project root and checkpoints/, PNG files in checkpoints/img/. It never runs
OpenDSS and never reads data/raw, data/processed or data/feeders.
A missing file returns None (the page then says 'not available yet').
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

# DASHBOARD_ROOT lets tests point the loaders at a temporary copy of the results.
ROOT = Path(os.environ.get("DASHBOARD_ROOT") or Path(__file__).resolve().parent.parent).resolve()
RESULTS = ROOT / "results"
CHECKPOINTS = ROOT / "checkpoints"
IMG = CHECKPOINTS / "img"

BANNER = "Simulated results. Synthetic NZ-parameterised data. Cable ratings are assumed."
NOT_AVAILABLE = "not available"

# Every results file a page reads (relative to the project root).
EXPECTED_CSV = [
    "results/stage4_hc.csv",
    "results/stage6_snapshot_hc.csv",
    "results/stage6_year.csv",
    "results/stage6_year_linecodes.csv",
    "results/stage6_year_seeds.csv",
    "results/stage6_year_seeds_linecodes.csv",
    "results/stage7_ev_hc.csv",
    "results/stage7_voltage_margin.csv",
    "results/stage7_hand_check.csv",
    "results/stage7_year_ev.csv",
    "results/stage7_year_ev_linecodes.csv",
    "results/stage8_hc.csv",
    "results/stage8_year.csv",
    "results/stage8_ev_tap.csv",
    "results/stage9_recheck.csv",
    "results/stage9b_scenarios.csv",
    "results/stage9b_backtest.csv",
    "results/stage9b_hc_curve.csv",
]
EXPECTED_MD = [
    "results/stage4_summary.md",
    "results/stage6_snapshot_summary.md",
    "results/stage7_summary.md",
    "results/stage8_summary.md",
    "results/stage9b_summary.md",
    "VALIDATION.md",
    "LIMITATIONS.md",
    "ASSUMPTIONS.md",
    "DATA.md",
]

_FORBIDDEN = ("data/raw", "data/processed", "data/feeders")


def check_allowed(p: Path) -> Path:
    """Resolve p and refuse anything inside the raw / processed / feeder data folders."""
    p = Path(p).resolve()
    for f in _FORBIDDEN:
        if p.is_relative_to((ROOT / f).resolve()):
            raise ValueError(f"dashboard must not read {p}")
    return p


def _resolve(rel: str) -> Path:
    return check_allowed(ROOT / rel.replace("\\", "/"))


def _mtime(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return -1.0


@st.cache_data(show_spinner=False)
def _read_csv_cached(path_str: str, mtime: float) -> pd.DataFrame | None:
    try:
        return pd.read_csv(path_str)
    except Exception:  # missing, half-written or empty file
        return None


@st.cache_data(show_spinner=False)
def _read_text_cached(path_str: str, mtime: float) -> str | None:
    try:
        return Path(path_str).read_text(encoding="utf-8")
    except Exception:
        return None


def load_csv(rel: str) -> pd.DataFrame | None:
    """Return the CSV as a DataFrame, or None if it is missing or unreadable."""
    p = _resolve(rel)
    if not p.is_file():
        return None
    df = _read_csv_cached(str(p), _mtime(p))
    if df is None:
        return None
    df = df.copy()
    df.attrs["rel"] = rel  # so messages can name the file
    return df


def load_text(rel: str) -> str | None:
    """Return a text/markdown file, or None if it is missing."""
    p = _resolve(rel)
    if not p.is_file():
        return None
    return _read_text_cached(str(p), _mtime(p))


def image_path(name: str) -> Path | None:
    """Path of a PNG in checkpoints/img, or None if missing."""
    p = check_allowed(IMG / name)
    return p if p.is_file() else None


def checkpoint_files() -> list[Path]:
    """CP-*.md files in checkpoints/, sorted by name."""
    return sorted(CHECKPOINTS.glob("CP-*.md"))


def pick_value(df: pd.DataFrame | None, column: str, problems: list | None = None, **filters):
    """Return the single value of `column` in the rows matching `filters`.

    A filter value of None means 'cell is empty'. Returns None when the file is
    missing, no row matches, or more than one row matches (never guesses).
    If a needed column is missing, a '<file>: column X missing (file format
    changed)' message is appended to `problems` (if given).
    """
    if df is None:
        return None
    rel = df.attrs.get("rel", "file")
    for col in (column, *filters):
        if col not in df.columns:
            if problems is not None:
                problems.append(f"{rel}: column {col} missing (file format changed)")
            return None
    mask = pd.Series(True, index=df.index)
    for col, val in filters.items():
        if val is None:
            mask &= df[col].isna()
        else:
            mask &= df[col] == val
    sub = df.loc[mask, column]
    if len(sub) != 1:
        return None
    return sub.iloc[0]
