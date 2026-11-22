# Stage 8 summary: mitigation (inverter control, transformer tap)

## HEADLINE (simulated; synthetic NZ-parameterised load; ratings assumed; numbers from the CSVs in results/)

1. Australia A inverter control (M3) cuts the year's customer-hours above 253 V from 1330.0 to 38.5 (tap 1.000, case Y3, 8 kWp on 60 % of houses); with tap 0.975 as well it is 0.0 (stage8_year.csv).
2. It does NOT raise the snapshot hosting capacity for balanced placement P1: M0 9.5 / 5.0 / 2.7 kW vs M3 9.3 / 4.9 / 2.7 kW at 30 / 60 / 100 %, because the ASSUMED 4c_70 trunk line rating binds and vars add current (stage8_hc.csv).
3. The cost is thermal: distinct hours with any line above 100 % of its assumed rating go from 326.5 (M0) to 582.5 (M3), and transformer peak from 195.1 to 216.6 kVA.
4. Volt-watt alone (M1) barely helps: 1302.0 customer-hours above 253 V, 48.3 kWh curtailed (volt-watt only starts cutting P above about 254 V at peak sun).
5. A 2.5 % lower tap (0.975) helps the voltage-limited end-clustered placement P2: M0 HC 5.4 to 7.5 kW (30 %) and 4.0 to 4.6 kW (60 %).
6. The tap costs EV evening voltage margin: minimum customer voltage with no EV 233.25 V to 227.08 V, with 30 EVs 213.53 V to 206.74 V (below 207 V, 1 low-voltage violation; stage8_ev_tap.csv).

**simulated; IEEE feeder; NZ-parameterised synthetic load; modelled inverter control; ratings assumed. Simulated, not measured.** Source 1.00 pu, L2 load (summer weekday midday median, diversity seed 2022). Single-phase PV on the customer's own phase. Modes: M0 unity PF no control, M1 volt-watt only, M2 volt-var only, M3 Australia A volt-var + volt-watt (curves in pu of 230 V, y-axes in fraction of S_rated). Inverter kVA = PV kW rating (kva_ratio 1.0, no spare kVA, var priority) unless stated. Tap 0.975 = TR1 secondary lowered 2.5 % (no-load LV 240.18 V x tap = 234.2 V). HC = largest PV kW per customer (sweep 1 to 20 kW then bisection 0.01 kW; quoted here to 0.1 kW because the inverter control only settles to its tolerance; the CSV keeps 0.01 kW) with no violation after the control has settled (207 to 253 V at customers, line ratings and 800 kVA transformer assumed, VUF 2 % assumed). Orion-capped = min(HC, 10 kW). Curtailed % = 1 - P_dispatched / P_available at the HC point (P_available = n_pv x HC). 'cap' means no violation up to 20 kW.

Reading note: Australia A volt-watt starts curtailing at 1.10 pu = 253.0 V, which is the NZ upper limit, so the steady state under curtailment sits at or above 253 V. Volt-watt alone therefore cannot lift the 253 V limit; its effect shows in curtailed %, not in HC. This is a property of the setting, not a model fault.

Snapshot inverter size: the PV rating swept is the full-sun output, and kVA = kW, so there is no spare kVA. OpenDSS then gives the vars priority (WattPriority=No, the OpenDSS default) and cuts P to make room. Var priority is the OpenDSS default and is an ASSUMPTION: no source says Australia A requires it. That is why M2/M3 show curtailed % even below 253 V. In the year runs kVA = kWp, but the PV profile peaks at 0.8915 kW per kWp (data/processed/avg_house_and_pv_30min.csv), so the spare kVA at peak is sqrt(1 - 0.8915^2) = 0.45 S, which is less than the 0.6 S volt-var maximum: 'there is spare kVA' is only partly true. Volt-watt on the S_rated basis only cuts output above about 254 V at peak sun (the curve reaches 0.8915 S at 1.1041 pu), which is why M1 curtails little and does not lower the over-253 V hours.

