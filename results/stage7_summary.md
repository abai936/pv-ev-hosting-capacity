# Stage 7 summary: EV hosting capacity

**simulated; IEEE feeder; NZ-parameterised synthetic load; ratings and VUF limit assumed. Simulated, not measured.** Source 1.00 pu, 7.4 kW single-phase EV (assumed, A18) at unity PF, constant power, at the customer's own node and phase. Limits: 207 to 253 V at customers, line ratings (assumed), transformer 800 kVA, VUF 2 % (assumed). EV HC = largest number of EVs charging at the same time with no violation; the first failing count ends it.

Placements. **P1_direct (headline)** = place_p1(k) re-picked for each k, so every count is phase-balanced (e.g. 2/2/2 at 6 EVs). **P1_nested_order** = one list built by appending the new picks of place_p1(1..55); it is an ordering artefact (only 4 of 55 counts equal place_p1(k)) and can be phase-unbalanced (see phase_mix_at_first_fail); kept as a secondary column. P2 = highest path resistance first. P3 = 50 random orderings (seeds 0 to 49).

**LE = median weekday evening, typical not design peak.** Per house, median non-EV 30-min load over weekday steps starting 19:00, 19:30, 20:00, 20:30 local (Pacific/Auckland) in Jun/Jul/Aug 2022 (264 steps = 66 weekdays x 4; public holidays count as weekdays). Total LE load 62.2 kW.

**LE_P90** = the single evening step (of the 264) whose total feeder load is closest to the 90th percentile of the step totals, each house at its own load at that step: 2022-06-24 08:00:00+00:00 UTC, total 91.0 kW.

## Main result (7.4 kW, source 1.00 pu)

Headroom columns = line1 (rating minus current) per phase 1/2/3, in A and in kW at 230 V, at the HC point and at the first failing count (negative = over the assumed rating).

| load_case | placement | EV_HC | pct_of_55 | per_phase | mix_at_first_fail | binding | line1_headroom_A_hc | line1_headroom_kW230_hc | line1_headroom_A_fail | line1_headroom_kW230_fail |
|---|---|---|---|---|---|---|---|---|---|---|
| LE | P1_direct | 6 | 10.9 | 2/2/2 | 3/2/2 | line (assumed rating) line1, linecode 4c_70, ph 1 | 26.11/33.71/57.26 | 6.01/7.75/13.17 | -7.66/34.08/57.64 | -1.76/7.84/13.26 |
| LE | P2 | 1 | 1.8 | 0/1/0 | 0/2/0 | line (assumed rating) line843, linecode 2c_.0225, ph 2 | 89.86/64.32/120.43 | 20.67/14.79/27.7 | 90.21/28.34/120.65 | 20.75/6.52/27.75 |
| LE | P1_nested_order | 4 | 7.3 | 2/1/1 | 3/1/1 | line (assumed rating) line1, linecode 4c_70, ph 1 | 25.55/66.17/89.46 | 5.88/15.22/20.57 | -9.04/66.49/89.76 | -2.08/15.29/20.64 |
| LE | P3 (P5/P50/P95 of 50) | 2/5/7 | 3.6/9.1/12.7 |  |  | line/4c_70:50 |  |  |  |  |
| LE_P90 | P1_direct | 2 | 3.6 | 1/1/0 | 1/1/1 | line (assumed rating) line1, linecode 4c_70, ph 3 | 23.54/51.98/32.73 | 5.41/11.96/7.53 | 23.96/52.37/-0.19 | 5.51/12.05/-0.04 |
| LE_P90 | P2 | 1 | 1.8 | 0/1/0 | 0/2/0 | line (assumed rating) line843, linecode 2c_.0225, ph 2 | 57.05/49.52/32.29 | 13.12/11.39/7.43 | 57.6/12.09/32.79 | 13.25/2.78/7.54 |
| LE_P90 | P1_nested_order | 2 | 3.6 | 1/1/0 | 1/1/1 | line (assumed rating) line1, linecode 4c_70, ph 3 | 23.54/51.98/32.73 | 5.41/11.96/7.53 | 23.96/52.37/-0.19 | 5.51/12.05/-0.04 |
| LE_P90 | P3 (P5/P50/P95 of 50) | 0/1/3 | 0.0/1.8/5.5 |  |  | line/4c_70:49, line/2c_16:1 |  |  |  |  |

