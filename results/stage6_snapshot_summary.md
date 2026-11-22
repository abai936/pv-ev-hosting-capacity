# Stage 6 summary: NZ headline snapshot PV hosting capacity (L2)

**simulated; IEEE feeder; NZ-parameterised synthetic load; ratings assumed. Simulated, not measured.** Source 1.00 pu, PV single-phase at unity PF, no inverter control. HC = kW per PV customer (= kW per phase), 1 decimal (bisection step 0.01 kW). Penetration N = ceil(pen x 55) = 17, 33, 55. Orion cap = min(HC, 10). HC_V = HC ignoring line ratings. Thermal limits (lines, transformer 800 kVA nameplate) use **assumed ratings** (data/line_ratings.csv, R10).

L2 = per house, the median of its 30-minute load over steps starting 12:00 and 12:30 NZDT on weekdays of Dec, Jan and Feb 2022 (126 steps = 63 weekdays x 2). L2b = the same from the appliances-only shape (sensitivity, no heating). L1 = Stage 4 (one random minute of non-NZ profiles).

## Per-phase load totals (kW, 55 customers)

| case | phase_1 | phase_2 | phase_3 | total |
|---|---|---|---|---|
| L1 | 12.81 | 9.75 | 7.18 | 29.75 |
| L2 | 8.62 | 8.83 | 6.72 | 24.17 |
| L2b | 8.58 | 8.79 | 6.69 | 24.06 |

Each house picks one of the feeder's 100 daily profiles at random per local day (diversity seed 2022 here; other seeds below). More midday load on a phase means more headroom for PV on that phase.

## P1 (balanced) and P2 (end-clustered), L2 next to L1 (Stage 4)

| placement | penetration | n_pv | source | HC | Orion_capped | HC_V | binding |
|---|---|---|---|---|---|---|---|
| P1 | 0.3 | 17 | L1 | 9.7 | 9.7 | 9.9 | line (assumed rating): linecode 4c_70, phase 2, nearest line line1, chain of 21 lines |
| P1 | 0.3 | 17 | L2 | 9.5 | 9.5 | 9.6 | line (assumed rating): linecode 4c_70, phase 1, nearest line line1, chain of 19 lines |
| P2 | 0.3 | 17 | L1 | 5.6 | 5.6 | 5.6 | voltage-high load53@899.2 |
| P2 | 0.3 | 17 | L2 | 5.4 | 5.4 | 5.4 | voltage-high load53@899.2 |
| P1 | 0.6 | 33 | L1 | 5.1 | 5.1 | 5.7 | line (assumed rating): linecode 4c_70, phase 3, nearest line line1, chain of 35 lines |
| P1 | 0.6 | 33 | L2 | 5.0 | 5.0 | 6.0 | line (assumed rating): linecode 4c_70, phase 3, nearest line line1, chain of 35 lines |
| P2 | 0.6 | 33 | L1 | 4.4 | 4.4 | 4.4 | voltage-high load55@906.1 |
| P2 | 0.6 | 33 | L2 | 4.0 | 4.0 | 4.0 | voltage-high load29@562.1 |
| P1 | 1.0 | 55 | L1 | 2.9 | 2.9 | 3.2 | line (assumed rating): linecode 4c_70, phase 1, nearest line line1, chain of 19 lines |
| P1 | 1.0 | 55 | L2 | 2.7 | 2.7 | 3.0 | line (assumed rating): linecode 4c_70, phase 1, nearest line line1, chain of 19 lines |
| P2 | 1.0 | 55 | L1 | 2.9 | 2.9 | 3.2 | line (assumed rating): linecode 4c_70, phase 1, nearest line line1, chain of 19 lines |
| P2 | 1.0 | 55 | L2 | 2.7 | 2.7 | 3.0 | line (assumed rating): linecode 4c_70, phase 1, nearest line line1, chain of 19 lines |

## P3 random placement (50 seeds, 0 to 49), L2

| load_case | penetration | P1_HC | P2_HC | P3_P5 | P3_P50 | P3_P95 | P2_below_P3_P5 | binding (assumed rating if line/transformer) |
|---|---|---|---|---|---|---|---|---|
| L2 | 0.3 | 9.5 | 5.4 | 4.5 | 6.0 | 8.4 | no | voltage-high:45, line/4c_70/ph1:3, line/4c_70/ph2:2 |
| L2 | 0.6 | 5.0 | 4.0 | 3.1 | 3.9 | 4.7 | no | voltage-high:36, line/4c_70/ph1:10, line/4c_70/ph2:2, line/4c_70/ph3:2 |
| L2 | 1.0 | 2.7 | 2.7 | 2.7 | 2.7 | 2.7 | no | line/4c_70/ph1:50 |

## Source-voltage sweep (P1, L2, 60 %)

