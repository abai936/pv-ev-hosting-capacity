"""Stage 3: "neutral-return" variant of the IEEE European LV feeder.

Why (see scripts/stage3_neutral_check.py for the numbers):
Every line in the feeder is a 3-phase, Kron-reduced line (no explicit neutral; node 0 is ideal ground at
every bus). For a Kron-reduced line, the phase self impedance is Zs = (2 Z1 + Z0) / 3 and the mutual is
Zm = (Z0 - Z1) / 3. The 2-core service codes have Z0 = Z1 (2c_16 nearly so), so Zm = 0 and a single-phase
current only sees ONE conductor. The real path is phase out and neutral back, so the loop is about
Zphase + Zneutral (= 2 x Zphase for two equal cores).

Kron reduction of phase conductors (Zp each) plus a neutral (Zn), ignoring coupling between them, gives
Zs = Zp + Zn and Zm = Zn, so Z1 = Zp and Z0 = Zp + 3 Zn. This module sets Z0 = Z1 (1 + 3 k) with k = Zn/Zp
(argument `scale`) for the codes that lack a neutral return. The 4-core codes already have
(R0 - R1)/3 = 0.79 to 0.86 x R1, i.e. they include a neutral return, so they are left alone.

Assumptions (believed, not sourced): neutral core same material and size as the phase core (k = 1);
loop reactance = 2 x X1 (same spacing); no earth path in parallel with the neutral; the existing R1/X1
are per-conductor values. Feeder data files are never edited: only OpenDSS commands after compile.
"""
import opendssdirect as dss

# Codes whose sequence data gives no (or negative) neutral return. 35_SAC_XSC has R0 < R1, which would
# mean a NEGATIVE neutral resistance, so it is treated the same way (assumed equal concentric neutral).
NO_RETURN_CODES = ("2c_.007", "2c_.0225", "2c_16", "35_sac_xsc")


def neutral_return_ohm_per_km(code):
    """Implied neutral impedance Zn = (Z0 - Z1)/3 (ohm/km) for a linecode in the active circuit."""
    dss.LineCodes.Name(code)
    return (dss.LineCodes.R0() - dss.LineCodes.R1()) / 3, (dss.LineCodes.X0() - dss.LineCodes.X1()) / 3


def apply_neutral_return(scale=1.0, codes=NO_RETURN_CODES):
    """Run after feeder.load_feeder(). Sets R0 = R1 (1 + 3 scale), X0 = X1 (1 + 3 scale) for `codes`,
    then re-assigns the linecode on every line that uses it (OpenDSS copies linecode data into a line
    when it is assigned, so editing the code alone does not change existing lines; checked).
    scale = Zneutral / Zphase. scale=0 gives Z0 = Z1 (the published model for the 2c_.007/.0225 codes).
    Returns {code: number of lines changed}."""
    codes = [c.lower() for c in codes]
    for c in codes:
        dss.LineCodes.Name(c)
        if dss.LineCodes.Name().lower() != c:
            raise KeyError(f"linecode {c} not in circuit")
        r1, x1 = dss.LineCodes.R1(), dss.LineCodes.X1()     # ohm per linecode unit (km here)
        dss.Command(f"Edit LineCode.{c} R0={r1 * (1 + 3 * scale):.9g} X0={x1 * (1 + 3 * scale):.9g}")
    changed = {c: 0 for c in codes}
    for name in dss.Lines.AllNames():
        dss.Lines.Name(name)
        lc = dss.Lines.LineCode().lower()
        if lc in changed:
            length, units = dss.Lines.Length(), dss.Lines.Units()
            dss.Command(f"Edit Line.{name} linecode={lc}")
            dss.Lines.Name(name)
            # Re-assigning keeps length and units (checked), but guard against a silent change.
            if abs(dss.Lines.Length() - length) > 1e-12 or dss.Lines.Units() != units:
                raise RuntimeError(f"Line.{name}: length/units changed on linecode re-assign")
            changed[lc] += 1
    return changed


def service_line_of(load):
    """Name of the line whose Bus2 is the load's bus (the last service segment)."""
    dss.Circuit.SetActiveElement(f"Load.{load}")
    bus = dss.CktElement.BusNames()[0].split(".")[0].lower()
    for name in dss.Lines.AllNames():
        dss.Lines.Name(name)
        if dss.Lines.Bus2().split(".")[0].lower() == bus:
            return name
    raise KeyError(load)


def service_drop_check(load="load1", kw=5.0):
    """Snapshot solve with `load` set to `kw` (pf 0.95, others at base kW). For the service line into
    that load returns the OpenDSS drop |V_send| - |V_recv| on the load's phase, and the hand formulas
    one-conductor dV = R I cos(phi) + X I sin(phi) and loop dV = 2 x that, where R = R1 x length,
    X = X1 x length, phi = angle(V_recv) - angle(I). Volts."""
    import numpy as np
    dss.Command(f"Edit Load.{load} kW={kw} pf=0.95")
    dss.Command("Set mode=snapshot")
    dss.Solution.Solve()
    dss.Circuit.SetActiveElement(f"Load.{load}")
    ph = int(dss.CktElement.BusNames()[0].split(".")[1])
    line = service_line_of(load)
    dss.Lines.Name(line)
    code, length = dss.Lines.LineCode(), dss.Lines.Length()            # length in m
    dss.LineCodes.Name(code)
    r = dss.LineCodes.R1() * length / 1000                             # linecode units are km (checked)
    x = dss.LineCodes.X1() * length / 1000
    dss.Circuit.SetActiveElement(f"Line.{line}")
    v = np.array(dss.CktElement.Voltages()); v = v[0::2] + 1j * v[1::2]
    i = np.array(dss.CktElement.Currents()); i = i[0::2] + 1j * i[1::2]
    nc = dss.CktElement.NumConductors()
    vs, vr, ia = v[ph - 1], v[nc + ph - 1], i[ph - 1]
    phi = np.angle(vr) - np.angle(ia)
    one = abs(ia) * (r * np.cos(phi) + x * np.sin(phi))
    other_i = max(abs(i[k]) for k in range(nc) if k != ph - 1)
    return {"load": load, "line": line, "linecode": code, "length_m": length, "phase": ph,
            "I_A": abs(ia), "other_phase_I_A": other_i, "cosphi": np.cos(phi),
            "dV_opendss_V": abs(vs) - abs(vr), "dV_one_conductor_V": one, "dV_loop_V": 2 * one}
