"""Stage 8: mitigation by inverter control and by the transformer tap (simulated; IEEE European LV feeder;
synthetic NZ-parameterised load; modelled PV; thermal ratings and VUF limit assumed).

Modes (all single-phase PV, same phase as the customer, AS/NZS 4777.2:2020 Australia A curves from inverter.py,
in pu of 230 V, y-axes in fraction of S_rated):
  M0 unity PF, no control (the Stage 4/6 baseline, here built from PVSystem objects)
  M1 volt-watt only    M2 volt-var only    M3 volt-var + volt-watt (combimode VV_VW)
Inverter kVA = kva_ratio x PV kW rating. Base choice kva_ratio = 1.0 (kVA = kW, i.e. PF 1 at full sun, no spare
kVA for vars: with var priority the inverter then trades P for Q); sensitivity 1.1.
Tap: Transformer.TR1 winding 2 tap = 0.975 lowers the secondary by 2.5 %. The no-load LV phase voltage is
(0.416 kV / sqrt 3) x tap = 240.18 V x tap at source 1.00 pu.

Why a cold start and a settle loop: OpenDSS InvControl moves its set-points in steps and stops when the change
is inside a tolerance (VarChangeTolerance 0.025, ActivePChangeTolerance 0.01, defaults), so where it stops depends
on where it started. If each point started from the previous point's state, the HC search became history
dependent (Stage 8 review: reported HC points above 253 V, M1 above M0). So every snapshot solve with a control
first does CtlModel.cold_start(), then solves and keeps solving until two successive solves agree to 0.02 V and
0.2 % of P. A point's answer is then repeatable, but it is still only accurate to the control tolerance (a
different but equally valid start moved Vmax by about 0.05 V in a test), so HC is quoted to 0.1 kW.
If OpenDSS reports "Max Control Iterations Exceeded" or the power flow does not converge, the point is `nonconverged`.
"""
import numpy as np
import opendssdirect as dss

from . import feeder as f
from . import hosting as h
from . import inverter as inv

MODES = {"M0": None, "M1": "VOLTWATT", "M2": "VOLTVAR", "M3": "VV_VW"}
TAP_BASE, TAP_LOW = 1.000, 0.975
MAX_CONTROL_ITER = 100
SETTLE_V_V, SETTLE_P_FRAC, SETTLE_MAX = 0.02, 0.002, 8
NOLOAD_LV_PHASE_V = 416.0 / np.sqrt(3)          # 240.18 V: 0.416 kV winding rating, phase to neutral


class NonConverged(RuntimeError):
    """Power flow or control loop did not settle."""


def apply_tap(tap):
    """Off-load tap on the LV winding: ratio becomes 11 kV : 0.416 kV x tap (tap < 1 lowers the LV)."""
    dss.Command(f"Edit Transformer.TR1 wdg=2 tap={tap}")


def add_invcontrol(mode, pv_names):
    """InvControl for M1/M2/M3 over the named PVSystems (curves built once in inverter.py)."""
    inv.australia_a_curves()
    lst = "[" + ",".join(f"PVSystem.{n}" for n in pv_names) + "]"
    if mode == "M3":
        spec = "combimode=VV_VW vvc_curve1=VV_AusA voltwatt_curve=VW_AusA VoltwattYAxis=KVARATINGPU RefReactivePower=VARMAX"
    elif mode == "M2":
        spec = "mode=VOLTVAR vvc_curve1=VV_AusA RefReactivePower=VARMAX"
    elif mode == "M1":
        spec = "mode=VOLTWATT voltwatt_curve=VW_AusA VoltwattYAxis=KVARATINGPU"
    else:
        raise ValueError(mode)
    dss.Command(f"New InvControl.InvCtl DERList={lst} {spec}")
    dss.Command(f"Set maxcontroliter={MAX_CONTROL_ITER}")


