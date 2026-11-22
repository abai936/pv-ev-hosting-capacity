# Stage 9b summary: 2027-2028 PV and EV uptake scenarios and the hosting-capacity reading

## HEADLINE
1. All numbers are MODELLED forecasts from national NZ data (EA residential solar, MoT battery-electric fleet, Stats NZ, MBIE); they are not measured, not about this feeder, and not causal. PV: 159 monthly points; EV (BEV only, PHEV excluded): 122 monthly points.
2. Did the non-linear or driver model beat a straight line? Logistic (assumed ceilings) beats the 36-month linear fit: PV yes, EV no, but the naive forecast (PV 0.13, EV 0.92) beat every logistic. Driver regression beats both naive and linear: PV no, EV no; driver beats momentum-only regression: PV no, EV yes. PV: mean MAE over h=12 and 24 (pp of share): naive 0.13, linear36 0.37, Holt 0.21, best logistic (logistic_K60) 0.15, momentum-only regression 0.33, driver regression (drv_cpi) 0.37. EV: mean MAE over h=12 and 24 (pp of share): naive 0.92, linear36 1.02, Holt 1.01, best logistic (logistic_K20) 1.30, momentum-only regression 1.62, driver regression (drv_cpi) 1.44. Best model: PV naive, EV naive.
3. PV share of residential ICPs (low/mid/high), Dec 2027: 5.0/5.1/5.6 %; Dec 2028: 5.5/5.8/6.7 % (now 4.3 %, Oct 2026). Average new system (kW): Dec 2027 8.6/9.0/10.6; Dec 2028 8.6/9.1/11.9 (last 12 months: 8.64 kW, EA).
4. BEV per residential ICP (A30: BEV stock / the EA monthly residential ICP count; an UPPER BOUND on the share of houses with an EV) low/mid/high, Dec 2027: 4.7/5.4/9.4 %; Dec 2028: 5.3/5.8/13.4 % (now 4.7 %, Feb 2026). Every scenario is floored at the last observed share, because BEV stock never fell in any of the 122 months. The 2027 mid (5.4 %) is below the level the Oct 2026 EVDB snippet implies (about 5.53 % BEV per residential ICP, using the file's light ratio 0.955; snippet, third-party, NOT data); MoT Mar-Oct 2026 data need a manual download. EV horizons are beyond the 24 months that were back-tested, and the 2026 fuel-price turn is not in the history.
5. Hosting-capacity reading (P1, L2, source 1.00 pu, ratings assumed): HC falls from about 19.6 kW to at least 20 kW at 5-10 % (the 5 % point is the 20 kW sweep cap, binding 'none (>= 20 kW)') down to 2.7 kW at 100 %. The scenarios use N = ceil(share x 55) PV houses simulated directly (N = 3/3/4 in 2027, 4/4/4 in 2028, low/mid/high), giving HC >= 20 kW/>= 20 kW/18.5 kW (Dec 2027) and 18.5 kW/18.5 kW/18.5 kW (Dec 2028), against average new systems of 8.6/9.0/10.6 and 8.6/9.1/11.9 kW. A system of today's size (8.6 kW) first exceeds the HC at about 34 % penetration, several times the forecast national share. The average new system is below the HC in every scenario. Caveat: the HC is kW per single-phase PV customer (one phase), while the EA size is a whole-house system, which may be split over three phases; the size-versus-HC comparison is rough, and a value shown '>= 20 kW' means the sweep stopped at its 20 kW cap.
6. EV reading: Stage 7 gives 6 of 55 EVs (10.9 %) on a typical evening and 2 of 55 (3.6 %) on a busy evening (7.4 kW chargers, assumed ratings). The forecast BEV per residential ICP, 4.7/5.4/9.4 % (2027) and 5.3/5.8/13.4 % (2028), is an UPPER BOUND on the share of houses with an EV (some homes have two BEVs, some BEVs are fleet), and it is compared here with the Stage 7 'EVs of 55' counts: it sits above the busy-evening count from the low 2027 case and at or above the typical-evening count only in the high 2028 case (mid stays between the two counts). A feeder is not the national average: this is a 'what if this feeder looked like NZ' reading, with every BEV assumed to charge at 7.4 kW at the evening peak (an upper bound).
7. Back-test warning: 80 % bands held the truth in only 40 % (PV) / 27 % (EV) of cases: the ranges are too narrow; PV models were biased low (under-forecast in 8 of 9 models at 12 months, 9 of 9 at 24 months; mean over 3 origins).

## Method and data (all inputs from saved files in data/raw/uptake, sources in research/R11-uptake-data.md)
- PV: EA 'Installed distributed generation trends', residential solar, 2013-08-31 to 2026-10-31. Share = ICPs with solar / residential ICPs; the EA file carries the uptake rate, so the denominator is in the file (about 2.03 million at Oct 2026). CC BY 4.0.
- EV: MoT fleet via Figure.NZ, Battery Electric, all vehicle classes, stock 2016-01-31 to 2026-02-28. BEV only; PHEV and hybrids are excluded. Per 1,000 people = BEV / ERP x 1000 (ERP is annual at 30 June, straight-line interpolated by month; after Jun 2025 extended with the last year's growth, so the 2025-26 population is an EXTRAPOLATION). Now: 17.6 BEV per 1,000 people.
- A30 (assumption): BEV per residential ICP = BEV stock / the monthly residential ICP count of the same month from the EA file (data; the EA file spans Aug 2013 to Oct 2026, so it covers every BEV month Jan 2016 to Feb 2026 and no month is filled). No persons-per-household figure is used any more. It is an UPPER BOUND on the share of houses with an EV: some homes have two BEVs and some BEVs are fleet or business vehicles, while ICPs include holiday homes and so on (BELIEVED, not checked). The earlier +/-15 % persons-per-household sensitivity is dropped because it no longer drives the number. 'Per 1,000 people' = share x ICPs per person (EA ICPs / ERP at Feb 2026, ERP extrapolated).
- Ceilings of the logistic curve are ASSUMED scenario parameters (PV 15/30/60 % of houses, EV 20/40/70 % of residential ICPs), never fitted; no source was found for them.
- Drivers: CPI annual change (Stats NZ, quarterly to 2026 Q2), population growth (ERP to Jun 2025), residential electricity price (MBIE, quarterly to 2025 Q1; STALE). Release lags (CPI 1 month, price 6, population 3) are ASSUMED so no forecast uses unreleased data. Price growth is blank after 2026-03 and population growth only after 2026-09. At the EV origin (Feb 2026) both exist, so the full driver model (drv_all) was usable for the EV forecast; it was not kept because its error was more than twice the best (2.35 vs 0.92 pp). At the PV origin (Oct 2026) both are blank, so drv_all is unusable for PV (and it was also more than twice the best, 0.42 vs 0.13 pp). Unusable inputs: OCR (blocked file), GDP (saved but not used in the model), household income (no file).
- Models (monthly): naive (last value + last 12-month change), linear (36 months), damped Holt (grid-fitted), logistic with an assumed ceiling (logit-line on 36 months), direct ridge regression of the h-month change on 12-month momentum (drv_mom) and on momentum + CPI (drv_cpi) or + price + population growth (drv_all), ridge strength by forward-chaining cross-validation. Bands: 80 % from bootstrapped relative errors of each model's own pseudo-forecasts inside its training window.
- Back-test: rolling origins Dec 2021, Dec 2022, Dec 2023, horizons 12 and 24 months, PV truth runs to 2026-10-31 and EV truth to 2026-02-28, but scoring stops at Dec 2025 (Dec 2023 + 24 months): 2026 is never scored. Only 3 origins, heavily overlapping, so differences of a few tenths of a point are not statistically meaningful. The three origins also share one policy regime (EV feebate end in 2024, flat 2024-25).

## Back-test result (mean over 3 origins; error = forecast - actual, percentage points of share)

| series | h | model | MAE at h (pp) | mean error at h (pp) | MAE over months 1..h (pp) | 80 % coverage |
|---|---|---|---|---|---|---|
| EV | 12 | naive | 0.59 | +0.07 | 0.27 | 0.42 |
| EV | 12 | holt_damped | 0.63 | +0.31 | 0.35 | 0.31 |
| EV | 12 | drv_cpi | 0.79 | +0.25 | 0.35 | 0.17 |
| EV | 12 | linear36 | 0.79 | -0.58 | 0.44 | 0.64 |
| EV | 12 | logistic_K20 | 0.91 | +0.11 | 0.48 | 0.33 |
| EV | 12 | drv_mom | 0.93 | +0.46 | 0.46 | 0.03 |
| EV | 12 | logistic_K40 | 0.97 | +0.22 | 0.51 | 0.33 |
| EV | 12 | logistic_K70 | 1.00 | +0.27 | 0.53 | 0.33 |
| EV | 12 | drv_all | 1.04 | +0.49 | 0.48 | 0.03 |
| EV | 24 | linear36 | 1.24 | -0.63 | 0.72 | 0.51 |
| EV | 24 | naive | 1.24 | +0.36 | 0.56 | 0.31 |
| EV | 24 | holt_damped | 1.40 | +0.58 | 0.68 | 0.24 |
| EV | 24 | logistic_K20 | 1.70 | +0.89 | 0.85 | 0.32 |
| EV | 24 | logistic_K40 | 2.05 | +1.28 | 0.96 | 0.32 |
| EV | 24 | drv_cpi | 2.10 | +1.00 | 0.90 | 0.12 |
| EV | 24 | logistic_K70 | 2.21 | +1.46 | 1.01 | 0.33 |
| EV | 24 | drv_mom | 2.31 | +1.24 | 1.02 | 0.06 |
| EV | 24 | drv_all | 3.66 | +1.39 | 1.21 | 0.04 |
| PV | 12 | naive | 0.08 | -0.08 | 0.07 | 0.42 |
| PV | 12 | drv_mom | 0.10 | -0.10 | 0.09 | 0.36 |
| PV | 12 | logistic_K60 | 0.13 | -0.13 | 0.09 | 0.61 |
| PV | 12 | holt_damped | 0.13 | +0.02 | 0.09 | 0.31 |
| PV | 12 | logistic_K30 | 0.14 | -0.14 | 0.09 | 0.61 |
| PV | 12 | logistic_K15 | 0.15 | -0.15 | 0.10 | 0.58 |
| PV | 12 | drv_cpi | 0.17 | -0.17 | 0.10 | 0.33 |
| PV | 12 | drv_all | 0.25 | -0.25 | 0.14 | 0.33 |
| PV | 12 | linear36 | 0.27 | -0.27 | 0.16 | 0.47 |
| PV | 24 | logistic_K30 | 0.18 | -0.18 | 0.11 | 0.21 |
| PV | 24 | logistic_K60 | 0.18 | -0.16 | 0.11 | 0.22 |
| PV | 24 | naive | 0.19 | -0.19 | 0.09 | 0.56 |
| PV | 24 | logistic_K15 | 0.22 | -0.22 | 0.13 | 0.21 |
| PV | 24 | holt_damped | 0.29 | -0.10 | 0.14 | 0.54 |
| PV | 24 | linear36 | 0.47 | -0.47 | 0.25 | 0.33 |
| PV | 24 | drv_mom | 0.56 | -0.56 | 0.21 | 0.36 |
| PV | 24 | drv_cpi | 0.57 | -0.57 | 0.23 | 0.38 |
| PV | 24 | drv_all | 0.59 | -0.59 | 0.43 | 0.36 |

Mean 80 % coverage over all models: PV 0.40, EV 0.27. The nominal level is 0.80, so the bands are too narrow: the 2024-25 EV slowdown and the 2023-26 PV acceleration are bigger than the errors seen inside each training window. Treat the low/high as a lower bound on the real uncertainty.

## Scenarios (modelled forecast; low = lowest of the best model's 80 % band and the kept models, mid = best model, high = highest)

| target | scenario | PV share of houses (%) | avg new PV system (kW) | BEV per residential ICP (%) | BEV per 1,000 people | PV houses of 55 | EV houses of 55 | HC at N PV houses (kW, direct) |
|---|---|---|---|---|---|---|---|---|
| 2027-12-31 | low | 4.99 | 8.64 | 4.69 | 17.6 | 3 | 3 | >= 20 kW (sweep cap, no limit hit) |
| 2027-12-31 | mid | 5.11 | 8.96 | 5.41 | 20.4 | 3 | 3 | >= 20 kW (sweep cap, no limit hit) |
| 2027-12-31 | high | 5.60 | 10.61 | 9.45 | 35.5 | 4 | 6 | 18.5 kW |
| 2028-12-31 | low | 5.50 | 8.64 | 5.35 | 20.1 | 4 | 3 | 18.5 kW |
| 2028-12-31 | mid | 5.78 | 9.10 | 5.81 | 21.8 | 4 | 4 | 18.5 kW |
| 2028-12-31 | high | 6.71 | 11.90 | 13.39 | 50.3 | 4 | 8 | 18.5 kW |

Kept models (back-test MAE within 2x of best and usable now): PV naive, logistic_K60, logistic_K30, logistic_K15, holt_damped; EV naive, holt_damped, linear36, logistic_K20, drv_cpi, logistic_K40, logistic_K70, drv_mom.
PV forecast horizons from Oct 2026: 14 and 26 months; EV from Feb 2026: 22 and 34 months (the last is beyond the tested 24).
System size: low / mid / high are the minimum / median / maximum of three simple methods (rolling 12-month volume-weighted average held flat, damped Holt, 36-month linear) on EA 'Avg. capacity - new installations (kW)' weighted by 'ICP count - new installations'.

## Hosting-capacity link (simulated; IEEE feeder; NZ-parameterised synthetic load; ratings assumed)

Method: national share is used as the feeder penetration (assumes this 55-house feeder equals the national average, which it does not); N = ceil(share x 55), and the HC for that N is simulated directly (find_hc, results/stage9b_hc_n_direct.csv), not interpolated. HC curve = P1 placement, L2 load (seed 2022), source 1.00 pu, fresh model per point as in Stage 6. HC is per single-phase PV customer and the EA system size is a whole-house system, so the comparison is a rough 'size versus per-phase limit' reading.
HC curve: 5 % -> 20.00 kW; 10 % -> 19.59 kW; 15 % -> 15.16 kW; 20 % -> 11.06 kW; 30 % -> 9.50 kW; 45 % -> 6.33 kW; 60 % -> 5.03 kW; 80 % -> 3.80 kW; 100 % -> 2.72 kW.
Penetration at which the HC first falls below the average new system size: today's 8.64 kW -> about 34 %; Dec 2028 mid size 9.10 kW -> about 32 %.
EV: Stage 7 P1 direct counts at 7.4 kW and source 1.00 pu: typical evening 6 of 55 (10.9 %), busy evening 2 of 55 (3.6 %) (assumed ratings).

## EV cross-check against a third-party snippet (not data)
R11 records an EVDB web snippet: about 107,200 fully electric light vehicles at 31 Oct 2026. Models fitted to MoT data to Feb 2026 and run 8 months (light share of BEV stock at Feb 2026 = 0.955 from the MoT file, assumed constant; residential ICPs at Oct 2026 from the EA file, 2,031,578): naive 96,040; linear36 100,927; holt_damped 95,603. Gap to 107,200: naive -10 %; linear36 -6 %; holt_damped -11 %. A negative gap means the models miss the 2026 rebound (no fuel-price shock in the history). Labelled snippet cross-check only; the snippet is light vehicles, the models are scaled to light with a constant ratio.

## Not done / limits
- No fit to registrations or new-BEV share (flow data not in saved files). EV data stop in Feb 2026; MoT Mar-Oct 2026 need a manual download.
- Drivers are tested for forecast skill only; a driver that helps in the back-test is not a cause. Population growth is almost constant, so it can carry little signal.
- No ceiling source found; the ceilings only set the shape of the S-curve.
- Runtime 59 s. Label: modelled forecast; national data (EA, MoT, Stats NZ, MBIE), not this feeder; synthetic feeder link is 'what if'.
