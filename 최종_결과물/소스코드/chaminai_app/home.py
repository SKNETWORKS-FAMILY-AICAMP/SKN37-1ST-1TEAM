"""Home page renderer."""
import streamlit as st

import db, base64
import io

from .config import *
from .ui_assets import _home_card
from .recommendation.data import SAMPLE_CARS

def go_page(menu_name: str):
    """보조 버튼용: 사이드바 메뉴를 바꾼다.
    st.session_state 는 스트림릿에서 "지금 화면이 어떤 상태인지" 기억해두는 저장소다.
    버튼을 누르면 이 함수가 실행되면서 session_state["menu"] 값을 바꾸고,
    화면 전체가 다시 그려질 때(rerun) 바뀐 메뉴에 맞는 화면이 나온다."""
    st.session_state["menu"] = menu_name


def _find_home_image(kind: str):
    """static 폴더 안에 car.jpg 같은 실제 사진 파일이 있는지 찾아본다. 없으면 None 반환."""
    for fname in HOME_IMAGES[kind]:
        path = STATIC_DIR / fname
        if path.exists():
            return path
    return None


@st.cache_data(show_spinner=False)
def _image_to_data_uri(path_str: str, mtime: float) -> str:
    """사진을 적당한 크기로 줄여서 HTML 에 바로 넣을 수 있는 글자(data URI)로 바꾼다."""
    from PIL import Image

    img = Image.open(path_str).convert("RGB")
    img.thumbnail((1400, 1400))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def home_image_src(kind: str) -> str:
    """카드에 넣을 이미지 주소를 결정한다: 실제 사진 있으면 사진, 없으면 SVG 일러스트."""
    path = _find_home_image(kind)
    if path is not None:
        try:
            return _image_to_data_uri(str(path), path.stat().st_mtime)
        except Exception:
            pass  # 깨진 이미지 파일이면 기본 일러스트로
    svg = {"car": CAR_SVG, "building": BUILDING_SVG,
           "hyundai": HYUNDAI_SVG, "kia": KIA_SVG,
           "reco_form": RECO_MAGIC_SVG, "reco_stats": RECO_STATS_SVG}.get(kind)
    if svg is None:
        # 15개 수입 브랜드처럼 전용 사진 자리는 있지만 SVG 일러스트가 따로 없는 kind는
        # 기본 건물 일러스트(BUILDING_SVG)로 대신한다.
        svg = BUILDING_SVG if kind in HOME_IMAGES else CAR_SVG
    return "data:image/svg+xml;charset=utf-8," + quote(svg)


def _home_card(href: str, kind: str, tag: str, title: str, desc: str, cta: str, icon_html: str = "",
                logo_url: str = "") -> str:
    """홈/추천선택/FAQ선택 화면에서 공통으로 쓰는 "사진 카드" HTML 한 장을 만들어 반환한다.
    href 를 누르면 그 주소(예: ?menu=recommend)로 이동하고, 마우스를 올리면 CSS 효과(확대)가 나온다.
    icon_html 을 주면 제목 앞에 작은 아이콘(bootstrap-icons)을 같이 그린다.
    logo_url 을 주면 카드 오른쪽 위에 흰색 배지 안에 브랜드 로고(사진)를 올려서 보여준다."""
    # 줄바꿈/빈 줄 없이 한 줄로 만들어야 st.markdown 이 HTML 로 그대로 처리한다
    icon_span = f'<span class="home-card-icon">{icon_html}</span>' if icon_html else ""
    logo_span = f'<div class="home-logo-badge"><img src="{logo_url}" alt="{title} 로고"></div>' if logo_url else ""
    return (
        f'<a class="home-card" href="{href}" target="_self">'
        f'<img src="{home_image_src(kind)}" alt="{title}">'
        f'<div class="home-shade"></div>'
        f'{logo_span}'
        f'<div class="home-text"><span class="home-tag">{tag}</span>'
        f'<h3>{icon_span}{title}</h3><p>{desc}</p><span class="home-cta">{cta}</span></div>'
        f'</a>'
    )


def render_home_stats():
    """DB 에 쌓인 데이터 요약 (DB 가 없거나 비어 있어도 홈 화면은 뜬다)."""
    try:
        faq_n = sum(db.faq_counts().values())
    except Exception:
        return
    c1, c2 = st.columns(2)
    c1.metric("등록된 FAQ", f"{int(faq_n):,} 건")
    c2.metric("추천 시스템 등록 차량", f"{len(SAMPLE_CARS)} 종")


def render_home():
    """사이드바에서 "Main Page"를 선택했을 때 그려지는 첫 화면.
    큰 제목 + 카드 2장(자동차 추천 / 기업FAQ) + 통계 요약 + AI 챗봇 안내 버튼 순서로 구성된다."""
    hero = (
        '<div class="home-hero"><h1>자동차 추천 시스템 &amp; 기업 FAQ</h1>'
        "<p>내 조건에 맞는 차량을 AI가 추천해드리고, 17개 브랜드 FAQ도 AI에게 물어보며 살펴보세요.</p></div>"
    )
    # 카드를 누르면 주소 뒤에 ?menu=recommend 같은 게 붙어서 해당 메뉴로 바로 이동한다
    cards = (
        '<div class="home-grid">'
        + _home_card("?menu=recommend", "car", "AI 추천", "자동차 추천 시스템",
                     "추천받기와 통계 확인 중 원하는 걸 골라 시작할 수 있어요.",
                     "들어가기 →")
        + _home_card("?menu=faq", "building", "FAQ · AI 상담", "기업 FAQ 조회",
                     "17개 브랜드 FAQ를 검색하고, 궁금한 점은 AI에게 바로 물어보세요.",
                     "FAQ 보러가기 →")
        + "</div>"
    )
    st.markdown(HOME_CSS + hero + cards, unsafe_allow_html=True)

    # 카드 클릭이 안 될 때를 대비한 보조 버튼 + DB 요약 통계
    st.divider()
    render_home_stats()

    st.divider()
    st.markdown("### 무엇을 골라야 할지 모르겠다면?")
    st.write("AI 챗봇에게 편하게 물어보세요 — 차량 추천부터 17개 브랜드 FAQ까지 한 번에 답해드려요.")
    st.button("AI 챗봇 열기", on_click=go_page, args=(CHATBOT_MENU,), key="home_go_chat")
