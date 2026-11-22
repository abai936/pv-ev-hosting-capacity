"""Page functions for the plain Stage 10 dashboard (default Streamlit widgets only)."""
from __future__ import annotations

import re

import streamlit as st

import data as d

SIM = "simulated"
_IMG_LINE = re.compile(r"^\s*!\[([^\]]*)\]\(([^)]+)\)\s*$")


# ---------------------------------------------------------------- helpers
def banner() -> None:
    st.warning(d.BANNER)


def missing(rel: str) -> None:
    st.info(f"{rel}: not available yet (file missing or still being written).")


def table(df, rel: str, note: str = SIM) -> None:
    """Show a dataframe with its source file and the 'simulated' label under it."""
    if df is None:
        missing(rel)
        return
    if df.attrs.get("missing_col"):
        st.info(f"{df.attrs.get('rel', rel)}: column {df.attrs['missing_col']} missing (file format changed)")
    elif df.empty:
        st.info(f"{rel}: no rows for this selection.")
    else:
        st.dataframe(df, hide_index=True)
    st.caption(f"Source: {rel} ({note})")


def figure(name: str, note: str = SIM) -> None:
    p = d.image_path(name)
    rel = f"checkpoints/img/{name}"
    if p is None:
        missing(rel)
        return
    st.image(str(p))
    st.caption(f"Source: {rel} ({note})")


def markdown_file(rel: str, base_dir=None) -> set:
    """Render a markdown file; image lines are shown with st.image.

    Returns the set of image file names it showed (so a page can avoid showing them twice).
    """
    shown: set = set()
    text = d.load_text(rel)
    if text is None:
        missing(rel)
        return shown
    base = base_dir if base_dir is not None else (d.ROOT / rel).parent
    buf: list[str] = []
    for line in text.splitlines():
        m = _IMG_LINE.match(line)
        if m:
            if buf:
                st.markdown("\n".join(buf))
                buf = []
            try:
                p = d.check_allowed(base / m.group(2))  # refuse data/raw etc. even from markdown
            except ValueError:
                p = None
            if p is not None and p.is_file():
                st.image(str(p), caption=m.group(1) or None)
                shown.add(p.name)
            else:
                st.caption(f"(image {m.group(2)} not available)")
        else:
            buf.append(line)
    if buf:
        st.markdown("\n".join(buf))
    st.caption(f"Source: {rel}")
    return shown


def summary_expander(rel: str, label: str = "Full summary file") -> None:
    with st.expander(f"{label}: {rel}"):
        markdown_file(rel)


def fmt(v, unit: str = "", nd: int = 1) -> str:
    if v is None:
        return d.NOT_AVAILABLE
    try:
        return f"{float(v):.{nd}f}{unit}"
    except (TypeError, ValueError):
        return str(v)


def select_rows(df, **filters):
    if df is None:
        return None
    m = df.index == df.index
    for col, val in filters.items():
        if col not in df.columns:
            out = df.iloc[0:0].copy()
            out.attrs.update(df.attrs)
            out.attrs["missing_col"] = col  # table() turns this into a 'column missing' message
            return out
        if val is None:
            m &= df[col].isna().to_numpy()
        elif isinstance(val, (list, tuple, set)):
            m &= df[col].isin(list(val)).to_numpy()
        else:
            m &= (df[col] == val).to_numpy()
    out = df.loc[m]
    out.attrs.update(df.attrs)
    return out


def keep(df, cols):
    if df is None:
        return None
    out = df[[c for c in cols if c in df.columns]]
    out.attrs.update(df.attrs)
    return out


def headline(df, column: str, fmt_args: tuple, problems: list, **filters) -> str:
    """Formatted value for a metric; column problems are collected in `problems`."""
    return fmt(d.pick_value(df, column, problems, **filters), *fmt_args)


def show_problems(problems: list) -> None:
    for msg in dict.fromkeys(problems):
        st.info(msg)


HC_CAP_KW = 20.0  # top of the PV sweep: an HC at this value means 'no limit hit up to 20 kW'