Settling: after each solve the control is solved again until two successive solves agree to 0.02 V and 0.2 % of P, starting every point from a fixed cold state (src/hc/mitigation.py, cold_start). Result file stage8_hc.csv: 1272 rows, 0 nonconverged; HC run time 494 s (results/stage8_hc_run.log).

## P1 (balanced)

| penetration | mode | tap | HC_kW | Orion_capped | HC_voltage_only | curtailed_pct_at_HC | curtailed_pct_at_HC_V_only | binding |
|---|---|---|---|---|---|---|---|---|
| 0.3 | M0 | 0.975 | 9.3 | 9.3 | 13.4 | 0.00 | 0.00 | line (assumed) 4c_70 ph1 |
| 0.3 | M0 | 1.0 | 9.5 | 9.5 | 9.6 | 0.00 | 0.00 | line (assumed) 4c_70 ph1 |
| 0.3 | M1 | 0.975 | 9.3 | 9.3 | 13.4 | 0.00 | 0.00 | line (assumed) 4c_70 ph1 |
| 0.3 | M1 | 1.0 | 9.5 | 9.5 | 9.6 | 0.00 | 0.00 | line (assumed) 4c_70 ph1 |
| 0.3 | M2 | 0.975 | 9.2 | 9.2 | 17.3 | 0.56 | 4.55 | line (assumed) 4c_70 ph1 |
| 0.3 | M2 | 1.0 | 9.3 | 9.3 | 12.6 | 3.25 | 5.53 | line (assumed) 4c_70 ph1 |
| 0.3 | M3 | 0.975 | 9.3 | 9.3 | 17.3 | 0.46 | 4.43 | line (assumed) 4c_70 ph1 |
| 0.3 | M3 | 1.0 | 9.3 | 9.3 | 12.5 | 2.95 | 5.32 | line (assumed) 4c_70 ph1 |
| 0.6 | M0 | 0.975 | 4.9 | 4.9 | 8.3 | 0.00 | 0.00 | line (assumed) 4c_70 ph3 |
| 0.6 | M0 | 1.0 | 5.0 | 5.0 | 6.0 | 0.00 | 0.00 | line (assumed) 4c_70 ph3 |
| 0.6 | M1 | 0.975 | 4.9 | 4.9 | 8.3 | 0.00 | 0.00 | line (assumed) 4c_70 ph3 |
| 0.6 | M1 | 1.0 | 5.0 | 5.0 | 6.0 | 0.00 | 0.00 | line (assumed) 4c_70 ph3 |
| 0.6 | M2 | 0.975 | 4.9 | 4.9 | 10.3 | 0.45 | 5.41 | line (assumed) 4c_70 ph3 |
| 0.6 | M2 | 1.0 | 4.9 | 4.9 | 7.5 | 3.06 | 6.43 | line (assumed) 4c_70 ph3 |
| 0.6 | M3 | 0.975 | 4.9 | 4.9 | 10.2 | 0.45 | 5.21 | line (assumed) 4c_70 ph3 |
| 0.6 | M3 | 1.0 | 4.9 | 4.9 | 7.5 | 2.76 | 6.13 | line (assumed) 4c_70 ph3 |
| 1.0 | M0 | 0.975 | 2.7 | 2.7 | 4.1 | 0.00 | 0.00 | line (assumed) 4c_70 ph1 |
| 1.0 | M0 | 1.0 | 2.7 | 2.7 | 2.9 | 0.00 | 0.00 | line (assumed) 4c_70 ph1 |
| 1.0 | M1 | 0.975 | 2.7 | 2.7 | 4.1 | 0.00 | 0.00 | line (assumed) 4c_70 ph1 |
| 1.0 | M1 | 1.0 | 2.7 | 2.7 | 2.9 | 0.00 | 0.00 | line (assumed) 4c_70 ph1 |
| 1.0 | M2 | 0.975 | 2.6 | 2.6 | 5.0 | 0.36 | 3.46 | line (assumed) 4c_70 ph1 |
| 1.0 | M2 | 1.0 | 2.7 | 2.7 | 3.6 | 2.53 | 4.47 | line (assumed) 4c_70 ph1 |
| 1.0 | M3 | 0.975 | 2.6 | 2.6 | 5.0 | 0.45 | 3.38 | line (assumed) 4c_70 ph1 |
| 1.0 | M3 | 1.0 | 2.7 | 2.7 | 3.6 | 2.45 | 4.27 | line (assumed) 4c_70 ph1 |

