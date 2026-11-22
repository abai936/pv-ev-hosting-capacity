"""Clean-clone check, one command:  .venv/Scripts/python scripts/clean_clone_check.py [--keep DIR]
1. git clone this repo (COMMITTED files only) into a new empty folder outside the project,
2. create a venv there and pip install requirements.txt,
3. run scripts/download_data.py (IEEE feeder files only; no Steidl, no big download),
4. run the fast tests (pytest -m "not slow"); tests that need uncommitted data (data/processed, Steidl) SKIP,
5. print PASS or FAIL with counts.
Because a clone holds only committed files, any file that is modified or new in the working copy is copied over
afterwards (--no-overlay turns that off) and listed, so the check can run before a commit. Never deletes anything;
the temp clone is left in place. On Windows keep the path short (default temp folder): pip fails on long paths."""
import argparse
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd, cwd, log):
    print("$", " ".join(map(str, cmd)), flush=True)
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    log.write(f"$ {' '.join(map(str, cmd))}\n{r.stdout}\n{r.stderr}\n")
    log.flush()
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", help="parent folder for the clone (default: system temp)")
    ap.add_argument("--no-overlay", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    parent = Path(a.keep) if a.keep else Path(tempfile.gettempdir())
    parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="hcc_", dir=parent))      # new, empty folder
    clone = work / "repo"
    log = open(work / "clean_clone.log", "w", encoding="utf-8")
    print("clone folder:", clone)
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    ok = run(["git", "clone", "--quiet", str(ROOT), str(clone)], work, log).returncode == 0
    overlay = []
    if ok and not a.no_overlay:
        st = subprocess.run(["git", "status", "--porcelain", "-uall"], cwd=ROOT, capture_output=True, text=True).stdout
        for line in st.splitlines():
            rel = line[3:].strip().strip('"')
            if line[:2].strip() in ("M", "A", "??") and rel.split("/")[0] in ("src", "tests", "scripts", "pytest.ini", "requirements.txt"):
                if "__pycache__" in rel:
                    continue
                dst = clone / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes((ROOT / rel).read_bytes())
                overlay.append(rel)
    py = clone / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    steps = [[sys.executable, "-m", "venv", str(clone / ".venv")],
             [py, "-m", "pip", "install", "--quiet", "-r", "requirements.txt"],
             [py, "scripts/download_data.py"]]
    for s in steps:
        if not ok:
            break
        ok = run(s, clone, log).returncode == 0
        if not ok:
            print("FAILED step:", s[:4])
    passed = skipped = failed = 0
    if ok:
        os.environ["CLEAN_CLONE"] = "1"      # tells tests/conftest.py that missing uncommitted data is a skip
        r = run([py, "-m", "pytest", "-m", "not slow", "-rs", "-q"], clone, log)
        last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        print(r.stdout[-3000:])
        count = lambda w: int((re.search(rf"(\d+) {w}", last) or [0, 0])[1])
        passed, skipped, failed = count("passed"), count("skipped"), count("failed") + count("error")
        ok = r.returncode == 0 and failed == 0
    print(f"commit {head}; overlay of uncommitted files: {overlay or 'none'}")
    print(f"{'PASS' if ok else 'FAIL'}: passed={passed} skipped={skipped} failed={failed} time={time.time() - t0:.0f}s log={work / 'clean_clone.log'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
