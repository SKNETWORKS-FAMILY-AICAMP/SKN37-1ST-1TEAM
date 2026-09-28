"""Shared image/UI helpers extracted from the original Streamlit app."""
import base64
import io
from urllib.parse import quote

import streamlit as st

from .config import (
    BUILDING_SVG,
    CAR_SVG,
    HOME_IMAGES,
    HYUNDAI_SVG,
    KIA_SVG,
    RECO_MAGIC_SVG,
    RECO_STATS_SVG,
    STATIC_DIR,
    HOME_CSS,
)

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