## P2 (end-clustered)

| penetration | mode | tap | HC_kW | Orion_capped | HC_voltage_only | curtailed_pct_at_HC | curtailed_pct_at_HC_V_only | binding |
|---|---|---|---|---|---|---|---|---|
| 0.3 | M0 | 0.975 | 7.5 | 7.5 | 7.5 | 0.00 | 0.00 | voltage-high load53@899.2 |
| 0.3 | M0 | 1.0 | 5.4 | 5.4 | 5.4 | 0.00 | 0.00 | voltage-high load53@899.2 |
| 0.3 | M1 | 0.975 | 7.5 | 7.5 | 7.5 | 0.00 | 0.00 | voltage-high load53@899.2 |
| 0.3 | M1 | 1.0 | 5.4 | 5.4 | 5.4 | 0.00 | 0.00 | voltage-high load53@899.2 |
| 0.3 | M2 | 0.975 | 7.7 | 7.7 | 8.6 | 3.74 | 4.83 | line (assumed) 4c_70 ph2 |
| 0.3 | M2 | 1.0 | 6.1 | 6.1 | 6.1 | 5.47 | 5.47 | voltage-high load29@562.1 |
| 0.3 | M3 | 0.975 | 7.7 | 7.7 | 8.5 | 3.76 | 4.82 | line (assumed) 4c_70 ph2 |
| 0.3 | M3 | 1.0 | 6.1 | 6.1 | 6.1 | 5.42 | 5.42 | voltage-high load29@562.1 |
| 0.6 | M0 | 0.975 | 4.6 | 4.6 | 5.7 | 0.00 | 0.00 | line (assumed) 4c_70 ph1 |
| 0.6 | M0 | 1.0 | 4.0 | 4.0 | 4.0 | 0.00 | 0.00 | voltage-high load29@562.1 |
| 0.6 | M1 | 0.975 | 4.6 | 4.6 | 5.7 | 0.00 | 0.00 | line (assumed) 4c_70 ph1 |
| 0.6 | M1 | 1.0 | 4.0 | 4.0 | 4.0 | 0.00 | 0.00 | voltage-high load29@562.1 |
| 0.6 | M2 | 0.975 | 4.5 | 4.5 | 7.2 | 1.34 | 5.33 | line (assumed) 4c_70 ph1 |
| 0.6 | M2 | 1.0 | 4.5 | 4.5 | 5.1 | 4.89 | 6.10 | line (assumed) 4c_70 ph1 |
| 0.6 | M3 | 0.975 | 4.5 | 4.5 | 7.2 | 1.31 | 5.23 | line (assumed) 4c_70 ph1 |
| 0.6 | M3 | 1.0 | 4.5 | 4.5 | 5.1 | 4.62 | 5.89 | line (assumed) 4c_70 ph1 |
| 1.0 | M0 | 0.975 | 2.7 | 2.7 | 4.1 | 0.00 | 0.00 | line (assumed) 4c_70 ph1 |
| 1.0 | M0 | 1.0 | 2.7 | 2.7 | 2.9 | 0.00 | 0.00 | line (assumed) 4c_70 ph1 |
| 1.0 | M1 | 0.975 | 2.7 | 2.7 | 4.1 | 0.00 | 0.00 | line (assumed) 4c_70 ph1 |
| 1.0 | M1 | 1.0 | 2.7 | 2.7 | 2.9 | 0.00 | 0.00 | line (assumed) 4c_70 ph1 |
| 1.0 | M2 | 0.975 | 2.6 | 2.6 | 5.0 | 0.36 | 3.46 | line (assumed) 4c_70 ph1 |
| 1.0 | M2 | 1.0 | 2.7 | 2.7 | 3.6 | 2.53 | 4.47 | line (assumed) 4c_70 ph1 |
| 1.0 | M3 | 0.975 | 2.6 | 2.6 | 5.0 | 0.45 | 3.38 | line (assumed) 4c_70 ph1 |
| 1.0 | M3 | 1.0 | 2.7 | 2.7 | 3.6 | 2.45 | 4.27 | line (assumed) 4c_70 ph1 |

