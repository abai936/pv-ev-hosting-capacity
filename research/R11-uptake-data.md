# R11: Open NZ data for a 2027-2028 EV and rooftop PV uptake forecast

Read on 19 Nov 2026. Labels: **checked** = I opened the file or page and read the numbers; **snippet-only** = only a web search summary, not opened; **blocked** = source exists but I could not read it.
Saved files are in `.\data\raw\uptake\` (git-ignored; nothing committed, nothing overwritten or deleted). Sizes and sha256 are at the end.

## 1. Datasets table

| # | What | Source (URL) | Span, frequency | Licence | Saved | Confidence |
|---|---|---|---|---|---|---|
| 1 | Residential solar PV (incl. with battery): ICP count, uptake rate %, installed MW, new installs per month, NZ | Electricity Authority EMI report "Installed distributed generation trends" (GUEHMT). CSV link pattern: `https://www.emi.ea.govt.nz/Retail/Download/DataReport/CSV/GUEHMT?RegionType=NZ&MarketSegment=Res&Capacity=All_Total&FuelType=solar_all&_rsdr=ALL&_si=v\|4` | Aug 2013 to 31 Oct 2026, monthly, 159 months | CC BY 4.0 (EA copyright page, https://www.ea.govt.nz/copyright-disclaimer-transparency/, checked) | yes | checked, direct CSV, high |
| 2 | Same, all market segments (res + business) solar | same URL with `MarketSegment=All` | same | same | yes | checked, high |
| 3 | Solar installs snapshot by region and segment (ICPs, avg and total kW) at Oct 2026 | https://www.emi.ea.govt.nz/Retail/Datasets/SolarInstallations/SolarInstallationsByRegion.csv (also `SolarInstallationsByStreet.csv`, 4.2 MB, not saved) | single snapshot, modified 18 Nov 2026 | CC BY 4.0 (EA) | ByRegion yes | checked; no time series, regional split only |
| 4 | Light-fleet EV/hybrid counts by engine type and vehicle class (battery electric, PHEV petrol/diesel, hybrid, petrol, diesel, total), NZ | Ministry of Transport "Fleet Statistics: Monthly Motor Vehicle fleet Feb 2026", republished by Figure.NZ: https://figure.nz/chart/qBM5TRld1dvbCH8C , CSV `https://figure.nz/table/c9iCbF6Qb0qNlAs2/download-source-dataset`. MoT original page https://www.transport.govt.nz/statistics-and-insights/fleet-statistics/monthly-mv-fleet is blocked to scripts (bot wall) | Jan 2016 to Feb 2026, monthly fleet stock (122 months); file name says Feb2017 because the chart starts there, the CSV itself starts Jan 2016 | Figure.NZ page states CC BY 4.0 (checked on page); MoT's own licence not read (blocked) | yes | checked. Fleet stock, not registrations. Data is 9 months old, MoT newer months need a manual download |
| 5 | Residential electricity cost c/kWh, MBIE sales-based, quarterly | MBIE "Sales-based electricity costs" (June 2025 release) via Figure.NZ https://figure.nz/table/5T4m9V7aIkI49k1R ; MBIE page https://www.mbie.govt.nz/building-and-energy/energy-and-natural-resources/energy-statistics-and-modelling/energy-statistics/energy-prices/electricity-cost-and-price-monitoring/ is blocked to scripts | 2013 Q2 to 2025 Q1, quarterly, 48 points (sheet "Quarterly Residential Elec Cost", B15:F62) | Figure.NZ page states CC BY 4.0 | yes (xlsx, 3 sheets; I did not parse values) | checked as to what it is; values not read. Stale: 2025 Q1 is the last point |
| 6 | Monthly typical residential bill by network region (fixed c/day, variable $/kWh, monthly kWh, total bill) | EA EMI `https://www.emi.ea.govt.nz/Retail/Datasets/RegionalPowerPrices/20260531_AveragePowerUseAndCosts.csv` | Jan 2025 to May 2026, monthly, 17 months | CC BY 4.0 (EA) | yes | checked. Too short for trend fitting, fine as a recent price level |
| 7 | CPI all groups, % change (annual and quarterly), NZ | Stats NZ Infoshare via Figure.NZ https://figure.nz/chart/1Vny7YwmIO8OoPNe-aoMb3PU42b6z7XK5 , CSV `https://figure.nz/table/R72dH7zYqMxp68t8/download-source-dataset` | 1925 Q4 to 2026 Q2, quarterly (annual-change column from 1989) | Figure.NZ page states CC BY 4.0 | yes | checked (2025 Q3 3.0%, 2026 Q2 4.1%). Sep 2026 quarter not in file, see snippet below |
| 8 | Estimated resident population (ERP), by age and sex, at 30 June | Stats NZ Infoshare via Figure.NZ https://figure.nz/chart/UjHz13ja0asuWu66 , CSV `https://figure.nz/table/xrVt8n4FqBvZNYBa/download-source-dataset` | 30 Jun 1991 to 30 Jun 2025, annual, 35 points; total all ages is the 3rd "Total All Ages" block (col index 815) | CC BY 4.0 on page | yes | checked: Jun 2025 = 5,324,700. File layout is awkward (wide, multi-row header) |
| 9 | GDP (production), rolling annual % change, chain volume | Stats NZ Infoshare via Figure.NZ https://figure.nz/table/POqkKyMYIs5xYtTv | 1988 Q1 to 2026 Q2, quarterly | Figure.NZ states Stats NZ data; CC BY 4.0 stated on Figure.NZ pages generally (not separately read for this page) | yes | checked (growth rates only, no level) |
| 10 | OCR history | RBNZ https://www.rbnz.govt.nz/monetary-policy/official-cash-rate and tables B2 / key-graph xlsx | 1999 to now | RBNZ terms not read | no | **blocked** (RBNZ returns 403 to scripts, my Chrome-extension attempt timed out waiting for user permission). Needs manual download. data.govt.nz lists an old RBNZ "graphdata.xlsx" link that also 403s |
| 11 | Stats NZ CPI/GDP direct CSVs, Aotearoa Data Explorer API | https://portal.apis.stats.govt.nz/ | n/a | Stats NZ: credit Stats NZ | no | needs a free API key (account creation, I did not do it) |
| 12 | NZTA Motor Vehicle Register (all registered vehicles snapshot, monthly) | data.govt.nz entries "Motor Vehicle Register" and "Motor Vehicle Register CSV downloads" (CC BY 4.0); CSV on opendata-nzta.opendata.arcgis.com | monthly snapshot (listing last modified Aug 2025) | CC BY 4.0 (data.govt.nz catalogue, checked) | no | checked the catalogue only. Full register is very large, not a "small file"; the ArcGIS service needs a token. Useful only if aggregated manually |
| 13 | EV market stats, new BEV/PHEV registrations and share by month; fleet counts | EVDB NZ https://evdb.nz/ev-stats and https://evdb.nz/fleet (source stated as NZTA/MoT) | to Oct 2026 | EVDB terms forbid scraping and need permission for external use | **no, by design** | checked page text only; third party, use as cross-check, not as a model input |

