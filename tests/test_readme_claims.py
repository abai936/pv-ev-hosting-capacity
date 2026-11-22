"""README claims registry (Stage 11): every headline number in README.md must match a results file.
docs/readme_claims.csv columns: claim, value_text (text found in source_file), source_file, readme_text (text found in README.md)."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROWS = list(csv.DictReader(open(ROOT / "docs" / "readme_claims.csv", encoding="utf-8", newline="")))
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_at_least_20_claims():
    assert len(ROWS) >= 20


def test_every_source_file_exists():
    missing = [r["source_file"] for r in ROWS if not (ROOT / r["source_file"]).is_file()]
    assert not missing, missing


def test_value_text_is_in_source_file():
    bad = []
    for r in ROWS:
        text = (ROOT / r["source_file"]).read_text(encoding="utf-8")
        if r["value_text"] not in text:
            bad.append((r["claim"], r["value_text"], r["source_file"]))
    assert not bad, bad


def test_number_with_unit_is_in_readme():
    bad = [(r["claim"], r["readme_text"]) for r in ROWS if r["readme_text"] not in README]
    assert not bad, bad


def test_readme_has_no_local_path():
    assert "C:" + chr(92) + "Users" not in README and "C:/" + "Users" not in README