| source_pu | HC | HC_voltage_only | binding |
|---|---|---|---|
| 0.98 | 5.0 | 7.8 | line (assumed rating): linecode 4c_70, phase 3, nearest line line1, chain of 35 lines |
| 1.0 | 5.0 | 6.0 | line (assumed rating): linecode 4c_70, phase 3, nearest line line1, chain of 35 lines |
| 1.025 | 3.5 | 3.5 | voltage-high load42@778.3 |
| 1.05 | 0.9 | 0.9 | voltage-high load33@619.3 |

## House-diversity seed sweep (P1, L2)

Same feeder, same P1 placement; only the per-day profile picks change with the seed. min / median / max over the 5 seeds (2022, 1, 2, 3, 4).

| penetration | HC_min | HC_median | HC_max | HC_per_seed | binding |
|---|---|---|---|---|---|
| 0.3 | 9.5 | 9.5 | 9.6 | 9.5, 9.5, 9.6, 9.5, 9.6 | seed 2022: line (assumed rating): linecode 4c_70, phase 1, nearest line line1, chain of 19 lines; seed 1: line (assumed rating): linecode 4c_70, phase 2, nearest line line1, chain of 21 lines; seed 2: line (assumed rating): linecode 4c_70, phase 2, nearest line line1, chain of 21 lines; seed 3: line (assumed rating): linecode 4c_70, phase 2, nearest line line1, chain of 21 lines; seed 4: line (assumed rating): linecode 4c_70, phase 2, nearest line line1, chain of 21 lines |
| 0.6 | 5.0 | 5.0 | 5.0 | 5.0, 5.0, 5.0, 5.0, 5.0 | seed 2022: line (assumed rating): linecode 4c_70, phase 3, nearest line line1, chain of 35 lines; seed 1: line (assumed rating): linecode 4c_70, phase 3, nearest line line1, chain of 35 lines; seed 2: line (assumed rating): linecode 4c_70, phase 3, nearest line line1, chain of 35 lines; seed 3: line (assumed rating): linecode 4c_70, phase 3, nearest line line1, chain of 35 lines; seed 4: line (assumed rating): linecode 4c_70, phase 3, nearest line line1, chain of 35 lines |
| 1.0 | 2.7 | 2.8 | 2.8 | 2.7, 2.8, 2.8, 2.8, 2.7 | seed 2022: line (assumed rating): linecode 4c_70, phase 1, nearest line line1, chain of 19 lines; seed 1: line (assumed rating): linecode 4c_70, phase 1, nearest line line1, chain of 19 lines; seed 2: line (assumed rating): linecode 4c_70, phase 1, nearest line line1, chain of 19 lines; seed 3: line (assumed rating): linecode 4c_70, phase 1, nearest line line1, chain of 19 lines; seed 4: line (assumed rating): linecode 4c_70, phase 1, nearest line line1, chain of 19 lines |

## L2b (no electric heating or hot water, appliances-only shape, same scale factor as L2) next to L2, P1

| load_case | penetration | n_pv | HC | HC_voltage_only | binding |
|---|---|---|---|---|---|
| L2 | 0.3 | 17 | 9.5 | 9.6 | line (assumed rating): linecode 4c_70, phase 1, nearest line line1, chain of 19 lines |
| L2b | 0.3 | 17 | 9.5 | 9.6 | line (assumed rating): linecode 4c_70, phase 1, nearest line line1, chain of 19 lines |
| L2 | 0.6 | 33 | 5.0 | 6.0 | line (assumed rating): linecode 4c_70, phase 3, nearest line line1, chain of 35 lines |
| L2b | 0.6 | 33 | 5.0 | 6.0 | line (assumed rating): linecode 4c_70, phase 3, nearest line line1, chain of 35 lines |
| L2 | 1.0 | 55 | 2.7 | 3.0 | line (assumed rating): linecode 4c_70, phase 1, nearest line line1, chain of 19 lines |
| L2b | 1.0 | 55 | 2.7 | 3.0 | line (assumed rating): linecode 4c_70, phase 1, nearest line line1, chain of 19 lines |

## Limits seen

- Max VUF at the HC points of the main grid: 1.07 % (limit 2 %, assumed, EN 50160 basis).
- Transformer max kVA at the HC points of the main grid: 137.2 kVA (800 kVA nameplate, assumed).

Runtime 162 s.

## Year time series 2022 (Stage 6b)

**simulated; IEEE feeder; NZ-parameterised synthetic load; PV modelled; ratings assumed. Simulated, not measured.** 17,520 steps of 30 min, source 1.00 pu, mode=yearly, one Solve per step, house diversity seed 2022 (each house picks one of 100 feeder profiles per local day). Loads: per-house kW series as OpenDSS yearly LoadShapes. Y1 to Y3: P1 placement at 60% (33 houses), unity PF, no inverter control, no EV, PV = kWp x PVGIS-ERA5 kW-per-kWp series (Generator objects). Customer-hours count each customer separately (x 0.5 h per step); distinct hours count a step once. `line_hours_above_100pct_sum_over_lines` is the sum over lines (each overloaded line counted separately); `distinct_hours_line_above_100pct` counts a step once if any line is above 100%. Ratings are assumed. The 30-min averages hide short peaks. Run time per case is in the table (runtime_s, ms_per_step), measured on this laptop.

