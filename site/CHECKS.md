# W4 checks (critique, audit, polish). Source read by hand; no browser was available.

## Critique (findings)
- Hierarchy: h1, then 11 sections each with a small kicker and an h2. Clear, but every section was one long left column (70ch) with the right 40% of the page empty.
- Cards (6 per section) and figures were left-aligned and capped (60rem, charts 40rem), so wide screens looked like a blank page.
- `<details>` summaries ("Data table", "Static image") looked like bold plain text: no marker, no frame.
- Density: 11 sections is a lot, but each has claim list, cards, figure, caveat in the same order. Kept; the new layout makes the order easier to scan.
- Cards use `auto-fit minmax(15rem)`: one column at 360 px, so they cannot overflow (by reading the CSS, not by viewing).
- Two small tap targets per page: the inline links in the footer (Zenodo URL in the citation, "Method and checks").

## Audit (how checked)
- Contrast: node script (WCAG formula) over the colour pairs. Text: ink on paper 14.99, ink-soft on paper 8.47 and on white 9.11, link #1E5AA8 on paper 6.33 and on white 6.81, amber text #7A4F0C on paper 6.62 and on white 7.12, banner and skip link 14.99, table header 13.81, chart text on white 16.11, bar label on grey bar 5.40. All >= 4.5. Non-text: blue 6.81, amber marker 3.64, cap line 5.50 (>= 3). Grey bar fill alone is 2.98 but it has a 1 px ink outline.
- Heading order from dist HTML: index h1,h2,h2,h3,... no skipped level (the hero box h3 was a skip after h1; changed to h2.box-title). method and about also fine.
- Landmarks in dist: header, nav, main, footer on all 3 pages. Skip link present, targets #main, visible on focus, 44 px.
- Focus: global `:focus-visible` 3 px ink outline. Chart points use tabindex=0, role=img, aria-label, and a text readout at the top of the chart on hover or focus (marker stroke also thickens).
- Reduced motion: motion.ts runs only under `no-preference`; the hero draw-on is inside a `no-preference` media query; added a global reduce rule for animation and transition.
- Alt text: every figure alt starts with or contains "Simulated" (read in index.astro). Meta description present on all 3 pages.

## Changed
- Footer: inline links moved into 44 px list rows (Zenodo URL stays as visible text, link is in the list; "Method and checks" now a list link).
- global.css: wide screens (>= 64rem) use a drawing-sheet layout: headline and kicker (with a 2 px top rule) in a left column, claim text beside it, cards, charts, figures, boxes and tables full width; main has thin side rules; figcaptions get a hairline rule above.
- Charts (HcChart, TradeoffChart): at >= 56rem plot is 36rem wide on the left, legend, caption and data table on the right.
- `<details>` summaries: framed 44 px bar with a +/- marker (marker hidden default replaced), hover border.
- Cards wrap long file names (`overflow-wrap: anywhere`, `min-width: 0`); tables wrap; chart tables scroll inside their own box. Phone stacked tables kept.
- Hero "Words used" heading h3 to h2 (heading order).
- Print: banner keeps a black border and no colour dependence; nav and skip link hidden; avoid page breaks inside figures and cards.
- Images already carry width and height (Figure.astro), so no layout shift. Content is plain HTML with no JS needed: the only JS adds a fade-in start state for figures below the fold, and a progress rule. Palette A and motion unchanged.

## Checks run after the change
- `npm run build`: 4 pages built (3 real pages plus the leftover test page src/pages/zz-feeder-test.astro), no errors. `pytest tests/test_site_chart_data.py`: 4 passed.
- dist: banner text exactly once on index, method, about; one h1 each; none of validated, accurate, utility-grade, production-ready, certified, local drive paths or personal email strings in any html.

## NOT checked (no browser)
- Nothing was viewed: the new two-column layout, chart grid and details styling are unrendered. a human reviewer should look at 360, 768 and 1280 px.
- Tap-target sizes were not re-measured; the footer fix is by CSS reading. Other inline prose links (for example "Method and checks" inside caveats) are inline in sentences and may still measure under 44 px (WCAG 2.5.8 inline exception).
- Print output not previewed; closed `<details>` stay closed in print.
- No screen reader or keyboard run-through; no contrast check of the PNG figures.

## Review fixes
- Added the single-phase vs whole-house caveat to the 34% claim; 141.5 hours now says any line, mostly the trunk; 0.003 V now says constant-power loads; mean absolute error; most of the 16 limits have a bias direction.
- About page wording says what was reviewed and that checks were written and run with GenAI coding tools. Figure alts and captions corrected (cp04 line chart, cp06 four cases, cp04_sensitivity L1 vs L2). HcChart and FeederHero captions clarified. README replaced.
- docs/site_claims.csv now uses whole table-row strings and has new rows (see file).

