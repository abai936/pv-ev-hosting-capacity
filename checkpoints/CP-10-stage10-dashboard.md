# CP-10: Stage 10, plain results dashboard (19 Nov 2026)

**Status: built, reviewed, fixed.** A plain Streamlit app that only **reads results already computed** (CSV and markdown files in `results/`, figures in `checkpoints/img/`). It never runs OpenDSS, and it refuses to read `data/raw`, `data/processed` and `data/feeders`. No styling yet: default widgets only. The look-and-feel pass waits until Aniket says.
Sources: `app/app.py`, `app/views.py`, `app/data.py`, `app/README.md`, `tests/test_app.py`, the recorded pytest run.

## Figures
No screenshot yet (I could not drive a browser here, and styling is not done). The existing result figures appear inside the app pages (cp04 to cp09b). To see it, run `.venv\Scripts\streamlit run app\app.py` and open the address it prints.

## Done: nine pages
1. **Overview:** a one-paragraph summary, seven headline numbers read straight from the CSVs, and the banner "Simulated results. Synthetic NZ-parameterised data. Cable ratings are assumed."
2. **PV hosting capacity:** penetration selector, Stage 4 against Stage 6, placements P1/P2/P3, source-voltage sweep, binding limits.
3. **Year simulation:** Y0 to Y3 table, hours above 253 V, overloaded cables, diversity seeds.
4. **EV hosting capacity:** typical against busy evening, sensitivities, voltage margin, hand check, year with EVs.
5. **Mitigation:** inverter mode, tap, placement and inverter-size selectors; year table; EV and tap.
6. **Uptake 2027–2028:** scenarios, back-test, link to the feeder limits, marked "modelled forecast from national data".
7. **Validation and limitations:** the re-check table, plus VALIDATION.md, LIMITATIONS.md and ASSUMPTIONS.md.
8. **Checkpoints:** every report rendered with its images.
9. **About and data:** data sources and licences, what is and is not in git, how to re-run.

Every table and figure shows its source file and the word "simulated" (or "modelled forecast" for Stage 9b). A missing file shows "not available yet" and a missing column shows "<file>: column X missing (file format changed)".

## Works (checked)
- **pytest: 132 passed, 0 failed** (the recorded pytest run), including 16 app tests with the dashboard's own page runner (all nine pages run with no error, banner present, tables present, headline numbers compared with an independent read of the CSVs, missing-column messages, loader guard).
- **Run proof:** the app started headless and answered HTTP 200; the process was stopped afterwards.
- The reviewer recomputed the headline numbers from the CSVs: P1 9.50 / 5.03 / 2.72 kW; EVs 6 (typical evening) and 2 (busy); year over-253 V customer-hours 1,330 without inverter control and 38.5 with Australia A.

## Found by the review, and fixed
- A missing column crashed page 2 and gave a misleading "no rows" message. Both fixed, with tests.
- The PV headline hid that it is limited by an **assumed cable rating**; the caption now says so and shows the voltage-only value.
- Values at the 20 kW search cap were shown as plain numbers; they now read "at least 20 kW".
- The loader's folder guard could be fooled by `..` paths; it now resolves paths first.
- Figures were labelled "simulated" even when they were forecasts; the forecast figures now carry the right label.

## Still open
- Layout and look were not checked in a real browser, by design. Styling comes later.
- One page-6 text format is not tested exactly ("at least X kW below").
- Whether to deploy publicly is undecided. The feeder data has no licence, so any public version must show results only.

## Decisions made
- Plain default Streamlit, no custom CSS, no extra plotting libraries (Aniket: make it work first).
- The app reads precomputed results only, so it stays fast and cannot change a result.

## Next
Stage 11 (README, licence, release preparation). Then Aniket tests it, and only then the UI/UX pass.

