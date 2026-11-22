# CP-09: Stage 9, validation, limitations and a clean-copy test (19 Nov 2026)

**Status: built, reviewed, fixed.** Everything in the project is **simulated**. This stage checks how far the model can be trusted, and says where it cannot.
Sources: `VALIDATION.md` (32 rows), `LIMITATIONS.md` (16 items), `ASSUMPTIONS.md` (A21 to A29 added), `results/stage9_recheck.csv`, the recorded pytest run.

## Figures
No new graph: this stage is tables. The headline graphs are in CP-04, CP-06, CP-07 and CP-08. The re-check values are in `results/stage9_recheck.csv`:

| Re-check on the final code | Expected | Got | Error (tolerance) |
|---|---|---|---|
| Far-end voltage rise, 5 kW PV (Stage 4) | 4.787 V | 4.787 V | −0.012% (3%) |
| 7.4 kW EV at the far-end house, current and drop (Stage 7) | 32.17 A, 7.460 V | 7.462 V | +0.025% (3%) |
| Volt-var reactive power at 1.0826 pu (Stage 8) | −1.5 kvar | −1.500 kvar | within 0.1 kvar |
| Benchmark vs published OpenDSS and GridLAB-D, constant-power loads (Stage 3) | – | worst 0.0028 V and 0.0012 V | 0.05 V |
| Same benchmark with default loads | – | worst 0.40 V | 1.0 V |

## Done
- **VALIDATION.md:** one table of every check (hand calculations, the published OpenDSS and GridLAB-D solution, curve points, the solar capacity factor, energy balances, the inverter cold-start test), with the expected value, what we got, the error, the test and the file. Plus 9 honest weak spots.
- **LIMITATIONS.md:** 16 limits in plain English, each with a bias direction (does it make hosting capacity look higher or lower).
- **Re-check script:** re-runs three hand checks and the benchmark against the final code, so the numbers are not copied from old runs.
- **Clean-copy test:** `scripts/clean_clone_check.py` clones the repo to a new folder, builds a fresh environment, installs the pinned packages, downloads the feeder files and runs the fast tests.

## Works (checked)
- **pytest: 101 passed, 0 skipped, 0 failed** (the recorded pytest run).
- **Clean copy of commit 800109b:** 61 passed, 33 skipped, 0 failed, in 619 s. The 33 skips are tests that need data not stored in git (the Steidl load data and processed profiles). So the clean copy proves the code installs and runs, but it does not re-check Stages 5 to 8 results. Say this whenever the clean copy is mentioned.

## Found by the review, and fixed
- **A test rule could hide a real failure.** The rule that turns "data file missing" into a skip also skipped a misspelled filename when the data was present. It now skips only when the data is really not built, and three tests prove it (a real failure still fails).
- **Three bias directions were wrong or unclear:** the inverter reactive-power priority is mixed (raises hosting capacity where voltage binds, lowers it where the cable binds); the house-diversity simplification makes the result optimistic, not pessimistic; and the five random seeds cannot test house-to-house differences.
- **Wording errors in the table:** a "published" value that was really our own earlier run is now labelled a repeatability check; a 1.0% error that was called "rounding" is now stated; one test's scope is stated.
- The re-check script now says "SKIPPED" loudly instead of looking like a pass.

## Still open
- The clean copy was run before the test rule was hardened. I will re-run it once at the end, on the final commit.
- Independent sources for three numbers (solar capacity factor 0.151, one line rating, the Jemena curve points) were not re-opened by the reviewer.
- The cable ratings are still assumptions. That is the biggest limit on how much any thermal result can be trusted.

## Decisions made
- Validation reports weak spots next to strong ones. Energy-balance checks are called bookkeeping, and hand checks that share the model's own path resistance are called partly circular.
- Stage 9b (uptake scenarios) was added to the plan on Aniket's idea and runs next.

## Next
Stage 9b: uptake scenarios for 2027 and 2028. Then Stage 10 (plain dashboard) and Stage 11 (README and release).

