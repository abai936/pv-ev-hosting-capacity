"""Stage 2 toy circuits: small OpenDSS builders plus independent hand calculations (plain complex maths).

Every `solve_*` function builds one circuit in OpenDSS and returns numbers (volts, SI).
Every `hand_*` function repeats the calculation without OpenDSS, so the two can be compared.
"""
import cmath
import math
from pathlib import Path

import opendssdirect as dss

ROOT = Path(__file__).resolve().parents[2]
FEEDERS = ROOT / "data" / "feeders"
SQRT3 = math.sqrt(3)


def _run(lines):
    dss.Basic.ClearAll()
    for ln in lines:
        dss.Command(ln)
    dss.Solution.Solve()
    assert dss.Solution.Converged(), "OpenDSS did not converge"


def node_v(bus):
    """{node number: |V| in volts} for one bus."""
    dss.Circuit.SetActiveBus(bus)
    mags = dss.Bus.VMagAngle()[0::2]
    return dict(zip(dss.Bus.Nodes(), mags))


# ---------------------------------------------------------------- case 1: balanced 2-bus
def solve_two_bus(p_kw, q_kvar):
    """Stiff 415 V LL source, one 0.1+j0.05 ohm/phase line, 3-phase PQ load. Returns load-bus LL volts."""
    _run([
        "New Circuit.toy1 basekv=0.4 pu=1.0375 phases=3 MVAsc3=1e6 MVAsc1=1e6",
        "New Line.L1 bus1=sourcebus bus2=load phases=3 r1=0.1 x1=0.05 r0=0.1 x0=0.05 length=1 units=none",
        f"New Load.LD bus1=load phases=3 conn=wye model=1 kV=0.4 kW={p_kw} kvar={q_kvar} vminpu=0.5 vmaxpu=2",
        "Set voltagebases=[0.4]", "Calcvoltagebases", "Solve",
    ])
    v = node_v("load")
    return sum(v[n] for n in (1, 2, 3)) / 3 * SQRT3  # mean phase V -> LL V


def hand_two_bus(p_kw, q_kvar, v_ll_src=415.0, z_ohm=0.1 + 0.05j):
    """Per-phase circuit: fixed-point iteration I = conj(S_phase / V_load); returns load LL volts."""
    v_src = v_ll_src / SQRT3
    s_ph_va = complex(p_kw, q_kvar) * 1000 / 3
    v = v_src
    for _ in range(200):
        i = (s_ph_va / v).conjugate()
        v = v_src - z_ohm * i
    return abs(v) * SQRT3


# ---------------------------------------------------------------- case 2: 1-phase load, sequence Z
Z1 = 0.1 + 0.05j
Z0 = 0.3 + 0.15j


def solve_single_phase(p_kw):
    """3-phase line with r1/x1/r0/x0, load on phase a only. Returns {1: Va, 2: Vb, 3: Vc} in volts."""
    _run([
        "New Circuit.toy2 basekv=0.4 pu=1.0 phases=3 MVAsc3=1e6 MVAsc1=1e6",
        "New Line.L1 bus1=sourcebus bus2=load phases=3 r1=0.1 x1=0.05 r0=0.3 x0=0.15 length=1 units=none",
        f"New Load.LD bus1=load.1 phases=1 conn=wye model=1 kV=0.23 kW={p_kw} kvar=0",
        "Set voltagebases=[0.4]", "Calcvoltagebases", "Solve",
    ])
    return node_v("load")


def hand_single_phase(p_kw, v_ll_src=400.0):
    """Phase matrix: self Zs=(2Z1+Z0)/3, mutual Zm=(Z0-Z1)/3. Ib=Ic=0, iterate Ia on phase a.
    Returns 'full' (Zs/Zm) and 'balanced' (Z1 only, b and c untouched) magnitudes in volts."""
    zs = (2 * Z1 + Z0) / 3
    zm = (Z0 - Z1) / 3
    vp = v_ll_src / SQRT3
    src = {1: vp, 2: vp * cmath.exp(-2j * math.pi / 3), 3: vp * cmath.exp(2j * math.pi / 3)}
    s_va = p_kw * 1000.0

    def iterate(z):
        va = src[1]
        for _ in range(200):
            ia = (s_va / va).conjugate()
            va = src[1] - z * ia
        return ia, va

    ia, va = iterate(zs)
    full = {1: abs(va), 2: abs(src[2] - zm * ia), 3: abs(src[3] - zm * ia)}
    _, va_bal = iterate(Z1)
    balanced = {1: abs(va_bal), 2: vp, 3: vp}
    return {"full": full, "balanced": balanced}


# ---------------------------------------------------------------- case 3: transformer
def solve_transformer(source_pu, tap=None):
    """Stiff 11 kV source, 800 kVA delta-wye 11/0.416 kV (same ratings as the LV feeder's TR1).
    Secondary carries 1 W. Voltage bases [11 0.4]. Returns (phase volts, phase pu on 230 V base)."""
    cmds = [
        f"New Circuit.toy3 basekv=11 pu={source_pu} phases=3 MVAsc3=1e6 MVAsc1=1e6",
        "New Transformer.TR1 Buses=[SourceBus LV] Conns=[Delta Wye] kVs=[11 0.416] kVAs=[800 800] XHL=4",
        "New Load.LD bus1=LV phases=3 conn=wye model=1 kV=0.4 kW=0.001 kvar=0",
        "Set voltagebases=[11 0.4]", "Calcvoltagebases",
    ]
    if tap:
        cmds.append(f"Transformer.TR1.wdg=1 tap={tap}")
    _run(cmds)
    v = node_v("lv")
    v_ph = sum(v[n] for n in (1, 2, 3)) / 3
    return v_ph, v_ph / 230.0


def hand_transformer(source_pu, tap=1.0):
    """No-load secondary phase volts = 416/sqrt(3) * source pu / tap (tap on the primary side)."""
    return 416.0 / SQRT3 * source_pu / tap


# ---------------------------------------------------------------- case 4: IEEE 13 bus
def solve_ieee13():
    """Compile and solve the IEEE 13-bus case; returns (converged, min pu, max pu) over energised nodes."""
    dss.Basic.ClearAll()
    dss.Command(f'Compile "{FEEDERS / "13Bus" / "IEEE13Nodeckt.dss"}"')
    dss.Solution.Solve()
    pu = [x for x in dss.Circuit.AllBusMagPu() if x > 0.0]  # zero = node not present on that bus
    return dss.Solution.Converged(), min(pu), max(pu)
