# R10 Line ratings (Stage 3b, PLAN decision b4)

Sources read from the PDFs by a researcher on 19 Nov 2026. Ratings: 90 C conductor, soil 25 C, 1.2 K.m/W, depth 0.5 m.
- A (Al): World Wire Cables (Aust), "4C+E XLPE Insulated Orange Circular Cables 0.6/1kV Flexible AL", https://media.mmem.com.au/Datasheets/WWC/WWC_CAL4C.pdf. DC R at 20 C; air touching / in ground.
- B (Cu): Prysmian AU/NZ, "XLPE Cables 0.6/1 kV, 4C+E XLPE Circular", 2019-05, https://media.mmem.com.au/Datasheets/Prysmian/Prysmian_4C-EXLPE_Circular.pdf. DC R at 20 C; unenclosed spaced (air) / buried direct.
- C: Prysmian NZ URD 185 mm2 Al sector, AC R at 90 C = 0.211 ohm/km, 340 A direct buried. https://nz.prysmian.com/sites/nz.prysmian.com/files/media/documents/0-61-1-2-kv-low-voltage-cable-xlpe-insulated-5v90-pvc-sheath.pdf
  (Used as a cross-check only: 0.211 / 0.164 = 1.29, matching the ~28 % Al rise from 20 to 90 C, and 340 A equals source A's 185 mm2 in-ground rating.)

## Matching (feeder R1 in ohm/km, linecode Units=km; datasheet DC R at 20 C)
| linecode | R1 | best match | datasheet R | error % | rating A | condition | confidence |
|---|---|---|---|---|---|---|---|
| 2c_.007 | 3.97 | Al 16 (nearest, UNMATCHED) | 1.91 | 107.9 | 54 | air | low |
| 2c_.0225 | 1.257 | Al 25 | 1.20 | 4.8 | 73 | air | medium |
| 2c_16 | 1.15 | Cu 16 | 1.15 | 0.0 | 88 | air | high |
| 35_SAC_XSC | 0.868 | Al 35 | 0.868 | 0.0 | 133 | ground | high |
| 4c_.06 | 0.469 | Al 70 | 0.443 | 5.9 | 195 | ground | medium |
| 4c_.1 | 0.274 | Cu 70 | 0.268 | 2.2 | 250 | ground | medium |
| 4c_.35 | 0.089 | Cu 185 | 0.0991 | 10.2 | 435 | ground | low |
| 4c_185 | 0.166 | Al 185 | 0.164 | 1.2 | 340 | ground | high |
| 4c_70 | 0.446 | Al 70 | 0.443 | 0.7 | 195 | ground | high |
| 4c_95_SAC_XC | 0.322 | Al 95 | 0.320 | 0.6 | 234 | ground | high |

Temperature: feeder R1 fits the 20 C DC values. At 90 C Al would be about 28 % higher (Al 70 about 0.57), which does not match 0.446. So the feeder R is at 20 C (believed, from the numbers matching).

Square-inch guess for decimal names (.007, .0225, .06, .1, .35 = 4.5, 14.5, 38.7, 64.5, 226 mm2): NOT supported. .06 in2 = 38.7 mm2 but R1 0.469 fits 70 mm2 Al, not 35 mm2 Al (0.868). .35 in2 = 226 mm2 would give R about 0.125 Al or 0.076 Cu, not 0.089. Sizes are only inferred from R.

Unmatched: 2c_.007 (R 3.97 is above every datasheet size; smallest is 16 mm2). Given the 16 mm2 Al rating as "assumed, low confidence". This is NON-conservative: the real cable is smaller (about 4 to 6 mm2) and has a lower rating.

## Assumptions and bias on the thermal limit
1. Mains are underground urban LV, rated "in ground". If some are in air or ducts, the true limit is lower (or higher for air on Cu 185). Bias: ground ratings are mostly higher than air for Al, so likely optimistic if cables are in ducts or crowded.
2. 2c service cables rated "in air". Lower than in-ground for Al, so conservative (low limit) if they are actually buried.
3. Rating conditions: soil 25 C, 1.2 K.m/W, 0.5 m, single circuit. Hot or dry soil, grouped circuits or deeper burial lower the rating. Optimistic.
4. Feeder R matched to DC R at 20 C of 4-core cable datasheets. The conductor could be a different material or size; conductor choice (Al vs Cu) is inferred from R only. 4c_.1 as Cu 70 (250 A) vs Al 95 (234 A, 14 % off) differ by 7 %; 4c_.35 as Cu 185 (435 A) is optimistic if it is really a larger Al cable (Al 185 buried is 340 A). Optimistic.
5. Datasheet cables are 4C+E circular; SAC/URD sector or other constructions have other ratings. Unknown direction.
6. Continuous rating, no daily cyclic or emergency rating. Conservative (real cables tolerate short overloads).
7. All values are "assumed", not feeder data. PLAN b4 asks for a +/-20 % sensitivity run (not done in this stage).
