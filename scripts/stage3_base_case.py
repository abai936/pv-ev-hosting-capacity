"""Stage 3a: NZ base case, full day of the feeder's own 1-minute profiles, no PV.
Writes results/stage3_base_case.csv. Synthetic, NZ-parameterised data (feeder is IEEE European LV)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hc import feeder as f  # noqa: E402

rows = []
for pu in (0.98, 1.00, 1.025, 1.05):
    f.load_feeder(source_pu=pu, nz_base=True)
    r = f.solve_minutes()
    v = np.array(r["v_cust"])               # minutes x 55 load nodes, volts
    rows.append({
        "source_pu": pu,
        "v_min_V": round(v.min(), 2), "v_max_V": round(v.max(), 2),
        "minutes_above_253V": int((v.max(axis=1) > f.V_HIGH_V).sum()),
        "minutes_below_207V": int((v.min(axis=1) < f.V_LOW_V).sum()),
        "xfmr_max_kVA": round(max(r["xfmr_kva"]), 2),
        "vuf_max_pct_assumed_limit_2": round(max(r["vuf"]), 3),
        "nonconverged_steps": sum(not c for c in r["converged"]),
        "runtime_s": round(r["solve_s"], 2),
        "note": "minutes counted if ANY customer node violates; synthetic NZ-parameterised, no PV",
    })
df = pd.DataFrame(rows)
out = ROOT / "results" / "stage3_base_case.csv"
out.parent.mkdir(exist_ok=True)
df.to_csv(out, index=False)
print(df.drop(columns="note").to_string(index=False))