**The EV count is a step function of the ASSUMED 195 A rating of the 4c_70 trunk (data/line_ratings.csv); a few % change moves it by whole EVs.** Rating-scale P1_direct HC: 0.8->3, 0.9->6, 1.0->6, 1.05->9, 1.1->9, 1.2->9. Voltage never binds before 30 EVs (P1_direct, LE; min customer voltage: 227.64 V at 6 EVs, 221.26 V at 15 EVs, 213.53 V at 30 EVs).

### Voltage margin (P1_direct, LE, 7.4 kW)

| n_ev | min_cust_v | voltage_violations | binding_limits |
|---|---|---|---|
| 6 | 227.64 | 0 | none |
| 15 | 221.26 | 0 | line |
| 30 | 213.53 | 0 | line |

## Source voltage (P1_direct headline)

| source_pu | EV_HC_count | pct_of_55_houses | ph1 | ph2 | ph3 | binding | line1_headroom_A_hc | line1_headroom_kW230_hc | line1_headroom_A_fail | line1_headroom_kW230_fail | nested_order_HC (secondary) | nested_mix_at_first_fail |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.98 | 6 | 10.9 | 2 | 2 | 2 | line (assumed rating) line1, linecode 4c_70, ph 1 | 22.39/30.14/54.27 | 5.15/6.93/12.48 | -12.25/30.54/54.68 | -2.82/7.02/12.58 | 4 | 3/1/1 |
| 1.0 | 6 | 10.9 | 2 | 2 | 2 | line (assumed rating) line1, linecode 4c_70, ph 1 | 26.11/33.71/57.26 | 6.01/7.75/13.17 | -7.66/34.08/57.64 | -1.76/7.84/13.26 | 4 | 3/1/1 |
| 1.025 | 6 | 10.9 | 2 | 2 | 2 | line (assumed rating) line1, linecode 4c_70, ph 1 | 30.54/37.95/60.82 | 7.02/8.73/13.99 | -2.22/38.3/61.17 | -0.51/8.81/14.07 | 4 | 3/1/1 |
| 1.05 | 9 | 16.4 | 3 | 3 | 3 | line (assumed rating) line1, linecode 4c_70, ph 1 | 3.78/10.72/33.4 | 0.87/2.46/7.68 | -29.25/11.11/33.69 | -6.73/2.56/7.75 | 9 | 4/3/3 |

## EV power (P1_direct, source 1.00 pu)

| ev_kw | EV_HC_count | pct_of_55_houses | ph1 | ph2 | ph3 | binding | line1_headroom_A_hc | line1_headroom_kW230_hc | line1_headroom_A_fail | line1_headroom_kW230_fail | nested_order_HC (secondary) | nested_mix_at_first_fail |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3.7 | 15 | 27.3 | 5 | 5 | 5 | line (assumed rating) line1, linecode 4c_70, ph 1 | 9.73/18.11/41.29 | 2.24/4.17/9.5 | -6.21/18.19/41.37 | -1.43/4.18/9.51 | 15 | 6/5/5 |
| 7.4 | 6 | 10.9 | 2 | 2 | 2 | line (assumed rating) line1, linecode 4c_70, ph 1 | 26.11/33.71/57.26 | 6.01/7.75/13.17 | -7.66/34.08/57.64 | -1.76/7.84/13.26 | 4 | 3/1/1 |

## Rating scale (P1_direct, 7.4 kW; 1.0 = main)