def add_pvsystems(m, kva_ratio):
    """One PVSystem per customer on its own node (same phase as the load), off (irradiance 0) until used.
    %cutin/%cutout = 0 so low sun is not switched off; varFollowInverter=Yes: no vars when not producing."""
    for i, n in enumerate(m.loads):
        dss.Command(f"New PVSystem.PVS_{n} phases=1 bus1={m.nodes[i]} kV=0.23 kVA=1 Pmpp=1 irradiance=0 "
                    f"temperature=25 pf=1 %cutin=0 %cutout=0 varFollowInverter=Yes vminpu=0.7 vmaxpu=1.3")
    m.pvs_names = [f"PVS_{n}" for n in m.loads]


class CtlModel(h.Model):
    """h.Model plus one PVSystem per customer, an optional InvControl, and the tap. Snapshot solves only."""

    def __init__(self, mode="M0", tap=TAP_BASE, kva_ratio=1.0, source_pu=1.0, rating_scale=1.0):
        super().__init__(source_pu, True, rating_scale=rating_scale)
        self.mode, self.tap, self.kva_ratio = mode, tap, kva_ratio
        if tap != 1.0:
            apply_tap(tap)
        add_pvsystems(self, kva_ratio)
        if MODES[mode]:
            add_invcontrol(mode, self.pvs_names)
        self.pv_idx = []
        self.last_p_kw = 0.0
        self.last_info = {}

    def set_case(self, load_case, pv_idx, load_kw=None):
        kw = load_kw if load_kw is not None else self.cases[load_case]
        for n in self.loads:
            dss.Loads.Name(n)
            dss.Loads.kW(kw[n])
        self.pv_idx = list(pv_idx)
        on = set(self.pv_idx)
        # Customers without PV: PVSystem disabled, not only irradiance 0. Review fix: at irradiance 0 (with
        # %cutin=0) a PVSystem in the InvControl list still absorbed volt-var vars up to its kvarMax, which was
        # left over from the previous placement (checked: -4.5 kvar in total fresh, -15.3 kvar after a 30 % case).
        for i, n in enumerate(self.loads):
            if i in on:
                dss.Command(f"Edit PVSystem.PVS_{n} enabled=yes")
            else:
                dss.Command(f"Edit PVSystem.PVS_{n} irradiance=0 enabled=no")

    def _set_pv(self, p_kw):
        """Rating of every PV customer = p_kw, kVA = kva_ratio x p_kw. Must go through the Edit command: the
        python kVARated setter does not update kvarMax, and InvControl scales its vars by kvarMax (a bug found in
        this stage: vars came out as if the inverter were 1 kVA)."""
        irr = 1.0 if p_kw > 0 else 0.0
        p_eff = max(p_kw, 1e-3)
        for i in self.pv_idx:
            dss.Command(f"Edit PVSystem.PVS_{self.loads[i]} Pmpp={p_eff} kVA={p_eff * self.kva_ratio} irradiance={irr}")

    def pv_output(self):
        """(P_kW, Q_kvar) delivered by the PV customers now; + P = generation, + Q = injecting vars."""
        p = q = 0.0
        for i in self.pv_idx:
            dss.Circuit.SetActiveElement(f"PVSystem.PVS_{self.loads[i]}")
            pw = dss.CktElement.Powers()
            p += -pw[0]
            q += -pw[1]
        return p, q

    def _one_solve(self):
        try:
            dss.Solution.Solve()
        except Exception as e:                      # OpenDSS #485: control loop hit MaxControlIter
            raise NonConverged(str(e).splitlines()[0])
        if not dss.Solution.Converged():
            raise NonConverged("power flow not converged")

    def cold_start(self):
        """Put the control back in one fixed starting state, so a point's answer does not depend on the points
        solved before it (review fix, Stage 8). Checked by experiment (dss-python 0.15.7): 'Reset Controls',
        'Calcvoltagebases', InitSnap and disabling/enabling the InvControl do NOT clear its memory; a PV-off solve
        alone leaves about 2 mV of history. What does: re-assigning DERList (rebuilds the InvControl per-PV
        arrays; only the PV customers are listed), putting each PV customer's PVSystem back to %Pmpp=100 pf=1 (undoes the P limit / var set-point the control
        wrote into it), one solve with PV off (fixed voltage start), and DERList again."""
        if not MODES[self.mode]:
            return                                  # M0: no control state; the power flow alone is unique
        if not self.pv_idx:
            dss.Command("Edit InvControl.InvCtl enabled=no")
            return
        dss.Command("Edit InvControl.InvCtl enabled=yes")
        names = [self.pvs_names[i] for i in self.pv_idx]   # only the customers that have PV (set_case)
        lst = "[" + ",".join(f"PVSystem.{n}" for n in names) + "]"
        dss.Command(f"Edit InvControl.InvCtl DERList={lst}")
        for n in names:
            dss.Command(f"Edit PVSystem.{n} %Pmpp=100 pf=1")
        self._set_pv(0.0)
        self._one_solve()
        dss.Command(f"Edit InvControl.InvCtl DERList={lst}")

    def solve(self, p_kw):
        """Cold start (control modes), then set every PV customer's rating to p_kw, solve, and settle.
        Raises NonConverged. Every call starts from the same state, so a retry would give the same answer."""
        self.cold_start()
        self._solve_settle(p_kw)

    def _solve_settle(self, p_kw):
        self._set_pv(p_kw)
        self._one_solve()
        if MODES[self.mode]:
            v_prev = np.array(dss.Circuit.AllBusVMag())[self.cust_idx].max()
            p_prev = self.pv_output()[0]
            for _ in range(SETTLE_MAX):
                self._one_solve()
                v = np.array(dss.Circuit.AllBusVMag())[self.cust_idx].max()
                p = self.pv_output()[0]
                done = abs(v - v_prev) < SETTLE_V_V and abs(p - p_prev) <= SETTLE_P_FRAC * max(p_kw * len(self.pv_idx), 1e-9)
                v_prev, p_prev = v, p
                if done:
                    break
            else:
                raise NonConverged("did not settle")
        self.last_p_kw = p_kw


