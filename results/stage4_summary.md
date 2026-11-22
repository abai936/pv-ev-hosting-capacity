# Stage 4 summary: snapshot PV hosting capacity

**IEEE European LV feeder; load data synthetic/non-NZ. Simulated, not measured.** Source 1.00 pu, 12:00 snapshot, PV single-phase at unity PF, no inverter control. HC = kW per PV customer (= kW per phase), reported to 1 decimal (bisection step 0.01 kW; the CSV keeps 2 decimals). Penetration N = ceil(pen x 55) = 17, 33, 55. Orion cap = min(HC, 10). HC_V = HC ignoring line ratings. Thermal limits (lines, transformer 800 kVA nameplate) use **assumed ratings** (data/line_ratings.csv, R10).

Load cases: L0 = zero load, the minimum-load bound (worst case for voltage rise). L1 = one stochastic minute of non-NZ feeder profiles (minute 720); it is a single random minute, not an NZ load case. An NZ case (L2) comes in Stage 6.

No-load LV voltage is about 240 V at 1.00 pu source (0.416 kV / sqrt(3)), because of the 11/0.416 kV ratio, so customers start close to the 253 V upper limit.

## P1 (balanced) and P2 (end-clustered), L0 next to L1

| placement | penetration | n_pv | load_case | HC | Orion_capped | HC_V | binding |
|---|---|---|---|---|---|---|---|
| P1 | 0.3 | 17 | L0 | 8.1 | 8.1 | 8.1 | voltage-high load50@886.2 |
| P1 | 0.3 | 17 | L1 | 9.7 | 9.7 | 9.9 | line (assumed rating): linecode 4c_70, phase 2, nearest line line1, chain of 21 lines |
| P2 | 0.3 | 17 | L0 | 4.5 | 4.5 | 4.5 | voltage-high load53@899.2 |
| P2 | 0.3 | 17 | L1 | 5.6 | 5.6 | 5.6 | voltage-high load53@899.2 |
| P1 | 0.6 | 33 | L0 | 4.4 | 4.4 | 5.0 | line (assumed rating): linecode 4c_70, phase 1, nearest line line1, chain of 35 lines |
| P1 | 0.6 | 33 | L1 | 5.1 | 5.1 | 5.7 | line (assumed rating): linecode 4c_70, phase 3, nearest line line1, chain of 35 lines |
| P2 | 0.6 | 33 | L0 | 3.5 | 3.5 | 3.5 | voltage-high load29@562.1 |
| P2 | 0.6 | 33 | L1 | 4.4 | 4.4 | 4.4 | voltage-high load55@906.1 |
| P1 | 1.0 | 55 | L0 | 2.3 | 2.3 | 2.5 | line (assumed rating): linecode 4c_70, phase 1, nearest line line1, chain of 19 lines |
| P1 | 1.0 | 55 | L1 | 2.9 | 2.9 | 3.2 | line (assumed rating): linecode 4c_70, phase 1, nearest line line1, chain of 19 lines |
| P2 | 1.0 | 55 | L0 | 2.3 | 2.3 | 2.5 | line (assumed rating): linecode 4c_70, phase 1, nearest line line1, chain of 19 lines |
| P2 | 1.0 | 55 | L1 | 2.9 | 2.9 | 3.2 | line (assumed rating): linecode 4c_70, phase 1, nearest line line1, chain of 19 lines |

## P3 random placement (50 seeds, 0 to 49), L0 next to L1

| load_case | penetration | P1_HC | P2_HC | P3_P5 | P3_P50 | P3_P95 | P2_below_P3_P5 | binding (assumed rating if line/transformer) |
|---|---|---|---|---|---|---|---|---|
| L0 | 0.3 | 8.1 | 4.5 | 3.9 | 5.3 | 7.3 | no | voltage-high:44, line/4c_70/ph1:4, line/4c_70/ph2:2 |
| L0 | 0.6 | 4.4 | 3.5 | 2.6 | 3.3 | 4.0 | no | voltage-high:32, line/4c_70/ph1:12, line/4c_70/ph2:5, line/4c_70/ph3:1 |
| L0 | 1.0 | 2.3 | 2.3 | 2.3 | 2.3 | 2.3 | no | line/4c_70/ph1:50 |
| L1 | 0.3 | 9.7 | 5.6 | 4.7 | 6.5 | 8.7 | no | voltage-high:45, line/4c_70/ph1:3, line/4c_70/ph2:1, line/4c_70/ph3:1 |
| L1 | 0.6 | 5.1 | 4.4 | 3.2 | 4.1 | 4.8 | no | voltage-high:39, line/4c_70/ph1:5, line/4c_70/ph2:4, line/4c_70/ph3:2 |
| L1 | 1.0 | 2.9 | 2.9 | 2.9 | 2.9 | 2.9 | no | line/4c_70/ph1:50 |

P2 (end-clustering) is not the worst case: where `P2_below_P3_P5` is `no`, P2 is at or above the 5th-percentile random placement, so some random placements give a lower HC than P2. Use the P3 P5 as the conservative figure.

## Source-voltage sweep (P1, L1, 60 %)

| model | source_pu | HC | HC_voltage_only | binding |
|---|---|---|---|---|
| base | 1.0 | 5.1 | 5.7 | line (assumed rating): linecode 4c_70, phase 3, nearest line line1, chain of 35 lines |
| sens_source_pu | 0.98 | 5.0 | 7.8 | line (assumed rating): linecode 4c_70, phase 3, nearest line line1, chain of 35 lines |
| sens_source_pu | 1.0 | 5.1 | 5.7 | line (assumed rating): linecode 4c_70, phase 3, nearest line line1, chain of 35 lines |
| sens_source_pu | 1.025 | 3.2 | 3.2 | voltage-high load42@778.3 |
| sens_source_pu | 1.05 | 0.7 | 0.7 | voltage-high load42@778.3 |

A lower source voltage (for example 0.98 pu) can give a LOWER HC than 1.00 pu, even though it gives more voltage headroom: the HC is thermal-bound (assumed rating), and a lower voltage means more current for the same power. HC_voltage_only (line ratings ignored) shows the voltage-rise limit alone.

## Other sensitivities (P1, L1, 60 %)

| model | HC | HC_voltage_only | binding |
|---|---|---|---|
| sens_no_neutral_return | 5.1 | 6.0 | line (assumed rating): linecode 4c_70, phase 3, nearest line line1, chain of 35 lines |
| sens_ratings_x0.8 | 4.2 | 5.7 | line (assumed rating): linecode 4c_70, phase 3, nearest line line1, chain of 35 lines |
| sens_ratings_x1.2 | 5.7 | 5.7 | voltage-high load42@778.3 |

## Limits seen

- VUF 2 % limit is **assumed** (EN 50160 basis, ASSUMPTIONS.md A7). Max VUF seen at the HC points of the main grid: 1.18 %.
- Transformer max kVA seen at the HC points of the main grid: 140.3 kVA (800 kVA nameplate, assumed rating).
- Hand check (load53-type worst customer load53, 5 kW, 151 lines): predicted 4.7872 V, OpenDSS 4.7867 V; the current uses the solved customer voltage. See results/stage4_hand_check.csv.

Runtime 119 s.