| rating_scale | EV_HC_count | pct_of_55_houses | ph1 | ph2 | ph3 | binding | line1_headroom_A_hc | line1_headroom_kW230_hc | line1_headroom_A_fail | line1_headroom_kW230_fail | nested_order_HC (secondary) | nested_mix_at_first_fail |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.8 | 3 | 5.5 | 1 | 1 | 1 | line (assumed rating) line1, linecode 4c_70, ph 1 | 18.81/26.96/50.26 | 4.33/6.2/11.56 | -13.66/27.13/50.43 | -3.14/6.24/11.6 | 3 | 2/1/1 |
| 0.9 | 6 | 10.9 | 2 | 2 | 2 | line (assumed rating) line1, linecode 4c_70, ph 1 | 6.61/14.21/37.76 | 1.52/3.27/8.69 | -27.16/14.58/38.14 | -6.25/3.35/8.77 | 4 | 3/1/1 |
| 1.0 | 6 | 10.9 | 2 | 2 | 2 | line (assumed rating) line1, linecode 4c_70, ph 1 | 26.11/33.71/57.26 | 6.01/7.75/13.17 | -7.66/34.08/57.64 | -1.76/7.84/13.26 | 4 | 3/1/1 |
| 1.05 | 9 | 16.4 | 3 | 3 | 3 | line (assumed rating) line1, linecode 4c_70, ph 1 | 3.11/10.35/34.45 | 0.72/2.38/7.92 | -32.13/10.83/34.81 | -7.39/2.49/8.01 | 9 | 4/3/3 |
| 1.1 | 9 | 16.4 | 3 | 3 | 3 | line (assumed rating) line1, linecode 4c_70, ph 1 | 12.86/20.1/44.2 | 2.96/4.62/10.17 | -22.38/20.58/44.56 | -5.15/4.73/10.25 | 9 | 4/3/3 |
| 1.2 | 9 | 16.4 | 3 | 3 | 3 | line (assumed rating) line1, linecode 4c_70, ph 1 | 32.36/39.6/63.7 | 7.44/9.11/14.65 | -2.88/40.08/64.06 | -0.66/9.22/14.73 | 9 | 4/3/3 |

## Diversity seed of the LE load (P1_direct, 7.4 kW)

| div_seed | EV_HC_count | pct_of_55_houses | ph1 | ph2 | ph3 | binding | line1_headroom_A_hc | line1_headroom_kW230_hc | line1_headroom_A_fail | line1_headroom_kW230_fail | nested_order_HC (secondary) | nested_mix_at_first_fail |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2022 | 6 | 10.9 | 2 | 2 | 2 | line (assumed rating) line1, linecode 4c_70, ph 1 | 26.11/33.71/57.26 | 6.01/7.75/13.17 | -7.66/34.08/57.64 | -1.76/7.84/13.26 | 4 | 3/1/1 |
| 1 | 6 | 10.9 | 2 | 2 | 2 | line (assumed rating) line1, linecode 4c_70, ph 1 | 25.7/33.55/56.31 | 5.91/7.72/12.95 | -8.14/33.91/56.69 | -1.87/7.8/13.04 | 4 | 3/1/1 |
| 2 | 6 | 10.9 | 2 | 2 | 2 | line (assumed rating) line1, linecode 4c_70, ph 1 | 23.57/34.34/56.83 | 5.42/7.9/13.07 | -10.32/34.71/57.2 | -2.37/7.98/13.16 | 4 | 3/1/1 |
| 3 | 6 | 10.9 | 2 | 2 | 2 | line (assumed rating) line1, linecode 4c_70, ph 1 | 25.16/35.48/56.89 | 5.79/8.16/13.09 | -8.73/35.85/57.27 | -2.01/8.24/13.17 | 4 | 3/1/1 |
| 4 | 6 | 10.9 | 2 | 2 | 2 | line (assumed rating) line1, linecode 4c_70, ph 1 | 22.28/35.29/52.27 | 5.12/8.12/12.02 | -11.63/35.65/52.67 | -2.68/8.2/12.11 | 4 | 3/1/1 |

## Hand check

Checks the (2R1+R0)/3 loop model; it shares path_r with the model code (independent of the OpenDSS solve only).

| customer | ev_kw | I_at_230V_A | lines_on_path | predicted_V | opendss_V | error_pct | note |
|---|---|---|---|---|---|---|---|
| load53 | 7.4 | 32.17 | 151 | 7.460249731744397 | 7.462144830866009 | 0.02540262309917782 | all other loads off, source 1.00 pu; current = P / solved customer voltage |

Runtime 45 s.

## Year with EV, no PV (Stage 7b)

**simulated; IEEE feeder; NZ-parameterised synthetic load and EV sessions; ratings and VUF limit assumed. Simulated, not measured.** 17,520 steps of 30 min, source 1.00 pu, no PV. Y0 = no EV (same as Stage 6 Y0). E30 / E60 = EV at 17 / 33 houses, P1 placement, one EV load per house driven by its column of data/processed/ev_kw.npz (7.4 kW charger, synthetic sessions, A18), unity PF. Rows with seed 1 to 4 change the house-load diversity picks only (the EV series stay the same). Line ratings are assumed, so line hours are indicative; Y0 already has line overload hours at these ratings.

