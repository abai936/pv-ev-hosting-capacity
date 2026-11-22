# Data sources

| Source | URL | Licence status | Downloaded | Location |
|---|---|---|---|---|
| IEEE European LV Test Feeder, OpenDSS files (LVTestCase) | https://github.com/dss-extensions/electricdss-tst/tree/master/Version8/Distrib/IEEETestCases/LVTestCase | no licence stated, not redistributed | 19 Nov 2026 | data/feeders/LVTestCase |
| IEEE European LV Test Feeder v2 (zip) | https://cmte.ieee.org/pes-testfeeders/wp-content/uploads/sites/167/2017/08/European_LV_Test_Feeder_v2.zip | no licence stated, not redistributed | 19 Nov 2026 | data/feeders/ieee_zip |
| Steidl et al. 2025, Zenodo 15362256 | https://zenodo.org/records/15362256 | CC BY 4.0, synthetic, NZ-parameterised | downloading separately | data/raw/steidl |
| Steidl subset used: Auckland Reference Total_electricity_load.csv and Electric-vehicles.csv (city aggregate, 1-min, UTC) | https://zenodo.org/records/15362256 | CC BY 4.0 | 19 Nov 2026 | data/raw/steidl/Data.zip -> data/processed/ (synthetic, NZ-parameterised) |
| PVGIS-ERA5 hourly 2022, Auckland -36.85/174.76, 1 kWp, 30 deg, loss 14%, aspect 0 and 180 | https://re.jrc.ec.europa.eu/api/v5_3/seriescalc?lat=-36.85&lon=174.76&pvcalculation=1&peakpower=1&loss=14&angle=30&aspect=180&raddatabase=PVGIS-ERA5&startyear=2022&endyear=2022&outputformat=csv | licence not checked | 19 Nov 2026 | data/raw/pvgis/ (modelled) |
| MBIE Sales-based Electricity Costs (Jun 2025) via Figure.NZ: 7,048 kWh per household, year to Mar 2025, national | https://figure.nz/chart/OO85CulTuE2TRnsE | licence not checked | read 19 Nov 2026 | number only, in `profiles.py` |
| EECA 2023 EV charging start-time survey and EECA/AMCL Appendix Seven Table 1 (PV capacity factor 0.151) | see research/R4 | licence not checked | numbers only | `profiles.py`, tests |
| Vector EV trial summary (median session 6.9 kWh) | see research/R4 | search snippet only, INFERRED | number only | `profiles.py` |

Everything under data/feeders/ and data/raw/ is git-ignored. Re-fetch the feeder files with `.venv/Scripts/python scripts/download_data.py`.

Stage 5 outputs in data/processed/ (git-ignored): avg_house_and_pv_30min.csv, house_load_kw.npz (55 houses), ev_kw.npz. Labels: load and EV "synthetic, NZ-parameterised"; PV "modelled". Rebuild with `.venv/Scripts/python scripts/stage5_build_profiles.py`. PVGIS aspect 0 is SOUTH-facing (PVGIS convention), 180 is north.
