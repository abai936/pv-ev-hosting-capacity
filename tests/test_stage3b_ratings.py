"""Stage 3b: line ratings. 4c_185 R1 must be within 15 % of the Al 185 mm2 datasheet R (0.164 ohm/km, 20 C),
and every line in the feeder must get a rating."""
import csv

import opendssdirect as dss

from hc import feeder as f


def test_4c_185_matches_al_185():
    f.load_feeder(1.0)
    dss.Command("LineCode.4c_185.units=km")
    dss.LineCodes.Name("4c_185")
    r1 = dss.LineCodes.R1()
    assert abs(r1 - 0.164) / 0.164 < 0.15


def test_every_line_has_rating():
    f.load_feeder(1.0)
    ratings = f.line_ratings_a()
    codes = set()
    for n in dss.Lines.AllNames():
        dss.Lines.Name(n)
        codes.add(dss.Lines.LineCode().lower())
    assert codes <= set(ratings)
    assert all(v > 0 for v in ratings.values())
    with open(f.RATINGS_CSV, newline="") as fh:
        assert all(r["rating_condition"].startswith("assumed") for r in csv.DictReader(fh))