| seed | case | n_ev_houses | cust_hours_below_207V | distinct_hours_below_207V | v_min_V | distinct_hours_line_above_100pct | line_hours_above_100pct_sum_over_lines | max_line_loading_pct | xfmr_max_kVA | vuf_max_pct | vuf_hours_above_2pct | n_ev_active_max_any_nonzero_half_hour | peak_coincident_ev_kw | peak_ev_equivalents | runtime_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2022 | Y0 | 0 | 0.0 | 0.0 | 208.56 | 141.5 | 4005.0 | 181.9 | 162.3 | 2.32 | 6.0 | 0 | 0.0 | 0.0 | 155.0 |
| 2022 | E30 | 17 | 0.0 | 0.0 | 208.43 | 242.5 | 6730.0 | 181.9 | 162.3 | 2.32 | 8.5 | 12 | 77.1 | 10.41 | 147.9 |
| 2022 | E60 | 33 | 0.0 | 0.0 | 208.67 | 557.5 | 16841.0 | 183.3 | 189.4 | 2.218 | 9.0 | 22 | 137.9 | 18.63 | 151.6 |
| 1 | E60 | 33 | 7.5 | 2.0 | 197.53 | 537.5 | 16329.5 | 191.7 | 188.9 | 3.232 | 11.5 | 22 | 137.9 | 18.63 | 165.2 |
| 2 | E60 | 33 | 4.0 | 1.5 | 199.78 | 571.5 | 17034.0 | 195.9 | 188.5 | 3.065 | 11.0 | 22 | 137.9 | 18.63 | 150.6 |
| 3 | E60 | 33 | 3.5 | 1.0 | 205.0 | 607.5 | 18586.0 | 203.1 | 208.1 | 2.698 | 12.5 | 22 | 137.9 | 18.63 | 145.4 |
| 4 | E60 | 33 | 1.5 | 0.5 | 202.56 | 578.0 | 17520.0 | 186.4 | 189.7 | 2.893 | 10.0 | 22 | 137.9 | 18.63 | 166.1 |

n_ev_active_max_any_nonzero_half_hour = most EVs with non-zero kW in the same half-hour (a partial step counts); peak_coincident_ev_kw = largest total EV kW in one half-hour; peak_ev_equivalents = that kW / 7.4 kW.

### EV effect = E60 minus Y0 for the same house-load seed (Y0 seeds 1 to 4 from results/stage6_year_seeds.csv, not re-run; seed 2022 Y0 from this file)

| seed | y0_v_min_V | v_min_V | delta_v_min_V | y0_cust_hours_below_207V | cust_hours_below_207V | y0_distinct_hours_below_207V | distinct_hours_below_207V | delta_distinct_hours_below_207V | y0_distinct_hours_line_above_100pct | distinct_hours_line_above_100pct | delta_distinct_hours_line_above_100pct | y0_line_hours_sum | line_hours_above_100pct_sum_over_lines |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2022 | 208.56 | 208.67 | 0.11 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 141.5 | 557.5 | 416.0 | 4005.0 | 16841.0 |
| 1 | 201.79 | 197.53 | -4.26 | 5.5 | 7.5 | 1.5 | 2.0 | 0.5 | 131.0 | 537.5 | 406.5 | 3567.5 | 16329.5 |
| 2 | 205.59 | 199.78 | -5.81 | 1.5 | 4.0 | 1.0 | 1.5 | 0.5 | 151.5 | 571.5 | 420.0 | 4324.5 | 17034.0 |
| 3 | 205.55 | 205.0 | -0.55 | 2.0 | 3.5 | 0.5 | 1.0 | 0.5 | 167.0 | 607.5 | 440.5 | 4805.0 | 18586.0 |
| 4 | 206.87 | 202.56 | -4.31 | 1.0 | 1.5 | 0.5 | 0.5 | 0.0 | 151.0 | 578.0 | 427.0 | 4249.5 | 17520.0 |

### Hours above 100 % by linecode (only linecodes with overload hours)

