"""Stage 7a: snapshot EV hosting capacity on the IEEE European LV feeder (simulated; synthetic NZ-parameterised
load; thermal ratings and VUF limit assumed).

LE = per house, the median of its NON-EV 30-min load over local-time weekday steps starting 19:00, 19:30, 20:00,
20:30 in Jun/Jul/Aug 2022 (winter evening peak, NZST = UTC+12 so no DST jump). Same per-house series as L2.
An EV is a single-phase constant-power consumer at the customer's own node and phase. It is modelled with the
Model's existing per-customer Generator object at NEGATIVE kW (a generator that absorbs power), unity PF.
EV HC = the largest NUMBER of simultaneously charging EVs with no violation, adding EVs one at a time in a
placement order (first failure ends the count)."""
import numpy as np
import opendssdirect as dss

from . import hosting as h
from . import l2
from . import profiles as P

WINTER_MONTHS = (6, 7, 8)
EVENING_HALF_HOURS = (38, 39, 40, 41)     # 19:00, 19:30, 20:00, 20:30 local, half-hour-of-day indices
EV_KW = 7.4                                # single-phase AC charger, ASSUMPTIONS.md A18


def winter_evening_mask(idx_utc):
    """Boolean mask over the UTC grid: local weekday, Jun/Jul/Aug, step starting 19:00 to 20:30 local."""
    loc = idx_utc.tz_convert(P.LOCAL_TZ)
    hh = loc.hour * 2 + loc.minute // 30
    return np.asarray(np.isin(hh, EVENING_HALF_HOURS) & (loc.day_of_week < 5) & np.isin(loc.month, WINTER_MONTHS))


def le_kw(house_kw, idx_utc):
    """Per-house median non-EV kW over the LE steps. Returns (kw[houses], n_steps)."""
    mask = winter_evening_mask(idx_utc)
    return np.median(house_kw[mask], axis=0), int(mask.sum())


def le_p90_kw(house_kw, idx_utc):
    """LE_P90: the ONE evening step (of the LE steps) whose total feeder load is closest to the 90th percentile of
    the step totals, with each house's own load at that step. Returns (kw[houses], timestamp_utc, total_kw, n_steps)."""
    pos = np.flatnonzero(winter_evening_mask(idx_utc))
    tot = house_kw[pos].sum(axis=1)
    j = int(np.argmin(np.abs(tot - np.percentile(tot, 90))))
    return house_kw[pos[j]].copy(), idx_utc[pos[j]], float(tot[j]), len(pos)


def line_phase_currents_a(model, line_name):
    """Phase currents (A, phases 1,2,3) at terminal 1 of a line from the current solution."""
    dss.Lines.Name(line_name)
    cur = dss.CktElement.CurrentsMagAng()[0:2 * dss.Lines.Phases():2]
    return np.array(cur[:3], dtype=float)


def headroom(model, i_a, line_name="line1"):
    """Phase headroom on a line: (rating - I) in A and in kW at 230 V per phase (one-phase EV charging at 230 V
    adds I = P/230). Negative = already over the (assumed) rating."""
    k = model.line_names.index(line_name)
    ha = model.line_rating_a[k] - np.asarray(i_a)
    return ha, ha * 230.0 / 1000.0


# ---- placement orders (a full ordering of the customers; EV count n = first n entries) ----
def order_p1(model):
    """place_p1(n) is NOT nested (its quantile picks move with n), so build one ordered list by repeated calls:
    for n = 1..N append the customers place_p1(n) picks that are not yet in the list. The first n entries are
    then a prefix of the list (equal to place_p1(n) whenever the sets happen to nest). Returns (order,
    n_exactly_nested) where n_exactly_nested counts the n for which set(order[:n]) == set(place_p1(n))."""
    order, nested = [], 0
    for n in range(1, len(model.loads) + 1):
        pick = h.place_p1(model, n)
        order += [i for i in pick if i not in order]
        nested += set(order[:n]) == set(pick)
    return order, nested


def order_p2(model):
    """Far end first: highest path resistance first."""
    return [int(i) for i in np.argsort(-model.path_r)]


def order_p3(model, seed):
    return [int(i) for i in np.random.default_rng(seed).permutation(len(model.loads))]