## P3 random placement (50 seeds): HC percentiles (kW) and median curtailed %

| penetration | mode | tap | P5 | P50 | P95 | median_curtailed_pct | nonconverged | binding |
|---|---|---|---|---|---|---|---|---|
| 0.3 | M0 | 0.975 | 5.7 | 7.7 | 9.1 | 0.00 | 0 | line:45, voltage-high:5 |
| 0.3 | M0 | 1.0 | 4.5 | 6.1 | 8.4 | 0.00 | 0 | voltage-high:45, line:5 |
| 0.3 | M1 | 0.975 | 5.7 | 7.7 | 9.1 | 0.00 | 0 | line:45, voltage-high:5 |
| 0.3 | M1 | 1.0 | 4.5 | 6.1 | 8.4 | 0.00 | 0 | voltage-high:45, line:5 |
| 0.3 | M2 | 0.975 | 5.6 | 7.8 | 9.0 | 1.14 | 0 | line:50 |
| 0.3 | M2 | 1.0 | 5.5 | 7.1 | 9.0 | 3.46 | 0 | line:33, voltage-high:17 |
| 0.3 | M3 | 0.975 | 5.6 | 7.8 | 9.0 | 1.05 | 0 | line:50 |
| 0.3 | M3 | 1.0 | 5.4 | 7.1 | 9.0 | 3.31 | 0 | line:32, voltage-high:18 |
| 0.6 | M0 | 0.975 | 3.6 | 4.0 | 4.6 | 0.00 | 0 | line:50 |
| 0.6 | M0 | 1.0 | 3.1 | 3.9 | 4.7 | 0.00 | 0 | voltage-high:36, line:14 |
| 0.6 | M1 | 0.975 | 3.6 | 4.0 | 4.6 | 0.00 | 0 | line:50 |
| 0.6 | M1 | 1.0 | 3.1 | 3.9 | 4.7 | 0.00 | 0 | voltage-high:36, line:14 |
| 0.6 | M2 | 0.975 | 3.6 | 4.0 | 4.6 | 0.63 | 0 | line:50 |
| 0.6 | M2 | 1.0 | 3.6 | 4.0 | 4.7 | 2.91 | 0 | line:50 |
| 0.6 | M3 | 0.975 | 3.6 | 4.0 | 4.6 | 0.61 | 0 | line:50 |
| 0.6 | M3 | 1.0 | 3.6 | 4.0 | 4.7 | 2.79 | 0 | line:50 |
| 1.0 | M0 | 0.975 | 2.7 | 2.7 | 2.7 | 0.00 | 0 | line:50 |
| 1.0 | M0 | 1.0 | 2.7 | 2.7 | 2.7 | 0.00 | 0 | line:50 |
| 1.0 | M1 | 0.975 | 2.7 | 2.7 | 2.7 | 0.00 | 0 | line:50 |
| 1.0 | M1 | 1.0 | 2.7 | 2.7 | 2.7 | 0.00 | 0 | line:50 |
| 1.0 | M2 | 0.975 | 2.6 | 2.6 | 2.6 | 0.36 | 0 | line:50 |
| 1.0 | M2 | 1.0 | 2.7 | 2.7 | 2.7 | 2.53 | 0 | line:50 |
| 1.0 | M3 | 0.975 | 2.6 | 2.6 | 2.6 | 0.45 | 0 | line:50 |
| 1.0 | M3 | 1.0 | 2.7 | 2.7 | 2.7 | 2.45 | 0 | line:50 |

## Sensitivity: inverter kVA = 1.1 x kW (P1, P2; compare with the kva_ratio 1.0 rows above)

