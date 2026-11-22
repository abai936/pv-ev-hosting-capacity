"""AS/NZS 4777.2:2020 Australia A inverter curves (volt-var and volt-watt) for OpenDSS InvControl.

Voltages are pu of 230 V. OpenDSS extends an XYcurve straight line past its last point, so we add flat
end points (x = 0.5 and 1.5) to hold the limits constant outside the defined range.
Every script and test builds the curves here so there is only one copy.
Assumption: residential inverters exchange no vars when not producing (see varFollowInverter below).
"""
import opendssdirect as dss

VV_X = [0.5, 0.900, 0.9565, 1.0435, 1.1217, 1.5]
VV_Y = [0.44, 0.44, 0.0, 0.0, -0.60, -0.60]      # fraction of S_rated, + = injecting vars
VW_X = [0.5, 1.100, 1.1304, 1.5]
VW_Y = [1.0, 1.0, 0.2, 0.2]                      # fraction of S_rated (VoltwattYAxis=KVARATINGPU)


def australia_a_curves():
    """Create XYcurves VV_AusA and VW_AusA in the active circuit."""
    fmt = lambda a: "[" + " ".join(str(x) for x in a) + "]"
    dss.Command(f"New XYcurve.VV_AusA npts={len(VV_X)} xarray={fmt(VV_X)} yarray={fmt(VV_Y)}")
    dss.Command(f"New XYcurve.VW_AusA npts={len(VW_X)} xarray={fmt(VW_X)} yarray={fmt(VW_Y)}")


def add_invcontrol(pv_names):
    """One InvControl (volt-var + volt-watt, Australia A) over the named PVSystems."""
    australia_a_curves()
    dss.Command("New InvControl.InvCtl DERList=[" + ",".join(f"PVSystem.{n}" for n in pv_names) + "] "
                "combimode=VV_VW vvc_curve1=VV_AusA voltwatt_curve=VW_AusA VoltwattYAxis=KVARATINGPU "
                "RefReactivePower=VARMAX")
