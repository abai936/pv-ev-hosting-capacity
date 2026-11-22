"""Hand check for the neutral-return variant: on a 2c service cable feeding one single-phase load, the
OpenDSS drop must match the phase-plus-neutral loop formula dV = 2 I (R cos(phi) + X sin(phi)) within 2 %.
The original model must match the ONE-conductor formula instead (that is the problem being fixed)."""
import pytest

from hc import feeder as f
from hc import neutral as nr


@pytest.mark.parametrize("load", ["load1", "load49"])
def test_variant_service_drop_matches_loop_formula(load):
    f.load_feeder(1.0)
    changed = nr.apply_neutral_return(1.0)
    assert changed == {"2c_.007": 36, "2c_.0225": 18, "2c_16": 482, "35_sac_xsc": 3}
    h = nr.service_drop_check(load, 5.0)
    assert h["other_phase_I_A"] < 1e-6            # only the load's phase carries current
    assert abs(h["dV_opendss_V"] / h["dV_loop_V"] - 1) < 0.02, h


@pytest.mark.parametrize("load", ["load1", "load49"])
def test_original_service_drop_is_one_conductor_only(load):
    f.load_feeder(1.0)
    h = nr.service_drop_check(load, 5.0)
    # 2c_16 has R0 = 1.2 vs R1 = 1.15, so Zs is 1.4 % above one conductor; 3 % tolerance.
    assert abs(h["dV_opendss_V"] / h["dV_one_conductor_V"] - 1) < 0.03, h


def test_four_core_codes_untouched():
    f.load_feeder(1.0)
    nr.apply_neutral_return(1.0)
    import opendssdirect as dss
    dss.LineCodes.Name("4c_70")
    assert (dss.LineCodes.R1(), dss.LineCodes.R0()) == (0.446, 1.505)
