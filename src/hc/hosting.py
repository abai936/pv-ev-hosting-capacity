"""Stage 4: snapshot PV hosting capacity, Orion style (PLAN b3).

One power flow, PV at full output, unity PF, no inverter control. Every PV customer exports the same P (kW).
P is raised in 1 kW steps until a limit breaks, then bisected to 0.01 kW. HC = the largest P with no violation.
Loads are any per-customer kW dict {load_name: kw}. Built in: L1 = one stochastic minute (720) of non-NZ feeder
profiles, L0 = zero load (minimum-load bound). A Stage 6 NZ case (L2) is just another dict.
IEEE European LV feeder, load data synthetic/non-NZ, simulated, thermal ratings assumed.
"""
import math

import numpy as np
import opendssdirect as dss

from . import feeder as f
from . import neutral

VUF_LIMIT_PCT = 2.0          # ASSUMED (EN 50160 basis), ASSUMPTIONS.md A7
XFMR_LIMIT_KVA = 800.0       # nameplate, ASSUMPTIONS.md A6
ORION_CAP_KW = 10.0
SWEEP_MAX_KW = 20
MINUTE = 720                 # 12:00, 0-based index into the 1-min profile
BISECT_KW = 0.01
LINE_TIE_FRAC = 0.005        # lines within 0.5 % of the max loading carry the same (series) current
_UNIT_KM = {1: 1.609344, 2: 0.3048, 3: 1.0, 4: 1e-3, 5: 3.048e-4, 6: 2.54e-5, 7: 1e-5, 8: 1e-6}


def n_pv_for(pen, n_cust):
    """Number of PV customers: ceil, so 30 % of 55 = 17 (not banker's-rounded 16). round(.,9) removes float
    noise such as 0.6*55 = 33.00000000000001."""
    return math.ceil(round(pen * n_cust, 9))