def find_ev_hc(model, order, ev_kw=EV_KW, pick=None):
    """Add EVs one at a time in `order`. Returns dict: hc (count), binding_limit, binding_element, per-phase
    count of the EVs that fit, info. `pick(k)` (optional) gives the EV set for count k directly instead of order[:k]
    (used for P1_direct = place_p1(k), which is not nested). Baseline (0 EVs) failing gives hc 0 with a 'baseline-' prefix."""
    n_max = len(order)
    pick = pick or (lambda k: order[:k])
    cache = {}

    def viol(k):
        if k not in cache:
            model.set_case("LE", pick(k), load_kw=model.cases["LE"])
            model.solve(-ev_kw)                      # negative generation = consumption
            v = np.array(dss.Circuit.AllBusVMag())[model.cust_idx]
            cache[k] = (model.violations(), model.last_vuf_max_pct, model.last_kva,
                        float(v.min()), line_phase_currents_a(model, "line1"))
        return cache[k][0]

    if viol(0):
        k_fail, hc, prefix = 0, 0, "baseline-"
    else:
        k_fail, prefix = None, ""
        for k in range(1, n_max + 1):
            if viol(k):
                k_fail = k
                break
        hc = (k_fail - 1) if k_fail else n_max
    ph = np.array(model.phase)
    per_phase = [int(sum(ph[i] == p for i in pick(hc))) for p in (1, 2, 3)]
    info = {"vuf_max_pct": cache[hc][1] if hc in cache else None, "xfmr_kva": cache[hc][2] if hc in cache else None,
            "vmin_v": cache[hc][3] if hc in cache else None,
            "line1_i_hc": cache[hc][4] if hc in cache else None,
            "line1_i_fail": cache[k_fail][4] if k_fail is not None else None}
    if k_fail is None:
        return {"hc": hc, "binding_limit": f"none (all {n_max})", "binding_element": "", "per_phase": per_phase,
                "line_linecode": "", "line_phase": "", "info": info}
    w = max(viol(k_fail), key=lambda x: x[2])
    el, lc, lph = w[1], "", ""
    if w[0] == "line":
        model.set_case("LE", pick(k_fail), load_kw=model.cases["LE"])
        model.solve(-ev_kw)
        b = model.line_binding()
        el, lc, lph = b["line"], b["linecode"], b["phase"]
    return {"hc": hc, "binding_limit": prefix + w[0], "binding_element": el, "per_phase": per_phase,
            "line_linecode": lc, "line_phase": lph, "info": info}


def add_ev_load(name, node, kw=EV_KW):
    """A plain constant-power Load (unity PF) at `node` ('34.1'). Used to check Load == negative Generator."""
    dss.Command(f"New Load.{name} phases=1 bus1={node} kV=0.23 kW={kw} pf=1 model=1 vminpu=0.7 vmaxpu=1.3")


def hand_check(ev_kw=EV_KW):
    """One EV at the far-end house (highest path resistance), every other load off, source 1.00 pu.
    Predicted drop = Re(sum Zs over the path) * I with I = P / SOLVED customer voltage (as hosting.hand_check).
    NOTE: this checks the (2R1+R0)/3 loop-resistance model only. The prediction uses model.path_r, the SAME
    path resistance the model code uses for placement, so it is not independent of that helper (it is independent
    of the OpenDSS solve). Returns (predicted_V, opendss_V, customer name, lines on path, I at exactly 230 V in A)."""
    m = h.Model(1.0, True)
    k = int(np.argmax(m.path_r))
    m.set_case("L0", [k])
    m.solve(-ev_kw)
    v = np.array(dss.Circuit.AllBusVMag())
    v_cust, v_lv = v[m.cust_idx[k]], v[m.node_idx[f"1.{m.phase[k]}"]]
    pred = m.path_r[k] * (ev_kw * 1000 / v_cust)
    return pred, v_lv - v_cust, m.loads[k], len(m.path_lines[k]), ev_kw * 1000 / 230.0


def snapshot(model, ev_set, ev_kw=EV_KW):
    """Solve LE with EVs at the customers in ev_set. Returns (min customer voltage V, violations list, line1 I A)."""
    model.set_case("LE", list(ev_set), load_kw=model.cases["LE"])
    model.solve(-ev_kw)
    v = np.array(dss.Circuit.AllBusVMag())[model.cust_idx]
    return float(v.min()), model.violations(), line_phase_currents_a(model, "line1")
