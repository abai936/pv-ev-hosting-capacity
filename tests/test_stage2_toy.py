"""Stage 2: OpenDSS vs independent hand calculations on toy circuits. Writes results/stage2_toy_checks.csv."""
import csv
from pathlib import Path

import pytest

from hc import toy

ROWS = []  # (case, quantity, hand, opendss, error_pct)
CSV = Path(__file__).resolve().parents[1] / "results" / "stage2_toy_checks.csv"


def rec(case, qty, hand, dssv):
    err = 100 * (dssv - hand) / hand
    ROWS.append((case, qty, f"{hand:.4f}", f"{dssv:.4f}", f"{err:.4f}"))
    return err


@pytest.fixture(scope="module", autouse=True)
def write_csv():
    yield
    CSV.parent.mkdir(exist_ok=True)
    with open(CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["case", "quantity", "hand_value", "opendss_value", "error_pct"])
        w.writerows(ROWS)


def test_case1_balanced_two_bus():
    # Tolerance 0.5 % of each value (volts, and the PV rise as a share of the rise).
    tol = 0.5
    v_load = toy.solve_two_bus(50, 20)
    assert abs(rec("1 load 50kW+20kvar", "load bus V_LL [V]", toy.hand_two_bus(50, 20), v_load)) < tol
    v_pv = toy.solve_two_bus(-50, 0)
    hand_pv = toy.hand_two_bus(-50, 0)
    assert abs(rec("1 PV -50kW", "load bus V_LL [V]", hand_pv, v_pv)) < tol
    rise_hand, rise_dss = hand_pv - 415.0, v_pv - 415.0
    assert abs(rec("1 PV -50kW", "rise above source [V]", rise_hand, rise_dss)) < tol
    print(f"\nhand rise {rise_hand:.3f} V exact; approx R*P/V = {0.1 * 50000 / 400:.3f} V")


@pytest.mark.parametrize("p_kw", [7.4, -7.4])
def test_case2_single_phase_sequence_z(p_kw):
    tol = 0.2  # percent, per phase magnitude
    h = toy.hand_single_phase(p_kw)
    d = toy.solve_single_phase(p_kw)
    print(f"\ncase 2, load {p_kw} kW on phase a (volts)")
    print("phase | balanced-Z1 est | Zs/Zm hand | OpenDSS")
    for n, name in ((1, "a"), (2, "b"), (3, "c")):
        print(f"  {name}   | {h['balanced'][n]:10.3f}      | {h['full'][n]:9.3f}  | {d[n]:9.3f}")
        err = rec(f"2 1ph {p_kw}kW", f"V phase {name} [V]", h["full"][n], d[n])
        assert abs(err) < tol


@pytest.mark.parametrize("pu,tap", [(1.0, None), (1.05, None), (1.0, 1.025)])
def test_case3_transformer(pu, tap):
    tol = 0.1  # percent
    v, v_pu = toy.solve_transformer(pu, tap)
    hand = toy.hand_transformer(pu, tap or 1.0)
    case = f"3 xfmr src {pu}pu tap {tap or 1.0}"
    assert abs(rec(case, "secondary phase V [V]", hand, v)) < tol
    rec(case, "secondary on 230 V base [pu]", hand / 230.0, v_pu)
    print(f"\n{case}: hand {hand:.2f} V, OpenDSS {v:.2f} V = {v_pu:.4f} pu (230 V base)")


def test_case4_ieee13_smoke():
    if not (toy.FEEDERS / "13Bus" / "IEEE13Nodeckt.dss").exists():
        pytest.skip("13Bus not downloaded; run scripts/download_data.py")
    ok, vmin, vmax = toy.solve_ieee13()
    print(f"\nIEEE 13-bus: min {vmin:.4f} pu, max {vmax:.4f} pu (R1 reported 0.9608 to 1.0560)")
    assert ok
    ROWS.append(("4 IEEE13", "min pu (R1 0.9608)", "0.9608", f"{vmin:.4f}", f"{100 * (vmin - 0.9608) / 0.9608:.4f}"))
    ROWS.append(("4 IEEE13", "max pu (R1 1.0560)", "1.0560", f"{vmax:.4f}", f"{100 * (vmax - 1.0560) / 1.0560:.4f}"))