| case | pv_kwp_per_house | cust_hours_above_253V | distinct_hours_above_253V | cust_hours_below_207V | v_min_V | v_max_V | line_hours_above_100pct_sum_over_lines | distinct_hours_line_above_100pct | max_line_loading_pct | xfmr_max_kVA | reverse_flow_hours | vuf_max_pct | vuf_hours_above_2pct | runtime_s | ms_per_step |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Y0 | 0.0 | 0.0 | 0.0 | 0.0 | 208.56 | 245.2 | 4005.0 | 141.5 | 181.9 | 162.3 | 0.0 | 2.32 | 6.0 | 177.2 | 10.11 |
| Y1 | 3.0 | 0.0 | 0.0 | 0.0 | 210.45 | 250.08 | 1399.5 | 58.5 | 177.8 | 154.9 | 969.0 | 2.231 | 3.0 | 200.8 | 11.46 |
| Y2 | 5.0 | 4.5 | 1.0 | 0.0 | 210.45 | 253.77 | 1100.5 | 46.0 | 175.1 | 154.9 | 1985.5 | 2.175 | 2.0 | 250.2 | 14.28 |
| Y3 | 8.0 | 1330.0 | 207.5 | 0.0 | 210.45 | 259.16 | 11042.5 | 326.5 | 171.1 | 195.1 | 2648.0 | 2.096 | 1.0 | 164.1 | 9.37 |

### Hours above 100 % by linecode (assumed ratings; only linecodes with overload hours)

| seed | case | linecode | n_lines | distinct_hours_above_100pct | line_hours_sum_over_lines | max_loading_pct |
|---|---|---|---|---|---|---|
| 2022 | Y0 | 2c_.0225 | 18 | 5.0 | 31.0 | 128.5 |
| 2022 | Y0 | 2c_16 | 482 | 12.5 | 104.5 | 181.9 |
| 2022 | Y0 | 4c_.1 | 102 | 1.0 | 22.0 | 102.4 |
| 2022 | Y0 | 4c_70 | 46 | 135.5 | 3847.5 | 155.4 |
| 2022 | Y1 | 2c_.0225 | 18 | 3.5 | 20.5 | 117.3 |
| 2022 | Y1 | 2c_16 | 482 | 10.5 | 85.5 | 177.8 |
| 2022 | Y1 | 4c_70 | 46 | 48.0 | 1293.5 | 140.2 |
| 2022 | Y2 | 2c_.0225 | 18 | 3.5 | 20.5 | 116.3 |
| 2022 | Y2 | 2c_16 | 482 | 6.5 | 59.0 | 175.1 |
| 2022 | Y2 | 4c_70 | 46 | 38.0 | 1021.0 | 137.8 |
| 2022 | Y3 | 2c_.0225 | 18 | 3.0 | 18.0 | 116.3 |
| 2022 | Y3 | 2c_16 | 482 | 5.5 | 48.5 | 171.1 |
| 2022 | Y3 | 4c_70 | 46 | 319.0 | 10976.0 | 140.9 |

### Energy balance (kWh): load + losses - PV = energy into the transformer HV terminal

| case | E_load_kWh_dss | E_loss_kWh | E_pv_kWh_dss | E_xfmr_in_kWh | balance_error_pct_of_xfmr | E_pv_kWh_register | E_pv_kWh_profile |
|---|---|---|---|---|---|---|---|
| Y0 | 387638.6 | 8093.5 | 0.0 | 395731.9 | 0.0001 | 0.0 | 0.0 |
| Y1 | 387639.1 | 5850.7 | 136641.2 | 256848.9 | -0.0001 | 136641.2 | 136641.2 |
| Y2 | 387639.7 | 6299.4 | 227735.3 | 166203.6 | 0.0001 | 227735.3 | 227735.3 |
| Y3 | 387640.1 | 9662.4 | 364376.5 | 32926.1 | -0.0002 | 364376.5 | 364376.5 |

### Y0 (no PV) across house-diversity seeds

| seed | max_line_loading_pct | distinct_hours_line_above_100pct | line_hours_above_100pct_sum_over_lines | xfmr_max_kVA | distinct_hours_below_207V | v_min_V | vuf_max_pct | vuf_hours_above_2pct |
|---|---|---|---|---|---|---|---|---|
| 1 | 174.9 | 131.0 | 3567.5 | 148.6 | 1.5 | 201.79 | 2.933 | 6.5 |
| 2 | 166.7 | 151.5 | 4324.5 | 148.7 | 1.0 | 205.59 | 2.515 | 6.0 |
| 3 | 198.4 | 167.0 | 4805.0 | 173.4 | 0.5 | 205.55 | 2.698 | 4.5 |
| 4 | 179.1 | 151.0 | 4249.5 | 170.4 | 0.5 | 206.87 | 2.514 | 3.0 |
| 2022 | 181.9 | 141.5 | 4005.0 | 162.3 | 0.0 | 208.56 | 2.32 | 6.0 |