## 2. Numbers I read (with labels)

EV fleet (MoT via Figure.NZ, all vehicle classes, checked). Battery-electric count at December: 2016 1,911; 2017 4,842; 2018 9,331; 2019 14,901; 2020 19,159; 2021 29,298; 2022 49,889; 2023 76,531; 2024 83,885; 2025 92,560; Feb 2026 94,239. PHEV petrol at December: 2016 898; 2019 4,646; 2022 19,006; 2023 30,814; 2024 35,222; 2025 42,798; Feb 2026 44,355. Growth in BEV stock flattened in 2024 (+7,354) and 2025 (+8,675) against +26,642 in 2023.

Residential solar (EA, checked). ICPs with solar at December: 2013 2,081; 2014 5,182; 2015 8,979; 2016 13,035; 2017 17,287; 2018 21,488; 2019 25,042; 2020 28,732; 2021 34,604; 2022 43,229; 2023 52,966; 2024 64,055; 2025 74,999; Oct 2026 87,766 (4.32% of residential ICPs, 523.4 MW; Oct 2025 was 72,971 so +14,795 in 12 months). Average new residential system is about 9.1 kW in 2026 vs 3.6 kW in 2013-14, so capacity is growing faster than connections. All segments: 96,462 ICPs, 1,306 MW at Oct 2026.

Newer EV facts, **EVDB page text, third party, not saved**: fleet at 31 Oct 2026 about 107,200 fully electric and 55,900 PHEV light vehicles (2.37% and 1.23% of the light fleet); Oct 2026 new-light-vehicle share 10.4% BEV (1,526 units) and 12.1% PHEV, against 4.2% and 4.8% in Oct 2025. This implies BEV stock rose about 14,600 between Dec 2025 (92,560, all classes) and Oct 2026 (107,200, light only; class bases differ slightly), a sharp turn up after the 2024-25 flat patch. Treat as believed until the MoT figure is downloaded.

