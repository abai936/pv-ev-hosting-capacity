"""Stage 10 dashboard tests: every page runs with no exception, shows the 'simulated'
banner, and each data page shows at least one dataframe. Skipped if streamlit is missing."""
import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(importlib.util.find_spec("streamlit") is None,
                                reason="streamlit not installed")

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app" / "app.py"
sys.path.insert(0, str(ROOT / "app"))

BANNER = "Simulated results. Synthetic NZ-parameterised data. Cable ratings are assumed."
PAGES = ["1 Overview", "2 PV hosting capacity", "3 Year simulation", "4 EV hosting capacity",
         "5 Mitigation", "6 Uptake 2027-2028", "7 Validation and limitations", "8 Checkpoints",
         "9 About and data"]
# page -> a results file whose presence means the page must show a dataframe
DATA_PAGES = {
    "2 PV hosting capacity": "results/stage6_snapshot_hc.csv",
    "3 Year simulation": "results/stage6_year.csv",
    "4 EV hosting capacity": "results/stage7_ev_hc.csv",
    "5 Mitigation": "results/stage8_hc.csv",
    "6 Uptake 2027-2028": "results/stage9b_scenarios.csv",
    "7 Validation and limitations": "results/stage9_recheck.csv",
}


def _run(page):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    at.sidebar.radio[0].set_value(page).run()
    return at


@pytest.mark.parametrize("page", PAGES)
def test_page_runs_with_banner(page):
    at = _run(page)
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.title) == 1
    assert any(BANNER in w.value for w in at.warning), "simulated banner missing"
    captions = [c.value for c in at.caption]
    assert not any("measured" in c for c in captions), "no result may be labelled measured"
    if page in DATA_PAGES:
        if (ROOT / DATA_PAGES[page]).is_file():
            assert len(at.dataframe) >= 1, f"{page}: no dataframe shown"
            # tables carry their source file and the 'simulated' label
            assert any(c.startswith("Source: results/") and "simulated" in c for c in captions)
        else:
            assert any("not available" in i.value for i in at.info)


def _expected_overview(csv, column, **filters):
    """Independent pandas filter of a results CSV (None filter = empty cell)."""
    import pandas as pd
    df = pd.read_csv(ROOT / csv)
    m = pd.Series(True, index=df.index)
    for c, v in filters.items():
        m &= df[c].isna() if v is None else (df[c] == v)
    assert m.sum() == 1, (csv, filters, int(m.sum()))
    return df.loc[m, column].iloc[0]


def test_overview_headline_numbers():
    at = _run("1 Overview")
    vals = {m.label: m.value for m in at.metric}
    assert len(vals) == 7
    for pen in (0.3, 0.6, 1.0):
        exp = _expected_overview("results/stage6_snapshot_hc.csv", "HC_kW", placement="P1",
                                 load_case="L2", source_pu=1.0, model="neutral_return",
                                 penetration=pen, seed=None, div_seed=None)
        assert vals[f"{int(pen * 100)} % of houses"] == f"{float(exp):.1f} kW"
    for lab, lc in (("Typical evening (LE)", "LE"), ("Busy evening (LE_P90)", "LE_P90")):
        exp = _expected_overview("results/stage7_ev_hc.csv", "EV_HC_count", placement="P1_direct",
                                 model="main", load_case=lc, source_pu=1.0, ev_kw=7.4,
                                 rating_scale=1.0, div_seed=None, seed=None)
        assert vals[lab] == f"{float(exp):.0f} EVs"
    for lab, case in (("No inverter control (M0)", "Y3_M0_tap1.000"),
                      ("Australia A volt-var + volt-watt (M3)", "Y3_M3_tap1.000")):
        exp = _expected_overview("results/stage8_year.csv", "cust_hours_above_253V", case=case)
        assert vals[lab] == f"{float(exp):.1f} h"
    captions = " ".join(c.value for c in at.caption)
    assert "assumed cable rating" in captions and "HC_voltage_only_kW" in captions
    assert "modelled inverter control" in captions