def hc_with_control(m, ignore=()):
    """h.find_hc on a CtlModel. Returns dict: status ('ok', 'cap' = no violation up to 20 kW, 'nonconverged'),
    hc_kw (None if nonconverged), binding_limit, binding_element, info, and at the HC point p_disp_kw,
    p_avail_kw, curtailed_pct, q_kvar, vmax_v."""
    try:
        hc, lim, el, info = h.find_hc(m, ignore=ignore)
        out = {"status": "cap" if lim.startswith("none") else "ok", "hc_kw": hc, "binding_limit": lim,
               "binding_element": el, "info": info}
        if hc > 0:
            m.solve(hc)
        else:
            m.solve(0.0)
        p, q = m.pv_output()
        avail = hc * len(m.pv_idx)
        out.update(p_disp_kw=p, p_avail_kw=avail, curtailed_pct=(100 * (1 - p / avail) if avail > 0 else 0.0),
                   q_kvar=q, vmax_v=float(np.array(dss.Circuit.AllBusVMag())[m.cust_idx].max()))
        return out
    except NonConverged as e:
        return {"status": "nonconverged", "hc_kw": None, "binding_limit": "nonconverged", "binding_element": str(e),
                "info": {}, "p_disp_kw": None, "p_avail_kw": None, "curtailed_pct": None, "q_kvar": None,
                "vmax_v": None}


# ---------------------------------------------------------------------------------------------------------
# Year (or window) time series with control. 30-min steps, mode=yearly, one Solve per step (the InvControl loop
# runs inside Solve, up to MaxControlIter). Same inputs, shapes and metrics as yearly.run_year, but the PV is a
# PVSystem (irradiance = kWp x PVGIS kW-per-kWp shape) so InvControl can act on it.
# ---------------------------------------------------------------------------------------------------------
import time  # noqa: E402

from . import yearly as Y  # noqa: E402