Drivers, **snippet-only** (news items citing Stats NZ/RBNZ, I did not open Stats NZ or RBNZ pages):
- CPI Sep 2026 quarter: annual 3.7% (June quarter 4.1%), petrol up 19.1% on the year (1News, interest.co.nz, 22 Oct 2026). The Jun 2026 4.1% is confirmed in my CPI file.
- OCR: 2.75% after the 28 Oct 2026 hold (vote 4-3); cut to 2.25% in Nov 2025; next decision 9 Dec 2026 (ANZ review and RBNZ page snippets).
- GDP Jun 2026 quarter +0.2% q/q (Stats NZ via 1News, 17 Sep 2026); annual figure reported as 1.7% (year-on-year to June). One source said 2.6%; not resolved. The saved rolling-annual file reaches 2026 Q2 and should settle it.
- Population: provisional ERP 5,357,300 at 30 Jun 2026 (Stats NZ news listing via search); Stats NZ 2024(base) projections released 4 Jun 2025 run to 2078 and say about 6 million by 2040. I did not find the medium-scenario value for 2027-2028.

## 3. How many yearly data points exist (decides whether a non-linear model is honest)

1. EV fleet stock (BEV and PHEV): 10 year-end points (Dec 2016 to Dec 2025), plus Feb 2026 and an unsaved Oct 2026 figure. Monthly stock gives 122 points but they are one smooth, cumulative series, not independent.
2. EV registrations (flows): derived from monthly fleet differences, so about 9 full years of annual flow. This includes used imports and fleet exits, so it is net change, not sales.
3. Rooftop PV (residential ICPs): 13 year-end points (Dec 2013 to Dec 2025) plus Oct 2026; 159 monthly points. This is the better series.
4. Both series cover a single adoption curve and several policy shocks (the 2022-23 feebate, the 2024 feebate end, 2026 fuel price rise), so a logistic or Bass fit with 3 or more free parameters is weakly identified from 10 to 13 annual points. A saturation level cannot be learned from the data (EV is about 2.4% of fleet, PV about 4.3% of residential ICPs). Believed: for a 2027-2028 horizon, report a simple trend or damped-trend model and a scenario range, and use the non-linear model only with an assumed ceiling taken from a published source.
5. Driver series are long (CPI 100 years, population 35 annual points, GDP 38 years) but electricity price (48 quarters, stale to 2025 Q1) and OCR (blocked) are weak links.

## 4. NZ projections found (cross-check only)

| Source | What it says | Status |
|---|---|---|
| Transpower, OTA-WKM A&B reconductoring application, Attachment 2, Dec 2025, https://www.comcom.govt.nz/assets/Documents/otahuhu-whakamaru-a-and-b-line-reconductoring-project/OTA-WKM-Attachment-2-Demand-and-Generation-Scenarios-December-2025.pdf | Upper North Island scenarios (Reference, Growth, Global, Environmental, Disruptive). Solar PV uptake given as number of 3 kW residential installations in 2050 and generation in 2050; EV demand in 2050 (e.g. Reference 3.2 TWh fixed charging). Regional peak-demand EV contribution in MW (2025 17 to 36 MW, 2035 68 to 115 MW). Text extracted from PDF is garbled in places, so the scenario-to-number mapping needs a human check | checked (opened) but 2050 horizon and regional; no 2030 national vehicle count |
| MBIE, Electricity Demand and Generation Scenarios 2024, https://mbie.govt.nz/assets/electricity-demand-and-generation-scenarios-report-2024.pdf | Solar 5.6% of generation by 2035; EV demand grows from late 2030s | snippet-only (MBIE site is bot-walled, PDF download returned an HTML block page). The results XLSX would hold EV and solar by year |
| Climate Change Commission, Emissions reduction monitoring report 2026 (transport summary and technical annex, July 2026) | Qualitative: moderate-to-significant risks to EV shift, Clean Vehicle Standard changes, no policy to cut upfront EV cost; EV prices converging. No 2030 EV count | checked (opened both PDFs) |
| Government targets as reported in the press (2/3 of new light registrations electric in 2030, 100% in 2035; 30% of light fleet zero-emission by 2035 in the first ERP); CCC 2023 path 40% of fleet by 2035 | policy targets, not forecasts; EVDB itself tracks "actual vs target" | snippet-only, secondary |
| Transpower older figures: distributed solar 535 MW by 2030 (EA 2023 article); solar about 1.1 GW by 2030 (2020 report) | already overtaken by actuals (EA data above: residential solar 523 MW at Oct 2026) | snippet-only |
| EA "Solar generation now and in the future" and EA/EECA solar pages | current totals, no 2030 MW figure found. A search snippet gave 81,671 solar systems, 856 MW (Jan 2026) which does not match my EA CSV (1,306 MW all segments at Oct 2026; EA counts grid-connected only), so do not use it | snippet-only, conflicting |
| EVDB (secondary) fleet projection page "about the projections" | says that even with 100% EV new sales from 2030 the light fleet would be only about 50% electric by 2040 | page read, method unverified |
| Concept Consulting "Shifting gear" EV studies (funded by AA, Transpower, others) | exist; I did not find or read the uptake numbers | snippet-only |
| EECA | no EV or solar uptake projection found; EECA, MBIE, MoT, NZTA sites are bot-walled to scripts | blocked |

