"""Application router and sidebar navigation."""
import sys
from pathlib import Path

import streamlit as st
from PIL import Image

from .config import (
    AI_ICON_HTML,
    CALC_ICON_HTML,
    CALC_MENU,
    CHATBOT_MENU,
    FAQ_ICON_HTML,
    FAQ_MENU,
    HOME_ICON_HTML,
    HOME_MENU,
    MENU_BY_QUERY,
    RECO_ICON_HTML,
    RECOMMEND_MENU,
)
from .chatbot import render_chatbot_menu
from .calculator import render_calc_menu
from .faq import BRAND_BY_QUERY, BRAND_INFO, _faq_display_name, render_faq_menu
from .home import render_home
from .recommendation.core import SCORE_LOOKUP  # noqa: F401
from .recommendation.ui import (
    RECO_VIEW_BY_QUERY,
    render_recommend_menu,
)

SIDEBAR_NAV_CSS = """<style>
.sidebar-nav-btn{
  display:flex; align-items:center; gap:10px; width:100%; box-sizing:border-box;
  padding:0.45rem 0.9rem; margin-bottom:0.5rem; border-radius:8px;
  border:1px solid rgba(128,128,128,0.35); background:transparent;
  color:inherit !important; text-decoration:none !important; font-size:1rem; font-weight:400;
  transition:background-color .15s ease, border-color .15s ease;
}
.sidebar-nav-btn:hover{ border-color:#ff4b4b; color:#ff4b4b !important; }
.sidebar-nav-btn.active{ background-color:#ff4b4b; border-color:#ff4b4b; color:#fff !important; }
.sidebar-nav-btn .bi{ font-size:1.15rem; line-height:1; flex:0 0 auto; }
</style>"""

QUERY_BY_MENU = {v: k for k, v in MENU_BY_QUERY.items()}

def _nav_button(label: str, target_menu: str, key: str, icon_html: str = ""):
    """대분류 메뉴 링크 하나를 그린다. icon_html(bootstrap-icons <i> 태그)을 버튼 글자 왼쪽에
    같이 넣어서, 진짜 버튼 "안에" 아이콘이 들어간 것처럼 보이게 한다.
    (실제로는 홈 화면 카드와 똑같이 ?menu=... 주소로 이동하는 HTML 링크다 — 눌리면 페이지가
    새로고침되면서 맨 위 쿼리파라미터 처리 코드가 session_state["menu"] 를 바꿔준다)"""
    is_active = st.session_state.get("menu") == target_menu
    href = f"?menu={QUERY_BY_MENU[target_menu]}"
    st.sidebar.markdown(
        f'<a class="sidebar-nav-btn{" active" if is_active else ""}" href="{href}" target="_self">'
        f'{icon_html}<span>{label}</span></a>',
        unsafe_allow_html=True,
    )

def run_app():
    """Run the original top-level Streamlit routing/navigation code."""
    st.session_state.setdefault("reco_nav_gen", 0)
    st.session_state.setdefault("faq_nav_gen", 0)

    # --- [로고 추가 영역] ---
    logo_path = Path(__file__).resolve().parent.parent / "static" / "CHAMINAI.png"
    if logo_path.exists():
        # width 값을 조절하여 크기를 줄일 수 있습니다 (기본 추천: 120~180)
        st.sidebar.image(str(logo_path), width=150)
    # ------------------------

    _target = st.query_params.get("menu")

    _target = st.query_params.get("menu")
    if _target in MENU_BY_QUERY:
        st.session_state["menu"] = MENU_BY_QUERY[_target]
        if _target == "faq":
            st.session_state["faq_brand"] = BRAND_BY_QUERY.get(st.query_params.get("brand"))
            st.session_state["faq_nav_gen"] += 1
        if _target == "recommend":
            st.session_state["reco_view"] = RECO_VIEW_BY_QUERY.get(st.query_params.get("view"))
            st.session_state["reco_nav_gen"] += 1
        st.query_params.clear()
    if "menu" not in st.session_state:
        st.session_state["menu"] = HOME_MENU

    st.sidebar.markdown("**메뉴 선택**")
    st.sidebar.markdown(SIDEBAR_NAV_CSS, unsafe_allow_html=True)

    _nav_button(HOME_MENU, HOME_MENU, "nav_home", icon_html=HOME_ICON_HTML)
    _nav_button(CHATBOT_MENU, CHATBOT_MENU, "nav_chat", icon_html=AI_ICON_HTML)
    _nav_button(RECOMMEND_MENU, RECOMMEND_MENU, "nav_reco", icon_html=RECO_ICON_HTML)

    if st.session_state.get("menu") == RECOMMEND_MENU:
        RECO_SUB_OPTIONS = ["자동차 추천 받기", "자동차 통계 확인"]
        RECO_SUB_TO_VIEW = {"자동차 추천 받기": "form", "자동차 통계 확인": "stats"}
        RECO_VIEW_TO_SUB = {v: k for k, v in RECO_SUB_TO_VIEW.items()}
        current_reco_sub = RECO_VIEW_TO_SUB.get(st.session_state.get("reco_view"))
        picked_reco_sub = st.sidebar.radio(
            "　", RECO_SUB_OPTIONS,
            index=(RECO_SUB_OPTIONS.index(current_reco_sub) if current_reco_sub else None),
            key=f"sidebar_reco_sub_{st.session_state['reco_nav_gen']}", label_visibility="collapsed",
        )
        if picked_reco_sub is not None:
            st.session_state["reco_view"] = RECO_SUB_TO_VIEW[picked_reco_sub]

    _nav_button(FAQ_MENU, FAQ_MENU, "nav_faq", icon_html=FAQ_ICON_HTML)

    if st.session_state.get("menu") == FAQ_MENU:
        FAQ_SUB_TO_BRAND = {f"{_faq_display_name(brand)} FAQ": brand for brand in BRAND_INFO}
        FAQ_SUB_OPTIONS = list(FAQ_SUB_TO_BRAND.keys())
        FAQ_BRAND_TO_SUB = {v: k for k, v in FAQ_SUB_TO_BRAND.items()}
        current_faq_sub = FAQ_BRAND_TO_SUB.get(st.session_state.get("faq_brand"))
        picked_faq_sub = st.sidebar.radio(
            "　", FAQ_SUB_OPTIONS,
            index=(FAQ_SUB_OPTIONS.index(current_faq_sub) if current_faq_sub else None),
            key=f"sidebar_faq_sub_{st.session_state['faq_nav_gen']}", label_visibility="collapsed",
        )
        if picked_faq_sub is not None:
            st.session_state["faq_brand"] = FAQ_SUB_TO_BRAND[picked_faq_sub]

    _nav_button(CALC_MENU, CALC_MENU, "nav_calc", icon_html=CALC_ICON_HTML)

    menu = st.session_state["menu"]
    if menu == HOME_MENU:
        render_home()
    elif menu == RECOMMEND_MENU:
        st.title("")
        render_recommend_menu()
    elif menu == CHATBOT_MENU:
        st.title("")
        render_chatbot_menu()
    elif menu == CALC_MENU:
        st.title("")
        render_calc_menu()
    else:
        st.title("")
        render_faq_menu()

    st.divider()
    st.caption("자동차 추천 시스템 및 기업FAQ 조회 시스템")
