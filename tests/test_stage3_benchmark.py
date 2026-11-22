"""Stage 3a benchmark vs published solutions (OpenDSS and GridLAB-D), all 55 load nodes, minutes 1, 566, 1440.
The published solution seems to use CONSTANT-P loads: constant-P matches to <= 0.003 V, while the original
default loads (vmin/vmax 0.95/1.05 pu, constant-Z outside) differ by up to 0.40 V at minute 566.
Tolerances: 0.05 V for the best-matching case (constant-P), 1.0 V for the other (default loads).
The full table is written by scripts/stage3_benchmark.py to results/stage3_benchmark.csv."""
import sys

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "scripts"))
import stage3_benchmark as b  # noqa: E402

if not (b.SOL / "OpenDSS" / "Snapshots").exists():
    pytest.skip("published snapshots not downloaded", allow_module_level=True)


@pytest.mark.parametrize("minute", [1, 566, 1440])
@pytest.mark.parametrize("case,constant_p,tol_v", [("default", False, 1.0), ("constant_P", True, 0.05)])
@pytest.mark.parametrize("ref", ["opendss", "gridlabd"])
def test_benchmark(minute, case, constant_p, tol_v, ref):
    ours, nodes = b.our_voltages(minute, constant_p)
    tab = (b.published_opendss if ref == "opendss" else b.published_gridlabd)(minute)
    err = abs(ours - [tab[n] for n in nodes])
    assert err.max() < tol_v, (case, minute, ref, err.max())