| placement | penetration | mode | tap | HC_kW | curtailed_pct_at_HC | binding |
|---|---|---|---|---|---|---|
| P1 | 0.3 | M2 | 1.0 | 9.0 | 0.00 | line (assumed) 4c_70 ph1 |
| P2 | 0.3 | M2 | 1.0 | 5.5 | 0.12 | voltage-high |
| P1 | 0.6 | M2 | 1.0 | 4.7 | 0.00 | line (assumed) 4c_70 ph3 |
| P2 | 0.6 | M2 | 1.0 | 4.2 | 0.00 | line (assumed) 4c_70 ph1 |
| P1 | 1.0 | M2 | 1.0 | 2.5 | 0.00 | line (assumed) 4c_70 ph1 |
| P2 | 1.0 | M2 | 1.0 | 2.5 | 0.00 | line (assumed) 4c_70 ph1 |
| P1 | 0.3 | M2 | 0.975 | 9.2 | 0.00 | line (assumed) 4c_70 ph1 |
| P2 | 0.3 | M2 | 0.975 | 7.2 | 0.00 | line (assumed) 4c_70 ph1 |
| P1 | 0.6 | M2 | 0.975 | 4.9 | 0.00 | line (assumed) 4c_70 ph3 |
| P2 | 0.6 | M2 | 0.975 | 4.3 | 0.00 | line (assumed) 4c_70 ph1 |
| P1 | 1.0 | M2 | 0.975 | 2.6 | 0.00 | line (assumed) 4c_70 ph1 |
| P2 | 1.0 | M2 | 0.975 | 2.6 | 0.00 | line (assumed) 4c_70 ph1 |
| P1 | 0.3 | M3 | 1.0 | 9.0 | 0.00 | line (assumed) 4c_70 ph1 |
| P2 | 0.3 | M3 | 1.0 | 5.4 | 0.00 | voltage-high |
| P1 | 0.6 | M3 | 1.0 | 4.7 | 0.00 | line (assumed) 4c_70 ph3 |
| P2 | 0.6 | M3 | 1.0 | 4.2 | 0.00 | line (assumed) 4c_70 ph1 |
| P1 | 1.0 | M3 | 1.0 | 2.5 | 0.00 | line (assumed) 4c_70 ph1 |
| P2 | 1.0 | M3 | 1.0 | 2.5 | 0.00 | line (assumed) 4c_70 ph1 |
| P1 | 0.3 | M3 | 0.975 | 9.2 | 0.00 | line (assumed) 4c_70 ph1 |
| P2 | 0.3 | M3 | 0.975 | 7.2 | 0.00 | line (assumed) 4c_70 ph1 |
| P1 | 0.6 | M3 | 0.975 | 4.9 | 0.00 | line (assumed) 4c_70 ph3 |
| P2 | 0.6 | M3 | 0.975 | 4.4 | 0.00 | line (assumed) 4c_70 ph1 |
| P1 | 1.0 | M3 | 0.975 | 2.6 | 0.00 | line (assumed) 4c_70 ph1 |
| P2 | 1.0 | M3 | 0.975 | 2.6 | 0.00 | line (assumed) 4c_70 ph1 |

What the sensitivity says (all 24 rows, P1/P2 x 30/60/100 % x M2/M3 x tap 1.000/0.975, from results/stage8_hc.csv): kVA = 1.1 x kW gives a LOWER HC than kVA = kW in every row, by 0.02 to 0.65 kW (for example P2 30 % M3 tap 1.000: 6.1 kW to 5.4 kW; P1 30 % M3 tap 1.000: 9.3 kW to 9.0 kW). Why is believed, not tested: with kVA = kW the inverter gives var priority and trims P, which also trims current, so the assumed 4c_70 line rating or the 253 V limit is reached later; with kVA = 1.1 x kW the full P is kept and vars are added on top. The curtailed % goes to about 0 with kVA = 1.1 x kW.

Nonconverged evaluations: 0 of 1272 rows.

## EV evening case LE: effect of the tap (P1_direct, 7.4 kW EV)