def uptake_text(df):
    """Page 6: values at the sweep cap become 'at least 20 kW' text, never plain numbers."""
    if df is None:
        return None
    out = df.copy()
    out.attrs.update(df.attrs)
    for hc in ("feeder_hc_kw_at_that_penetration", "HC_kW"):
        if hc not in out.columns:
            continue
        capped = out[hc] >= HC_CAP_KW - 1e-6
        if "feeder_hc_display" in out.columns:
            out = out.drop(columns=[hc])
        else:
            out[hc] = [f"at least {HC_CAP_KW:g} kW" if c else f"{v:.1f} kW"
                       for v, c in zip(out[hc], capped)]
        gap = "new_system_minus_hc_kw"
        if gap in out.columns:
            def txt(g, c):
                if c:
                    return (f"at least {-g:.1f} kW below HC" if g <= 0
                            else f"at most {g:.1f} kW above HC")
                return f"{abs(g):.1f} kW {'below' if g <= 0 else 'above'} HC"
            out["new_system_vs_hc"] = [txt(g, c) for g, c in zip(out[gap], capped)]
            out = out.drop(columns=[gap])
        break
    return out


# ---------------------------------------------------------------- pages
def page_overview() -> None:
    st.title("PV + EV hosting capacity of a low-voltage feeder (NZ-parameterised)")
    banner()
    st.write(
        "This project asks how much rooftop solar (PV) and how many electric vehicle (EV) "
        "chargers one low-voltage street feeder can take before customer voltage leaves "
        "207 to 253 V or a cable or the transformer goes over its rating. It uses the IEEE "
        "European LV Test Feeder (55 houses) in OpenDSS with synthetic, NZ-parameterised load "
        "and solar data: a midday summer snapshot for hosting capacity, a full 2022 year for "
        "violation hours, inverter control and transformer tap as fixes, and a 2027-2028 uptake "
        "what-if from national data. All numbers on this site are simulated and read from "
        "precomputed files; nothing is re-run here."
    )

    s6 = d.load_csv("results/stage6_snapshot_hc.csv")
    st.subheader("PV hosting capacity, balanced placement P1 (kW per PV customer)")
    problems: list = []
    cols = st.columns(3)
    for col, pen in zip(cols, (0.3, 0.6, 1.0)):
        col.metric(f"{int(pen * 100)} % of houses",
                   headline(s6, "HC_kW", (" kW",), problems, placement="P1", load_case="L2",
                            source_pu=1.0, model="neutral_return", penetration=pen, seed=None,
                            div_seed=None))
    vo = d.pick_value(s6, "HC_voltage_only_kW", problems, placement="P1", load_case="L2",
                      source_pu=1.0, model="neutral_return", penetration=0.3, seed=None,
                      div_seed=None)
    st.caption("Source: results/stage6_snapshot_hc.csv (simulated; L2 midday load, source 1.00 pu). "
               "These P1 numbers are limited by an assumed cable rating (line1, 4c_70), not by "
               f"voltage. Voltage-only value at 30 % (HC_voltage_only_kW): {fmt(vo, ' kW')}.")

    s7 = d.load_csv("results/stage7_ev_hc.csv")
    st.subheader("EVs charging at once (7.4 kW, placement P1_direct)")
    c1, c2 = st.columns(2)
    for col, lc, lab in ((c1, "LE", "Typical evening (LE)"), (c2, "LE_P90", "Busy evening (LE_P90)")):
        col.metric(lab, headline(s7, "EV_HC_count", (" EVs", 0), problems, placement="P1_direct",
                                 model="main", load_case=lc, source_pu=1.0, ev_kw=7.4,
                                 rating_scale=1.0, div_seed=None, seed=None))
    st.caption("Source: results/stage7_ev_hc.csv (simulated; limited by an assumed cable rating)")

    s8 = d.load_csv("results/stage8_year.csv")
    st.subheader("Year 2022, customer-hours above 253 V (case Y3, 8 kWp on 60 % of houses)")
    c1, c2 = st.columns(2)
    for col, case, lab in ((c1, "Y3_M0_tap1.000", "No inverter control (M0)"),
                           (c2, "Y3_M3_tap1.000", "Australia A volt-var + volt-watt (M3)")):
        col.metric(lab, headline(s8, "cust_hours_above_253V", (" h",), problems, case=case))
    st.caption("Source: results/stage8_year.csv (simulated; modelled inverter control)")
    show_problems(problems)


