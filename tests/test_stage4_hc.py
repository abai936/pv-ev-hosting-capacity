"""Stage 4: hand check of voltage rise, penetration counts, placement sanity."""
from pathlib import Path

from hc import hosting as h

RESULTS = Path(__file__).resolve().parents[1] / "results"


def test_hand_check_voltage_rise_3pct():
    pred, sim, name, n = h.write_hand_check(RESULTS / "stage4_hand_check.csv", 5.0)
    print(f"\n{name}: lines on path {n}; predicted rise {pred:.4f} V, OpenDSS {sim:.4f} V, "
          f"error {100 * (sim - pred) / pred:.2f} %")
    assert abs(sim - pred) / pred < 0.03


def test_penetration_counts_ceil():
    # the same function the runner uses
    assert [h.n_pv_for(p, 55) for p in (0.30, 0.60, 1.00)] == [17, 33, 55]


def test_placements():
    m = h.Model(1.0, True)
    for pen in (0.30, 0.60, 1.00):
        n = h.n_pv_for(pen, len(m.loads))
        p1 = h.place_p1(m, n)
        assert len(p1) == len(set(p1)) == n
        cnt = [sum(m.phase[i] == p for i in p1) for p in (1, 2, 3)]
        if n < 55:
            assert max(cnt) - min(cnt) <= 1
        assert len(h.place_p2(m, n)) == n
        assert len(h.place_p3(m, n, 0)) == n


def test_custom_load_dict_accepted():
    m = h.Model(1.0, True)
    m.set_case("custom", [0], load_kw={n: 0.5 for n in m.loads})
    m.solve(1.0)