| tap | EV_HC_count | binding_limit | binding_element | min_cust_V_no_EV | min_cust_V_at_HC | min_cust_V_at_30_EVs | low_voltage_violations_no_EV | low_voltage_violations_30_EVs |
|---|---|---|---|---|---|---|---|---|
| 1.0 | 6 | line | line1 | 233.25 | 227.64 | 213.53 | 0 | 0 |
| 0.975 | 6 | line | line1 | 227.08 | 221.32 | 206.74 | 0 | 1 |

HC run time 494 s (results/stage8_hc_run.log; the 12 combinations ran 4 at a time).

## Year with control

**simulated; IEEE feeder; NZ-parameterised synthetic load; PV modelled; modelled inverter control; ratings assumed. Simulated, not measured.** Case Y3 = 8 kWp on 60 % of houses (P1, 33 houses), inverter kVA = kW, source 1.00 pu, diversity seed 2022. Scope: full year 2022 (17,520 steps). Spike (2 days, M3): 25.36 ms/step, projected full year 7.4 min. Curtailed kWh = PV available (kWp x PVGIS-ERA5 profile) minus PV delivered (OpenDSS PVSystem output). Reactive energy: absorbed and injected, summed over inverters. Customer-hours count each customer separately; distinct hours count a step once. Line overloads use assumed ratings. M0 row of a full-year scope is reused from stage6_year.csv. 30-min averages hide short peaks. Only the M3, M3+tap and M1 cases (and the extra M3 kVA = 1.1 x kWp case) use InvControl; they were re-run after the fix that disables customers without PV (they used to absorb volt-var vars). The M0+tap 0.975 reactive energy of about 4 kvarh (absorbed and injected) is numerical noise of a case with no control (no source of vars), not a result.

| case | kva_ratio | cust_hours_above_253V | distinct_hours_above_253V | cust_hours_below_207V | v_min_V | v_max_V | curtailed_kWh | curtailed_pct_of_pv_energy | q_absorbed_kvarh | q_injected_kvarh | distinct_hours_line_above_100pct | max_line_loading_pct | xfmr_max_kVA | nonconverged_steps | control_not_settled_steps | balance_error_pct_of_xfmr | runtime_s | ms_per_step |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Y3_M0_tap1.000 | 1.0 | 1330.0 | 207.5 | 0.0 | 210.45 | 259.16 | below 1 kWh | 0.0 | 0.0 | 0.0 | 326.5 | 171.1 | 195.1 | 0 | 0 | -0.0002 | 164.1 | 9.37 |
| Y3_M3_tap1.000 | 1.0 | 38.5 | 14.5 | 0.0 | 211.43 | 255.36 | below 1 kWh | 0.00012 | 87499.8 | 24.4 | 582.5 | 171.0 | 216.6 | 0 | 0 | -0.00279 | 261.2 | 14.91 |
| Y3_M3_tap0.975 | 1.0 | 0.0 | 0.0 | 2.0 | 205.73 | 250.76 | below 1 kWh | 1e-05 | 18387.2 | 435.3 | 430.5 | 175.9 | 202.3 | 0 | 0 | -0.00182 | 213.9 | 12.21 |
| Y3_M0_tap0.975 | 1.0 | 2.0 | 0.5 | 4.5 | 203.51 | 253.57 | below 1 kWh | -0.0 | 4.1 | 4.1 | 376.0 | 176.0 | 194.6 | 0 | 0 | -6e-05 | 158.9 | 9.07 |
| Y3_M1_tap1.000 | 1.0 | 1302.0 | 207.5 | 0.0 | 210.45 | 256.47 | 48.333 | 0.01326 | 0.2 | 0.2 | 326.5 | 171.1 | 192.8 | 0 | 0 | 0.0 | 190.4 | 10.87 |
| Y3_M3_tap1.000_kva1.1 | 1.1 | 24.0 | 10.0 | 0.0 | 211.51 | 255.43 | below 1 kWh | 5e-05 | 94281.0 | 26.4 | 610.5 | 170.9 | 219.4 | 0 | 0 | -0.00281 | 264.2 | 15.08 |