def page_pv() -> None:
    st.title("PV hosting capacity (midday summer snapshot)")
    banner()
    st.write("HC = largest PV kW per PV customer with no voltage, line, transformer or VUF "
             "violation. Line ratings are assumed. Stage 4 uses the feeder's own load (L1); "
             "Stage 6 uses the NZ midday load (L2).")
    s4 = d.load_csv("results/stage4_hc.csv")
    s6 = d.load_csv("results/stage6_snapshot_hc.csv")
    pen = st.selectbox("Penetration (share of the 55 houses with PV)", [0.3, 0.6, 1.0],
                       format_func=lambda x: f"{int(x * 100)} %")
    cols = ["placement", "seed", "penetration", "n_pv", "load_case", "source_pu", "HC_kW",
            "Orion_capped_HC_kW", "HC_voltage_only_kW", "binding_limit", "binding_element",
            "binding_linecode", "binding_phase", "rating_status"]

    st.subheader("P1 (balanced) and P2 (end-clustered): Stage 4 (L1) vs Stage 6 (L2)")
    t4 = select_rows(s4, model="neutral_return", source_pu=1.0, penetration=pen,
                     placement=["P1", "P2"], load_case="L1")
    table(keep(t4, cols), "results/stage4_hc.csv")
    t6 = select_rows(s6, model="neutral_return", source_pu=1.0, penetration=pen,
                     placement=["P1", "P2"], load_case="L2", div_seed=None)
    table(keep(t6, cols), "results/stage6_snapshot_hc.csv")

    st.subheader("P3 random placement (50 seeds), Stage 6, L2")
    t3 = select_rows(s6, model="neutral_return", source_pu=1.0, penetration=pen, placement="P3")
    table(keep(t3, cols), "results/stage6_snapshot_hc.csv")
    st.caption("P5 / P50 / P95 over the seeds are in results/stage6_snapshot_summary.md.")

    st.subheader("Source-voltage sweep (P1, L2, 60 %)")
    sw = select_rows(s6, placement="P1", load_case="L2", penetration=0.6, div_seed=None,
                     model=["neutral_return", "sens_source_pu"])
    if sw is not None and "source_pu" in sw.columns:
        sw = sw.sort_values("source_pu")
    table(keep(sw, ["source_pu", "model", "HC_kW", "HC_voltage_only_kW", "binding_limit",
                    "binding_element", "binding_linecode", "binding_phase"]),
          "results/stage6_snapshot_hc.csv")

    st.subheader("Other Stage 6 sensitivities (L2b appliances only, diversity seed)")
    sens = st.selectbox("Sensitivity", ["sens_L2b_appliances_only", "sens_diversity_seed"])
    table(keep(select_rows(s6, model=sens), cols + ["div_seed"]), "results/stage6_snapshot_hc.csv")

    st.subheader("Figures")
    st.caption("Orion_capped_HC_kW = min(HC, 10 kW): the 10 kW per-customer cap of the Orion-style "
               "method. HC_kW is the uncapped value from the 20 kW sweep.")
    figure("cp06_hc_nz_vs_feeder.png")
    figure("cp04_hc_vs_penetration.png")
    figure("cp04_sensitivity.png")
    summary_expander("results/stage6_snapshot_summary.md")
    summary_expander("results/stage4_summary.md")


