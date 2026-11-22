# Project 1 website (not published)

A plain results site for the PV and EV hosting capacity project (OpenDSS and Python, IEEE European LV test feeder). Built with Astro. It is not published.

## Run it

    npm install
    npm run dev
    npm run build

## Data

Figures and chart JSON come from `../results`. They are built by `scripts/build_chart_data.py` and `scripts/build_feeder_svg.py`, which read local, git-ignored feeder data (not committed).

## Notice

Everything shown is simulated, on synthetic NZ-parameterised data with assumed cable ratings. Nothing here is measured.
