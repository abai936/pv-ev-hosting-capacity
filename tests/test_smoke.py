"""Smoke test: the IEEE European LV feeder compiles, solves a snapshot and has 907 buses."""
from pathlib import Path

import opendssdirect as dss
import pytest

MASTER = Path(__file__).resolve().parents[1] / "data" / "feeders" / "LVTestCase" / "Master.dss"


def test_feeder_solves_with_907_buses():
    # The feeder is not committed (no licence), so a fresh clone has no copy.
    if not MASTER.exists():
        pytest.skip("feeder not downloaded; run scripts/download_data.py")
    dss.Basic.ClearAll()
    dss.Command(f'Compile "{MASTER}"')
    dss.Solution.Solve()
    assert dss.Solution.Converged()
    assert dss.Circuit.NumBuses() == 907