class Model:
    """A compiled feeder plus one disabled generator per customer (the PV) and cached lookups."""

    def __init__(self, source_pu=1.0, neutral_return=True, rating_scale=1.0):
        f.load_feeder(source_pu, nz_base=True, constant_p=True)
        if neutral_return:
            neutral.apply_neutral_return(1.0)
        dss.Command("Set mode=snapshot")
        self.loads = list(dss.Loads.AllNames())
        self.nodes = f.customer_nodes()                       # '34.1' per load
        self.phase = [int(n.split(".")[1]) for n in self.nodes]
        # minute-720 kW per customer from its own profile (loadshapes are multipliers on kW=1)
        self.kw_l1 = []
        for n in self.loads:
            dss.Loads.Name(n)
            base_kw = dss.Loads.kW()
            dss.LoadShape.Name(dss.Loads.Yearly())
            self.kw_l1.append(base_kw * dss.LoadShape.PMult()[MINUTE])
        for n, node in zip(self.loads, self.nodes):
            dss.Command(f"New Generator.PV_{n} phases=1 bus1={node} kV=0.23 kW=0 kvar=0 model=1 "
                        f"vminpu=0.7 vmaxpu=1.3 enabled=no")
        self.line_names = list(dss.Lines.AllNames())
        rat = f.line_ratings_a()
        self.line_rating_a = []
        for n in self.line_names:
            dss.Lines.Name(n)
            self.line_rating_a.append(rat[dss.Lines.LineCode().lower()] * rating_scale)
        idx = f._node_index()
        self.node_idx = idx
        self.cust_idx = [idx[n] for n in self.nodes]
        self.triples = f.three_phase_nodes()
        self.vuf_buses = sorted({k.split(".")[0] for k in idx
                                 if all(f"{k.split('.')[0]}.{p}" in idx for p in (1, 2, 3))})
        self.path_r = self._path_resistance()
        self.cases = {"L0": {n: 0.0 for n in self.loads}, "L1": dict(zip(self.loads, self.kw_l1))}
        self._line_info()
        self.last_vuf_max_pct = self.last_kva = 0.0

    def _path_resistance(self):
        """Re(Zs) summed over the lines from the transformer LV bus ('1') to each customer, ohm.
        Zs = (2 R1 + R0)/3 per length: the one-phase-in, neutral-out loop resistance after the neutral fix.
        Also stores self.path_lines (line names) per customer."""
        parent, r_line = {}, {}
        for n in self.line_names:
            dss.Lines.Name(n)
            b1, b2 = (b.split(".")[0] for b in (dss.Lines.Bus1(), dss.Lines.Bus2()))
            dss.LineCodes.Name(dss.Lines.LineCode())
            km = dss.Lines.Length() * _UNIT_KM[dss.Lines.Units()]
            r_line[n] = (2 * dss.LineCodes.R1() + dss.LineCodes.R0()) / 3 * km   # linecode units are km (Stage 3)
            parent[b2] = (b1, n)
        self.path_lines, out = [], []
        for node in self.nodes:
            bus, r, lines = node.split(".")[0], 0.0, []
            while bus != "1":
                bus, ln = parent[bus]
                r += r_line[ln]
                lines.append(ln)
            out.append(r)
            self.path_lines.append(lines)
        return np.array(out)

    def _line_info(self):
        """Per line: linecode, phase nodes, and depth = number of lines between it and the transformer LV bus."""
        parent = {}
        self.line_code, self.line_phase_nodes, b1s = [], [], []
        for n in self.line_names:
            dss.Lines.Name(n)
            b1, b2 = dss.Lines.Bus1().split("."), dss.Lines.Bus2().split(".")
            parent[b2[0]] = b1[0]
            b1s.append(b1[0])
            self.line_code.append(dss.Lines.LineCode())
            self.line_phase_nodes.append(b1[1:] or ["1", "2", "3"])

        def depth(bus):
            d = 0
            while bus != "1":
                bus, d = parent[bus], d + 1
            return d
        self.line_depth = [depth(b) + 1 for b in b1s]

    def line_binding(self):
        """Binding line from the CURRENT solution. Series lines carry the same current, so the single 'max'
        line is float noise: take all lines within 0.5 % of the max loading and report the one nearest the
        transformer, its linecode and the phase with the highest current, plus the chain length."""
        ratio, ph = [], []
        for n, rating, nodes in zip(self.line_names, self.line_rating_a, self.line_phase_nodes):
            dss.Lines.Name(n)
            cur = dss.CktElement.CurrentsMagAng()[0:2 * dss.Lines.Phases():2]
            k = int(np.argmax(cur))
            ratio.append(cur[k] / rating)
            ph.append(nodes[k] if k < len(nodes) else str(k + 1))
        ratio = np.array(ratio)
        near = [i for i in range(len(ratio)) if ratio[i] >= ratio.max() * (1 - LINE_TIE_FRAC)]
        i = min(near, key=lambda j: self.line_depth[j])
        return {"line": self.line_names[i], "linecode": self.line_code[i], "phase": ph[i],
                "chain_len": len(near), "loading_pct": 100 * ratio[i]}

    # ---- one load flow ----
    def set_case(self, load_case, pv_idx, load_kw=None):
        """load_kw: any {load_name: kw} dict (e.g. a Stage 6 NZ case). If None, use the built-in `load_case`."""
        kw = load_kw if load_kw is not None else self.cases[load_case]
        for n in self.loads:
            dss.Loads.Name(n)
            dss.Loads.kW(kw[n])
        on = set(pv_idx)
        for i, n in enumerate(self.loads):
            dss.Circuit.SetActiveElement(f"Generator.PV_{n}")
            dss.CktElement.Enabled(i in on)
        self.pv_names = [f"PV_{self.loads[i]}" for i in pv_idx]

    def solve(self, p_kw):
        for n in self.pv_names:
            dss.Generators.Name(n)
            dss.Generators.kW(p_kw)
        dss.Solution.Solve()
        if not dss.Solution.Converged():
            raise RuntimeError(f"no convergence at {p_kw} kW")

    def violations(self):
        """List of (limit, element, excess) where excess is the normalised exceedance (>0 = violated)."""
        out = []
        v = np.array(dss.Circuit.AllBusVMag())[self.cust_idx]
        for k, vk in enumerate(v):
            if vk > f.V_HIGH_V:
                out.append(("voltage-high", f"{self.loads[k]}@{self.nodes[k]}", (vk - f.V_HIGH_V) / f.V_HIGH_V))
            if vk < f.V_LOW_V:
                out.append(("voltage-low", f"{self.loads[k]}@{self.nodes[k]}", (f.V_LOW_V - vk) / f.V_LOW_V))
        kva = f.transformer_kva()
        self.last_kva = kva
        if kva > XFMR_LIMIT_KVA:
            out.append(("transformer", "TR1", kva / XFMR_LIMIT_KVA - 1))
        for n, rating in zip(self.line_names, self.line_rating_a):
            dss.Lines.Name(n)
            i = max(dss.CktElement.CurrentsMagAng()[0:2 * dss.Lines.Phases():2])
            if i > rating:
                out.append(("line", n, i / rating - 1))
        vuf = f.vuf_percent(self.triples)
        self.last_vuf_max_pct = float(np.max(vuf))
        for b, u in zip(self.vuf_buses, vuf):
            if u > VUF_LIMIT_PCT:
                out.append(("VUF", f"bus{b}", u / VUF_LIMIT_PCT - 1))
        return out