## Round 2 polish (22 Nov 2026)
- Banner: light warm strip (#FBF3DC), ink text 1rem semibold, 1px amber-dark rule, CSS diamond marker (aria-hidden). Contrast by node WCAG script: ink on strip 14.55, amber-dark on strip 6.42 (marker and rule only). Wraps by CSS flex; not viewed in a browser.
- Authorship line changed on all pages to the generative-AI wording; no AI brand or tool named under site/src or dist (grep). tests/test_site_claims.py AUTHORSHIP updated.
- KaTeX rendered at build time (Math.astro, htmlAndMathml, throwOnError); CSS and fonts bundled from the package; no client JS. Six worked examples on Method, two tie-ins on Home; 13 rows added to docs/site_claims.csv.
- Method: checks ladder (7 rungs) with status word plus shape (square, half circle, dashed square).
- Figures get a sheet title strip (number and title derived from the figure id); footer is two columns; type scale tightened.
- Not done: no browser/visual check, no screen-reader check of the MathML.

## Round 3 and 4 visual redo (22 Nov 2026): all light, no dark panels
- Round 3 (dark banner, dark hero, dark footer) was built and then replaced the same day at Aniket's request (no dark colours). Superseded too: the light #FBF3DC banner (Round 2) and the cream page #F6F7F4.
- Grep of src and dist (outside zz-feeder-test) for #F6F7F4, #FBF3DC, #EEF1F3, #EAEEF1, #EEF2F5, #C3CCD4, the old ink/amber/blue hexes and every Round 3 dark token (#F5A524, #12303F, #AFC4D6, #8FD0FF, #D7E2EB, #9CCBFF, #F2F6FA, --dark, --paper): no hits. Ink as a background remains only on three small icons: the 0.55rem site-title square and the filled-square / half-circle status shapes on Method.
- Banner: white strip, 3 px #0F52BA rule at the very top of the page, 1 px #CBD5DF rule under it, ink 16 px (15 px under 40rem) weight 600, solid blue diamond (aria-hidden). Text in one element, once per page (dist count 1 on index, method, about).
- Contrast, node WCAG script (checked). Text (>= 4.5): banner and ink #0B1620 on white 18.26, on band #F2F5F8 16.69; body #1B2733 on white 15.17, on band 13.86 (footer); ink-soft #3B4A58 9.11 / 8.32; link #0F52BA 7.15 / 6.54; amber text #9A5B00 5.43 / 4.96; primary button white on #0F52BA 7.15, hover #0B3F91 9.84.
- Graphics (>= 3): amber stroke/rule #C27400 3.63 on white, 3.31 on band, 3.05 on the sheet grid line #E6ECF2 (the requested #E8920A is 2.46 on white, so it is kept only as the chart circle fill, which has an ink outline). Feeder lines #2B3A47 11.67 (9.81 on grid line), load dots #0F52BA 7.15 (6.01), grey bar #7D8B98 3.49 with ink outline. Decorative only, below 3 by design: sheet grid #E6ECF2 1.19, hairlines #CBD5DF 1.49.
- Meaning-only colour kept: amber = assumed cable rating binds (card top rule, chart circle, trunk, story steps, key-result card); blue = voltage-only (card top rule, triangle marker, P3 band at 16% alpha) and links/buttons. Method "Does NOT prove" rule is ink-soft; maths block rule is ink.
- Hero: white, faint 32 px sheet grid behind the feeder only (masked pseudo-element, fades at the edges), ink headline, thick amber trunk with a 0.22-alpha amber drop-shadow on the top layer only. `--limit` is no longer overridden in the hero, so motion.ts's pulse (var(--limit)) is #C27400; motion.ts not edited. Buttons: blue filled primary, ink outlined secondary. Added: Key result card (the same ResultCard props as the 60% flagship card: 5.0 kW per solar house, same caveat and source) and a Jump to row (#flagship, #tradeoff, #checks, #limits, #uptake). No new numbers.
- Footer: #F2F5F8 band, 1 px top rule, ink text, blue links.
- Ran: `npm run build` (4 pages, no errors); `pytest tests/test_site_claims.py tests/test_site_chart_data.py -q`: 16 passed, 1 failed (test_only_real_pages, expected: zz-feeder-test).
- NOT checked (no browser): nothing viewed. Not seen: banner wrap at 360 px, hero height and stacking at 360/768/1280 px with the new key card, sheet-grid fade, glow strength, tilt with the filter on the top layer, band edges, jump row wrapping.
- Claims registry re-pointed to kept public files (R12, R3); clean-copy test-run line and its rows removed.