def page_year() -> None:
    st.title("Year simulation 2022 (30-minute steps)")
    banner()
    st.write("Y0 = no PV; Y1 / Y2 / Y3 = 3 / 5 / 8 kWp on 60 % of houses (P1), no inverter "
             "control, no EV. Line hours use assumed ratings.")
    y = d.load_csv("results/stage6_year.csv")
    table(keep(y, ["seed", "case", "pv_kwp_per_house", "n_pv_houses", "cust_hours_above_253V",
                   "distinct_hours_above_253V", "cust_hours_below_207V", "v_min_V", "v_max_V",
                   "distinct_hours_line_above_100pct", "line_hours_above_100pct_sum_over_lines",
                   "max_line_loading_pct", "xfmr_max_kVA", "reverse_flow_hours", "vuf_max_pct",
                   "vuf_hours_above_2pct", "nonconverged"]), "results/stage6_year.csv")
    if y is not None and {"case", "cust_hours_above_253V"} <= set(y.columns):
        st.write("Customer-hours above 253 V by case")
        st.bar_chart(y.set_index("case")["cust_hours_above_253V"])
        st.caption("Source: results/stage6_year.csv (simulated)")
    with st.expander("All columns, including energy balance"):
        table(y, "results/stage6_year.csv")

    st.subheader("Hours above 100 % by linecode (assumed ratings)")
    lc = d.load_csv("results/stage6_year_linecodes.csv")
    cases = sorted(lc["case"].unique()) if lc is not None and "case" in lc.columns else []
    case = st.selectbox("Case", cases) if cases else None
    table(select_rows(lc, case=case) if case else lc, "results/stage6_year_linecodes.csv")

    st.subheader("Y0 across house-diversity seeds")
    table(d.load_csv("results/stage6_year_seeds.csv"), "results/stage6_year_seeds.csv")
    with st.expander("Seed runs by linecode"):
        table(d.load_csv("results/stage6_year_seeds_linecodes.csv"),
              "results/stage6_year_seeds_linecodes.csv")
    figure("cp06_year_violations.png")


def page_ev() -> None:
    st.title("EV hosting capacity (winter weekday evening)")
    banner()
    st.write("EV HC = most 7.4 kW EVs charging at the same time with no violation. LE = typical "
             "(median) evening; LE_P90 = busy evening. The count is set by an assumed cable rating.")
    e = d.load_csv("results/stage7_ev_hc.csv")
    cols = ["placement", "load_case", "seed", "source_pu", "ev_kw", "rating_scale", "div_seed",
            "EV_HC_count", "pct_of_55_houses", "ph1", "ph2", "ph3", "phase_mix_at_first_fail",
            "binding_limit", "binding_element", "binding_linecode", "binding_phase",
            "rating_status", "min_cust_v_at_HC", "xfmr_kva_at_HC"]
    st.subheader("Main result (source 1.00 pu, 7.4 kW)")
    lc = st.selectbox("Load case", ["LE", "LE_P90"])
    table(keep(select_rows(e, model="main", load_case=lc,
                           placement=["P1_direct", "P1_nested_order", "P2"]), cols),
          "results/stage7_ev_hc.csv")
    with st.expander("P3 random orderings (50 seeds)"):
        table(keep(select_rows(e, model="main", load_case=lc, placement="P3"), cols),
              "results/stage7_ev_hc.csv")

    st.subheader("Sensitivities (P1_direct)")
    sens = st.selectbox("Sensitivity", ["sens_ev_kw", "sens_source_pu", "sens_rating_scale",
                                        "sens_diversity_seed"])
    table(keep(select_rows(e, model=sens), cols), "results/stage7_ev_hc.csv")

    st.subheader("Voltage margin (P1_direct, LE)")
    table(d.load_csv("results/stage7_voltage_margin.csv"), "results/stage7_voltage_margin.csv")
    st.subheader("Hand check")
    table(d.load_csv("results/stage7_hand_check.csv"), "results/stage7_hand_check.csv")

    st.subheader("Year 2022 with EV, no PV")
    ye = d.load_csv("results/stage7_year_ev.csv")
    table(keep(ye, ["seed", "case", "ev_penetration", "n_ev_houses", "cust_hours_below_207V",
                    "distinct_hours_below_207V", "v_min_V", "distinct_hours_line_above_100pct",
                    "line_hours_above_100pct_sum_over_lines", "max_line_loading_pct",
                    "xfmr_max_kVA", "vuf_max_pct", "n_ev_active_max_any_nonzero_half_hour",
                    "peak_coincident_ev_kw", "delta_v_min_V",
                    "delta_distinct_hours_line_above_100pct"]), "results/stage7_year_ev.csv")
    with st.expander("Year with EV by linecode"):
        table(d.load_csv("results/stage7_year_ev_linecodes.csv"),
              "results/stage7_year_ev_linecodes.csv")
    figure("cp07_ev_hc_vs_placement.png")
    figure("cp07_year_ev_lowvoltage.png")
    summary_expander("results/stage7_summary.md")