def run_year_ctl(house_kw, pv_per_kwp, pv_idx, kwp, mode="M3", tap=TAP_BASE, kva_ratio=1.0, n_steps=None, start=0,
                 source_pu=1.0):
    t0 = time.perf_counter()
    m = CtlModel(mode, tap, kva_ratio, source_pu)
    n_steps = n_steps or house_kw.shape[0] - start
    sl = slice(start, start + n_steps)
    for i, n in enumerate(m.loads):
        Y._new_shape(f"nz_{n}", house_kw[sl, i])
        dss.Loads.Name(n)
        dss.Loads.kW(1.0)                       # base 1 kW, the shape multiplier IS the kW (pf 0.95 kept)
        dss.Loads.Yearly(f"nz_{n}")
    on = set(pv_idx)
    m.pv_idx = list(pv_idx)
    if on:
        Y._new_shape("nz_pv", pv_per_kwp[sl])
    for i, n in enumerate(m.loads):
        if i in on:                              # Edit command, not the python setters (kvarMax, see CtlModel._set_pv)
            dss.Command(f"Edit PVSystem.PVS_{n} Pmpp={kwp} kVA={kwp * kva_ratio} irradiance=1 yearly=nz_pv")
        else:                                    # Review fix (same as set_case): a PVSystem left in the InvControl list
            dss.Command(f"Edit PVSystem.PVS_{n} irradiance=0 enabled=no")   # at irradiance 0 still absorbs volt-var vars
    if MODES[mode]:
        if on:                                   # rebuild the DER list with the PV customers only
            lst = "[" + ",".join(f"PVSystem.PVS_{m.loads[i]}" for i in pv_idx) + "]"
            dss.Command(f"Edit InvControl.InvCtl DERList={lst}")
        else:
            dss.Command("Edit InvControl.InvCtl enabled=no")
    dss.Command("Set mode=yearly stepsize=30m number=1")
    dss.Command("Set year=1")
    cust_idx, triples = m.cust_idx, m.triples
    names = [x.lower() for x in dss.PDElements.AllNames()]
    line_pos = [names.index("line." + n.lower()) for n in m.line_names]
    rating = np.array(m.line_rating_a)
    n_pv = len(pv_idx)
    v_cust = np.empty((n_steps, len(cust_idx)), np.float32)
    line_ratio = np.empty((n_steps, len(line_pos)), np.float32)
    p_hv, kva, loss_kw, vuf = (np.empty(n_steps) for _ in range(4))
    load_kw = np.zeros(n_steps)
    pv_p = np.zeros((n_steps, n_pv))             # float64: energies are summed over ~17,500 steps x 33 inverters
    pv_q = np.zeros((n_steps, n_pv))
    ok = ctl_fail = 0
    load_elems = [f"Load.{n}" for n in m.loads]
    pvs = [f"PVSystem.PVS_{m.loads[i]}" for i in pv_idx]
    for k in range(n_steps):
        try:
            dss.Solution.Solve()
            ok += bool(dss.Solution.Converged())
        except Exception:                       # OpenDSS #485 Max Control Iterations Exceeded
            ctl_fail += 1
        v_cust[k] = np.array(dss.Circuit.AllBusVMag())[cust_idx]
        line_ratio[k] = np.array(dss.PDElements.AllMaxCurrents())[line_pos] / rating
        dss.Circuit.SetActiveElement("Transformer.tr1")
        p = dss.CktElement.Powers()[:6]
        p_hv[k] = sum(p[0::2])
        kva[k] = np.hypot(p_hv[k], sum(p[1::2]))
        loss_kw[k] = dss.Circuit.Losses()[0] / 1000.0
        vuf[k] = f.vuf_percent(triples).max()
        for e in load_elems:
            dss.Circuit.SetActiveElement(e)
            load_kw[k] += sum(dss.CktElement.Powers()[0::2])
        for j, e in enumerate(pvs):
            dss.Circuit.SetActiveElement(e)
            pw = dss.CktElement.Powers()
            pv_p[k, j], pv_q[k, j] = -pw[0], -pw[1]       # + = generation / injecting vars
    return {"model": m, "v_cust_v": v_cust, "line_ratio": line_ratio, "p_hv_kw": p_hv, "kva": kva,
            "loss_kw": loss_kw, "vuf_pct": vuf, "pv_kw_per_step": pv_p.sum(axis=1), "pv_p": pv_p, "pv_q": pv_q,
            "load_kw": load_kw, "converged": ok, "ctl_fail_steps": ctl_fail, "n_steps": n_steps,
            "pv_avail_kw_per_step": kwp * n_pv * pv_per_kwp[sl], "runtime_s": time.perf_counter() - t0}