def _tmp_results(tmp_path, monkeypatch, drop):
    """Copy of the results CSVs with the given columns removed; loaders point at it."""
    import pandas as pd
    import data as d
    (tmp_path / "results").mkdir()
    for rel in d.EXPECTED_CSV:
        src = ROOT / rel
        if src.is_file():
            df = pd.read_csv(src)
            df = df.drop(columns=[c for c in drop.get(Path(rel).name, []) if c in df.columns])
            df.to_csv(tmp_path / rel, index=False)
    for name in ("ROOT", "RESULTS", "CHECKPOINTS", "IMG"):
        monkeypatch.setattr(d, name, tmp_path / {"ROOT": "", "RESULTS": "results",
                                                 "CHECKPOINTS": "checkpoints",
                                                 "IMG": "checkpoints/img"}[name])


def _infos(at):
    return [i.value for i in at.info]


def test_missing_column_overview_message_no_exception(tmp_path, monkeypatch):
    _tmp_results(tmp_path, monkeypatch, {"stage6_snapshot_hc.csv": ["HC_kW"],
                                         "stage8_year.csv": ["cust_hours_above_253V"]})
    at = _run("1 Overview")
    assert not at.exception
    msgs = _infos(at)
    assert any("stage6_snapshot_hc.csv: column HC_kW missing (file format changed)" in m for m in msgs)
    assert any("stage8_year.csv: column cust_hours_above_253V missing (file format changed)" in m
               for m in msgs)


def test_missing_column_pv_and_mitigation_pages(tmp_path, monkeypatch):
    _tmp_results(tmp_path, monkeypatch, {"stage6_snapshot_hc.csv": ["source_pu"],
                                         "stage4_hc.csv": ["source_pu"],
                                         "stage8_hc.csv": ["mode"]})
    for page, col in (("2 PV hosting capacity", "source_pu"), ("5 Mitigation", "mode")):
        at = _run(page)
        assert not at.exception, [e.value for e in at.exception]
        assert any(f"column {col} missing (file format changed)" in m for m in _infos(at)), page


def test_uptake_page_caps_shown_as_text():
    at = _run("6 Uptake 2027-2028")
    assert not at.exception
    import pandas as pd
    sc = pd.read_csv(ROOT / "results/stage9b_scenarios.csv")
    shown = at.dataframe[0].value
    if "feeder_hc_display" in sc.columns:
        assert "new_system_minus_hc_kw" not in shown.columns
        assert "feeder_hc_kw_at_that_penetration" not in shown.columns


def test_expected_results_files_exist_or_are_handled():
    import data as d
    for rel in d.EXPECTED_CSV:
        df = d.load_csv(rel)
        if (ROOT / rel).is_file():
            assert df is not None and len(df) > 0, rel
        else:
            assert df is None, rel
    for rel in d.EXPECTED_MD:
        txt = d.load_text(rel)
        assert (txt is not None) == (ROOT / rel).is_file(), rel
    assert d.load_csv("results/does_not_exist.csv") is None
    assert d.load_text("results/does_not_exist.md") is None


def test_loader_refuses_raw_data():
    import data as d
    for rel in ("data/raw/x.csv", "data/processed/x.csv", "data/feeders/x.csv"):
        with pytest.raises(ValueError):
            d.load_csv(rel)


def test_loader_guard_resolves_paths():
    import data as d
    # '..' tricks and absolute paths into the forbidden folders are refused too
    for rel in ("results/../data/raw/x.csv", "./data/feeders/x.csv", "data\\processed\\x.csv"):
        with pytest.raises(ValueError):
            d.load_text(rel)
    with pytest.raises(ValueError):
        d.check_allowed(ROOT / "checkpoints" / ".." / "data" / "raw" / "a.png")
    assert d.check_allowed(ROOT / "results" / "x.csv").name == "x.csv"
