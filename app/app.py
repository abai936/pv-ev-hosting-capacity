"""Stage 10: plain Streamlit results dashboard (reads precomputed results only).

Run from the project root:  .venv\\Scripts\\streamlit run app\\app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st  # noqa: E402

import views  # noqa: E402

st.set_page_config(page_title="PV + EV hosting capacity (simulated)")

choice = st.sidebar.radio("Page", list(views.PAGES.keys()))
st.sidebar.caption("All results are simulated, read from precomputed files.")
views.PAGES[choice]()