def find_hc(model, ignore=()):
    """Sweep 0 (baseline), 1..20 kW, then bisect to 0.01 kW.
    Returns (hc_kw, binding_limit, binding_element, info). info has vuf_max_pct and xfmr_kva at the HC point
    and, when a line limit binds, line_linecode / line_phase / binding_chain_len.
    `ignore` lists limit names not counted (e.g. ('line',) for the voltage-only HC)."""
    cache = {}

    def run(p):
        if p not in cache:
            model.solve(p)
            cache[p] = (model.violations(), model.last_vuf_max_pct, model.last_kva)
        return cache[p]

    def fails(p):
        return [x for x in run(p)[0] if x[0] not in ignore]

    def finish(p_fail, hc, prefix=""):
        w = max(fails(p_fail), key=lambda x: x[2])
        info = {"vuf_max_pct": run(hc)[1], "xfmr_kva": run(hc)[2]}
        el = w[1]
        if w[0] == "line":
            model.solve(p_fail)                       # make the failing point the active solution
            b = model.line_binding()
            el = b["line"]
            info.update(line_linecode=b["linecode"], line_phase=b["phase"], binding_chain_len=b["chain_len"])
        return hc, prefix + w[0], el, info

    if fails(0.0):
        # Already violating with no export (e.g. low voltage under L1): HC is 0 by definition here.
        return finish(0.0, 0.0, "baseline-")
    last_pass, first_fail = 0.0, None
    for p in range(1, SWEEP_MAX_KW + 1):
        if fails(float(p)):
            first_fail = float(p)
            break
        last_pass = float(p)
    if first_fail is None:
        v, kva = run(float(SWEEP_MAX_KW))[1:]
        return float(SWEEP_MAX_KW), "none (>= %d kW)" % SWEEP_MAX_KW, "", {"vuf_max_pct": v, "xfmr_kva": kva}
    while first_fail - last_pass > BISECT_KW + 1e-9:
        mid = round((first_fail + last_pass) / 2, 4)
        if fails(mid):
            first_fail = mid
        else:
            last_pass = mid
    return finish(first_fail, round(last_pass, 4))


# ---- placement ----
def place_p1(model, n_pv):
    """Orion-like balanced: per phase, customers ranked by path resistance, evenly spaced quantiles picked.
    Counts per phase differ by at most 1 (extras go to the phases with more customers); at 100 % every
    customer is picked, so counts follow the feeder's own phase split."""
    ph = np.array(model.phase)
    members = {p: [int(i) for i in np.argsort(model.path_r) if ph[i] == p] for p in (1, 2, 3)}
    cap = {p: len(m) for p, m in members.items()}
    order = sorted(cap, key=lambda p: (-cap[p], p))
    cnt = {p: 0 for p in cap}
    for _ in range(n_pv):                    # one customer at a time to the emptiest phase that has room
        p = min((q for q in order if cnt[q] < cap[q]), key=lambda q: cnt[q])
        cnt[p] += 1
    pick = []
    for p, k in cnt.items():
        m = len(members[p])
        pick += [members[p][int((j + 0.5) * m / k)] for j in range(k)] if k else []
    return sorted(pick)


def place_p2(model, n_pv):
    """End-clustered: the n_pv customers with the highest path resistance."""
    return sorted(int(i) for i in np.argsort(-model.path_r)[:n_pv])


def place_p3(model, n_pv, seed):
    return sorted(int(i) for i in np.random.default_rng(seed).choice(len(model.loads), n_pv, replace=False))


def hand_check(p_kw=5.0):
    """One customer (highest path resistance) at p_kw, all loads and other PV off, source 1.00 pu.
    Returns (predicted_V, opendss_V, customer name, number of lines on path).
    Predicted = Re(sum Zs) * P / V (Zs per line after the neutral fix). The current P/V uses the SOLVED
    customer voltage (not nominal 230 V), so prediction and OpenDSS share the same operating point."""
    m = Model(1.0, True)
    k = int(np.argmax(m.path_r))
    m.set_case("L0", [k])
    m.solve(p_kw)
    v = np.array(dss.Circuit.AllBusVMag())
    v_cust = v[m.cust_idx[k]]
    v_lv = v[m.node_idx[f"1.{m.phase[k]}"]]
    pred = m.path_r[k] * (p_kw * 1000 / v_cust)
    return pred, v_cust - v_lv, m.loads[k], len(m.path_lines[k])


def write_hand_check(path, p_kw=5.0):
    """Run the hand check and write a CSV (error_pct = 100*(opendss-predicted)/predicted)."""
    import pandas as pd
    pred, sim, name, n = hand_check(p_kw)
    pd.DataFrame([{"customer": name, "p_kw": p_kw, "lines_on_path": n, "predicted_V": pred, "opendss_V": sim,
                   "error_pct": 100 * (sim - pred) / pred,
                   "note": "current = P / solved customer voltage"}]).to_csv(path, index=False)
    return pred, sim, name, n
