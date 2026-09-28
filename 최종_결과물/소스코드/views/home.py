import base64
import io
from urllib.parse import quote
from PIL import Image
import streamlit as st

from config import (
    HOME_CSS, CAR_SVG, BUILDING_SVG, HYUNDAI_SVG, KIA_SVG,
    STATIC_DIR, CHATBOT_MENU
)
from db.faq import faq_counts

def go_page(menu_name: str):
    st.session_state["menu"] = menu_name

def home_image_src(kind: str) -> str:
    path = STATIC_DIR / f"{kind}.jpg"
    if path.exists():
        img = Image.open(path).convert("RGB")
        img.thumbnail((1400, 1400))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=82)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    
    svg = {"car": CAR_SVG, "building": BUILDING_SVG, "hyundai": HYUNDAI_SVG, "kia": KIA_SVG}.get(kind, CAR_SVG)
    return "data:image/svg+xml;charset=utf-8," + quote(svg)

def _home_card(href: str, kind: str, tag: str, title: str, desc: str, cta: str) -> str:
    return (
        f'<a class="home-card" href="{href}" target="_self">'
        f'<img src="{home_image_src(kind)}" alt="{title}">'
        f'<div class="home-shade"></div>'
        f'<div class="home-text"><span class="home-tag">{tag}</span>'
        f'<h3>{title}</h3><p>{desc}</p><span class="home-cta">{cta}</span></div>'
        f'</a>'
    )

def render_home(sample_cars_count: int):
    hero = (
        '<div class="home-hero"><h1>자동차 추천 시스템 &amp; 기업 FAQ</h1>'
        "<p>내 조건에 맞는 차량을 AI가 추천해드리고, 17개 브랜드 FAQ도 AI에게 물어보며 살펴보세요.</p></div>"
    )
    cards = (
        '<div class="home-grid">'
        + _home_card("?menu=recommend", "car", "AI 추천", "자동차 추천 시스템",
                     "추천받기와 통계 확인 중 원하는 걸 골라 시작할 수 있어요.", "들어가기 →")
        + _home_card("?menu=faq", "building", "FAQ · AI 상담", "기업 FAQ 조회",
                     "17개 브랜드 FAQ를 검색하고, 궁금한 점은 AI에게 바로 물어보세요.", "FAQ 보러가기 →")
        + "</div>"
    )
    st.markdown(HOME_CSS + hero + cards, unsafe_allow_html=True)
    st.divider()

    try:
        faq_n = sum(faq_counts().values())
        c1, c2 = st.columns(2)
        c1.metric("등록된 FAQ", f"{int(faq_n):,} 건")
        c2.metric("추천 시스템 등록 차량", f"{sample_cars_count} 종")
    except Exception:
        pass

    st.divider()
    st.markdown("### 무엇을 골라야 할지 모르겠다면?")
    st.write("AI 챗봇에게 편하게 물어보세요 — 차량 추천부터 17개 브랜드 FAQ까지 한 번에 답해드려요.")
    st.button("AI 챗봇 열기", on_click=go_page, args=(CHATBOT_MENU,), key="home_go_chat")