def page_mitigation() -> None:
    st.title("Mitigation: inverter control and transformer tap")
    banner()
    st.write("M0 = unity PF, no control; M1 = volt-watt only; M2 = volt-var only; M3 = Australia A "
             "volt-var + volt-watt. Tap 0.975 = LV side lowered 2.5 %. Inverter control is modelled.")
    h = d.load_csv("results/stage8_hc.csv")
    c1, c2, c3, c4 = st.columns(4)
    modes = c1.multiselect("Mode", ["M0", "M1", "M2", "M3"], default=["M0", "M3"])
    tap = c2.selectbox("Tap", [1.0, 0.975])
    place = c3.selectbox("Placement", ["P1", "P2", "P3"])
    kva = c4.selectbox("Inverter kVA / kW", [1.0, 1.1])
    t = select_rows(h, mode=modes, tap=tap, placement=place, kva_ratio=kva)
    if t is not None:
        keys = [c for c in ("penetration", "mode", "seed") if c in t.columns]
        if keys:
            t = t.sort_values(keys)
    st.subheader("Snapshot hosting capacity")
    table(keep(t, ["mode", "tap", "kva_ratio", "placement", "seed", "penetration", "n_pv",
                   "status", "HC_kW", "Orion_capped_HC_kW", "HC_voltage_only_kW",
                   "curtailed_pct_at_HC", "binding_limit", "binding_element", "binding_linecode",
                   "binding_phase", "rating_status", "vmax_v_at_HC"]),
          "results/stage8_hc.csv", "simulated; modelled inverter control")

    st.subheader("Year 2022, case Y3 (8 kWp on 60 % of houses)")
    table(keep(d.load_csv("results/stage8_year.csv"),
               ["case", "mode", "tap", "kva_ratio", "scope", "cust_hours_above_253V",
                "distinct_hours_above_253V", "cust_hours_below_207V", "v_min_V", "v_max_V",
                "curtailed_kWh", "curtailed_pct_of_pv_energy", "q_absorbed_kvarh",
                "distinct_hours_line_above_100pct", "max_line_loading_pct", "xfmr_max_kVA",
                "nonconverged_steps", "control_not_settled_steps"]),
          "results/stage8_year.csv")
    st.subheader("Tap effect on EV evening voltage")
    table(d.load_csv("results/stage8_ev_tap.csv"), "results/stage8_ev_tap.csv")
    st.caption("Orion_capped_HC_kW = min(HC, 10 kW): the 10 kW cap of the Orion-style method.")
    figure("cp08_hc_mitigation.png")
    figure("cp08_year_curtailment.png")
    summary_expander("results/stage8_summary.md")


def page_uptake() -> None:
    st.title("Uptake 2027-2028 (what-if)")
    banner()
    st.info("This page is a national-data what-if: PV and EV uptake is a modelled forecast from "
            "national data (EA, MoT, Stats NZ, MBIE), not data for this feeder. Linking it to the "
            "synthetic feeder's simulated hosting capacity is a 'what if', not a prediction for "
            "any real street.")
    note = "modelled forecast from national data; feeder link simulated"
    st.subheader("Scenarios")
    st.caption(f"Feeder PV hosting capacity is capped at {HC_CAP_KW:g} kW by the sweep, so capped "
               "values are shown as 'at least 20 kW' and the gap to the new-system size as a bound.")
    table(uptake_text(d.load_csv("results/stage9b_scenarios.csv")),
          "results/stage9b_scenarios.csv", note)
    st.subheader("Back-test of the forecast models")
    bt = d.load_csv("results/stage9b_backtest.csv")
    if bt is not None and "series" in bt.columns:
        series = st.selectbox("Series", sorted(bt["series"].dropna().unique()))
        bt = select_rows(bt, series=series)
    table(bt, "results/stage9b_backtest.csv", "modelled forecast vs national data")
    st.subheader("PV hosting capacity vs penetration (link curve)")
    table(uptake_text(d.load_csv("results/stage9b_hc_curve.csv")), "results/stage9b_hc_curve.csv",
          note)
    figure("cp09b_scenarios_vs_hc.png", note)
    figure("cp09b_backtest.png", "modelled forecast vs national data")
    summary_expander("results/stage9b_summary.md")