| seed | case | linecode | n_lines | distinct_hours_above_100pct | line_hours_sum_over_lines | max_loading_pct |
|---|---|---|---|---|---|---|
| 2022 | Y0 | 2c_.0225 | 18 | 5.0 | 31.0 | 128.5 |
| 2022 | Y0 | 2c_16 | 482 | 12.5 | 104.5 | 181.9 |
| 2022 | Y0 | 4c_.1 | 102 | 1.0 | 22.0 | 102.4 |
| 2022 | Y0 | 4c_70 | 46 | 135.5 | 3847.5 | 155.4 |
| 2022 | E30 | 2c_.0225 | 18 | 7.0 | 44.0 | 128.5 |
| 2022 | E30 | 2c_16 | 482 | 17.0 | 159.0 | 181.9 |
| 2022 | E30 | 4c_.1 | 102 | 1.5 | 31.0 | 102.8 |
| 2022 | E30 | 4c_70 | 46 | 235.0 | 6496.0 | 157.3 |
| 2022 | E60 | 2c_.0225 | 18 | 7.0 | 43.0 | 134.2 |
| 2022 | E60 | 2c_16 | 482 | 21.0 | 206.5 | 183.3 |
| 2022 | E60 | 4c_.1 | 102 | 3.5 | 66.0 | 104.5 |
| 2022 | E60 | 4c_70 | 46 | 546.5 | 16525.5 | 177.3 |
| 1 | E60 | 2c_.0225 | 18 | 7.5 | 43.0 | 134.9 |
| 1 | E60 | 2c_16 | 482 | 17.0 | 185.5 | 174.9 |
| 1 | E60 | 4c_.06 | 144 | 0.5 | 2.0 | 120.1 |
| 1 | E60 | 4c_.1 | 102 | 5.5 | 114.0 | 139.2 |
| 1 | E60 | 4c_70 | 46 | 527.0 | 15985.0 | 191.7 |
| 2 | E60 | 2c_.0225 | 18 | 7.0 | 35.0 | 143.6 |
| 2 | E60 | 2c_16 | 482 | 12.0 | 129.0 | 131.4 |
| 2 | E60 | 4c_.1 | 102 | 5.0 | 99.0 | 127.2 |
| 2 | E60 | 4c_70 | 46 | 560.5 | 16771.0 | 195.9 |
| 3 | E60 | 2c_.0225 | 18 | 5.0 | 24.5 | 140.7 |
| 3 | E60 | 2c_16 | 482 | 24.0 | 327.5 | 148.5 |
| 3 | E60 | 4c_.06 | 144 | 0.5 | 2.0 | 106.2 |
| 3 | E60 | 4c_.1 | 102 | 6.5 | 133.0 | 130.5 |
| 3 | E60 | 4c_70 | 46 | 600.5 | 18099.0 | 203.1 |
| 4 | E60 | 2c_.0225 | 18 | 6.0 | 30.0 | 140.8 |
| 4 | E60 | 2c_16 | 482 | 18.5 | 215.0 | 149.0 |
| 4 | E60 | 4c_.1 | 102 | 5.0 | 99.0 | 117.7 |
| 4 | E60 | 4c_70 | 46 | 571.5 | 17176.0 | 186.4 |

### Energy balance (kWh): house load + EV + losses = energy into the transformer HV terminal

| seed | case | E_load_kWh_dss | E_ev_kWh_dss | E_ev_kWh_profile | E_loss_kWh | E_xfmr_in_kWh | balance_error_pct_of_xfmr |
|---|---|---|---|---|---|---|---|
| 2022 | Y0 | 387638.6 | 0.0 | 0.0 | 8093.5 | 395731.9 | 6e-05 |
| 2022 | E30 | 387638.7 | 49243.2 | 49243.6 | 10294.5 | 447176.0 | 7e-05 |
| 2022 | E60 | 387638.7 | 94551.2 | 94551.8 | 12715.8 | 494905.2 | 9e-05 |
| 1 | E60 | 387638.6 | 94551.2 | 94551.8 | 12726.3 | 494915.5 | 0.00011 |
| 2 | E60 | 387638.7 | 94551.2 | 94551.8 | 12754.9 | 494944.3 | 0.00011 |
| 3 | E60 | 387638.7 | 94551.2 | 94551.8 | 12825.4 | 495014.6 | 0.00014 |
| 4 | E60 | 387638.8 | 94551.2 | 94551.8 | 12715.1 | 494904.4 | 0.00013 |
