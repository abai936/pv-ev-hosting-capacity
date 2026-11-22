"""Download the IEEE European LV Test Feeder files into data/feeders/ (not committed: no licence stated).

Standard library only. Run:  .venv/Scripts/python scripts/download_data.py
Writes data/feeders/CHECKSUMS.sha256; the committed copy is DATA-CHECKSUMS.sha256 in the repo root.
"""
import hashlib
import json
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "feeders"
# Pinned to a fixed commit so the feeder files cannot change under us. This was the HEAD of the
# default branch of dss-extensions/electricdss-tst on 18 Nov 2026 (commit dated 24 Jun 2024).
COMMIT_SHA = "3b208397160213cae4a9e2d0a7d1aa3528ce26e1"
API = ("https://api.github.com/repos/dss-extensions/electricdss-tst/contents/"
       f"Version8/Distrib/IEEETestCases/LVTestCase?ref={COMMIT_SHA}")
API_13BUS = ("https://api.github.com/repos/dss-extensions/electricdss-tst/contents/"
             f"Version8/Distrib/IEEETestCases/13Bus?ref={COMMIT_SHA}")  # same pinned commit
ZIP_URL = ("https://cmte.ieee.org/pes-testfeeders/wp-content/uploads/sites/167/"
           "2017/08/European_LV_Test_Feeder_v2.zip")
RETRIES = 3


def get(url):
    """Fetch a URL, retrying up to RETRIES extra times (this network is slow and flaky)."""
    req = urllib.request.Request(url, headers={"User-Agent": "hc-download"})
    for attempt in range(RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception:
            if attempt == RETRIES:
                raise
            time.sleep(2 * (attempt + 1))


def main():
    lv = OUT / "LVTestCase"
    jobs = []  # (download_url, local path, expected size); recurse into sub-folders (100 load profiles)

    def walk(api_url, folder):
        folder.mkdir(parents=True, exist_ok=True)
        for item in json.loads(get(api_url)):
            if item["type"] == "file":
                jobs.append((item["download_url"], folder / item["name"], item["size"]))
            elif item["type"] == "dir":
                walk(item["url"], folder / item["name"])

    def fetch(job):
        url, path, size = job
        if path.exists() and (size is None or path.stat().st_size == size):
            return f"skip {path.name}"          # already there with the right size
        path.write_bytes(get(url))
        return f"got {path.name}"

    walk(API, lv)
    # 13Bus/IEEELineCodes.DSS is a one-line stub: "redirect ../IEEELineCodes.DSS", so fetch the parent file too.
    jobs.append((f"https://raw.githubusercontent.com/dss-extensions/electricdss-tst/{COMMIT_SHA}/"
                 "Version8/Distrib/IEEETestCases/IEEELineCodes.DSS", OUT / "IEEELineCodes.DSS", None))
    walk(API_13BUS, OUT / "13Bus")   # IEEE 13-bus small benchmark (Stage 2 smoke run)
    # Each request can take a minute on this network, so fetch in parallel.
    with ThreadPoolExecutor(max_workers=24) as pool:
        for msg in pool.map(fetch, jobs):
            print(msg)

    z = OUT / "ieee_zip"
    z.mkdir(parents=True, exist_ok=True)
    zp = z / "European_LV_Test_Feeder_v2.zip"
    if zp.exists() and zipfile.is_zipfile(zp):
        print("skip", zp.name)
    else:
        zp.write_bytes(get(ZIP_URL))
    with zipfile.ZipFile(zp) as zf:
        zf.extractall(z)

    # Checksum every downloaded file so a later re-download can be compared byte for byte.
    lines = []
    for p in sorted(f for f in OUT.rglob("*") if f.is_file() and f.name != "CHECKSUMS.sha256"):
        lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(OUT).as_posix()}")
    text = "\n".join(lines) + "\n"
    (OUT / "CHECKSUMS.sha256").write_text(text)
    (ROOT / "DATA-CHECKSUMS.sha256").write_text(text)
    print(f"checksummed {len(lines)} files")


if __name__ == "__main__":
    main()