def page_validation() -> None:
    st.title("Validation and limitations")
    banner()
    st.subheader("Stage 9 recheck")
    table(d.load_csv("results/stage9_recheck.csv"), "results/stage9_recheck.csv")
    t1, t2, t3 = st.tabs(["VALIDATION.md", "LIMITATIONS.md", "ASSUMPTIONS.md"])
    with t1:
        markdown_file("VALIDATION.md")
    with t2:
        markdown_file("LIMITATIONS.md")
    with t3:
        markdown_file("ASSUMPTIONS.md")


def page_checkpoints() -> None:
    st.title("Checkpoints (progress log)")
    banner()
    files = d.checkpoint_files()
    if not files:
        missing("checkpoints/CP-*.md")
        return
    names = [f.name for f in files]
    pick = st.selectbox("Checkpoint", names, index=len(names) - 1)
    shown = markdown_file(f"checkpoints/{pick}")
    m = re.match(r"CP-(\d+)", pick)
    if m:
        imgs = sorted(d.IMG.glob(f"cp{m.group(1)}*.png")) if d.IMG.is_dir() else []
        imgs = [p for p in imgs if p.name not in shown]  # each image once
        if imgs:
            st.subheader("More images for this checkpoint")
            for p in imgs:
                # 9b figures are a modelled forecast from national data, not plain simulation
                figure(p.name, "modelled forecast from national data" if p.name.startswith("cp09b")
                       else SIM)
    with st.expander("Checkpoint index: checkpoints/README.md"):
        markdown_file("checkpoints/README.md")


def page_about() -> None:
    st.title("About and data")
    banner()
    st.subheader("Data sources")
    markdown_file("DATA.md")
    st.subheader("Licences")
    lic = [p.name for p in d.ROOT.glob("LICENSE*")]
    st.write("Project code licence: " + (", ".join(lic) if lic else "not available (no LICENSE file yet)") + ".")
    st.write("The IEEE European LV Test Feeder files have no licence stated, so they are not "
             "committed. Other downloaded data is not committed either; see DATA.md for sources.")
    st.subheader("What is committed and what is not")
    st.markdown(
        "- Committed: `src/`, `tests/`, `scripts/` (including `download_data.py`), `app/`, "
        "`results/` CSV and md files, `checkpoints/`, `DATA.md`, `DATA-CHECKSUMS.sha256`, "
        "planning files.\n"
        "- Not committed (git-ignored): `data/raw/`, `data/feeders/`, `data/processed/`, "
        "`results/cache/`, `.venv/`."
    )
    st.subheader("How to rerun")
    scripts = sorted(p.name for p in (d.ROOT / "scripts").glob("*.py"))
    st.markdown(
        "1. Create `.venv` with Python 3.13.9 and `pip install -r requirements.txt`.\n"
        "2. `.venv\\Scripts\\python scripts\\download_data.py` (feeder and public data).\n"
        "3. Run the stage scripts in `scripts/` in order, then `.venv\\Scripts\\python -m pytest`.\n"
        "4. Dashboard: `.venv\\Scripts\\streamlit run app\\app.py` (reads results only)."
    )
    st.write("Scripts found: " + (", ".join(scripts) if scripts else d.NOT_AVAILABLE))


PAGES = {
    "1 Overview": page_overview,
    "2 PV hosting capacity": page_pv,
    "3 Year simulation": page_year,
    "4 EV hosting capacity": page_ev,
    "5 Mitigation": page_mitigation,
    "6 Uptake 2027-2028": page_uptake,
    "7 Validation and limitations": page_validation,
    "8 Checkpoints": page_checkpoints,
    "9 About and data": page_about,
}
