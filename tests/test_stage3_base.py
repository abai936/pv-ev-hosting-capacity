"""Stage 3a hand check: at minute 1 (light load) the transformer LV terminal phase voltage is within
2 % of 240.2 V x source pu. 240.2 V = 11 kV x (0.416/11) / sqrt(3) (kept 11/0.416 ratio, PLAN b2)."""
import numpy as np
import opendssdirect as dss
import pytest

from hc import feeder as f


@pytest.mark.parametrize("pu", [0.98, 1.00, 1.025, 1.05])
def test_no_load_voltage_minute1(pu):
    f.load_feeder(source_pu=pu, nz_base=True)
    f.solve_minutes(n_minutes=1, collect=False)
    dss.Circuit.SetActiveBus("1")               # bus 1 is the transformer LV terminal (Transformers.txt)
    v = np.array(dss.Bus.VMagAngle())[0::2]
    expected = 240.2 * pu
    assert np.all(np.abs(v - expected) / expected < 0.02), (v, expected)


def test_vuf_zero_for_balanced():
    f.load_feeder(1.0)
    dss.Command("batchedit load..* enabled=no")
    dss.Solution.Solve()
    assert f.vuf_percent().max() < 0.05      # no loads: only tiny line asymmetry remains


def test_vuf_hand_calc_r6_phasors(monkeypatch):
    """R6 hand calc: Va=230@0, Vb=220@-120, Vc=240@+120 gives VUF = |V2|/|V1| = 2.51 %."""
    import numpy as np
    import opendssdirect as dss
    ph = lambda m, a: m * np.exp(1j * np.deg2rad(a))
    v = [ph(230, 0), ph(220, -120), ph(240, 120)]
    # Feed the same phasors through the production function by patching the voltage vector it reads.
    raw = np.empty(6)
    raw[0::2] = [z.real for z in v]
    raw[1::2] = [z.imag for z in v]
    class _FakeCircuit:                       # stands in for dss.Circuit, returning our phasors
        AllBusVolts = staticmethod(lambda: raw)
    class _FakeDss:
        Circuit = _FakeCircuit
    monkeypatch.setattr(f, "dss", _FakeDss)
    got = f.vuf_percent(triples=[(0, 1, 2)])[0]
    assert abs(got - 2.51) < 0.01, got
