"""Application router and sidebar navigation."""
import sys
from pathlib import Path

import streamlit as st
import base64
from PIL import Image

from .config import *
from .dino_game import render_dino_game
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
    st.session_state.setdefault("logo_click_count", 0)

    # 1. 로고 이미지 클릭 이벤트 감지 (URL 쿼리 파라미터 확인 및 수량 동기화)
    if "logo_click" in st.query_params:
        try:
            # URL로 전달받은 클릭 횟수로 세션 스테이트 업데이트
            clicks = int(st.query_params.get("logo_click", 1))
            st.session_state["logo_click_count"] = clicks
        except ValueError:
            st.session_state["logo_click_count"] += 1
            clicks = st.session_state["logo_click_count"]

        del st.query_params["logo_click"]  # 감지 후 쿼리 파라미터 정리

        if clicks < 3:
            st.toast(f"🔑 이스터에그 힌트: {clicks}/3 회 클릭됨!")
        elif clicks >= 3:
            st.toast("🎉 축하합니다! 공룡 게임이 해금되었습니다!")
            st.session_state["menu"] = DINO_MENU
            st.rerun()

    # 2. 로고 이미지를 클릭 가능한 HTML <a> 태그로 출력 (다음 클릭 수 동적 생성)
    current_clicks = st.session_state.get("logo_click_count", 0)
    next_click = current_clicks + 1

    logo_path = (
        Path(__file__).resolve().parent.parent / "static" / "CHAMINAI.png"
    )
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            encoded_logo = base64.b64encode(f.read()).decode()

        # href에 다음 클릭 횟수를 담아 전달 (?logo_click=1, ?logo_click=2, ...)
        st.sidebar.markdown(
            f"""
            <a href="?logo_click={next_click}" target="_self" style="text-decoration: none;">
                <img src="data:image/png;base64,{encoded_logo}" width="150" style="cursor: pointer; display: block; margin-bottom: 15px; border-radius: 8px;">
            </a>
            """,
            unsafe_allow_html=True,
        )

    # 3. 메뉴 및 페이지 라우팅
    _target = st.query_params.get("menu")
    if _target in MENU_BY_QUERY:
        st.session_state["menu"] = MENU_BY_QUERY[_target]
        if _target == "faq":
            st.session_state["faq_brand"] = BRAND_BY_QUERY.get(
                st.query_params.get("brand")
            )
            st.session_state["faq_nav_gen"] += 1
        if _target == "recommend":
            st.session_state["reco_view"] = RECO_VIEW_BY_QUERY.get(
                st.query_params.get("view")
            )
            st.session_state["reco_nav_gen"] += 1
        st.query_params.clear()

    if "menu" not in st.session_state:
        st.session_state["menu"] = HOME_MENU

    st.sidebar.markdown("**메뉴 선택**")
    st.sidebar.markdown(SIDEBAR_NAV_CSS, unsafe_allow_html=True)

    _nav_button(HOME_MENU, HOME_MENU, "nav_home", icon_html=HOME_ICON_HTML)
    _nav_button(CHATBOT_MENU, CHATBOT_MENU, "nav_chat", icon_html=AI_ICON_HTML)
    _nav_button(
        RECOMMEND_MENU, RECOMMEND_MENU, "nav_reco", icon_html=RECO_ICON_HTML
    )
    _nav_button(FAQ_MENU, FAQ_MENU, "nav_faq", icon_html=FAQ_ICON_HTML)
    _nav_button(CALC_MENU, CALC_MENU, "nav_calc", icon_html=CALC_ICON_HTML)

    # 3번 이상 클릭 시 공룡 게임 메뉴 추가
    if st.session_state.get("logo_click_count", 0) >= 3:
        _nav_button(DINO_MENU, DINO_MENU, "nav_dino", icon_html=DINO_ICON_HTML)

    # 페이지 라우터
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
    elif menu == DINO_MENU:
        st.title("")
        render_dino_game()
    else:
        st.title("")
        render_faq_menu()