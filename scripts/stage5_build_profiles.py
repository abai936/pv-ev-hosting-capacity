"""Stage 5 runner: build load, PV and EV profiles into data/processed/ and print the checks."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np
from hc import profiles as P

r = P.build_all()
kwh = (r["houses"] * P.STEP_H).sum(axis=0)
print(f"Average house: {r['avg_house'].sum() * P.STEP_H:.1f} kWh/yr")
print(f"55 houses annual kWh: mean {kwh.mean():.1f}, std {kwh.std():.1f}, "
      f"min {kwh.min():.1f}, max {kwh.max():.1f}")
print(f"PV CF north (PVGIS aspect {r['north_aspect']}): {r['cf_north']:.4f}; south: {r['cf_south']:.4f}; "
      f"ref {P.PV_CF_REFERENCE}, ratio {r['cf_north'] / P.PV_CF_REFERENCE:.3f}")
s = r["sessions"]
print(f"EV: mean session {s.energy_kwh.mean():.2f} kWh (theory {np.exp(np.log(6.9) + 0.125):.2f}); "
      f"mean EV annual {r['ev'].sum(axis=0).mean() * P.STEP_H:.0f} kWh; steps {r['ev'].shape[0]}")

# Sentinel: tells tests/conftest.py the data is built, so a missing file is a real error, not a skip.
(Path(__file__).resolve().parents[1] / "data" / "processed" / ".built").touch()
