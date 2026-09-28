"""Streamlit application entry point."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from chaminai_app.config import (
    AI_ICON_HTML,
    CALC_ICON_HTML,
    FAQ_ICON_HTML,
    HOME_ICON_HTML,
    RECO_ICON_HTML,
)
from chaminai_app.navigation import run_app

def main():
    st.set_page_config(page_title="자동차 추천 시스템 및 기업FAQ 조회", layout="wide")
    st.markdown(
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">',
        unsafe_allow_html=True,
    )

    run_app()

if __name__ == "__main__":
    main()