## 5. Gaps and what needs a manual step by Aniket

1. **MoT monthly fleet and monthly registrations, latest months (Mar to Oct 2026).** The saved MoT data stops at Feb 2026. Manual download from https://www.transport.govt.nz/statistics-and-insights/fleet-statistics/monthly-mv-fleet (Tableau page; the Figure.NZ page "How to find the data" explains the Motor tech > Download > Data steps). New-registration counts and used-import split (flow data) are not in the saved files.
2. **RBNZ OCR history** (table B2 or OCR page) and **MBIE QSDEP / sales-based price after 2025 Q1** need manual download; both sites block scripted access.
3. **Stats NZ Sep 2026 CPI, 2024(base) national population projections 2027-2028, household income.** Not obtained as files; Infoshare/Data Explorer is interactive or needs an API key. I did not find a clean household-income series.
4. **EV charger and driver data** (EECA Public EV Chargers, CC BY 4.0, data.govt.nz) not saved; not needed unless chargers are used as a driver.
5. **MBIE EDGS 2024 XLSX, Transpower Whakamana i Te Mauri Hiko report data, Concept Consulting and EECA numbers** for a 2027-2030 cross-check are unread. The only opened projection is Transpower's 2050 regional one.
6. EA "installed DG" counts depend on distributor registry entries and can be revised or backdated (EA caveat in the report description, snippet from EA pages).
7. Fuel-price shock in 2026 (petrol +19.1%, Middle East conflict per news) is a regime change absent from 2016-2025 history. Any model fitted to the history will miss it; treat as scenario.

## 6. Saved files (all under `.\data\raw\uptake\`)

| File | Bytes | sha256 |
|---|---|---|
| EA_DG_solar_all_Res_NZ_monthly.csv | 14708 | 127a0e79cb2577c6354c12d702b5ffedf320911622036b49215ca8767a0a359e |
| EA_DG_solar_all_ALLsegments_NZ_monthly.csv | 14775 | 5f986d423c5997823c1fe013b3ef38ad87a3961fc1406cee276f938da955acfa |
| EA_SolarInstallationsByRegion.csv | 11274 | fbbcac1530c66f9de1bfb60edad2da093191e76dfa50eb8a95316c105450f042 |
| EA_20260531_AveragePowerUseAndCosts.csv | 112469 | 30c6382a91d3d08bd5e43a9d5407c2e09af0d80aa6977c65e8cde2ba7fee62ac |
| FigureNZ_MoT_EV_hybrid_fleet_by_engine_monthly_Feb2017-Feb2026.csv | 344792 | 247be506e70e5a9e5df9f1fe4e5441d13a014dc699e6bbc14b24f3497bbffe48 |
| FigureNZ_MBIE_residential_sales_based_electricity_cost_quarterly_2013Q2-2025Q1.xlsx | 128090 | 5e6d2dd43449fba788bb1bf8ee1379d6ada04761fc708fa93397978705b177b4 |
| FigureNZ_StatsNZ_CPI_all_groups_pct_change_qtrly_to_Jun2026.csv | 8029 | f5879a95d9e66bdc673b96f384eab969a64b7703f56bad7444c3fc466113ba38 |
| FigureNZ_StatsNZ_ERP_by_age_sex_annual_Jun_1991-2025.csv | 157839 | 70db1196867508b04a2f8113cc4fc95ba022679c001cbfc59e0ed3c36bf21dbd |
| FigureNZ_StatsNZ_GDP_rolling_annual_growth_1988Q1-2026Q2.csv | 3374 | 8e31a11acbdc725e0b4dfd3e015429b56b1e012d3ecf14de456a4baff3f69b9b |

Notes: the Figure.NZ files are republished government data (Figure.NZ is a third party, so cite the original provider: Ministry of Transport, MBIE, Stats NZ, with the Figure.NZ URL). The xlsx was first saved with a .csv name by mistake and renamed (my own new file). The MoT file name says Feb2017 but the data starts Jan 2016.
