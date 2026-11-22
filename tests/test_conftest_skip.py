"""Proves the conftest skip rule on a tiny scratch project in tmp_path (subprocess pytest).
Missing data + CLEAN_CLONE=1 -> skipped; built data + wrong filename -> failed; assertion error -> failed."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

CONF = Path(__file__).with_name("conftest.py")
TESTS = '''
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def test_missing_processed():
    open(ROOT / "data" / "processed" / "x.csv")
def test_assertion():
    assert 1 == 2
'''


def _run(tmp_path, built, clean_clone):
    (tmp_path / "tests").mkdir()
    shutil.copy(CONF, tmp_path / "tests" / "conftest.py")
    (tmp_path / "tests" / "test_x.py").write_text(TESTS)
    proc = tmp_path / "data" / "processed"
    proc.mkdir(parents=True)
    if built:
        (proc / ".built").touch()
        (proc / "real.csv").write_text("a\n")
    env = {k: v for k, v in os.environ.items() if k != "CLEAN_CLONE"}
    if clean_clone:
        env["CLEAN_CLONE"] = "1"
    r = subprocess.run([sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-p", "no:faulthandler",
                        "-rsf", "-q", "tests"], cwd=tmp_path, env=env, capture_output=True, text=True)
    return r.stdout


def test_missing_data_clean_clone_is_skipped(tmp_path):
    out = _run(tmp_path, built=False, clean_clone=True)
    assert "1 skipped" in out and "1 failed" in out      # the missing file skips; the assertion still fails
    assert "scripts/stage5_build_profiles.py" in out


def test_unbuilt_without_env_is_skipped_by_sentinel(tmp_path):
    assert "1 skipped" in _run(tmp_path, built=False, clean_clone=False)


def test_built_data_wrong_filename_fails(tmp_path):
    out = _run(tmp_path, built=True, clean_clone=False)
    assert "2 failed" in out and "skipped" not in out    # typo under populated data must FAIL, assertion fails too
    assert "FileNotFoundError" in out
