"""W5 honesty and number audit for the website (site/). Builds the site once, then checks
docs/site_claims.csv, the banner, banned words, private strings, alt text, authorship and stray files."""
import csv
import html
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
DIST = SITE / "dist"
SRC = SITE / "src"
ROWS = list(csv.DictReader(open(ROOT / "docs" / "site_claims.csv", encoding="utf-8", newline="")))

BANNER = "Simulated. Synthetic NZ-parameterised data. Cable ratings assumed. One feeder. v0.9."
AUTHORSHIP = ("I designed and directed this using generative AI tools: the code was written with AI coding "
              "assistants, and every result went through tests and an independent review.")
CREDIT = "Feeder layout (hero drawing): IEEE PES European LV Test Feeder"


def _visible(raw: str) -> str:
    """Visible text: drop script/style/comments/tags, decode entities, collapse whitespace."""
    raw = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<!--.*?-->", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


@pytest.fixture(scope="module")
def built():
    npm = shutil.which("npm")
    if npm is None:
        pytest.skip("npm is not on PATH; cannot build the site")
    r = subprocess.run([npm, "run", "build"], cwd=SITE, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-1500:]
    pages = {p: p.read_text(encoding="utf-8") for p in DIST.rglob("*.html")}
    assert pages, "no html built"
    return pages


@pytest.fixture(scope="module")
def all_text(built):
    return " ".join(_visible(t) for t in built.values())


def _src_files():
    return [p for p in SRC.rglob("*") if p.is_file() and p.suffix in
            {".astro", ".ts", ".js", ".css", ".json", ".svg", ".md", ".mdx", ".mjs"}]


def _dist_files(exts):
    return [p for p in DIST.rglob("*") if p.is_file() and p.suffix in exts]


def _page(built, rel):
    return built[DIST / rel]


def test_claim_rows_source_and_site(built, all_text):
    assert len(ROWS) >= 44
    bad = []
    for r in ROWS:
        src = ROOT / r["source_file"]
        if not src.is_file():
            bad.append(("missing source", r["claim"], r["source_file"]))
            continue
        if r["value_text"] not in src.read_text(encoding="utf-8"):
            bad.append(("value not in source", r["claim"], r["value_text"]))
        if _norm(r["site_text"]) not in all_text:
            bad.append(("not on site", r["claim"], r["site_text"]))
    assert not bad, bad


@pytest.mark.parametrize("rel", ["index.html", "method/index.html", "about/index.html"])
def test_banner_exactly_once(built, rel):
    text = _visible(_page(built, rel))
    assert text.count(BANNER) == 1, f"{rel}: banner count {text.count(BANNER)}"


BANNED = ["validated", "utility-grade", "production-ready", "certified", "I wrote all",
          "I can explain every file", "compliant with AS/NZS", "months of work", "same as Orion"]


def test_never_claim_words(all_text):
    src_texts = {str(p.relative_to(SITE)): p.read_text(encoding="utf-8", errors="replace") for p in _src_files()}
    hits = []
    for w in BANNED:
        pat = re.compile(re.escape(w), re.I)
        if pat.search(all_text):
            hits.append(("built", w))
        hits += [(name, w) for name, t in src_texts.items() if pat.search(t)]
    assert not hits, hits


def _sentences_with(text, word):
    out = []
    for m in re.finditer(word, text, re.I):
        start = max(text.rfind(".", 0, m.start()), text.rfind("<", 0, m.start()), text.rfind(">", 0, m.start())) + 1
        ends = [i for i in (text.find(".", m.end()), text.find("<", m.end())) if i != -1]
        out.append(_norm(text[start:min(ends) if ends else len(text)]))
    return out


def test_accurate_only_in_negative_sentence(all_text):
    srcs = " ".join(p.read_text(encoding="utf-8", errors="replace") for p in _src_files()
                    if p.suffix in {".astro", ".md", ".mdx"})
    bad = []
    for label, text in (("built", all_text), ("src", srcs)):
        for s in _sentences_with(text, r"\baccurate\b|\baccuracy\b"):
            if not re.search(r"\b(not|never|no)\b", s, re.I):
                bad.append((label, s))
    assert not bad, f"'accurate' outside a negative sentence: {bad}"


PRIVATE = ["C:\\", "C:/Users", "abai936", "\\Users\\", "aucklanduni"]


def test_private_strings_absent():
    files = _src_files() + _dist_files({".html", ".js", ".css", ".json", ".svg"})
    hits = []
    for p in files:
        t = p.read_text(encoding="utf-8", errors="replace")
        for s in PRIVATE:
            if s.lower() in t.lower():
                hits.append((str(p.relative_to(SITE)), s))
    assert not hits, hits


def test_images_and_svgs_have_simulated_labels(built):
    bad = []
    for p, raw in built.items():
        name = str(p.relative_to(DIST))
        for tag in re.findall(r"(?is)<img\b[^>]*>", raw):
            alt = re.search(r'\balt\s*=\s*"([^"]*)"', tag)
            decorative = alt is not None and alt.group(1) == "" and re.search(r"aria-hidden", tag)
            if decorative:
                continue
            if not alt or "simulated" not in alt.group(1).lower():
                bad.append((name, "img", tag[:120]))
        for m in re.finditer(r"(?is)<svg\b([^>]*)>(.*?)</svg>", raw):
            attrs, inner = m.group(1), m.group(2)
            if re.search(r'aria-hidden\s*=\s*"true"', attrs):
                continue
            if re.search(r'role\s*=\s*"img"', attrs):
                label = re.search(r'aria-label\s*=\s*"([^"]*)"', attrs)
                title = re.search(r"(?is)<title[^>]*>(.*?)</title>", inner)
                labelled = (label.group(1) if label else "") + (title.group(1) if title else "")
                if "simulated" not in labelled.lower():
                    bad.append((name, "svg", attrs[:120]))
    assert not bad, bad


def test_forecast_not_prediction_in_uptake_section(built):
    raw = _page(built, "index.html")
    text = _visible(raw)
    assert "forecast, not prediction" in text.lower()


def test_authorship_line_on_about(built):
    assert AUTHORSHIP in _visible(_page(built, "about/index.html"))


def test_no_copied_feeder_data_files(built):
    bad = [str(p) for d in (DIST, SITE / "public") if d.exists()
           for p in d.rglob("*") if p.is_file() and p.suffix.lower() in {".dss", ".csv", ".txt"}]
    assert not bad, bad


def test_only_real_pages(built):
    allowed = {"index.html", "method/index.html", "about/index.html", "404.html"}
    extra = sorted(str(p.relative_to(DIST)).replace("\\", "/") for p in built)
    extra = [e for e in extra if e not in allowed]
    assert not extra, f"delete leftover test page: {extra}"


def test_feeder_credit_on_every_page(built):
    missing = [str(p.relative_to(DIST)) for p, raw in built.items()
               if p.relative_to(DIST).parts[0] != "zz-feeder-test" and CREDIT not in _visible(raw)]
    assert not missing, missing
