"""Test helpers for a clean clone.
Data that is NOT committed (data/raw, data/processed, Steidl, PVGIS) is rebuilt by scripts, not by the clone.
A FileNotFoundError becomes a SKIP only when that data genuinely has not been built:
  - the clean-clone script sets CLEAN_CLONE=1, or
  - data/processed has no sentinel file `.built` (written by scripts/stage5_build_profiles.py), or
  - data/raw is missing or empty.
Otherwise (data is built but a name is wrong) the error stays a FAILURE, so a typo cannot hide as a skip.
An OpenDSS DSSException about data/feeders also becomes a SKIP, but only when the IEEE feeder
(data/feeders/LVTestCase/Master.dss, from scripts/download_data.py) is genuinely absent; if it is present it stays a FAILURE.
AssertionErrors and missing results/ files always fail.
Tests marked `slow` take more than about 10 s each; the clean-clone check runs `-m "not slow"`."""
import os
import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
# folder (after turning backslashes into slashes) -> script that builds it
_UNCOMMITTED = {"data/processed": "scripts/stage5_build_profiles.py", "data/raw": "scripts/download_data.py"}


def _genuinely_unbuilt(folder):
    if os.environ.get("CLEAN_CLONE") == "1":
        return True
    d = _ROOT / folder
    if folder == "data/processed":
        return not (d / ".built").exists()
    return not d.exists() or not any(d.iterdir())


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when in ("setup", "call") and rep.failed and call.excinfo is not None:
        exc = call.excinfo.value
        if isinstance(exc, FileNotFoundError):
            msg = re.sub(r"[\\/]+", "/", str(exc))
            for folder, script in _UNCOMMITTED.items():
                if folder in msg and _genuinely_unbuilt(folder):
                    rep.outcome = "skipped"
                    rep.longrepr = (str(item.fspath), item.location[1],
                                    f"Skipped: {folder} not built (run {script}): " + str(exc)[:120])
                    break
        elif type(exc).__name__ == "DSSException" or "DSSException" in repr(exc):
            # OpenDSS cannot find the git-ignored IEEE feeder files (downloaded, not committed).
            msg = re.sub(r"[\\/]+", "/", str(exc))
            master = _ROOT / "data/feeders/LVTestCase/Master.dss"
            if "data/feeders" in msg and (not master.exists() or (os.environ.get("CLEAN_CLONE") == "1" and not master.exists())):
                rep.outcome = "skipped"
                rep.longrepr = (str(item.fspath), item.location[1],
                                "Skipped: IEEE feeder not downloaded (run scripts/download_data.py): " + str(exc)[:120])


def pytest_collection_modifyitems(items):
    """Mark the 1440-minute benchmark runs slow (6 to 7 s each) so the clean-clone check can skip them."""
    for it in items:
        if "test_stage3_benchmark" in it.nodeid and "1440" in it.name:
            it.add_marker(pytest.mark.slow)
