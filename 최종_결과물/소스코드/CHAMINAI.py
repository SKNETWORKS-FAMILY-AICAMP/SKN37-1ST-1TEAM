# ============================================================
# 이 파일(app.py) 전체 구조 안내 (사이드바 메뉴탭이 나오는 순서와 동일하게 정리함)
#   1) 제미나이(무료 AI) 호출 함수
#   2) 메인(홈) 페이지 — 사이드바에서 "Main Page"를 눌렀을 때 뜨는 화면
#   3) AI 챗봇 — 사이드바 "AI 챗봇" 메뉴
#   4) 자동차 추천 시스템 — "추천 받기" 화면 + "통계 확인" 화면
#   5) 기업 FAQ 메뉴 — 17개 브랜드 FAQ (하나의 함수가 모든 브랜드를 같이 처리함)
#   6) 월납입금 계산기 — 사이드바 "월납입금 계산기" 메뉴
#   7) 맨 아래: 사이드바 메뉴를 읽어서 위 화면 중 하나를 실제로 그려주는 라우팅 코드
# ============================================================

# ---- 파이썬 기본 제공 라이브러리 -----------------------------------------------
import base64   # 이미지를 글자(문자열)로 바꿀 때 사용 (data URI 인코딩)
import io       # 이미지를 파일로 저장하지 않고 메모리에서 바로 다루기 위해 사용
import json     # AI에게 "JSON 형식으로만 답해줘"라고 요청한 응답을 파싱할 때 사용
import os       # .env 에 적어둔 환경변수(API 키 등)를 읽어올 때 사용
import re       # DB에서 읽어온 "12.5㎞/ℓ" 같은 연비 문자열에서 숫자만 뽑아낼 때 사용
import sys      # 실행 경로(폴더) 관련 설정
import time     # AI 호출 실패 시 몇 초 쉬었다가 재시도(sleep)할 때 사용
from pathlib import Path        # 파일/폴더 경로를 다루기 쉽게 해주는 도구
from urllib.parse import quote  # SVG 그림을 URL 안에 넣을 수 있게 글자를 인코딩

# ---- 외부에서 설치한 라이브러리 (requirements.txt 참고) ------------------------
import pandas as pd             # 표(DataFrame) 형태로 데이터를 계산·정렬할 때 사용
import plotly.express as px     # 막대·도넛·히스토그램·지도 같은 그래프를 그리는 도구
import plotly.graph_objects as go  # 게이지 차트처럼 좀 더 세밀하게 그래프를 그릴 때 사용
import streamlit as st          # 이 웹앱 화면 자체를 만들어주는 라이브러리

# 어느 폴더에서 실행해도 db.py / data 패키지를 찾을 수 있게 설정
sys.path.insert(0, str(Path(__file__).resolve().parent))

import db  # noqa: E402  (.env 도 여기서 읽는다) — MySQL DB 연결/조회 함수 모음 (db.py 파일)

# 웹페이지 제목과 화면 폭(레이아웃)을 설정. 이 줄은 앱 시작할 때 딱 한 번만 실행됨.
st.set_page_config(page_title="자동차 추천 시스템 및 기업FAQ 조회", layout="wide")

# Bootstrap Icons — AI 상담사 버튼/AI 챗봇 메뉴에 아이콘을 쓰기 위해 CDN에서 아이콘 폰트를 불러온다.
st.markdown(
    '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">',
    unsafe_allow_html=True,
)
AI_ICON_HTML = '<i class="bi bi-android2" style="font-size:1.3rem;"></i>'
HOME_ICON_HTML = '<i class="bi bi-house" style="font-size:1.3rem;"></i>'
RECO_ICON_HTML = '<i class="bi bi-car-front" style="font-size:1.3rem;"></i>'
FAQ_ICON_HTML = '<i class="bi bi-buildings" style="font-size:1.3rem;"></i>'
CALC_ICON_HTML = '<i class="bi bi-calculator" style="font-size:1.3rem;"></i>'

# ---- 제미나이(AI) 관련 기본 설정값 ------------------------------------------
GEMINI_MODEL = os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"  # .env 에 없으면 기본 모델 사용
FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
RETRYABLE_MARKERS = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "overloaded")
RETRY_DELAYS = (1, 2, 4)  # 초 단위: 모델 하나당 최대 3번 재시도 (1초→2초→4초 대기)
MAX_FAQ_SHOWN = 50  # FAQ 검색 결과를 화면에 몇 건까지만 보여줄지


# 제미나이 (무료 AI) ============================================================
def ask_gemini(prompt: str) -> str:
    """제미나이 호출 함수."""
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_KEY") or "").strip()
    if not api_key:
        return "AI 키가 설정되지 않았습니다. .env 파일에 GEMINI_API_KEY 를 넣어주세요."
    try:
        from google import genai
    except ImportError:
        return "google-genai 패키지가 없습니다. `pip install google-genai` 후 다시 실행하세요."

    client = genai.Client(api_key=api_key)
    models = [GEMINI_MODEL] + [m for m in FALLBACK_MODELS if m != GEMINI_MODEL]
    last_error = None
    for model in models:
        error = None
        for delay in (0,) + RETRY_DELAYS:
            if delay:
                time.sleep(delay)
            try:
                resp = client.models.generate_content(model=model, contents=prompt)
                return resp.text or "(AI가 빈 답변을 돌려줬습니다. 다시 시도해 주세요.)"
            except Exception as e:
                error = e
                if any(marker in str(e) for marker in RETRYABLE_MARKERS):
                    continue
                break

        last_error = error
        is_bad_model = "404" in str(error) or "NOT_FOUND" in str(error)
        is_transient = any(marker in str(error) for marker in RETRYABLE_MARKERS)
        if not (is_bad_model or is_transient):
            break

    if last_error is not None and any(marker in str(last_error) for marker in RETRYABLE_MARKERS):
        return "지금 AI 서버가 많이 붐빕니다 (일시적 과부하). 잠시 후 다시 시도해 주세요."
    return f"[AI 답변 오류] {last_error}"


# 메인(홈) 페이지 ============================================================
HOME_MENU = "Main Page"
RECOMMEND_MENU = "자동차 추천 시스템"
CHATBOT_MENU = "AI 챗봇"
FAQ_MENU = "기업FAQ 조회"
CALC_MENU = "월납입금 계산기"

MENU_BY_QUERY = {
    "home": HOME_MENU, "chat": CHATBOT_MENU, "recommend": RECOMMEND_MENU,
    "faq": FAQ_MENU, "calc": CALC_MENU,
}

STATIC_DIR = Path(__file__).resolve().parent / "static"
HOME_IMAGES = {
    "car": ("car.jpg", "car.jpeg", "car.png", "car.webp"),
    "building": ("building.jpg", "building.jpeg", "building.png", "building.webp"),
    "hyundai": ("hyundai.jpg", "hyundai.jpeg", "hyundai.png", "hyundai.webp"),
    "kia": ("kia.jpg", "kia.jpeg", "kia.png", "kia.webp"),
    "bmw": ("bmw.jpg", "bmw.jpeg", "bmw.png", "bmw.webp"),
    "benz": ("benz.jpg", "benz.jpeg", "benz.png", "benz.webp"),
    "audi": ("audi.jpg", "audi.jpeg", "audi.png", "audi.webp"),
    "volkswagen": ("volkswagen.jpg", "volkswagen.jpeg", "volkswagen.png", "volkswagen.webp"),
    "volvo": ("volvo.jpg", "volvo.jpeg", "volvo.png", "volvo.webp"),
    "mini": ("mini.jpg", "mini.jpeg", "mini.png", "mini.webp"),
    "landrover": ("landrover.jpg", "landrover.jpeg", "landrover.png", "landrover.webp"),
    "tesla": ("tesla.jpg", "tesla.jpeg", "tesla.png", "tesla.webp"),
    "toyota": ("toyota.jpg", "toyota.jpeg", "toyota.png", "toyota.webp"),
    "lexus": ("lexus.jpg", "lexus.jpeg", "lexus.png", "lexus.webp"),
    "honda": ("honda.jpg", "honda.jpeg", "honda.png", "honda.webp"),
    "chevrolet": ("chevrolet.jpg", "chevrolet.jpeg", "chevrolet.png", "chevrolet.webp"),
    "ford": ("ford.jpg", "ford.jpeg", "ford.png", "ford.webp"),
    "jeep": ("jeep.jpg", "jeep.jpeg", "jeep.png", "jeep.webp"),
    "renault": ("renault.jpg", "renault.jpeg", "renault.png", "renault.webp"),
    "reco_form": ("reco_form.jpg", "reco_form.jpeg", "reco_form.png", "reco_form.webp"),
    "reco_stats": ("reco_stats.jpg", "reco_stats.jpeg", "reco_stats.png", "reco_stats.webp"),
}

CAR_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500" preserveAspectRatio="xMidYMid slice">
<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0f2a5c"/><stop offset="1" stop-color="#2b6cb0"/></linearGradient>
<linearGradient id="body" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ff6b6b"/><stop offset="1" stop-color="#d63447"/></linearGradient>
</defs>
<rect width="800" height="500" fill="url(#sky)"/>
<circle cx="640" cy="120" r="90" fill="#ffd98a" opacity=".18"/>
<circle cx="640" cy="120" r="60" fill="#ffd98a" opacity=".9"/>
<path d="M0 330 L120 250 L220 310 L330 220 L450 320 L560 240 L680 320 L800 260 L800 500 L0 500Z" fill="#183a73" opacity=".8"/>
<rect y="380" width="800" height="120" fill="#1b2438"/>
<rect y="376" width="800" height="8" fill="#2f3b57"/>
<g fill="#f5f5f5" opacity=".8"><rect x="30" y="445" width="90" height="8" rx="4"/><rect x="200" y="445" width="90" height="8" rx="4"/><rect x="510" y="445" width="90" height="8" rx="4"/><rect x="680" y="445" width="90" height="8" rx="4"/></g>
<ellipse cx="400" cy="400" rx="240" ry="16" fill="#000" opacity=".35"/>
<path d="M170 382 L170 337 Q170 317 195 312 L270 300 L320 242 Q332 228 352 228 L468 228 Q488 228 500 242 L548 300 L610 312 Q632 317 632 337 L632 382 Z" fill="url(#body)"/>
<path d="M336 246 L484 246 L528 296 L292 296 Z" fill="#cfe8ff" opacity=".92"/>
<rect x="405" y="246" width="7" height="50" fill="#d63447"/>
<circle cx="275" cy="384" r="42" fill="#111"/><circle cx="275" cy="384" r="20" fill="#9aa4b5"/>
<circle cx="527" cy="384" r="42" fill="#111"/><circle cx="527" cy="384" r="20" fill="#9aa4b5"/>
<rect x="598" y="332" width="30" height="16" rx="6" fill="#ffe27a"/>
<rect x="174" y="332" width="22" height="14" rx="6" fill="#ff8a8a"/>
</svg>"""

BUILDING_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500" preserveAspectRatio="xMidYMid slice">
<defs>
<linearGradient id="sky2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1e1b4b"/><stop offset="1" stop-color="#7c5cbf"/></linearGradient>
<pattern id="win" width="22" height="28" patternUnits="userSpaceOnUse"><rect x="5" y="6" width="11" height="15" rx="2" fill="#ffe9a8" opacity=".9"/></pattern>
<pattern id="win2" width="22" height="28" patternUnits="userSpaceOnUse"><rect x="5" y="6" width="11" height="15" rx="2" fill="#9ad1ff" opacity=".8"/></pattern>
</defs>
<rect width="800" height="500" fill="url(#sky2)"/>
<circle cx="130" cy="105" r="46" fill="#fff" opacity=".9"/>
<g fill="#fff" opacity=".7"><circle cx="300" cy="60" r="2"/><circle cx="520" cy="90" r="2"/><circle cx="640" cy="50" r="2.5"/><circle cx="720" cy="130" r="2"/><circle cx="220" cy="150" r="2"/></g>
<rect x="50" y="230" width="120" height="270" fill="#2b2a63" opacity=".85"/>
<rect x="620" y="200" width="130" height="300" fill="#2b2a63" opacity=".85"/>
<rect x="190" y="210" width="110" height="290" fill="#3d3a8f"/><rect x="190" y="210" width="110" height="290" fill="url(#win2)"/>
<rect x="300" y="100" width="150" height="400" fill="#34317a"/><rect x="300" y="100" width="150" height="400" fill="url(#win)"/>
<rect x="372" y="55" width="6" height="45" fill="#34317a"/><circle cx="375" cy="52" r="5" fill="#ff6b6b"/>
<rect x="450" y="170" width="120" height="330" fill="#3d3a8f"/><rect x="450" y="170" width="120" height="330" fill="url(#win2)"/>
<rect x="570" y="260" width="60" height="240" fill="#2b2a63"/><rect x="570" y="260" width="60" height="240" fill="url(#win)"/>
<rect y="470" width="800" height="30" fill="#16143a"/>
</svg>"""


def _recolor_car(sky1: str, sky2: str, mountain: str, body1: str, body2: str) -> str:
    return (
        CAR_SVG.replace("#0f2a5c", sky1)
        .replace("#2b6cb0", sky2)
        .replace("#183a73", mountain)
        .replace("#ff6b6b", body1)
        .replace("#d63447", body2)
    )


HYUNDAI_SVG = _recolor_car("#0b1f4b", "#2f6fd0", "#14306b", "#eef2f9", "#a9b7cf")
KIA_SVG = _recolor_car("#17171c", "#8a2233", "#2a1a20", "#ffffff", "#c4c4c4")

RECO_MAGIC_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500" preserveAspectRatio="xMidYMid slice">
<defs>
<linearGradient id="magicSky" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1b1140"/><stop offset="1" stop-color="#5b34b3"/></linearGradient>
<linearGradient id="magicBody" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#c9a6ff"/><stop offset="1" stop-color="#8a5cf6"/></linearGradient>
<radialGradient id="magicGlow" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#ffe9a8" stop-opacity=".9"/><stop offset="1" stop-color="#ffe9a8" stop-opacity="0"/></radialGradient>
</defs>
<rect width="800" height="500" fill="url(#magicSky)"/>
<circle cx="620" cy="130" r="110" fill="url(#magicGlow)"/>
<g fill="#fff">
<circle cx="120" cy="90" r="3"/><circle cx="220" cy="150" r="2"/><circle cx="500" cy="60" r="2.5"/>
<circle cx="700" cy="90" r="3"/><circle cx="90" cy="220" r="2"/><circle cx="740" cy="220" r="2.5"/>
</g>
<g fill="#ffe9a8">
<path d="M150 250 L160 275 L185 285 L160 295 L150 320 L140 295 L115 285 L140 275 Z"/>
<path d="M650 300 L657 318 L675 325 L657 332 L650 350 L643 332 L625 325 L643 318 Z"/>
<path d="M420 60 L425 74 L439 79 L425 84 L420 98 L415 84 L401 79 L415 74 Z"/>
</g>
<ellipse cx="400" cy="400" rx="240" ry="16" fill="#000" opacity=".35"/>
<path d="M170 382 L170 337 Q170 317 195 312 L270 300 L320 242 Q332 228 352 228 L468 228 Q488 228 500 242 L548 300 L610 312 Q632 317 632 337 L632 382 Z" fill="url(#magicBody)"/>
<path d="M336 246 L484 246 L528 296 L292 296 Z" fill="#efe4ff" opacity=".92"/>
<rect x="405" y="246" width="7" height="50" fill="#ffe9a8"/>
<circle cx="275" cy="384" r="42" fill="#161029"/><circle cx="275" cy="384" r="20" fill="#a692d6"/>
<circle cx="527" cy="384" r="42" fill="#161029"/><circle cx="527" cy="384" r="20" fill="#a692d6"/>
<rect x="598" y="332" width="30" height="16" rx="6" fill="#ffe9a8"/>
<rect x="174" y="332" width="22" height="14" rx="6" fill="#ffe9a8"/>
</svg>"""

RECO_STATS_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500" preserveAspectRatio="xMidYMid slice">
<defs>
<linearGradient id="statsSky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#04283a"/><stop offset="1" stop-color="#0f6a6a"/></linearGradient>
<linearGradient id="bar1" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#0f9d9d"/><stop offset="1" stop-color="#5fe0c8"/></linearGradient>
</defs>
<rect width="800" height="500" fill="url(#statsSky)"/>
<g fill="#fff" opacity=".18"><line x1="80" y1="120" x2="720" y2="120" stroke="#fff" stroke-width="1"/><line x1="80" y1="230" x2="720" y2="230" stroke="#fff" stroke-width="1"/><line x1="80" y1="340" x2="720" y2="340" stroke="#fff" stroke-width="1"/></g>
<g fill="url(#bar1)">
<rect x="120" y="290" width="80" height="130" rx="6"/>
<rect x="250" y="230" width="80" height="190" rx="6"/>
<rect x="380" y="170" width="80" height="250" rx="6"/>
<rect x="510" y="110" width="80" height="310" rx="6"/>
</g>
<polyline points="160,270 290,205 420,150 550,95" fill="none" stroke="#ffe27a" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
<g fill="#ffe27a"><circle cx="160" cy="270" r="7"/><circle cx="290" cy="205" r="7"/><circle cx="420" cy="150" r="7"/><circle cx="550" cy="95" r="7"/></g>
<rect y="420" width="800" height="80" fill="#04222f"/>
<g fill="#fff" opacity=".8"><rect x="30" y="455" width="90" height="8" rx="4"/><rect x="200" y="455" width="90" height="8" rx="4"/><rect x="510" y="455" width="90" height="8" rx="4"/><rect x="680" y="455" width="90" height="8" rx="4"/></g>
</svg>"""

HOME_CSS = """<style>
.home-hero{text-align:center;padding:1rem 0 1.6rem}
.home-hero h1{font-size:2.3rem;font-weight:800;line-height:1.25;margin:0 0 .6rem;padding:0}
.home-hero p{opacity:.75;font-size:1.05rem;margin:0}
.home-grid{display:grid;grid-template-columns:1fr 1fr;gap:26px;margin:0 0 1.5rem}
a.home-card,a.home-card:hover,a.home-card:visited{color:#fff !important;text-decoration:none !important}
.home-card{position:relative;display:block;height:400px;border-radius:22px;overflow:hidden;background:#111;box-shadow:0 10px 30px rgba(0,0,0,.22);transition:transform .35s ease,box-shadow .35s ease}
.home-card:hover{transform:translateY(-6px);box-shadow:0 18px 44px rgba(0,0,0,.34)}
.home-card img{position:absolute;top:0;left:0;width:100%;height:100%;object-fit:cover;display:block;transition:transform .6s ease}
.home-card:hover img{transform:scale(1.12)}
.home-shade{position:absolute;top:0;left:0;right:0;bottom:0;background:linear-gradient(to top,rgba(0,0,0,.78) 0%,rgba(0,0,0,.25) 55%,rgba(0,0,0,0) 100%)}
.home-text{position:absolute;left:0;right:0;bottom:0;padding:28px 30px}
.home-tag{display:inline-block;font-size:.72rem;letter-spacing:.08em;font-weight:700;padding:4px 10px;border-radius:999px;background:rgba(255,255,255,.22);margin-bottom:10px}
.home-text h3{color:#fff;font-size:1.7rem;font-weight:800;margin:0 0 8px;padding:0}
.home-card-icon{margin-right:10px;vertical-align:-2px}
.home-logo-badge{position:absolute;top:16px;right:16px;width:52px;height:52px;border-radius:14px;background:#fff;box-shadow:0 4px 14px rgba(0,0,0,.28);display:flex;align-items:center;justify-content:center;padding:8px;box-sizing:border-box}
.home-logo-badge img{position:static;width:100%;height:100%;object-fit:contain}
.home-text p{color:rgba(255,255,255,.88);font-size:.98rem;line-height:1.5;margin:0 0 14px}
.home-cta{display:inline-block;font-weight:700;font-size:.95rem;border-bottom:2px solid rgba(255,255,255,.85);padding-bottom:2px;transition:letter-spacing .3s}
.home-card:hover .home-cta{letter-spacing:.04em}
@media (max-width:820px){.home-grid{grid-template-columns:1fr}.home-card{height:320px}.home-hero h1{font-size:1.8rem}}
</style>"""


def go_page(menu_name: str):
    st.session_state["menu"] = menu_name


def _find_home_image(kind: str):
    for fname in HOME_IMAGES[kind]:
        path = STATIC_DIR / fname
        if path.exists():
            return path
    return None


@st.cache_data(show_spinner=False)
def _image_to_data_uri(path_str: str, mtime: float) -> str:
    from PIL import Image

    img = Image.open(path_str).convert("RGB")
    img.thumbnail((1400, 1400))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def home_image_src(kind: str) -> str:
    path = _find_home_image(kind)
    if path is not None:
        try:
            return _image_to_data_uri(str(path), path.stat().st_mtime)
        except Exception:
            pass
    svg = {
        "car": CAR_SVG,
        "building": BUILDING_SVG,
        "hyundai": HYUNDAI_SVG,
        "kia": KIA_SVG,
        "reco_form": RECO_MAGIC_SVG,
        "reco_stats": RECO_STATS_SVG,
    }.get(kind)
    if svg is None:
        svg = BUILDING_SVG if kind in HOME_IMAGES else CAR_SVG
    return "data:image/svg+xml;charset=utf-8," + quote(svg)


def _home_card(
    href: str,
    kind: str,
    tag: str,
    title: str,
    desc: str,
    cta: str,
    icon_html: str = "",
    logo_url: str = "",
) -> str:
    icon_span = f'<span class="home-card-icon">{icon_html}</span>' if icon_html else ""
    logo_span = (
        f'<div class="home-logo-badge"><img src="{logo_url}" alt="{title} 로고"></div>'
        if logo_url
        else ""
    )
    return (
        f'<a class="home-card" href="{href}" target="_self">'
        f'<img src="{home_image_src(kind)}" alt="{title}">'
        f'<div class="home-shade"></div>'
        f"{logo_span}"
        f'<div class="home-text"><span class="home-tag">{tag}</span>'
        f"<h3>{icon_span}{title}</h3><p>{desc}</p><span class=\"home-cta\">{cta}</span></div>"
        f"</a>"
    )


def render_home_stats():
    try:
        faq_n = sum(db.faq_counts().values())
    except Exception:
        faq_n = 0
    c1, c2 = st.columns(2)
    c1.metric("등록된 FAQ", f"{int(faq_n):,} 건")
    c2.metric("추천 시스템 등록 차량", f"{len(SAMPLE_CARS)} 종")


def render_home():
    hero = (
        '<div class="home-hero"><h1>자동차 추천 시스템 &amp; 기업 FAQ</h1>'
        "<p>내 조건에 맞는 차량을 AI가 추천해드리고, 17개 브랜드 FAQ도 AI에게 물어보며 살펴보세요.</p></div>"
    )
    cards = (
        '<div class="home-grid">'
        + _home_card(
            "?menu=recommend",
            "car",
            "AI 추천",
            "자동차 추천 시스템",
            "추천받기와 통계 확인 중 원하는 걸 골라 시작할 수 있어요.",
            "들어가기 →",
        )
        + _home_card(
            "?menu=faq",
            "building",
            "FAQ · AI 상담",
            "기업 FAQ 조회",
            "17개 브랜드 FAQ를 검색하고, 궁금한 점은 AI에게 바로 물어보세요.",
            "FAQ 보러가기 →",
        )
        + "</div>"
    )
    st.markdown(HOME_CSS + hero + cards, unsafe_allow_html=True)

    st.divider()
    render_home_stats()

    st.divider()
    st.markdown("### 무엇을 골라야 할지 모르겠다면?")
    st.write("AI 챗봇에게 편하게 물어보세요 — 차량 추천부터 17개 브랜드 FAQ까지 한 번에 답해드려요.")
    st.button("AI 챗봇 열기", on_click=go_page, args=(CHATBOT_MENU,), key="home_go_chat")


# AI 챗봇 ============================================================
CHATBOT_SYSTEM_NOTE = (
    "너는 '자동차 추천 시스템 및 기업FAQ 조회' 사이트의 AI 챗봇이다. "
    "이 사이트는 (1) 주행거리·지역·예산·선호연료 조건으로 차량을 추천하는 기능과 "
    "(2) 현대·기아·BMW·벤츠 등 17개 브랜드 FAQ 검색 기능을 제공한다. "
    "차량 추천이나 FAQ와 관련 없는 일반적인 질문에도 친절하게 답하되, "
    "차량 구매·FAQ 관련 질문이면 위 두 기능과 자연스럽게 연결지어 안내해줘."
)


def _recent_chat_text(n: int = 6) -> str:
    msgs = st.session_state.get("chat_msgs", [])[-n:]
    return "\n".join(f"{m['role']}: {m['content'][:200]}" for m in msgs)


def classify_chat_intent(user_msg: str, history_text: str) -> dict:
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_KEY") or "").strip()
    if not api_key:
        return {"intent": "general"}
    try:
        from google import genai
    except ImportError:
        return {"intent": "general"}

    prompt = (
        "사용자 메시지를 분석해서 의도를 아래 중 하나로 분류하고, JSON 하나만 출력해라 "
        "(설명이나 코드블록 없이 JSON 텍스트만).\n\n"
        '- "recommend": 차량 구매/추천을 원하는 경우 (예: 차 추천해줘, 전기차 살까 고민, 연비 좋은 차 뭐있어)\n'
        '- "faq": 현대차·기아차 이용 중 궁금한 점 (보증, 정비, 충전, 멤버십 등)\n'
        '- "general": 그 외 일반 대화/질문\n\n'
        "recommend 인 경우 대화 속에서 실제 언급된 값만 채우고, 언급 안 됐으면 null(연료는 빈 리스트):\n"
        '{"intent":"recommend","annual_km":<int|null>,"region":<지역명|null>,'
        '"budget_manwon":<int|null>,"fuel_pref":[<언급된 연료만>]}\n'
        'faq 면 {"intent":"faq"}, general 이면 {"intent":"general"}\n\n'
        f"사용 가능한 지역명: {REGIONS}\n사용 가능한 연료: {FUEL_CHOICES}\n\n"
        f"최근 대화:\n{history_text}\n\n사용자 메시지: {user_msg}"
    )
    try:
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        text = (resp.text or "").strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(text)
    except Exception:
        return {"intent": "general"}


def build_recommend_summary(profile: str, df: pd.DataFrame) -> str:
    lines = [f"사용자 프로필: {profile}\n추천 결과 상위 차량:"]
    for i, row in df.head(3).iterrows():
        lines.append(
            f"{i+1}위: {row['브랜드']} {row['모델명']} ({row['연료']}) - "
            f"실구매가 {row['effective_price']:,.0f}원, 연간연료비 {row['annual_fuel_cost']:,.0f}원, "
            f"종합점수 {row['종합점수']:.1f}점"
        )
    return "\n".join(lines)


def chatbot_answer(user_msg: str) -> str:
    history_text = _recent_chat_text()
    route = classify_chat_intent(user_msg, history_text)
    intent = route.get("intent", "general")

    if intent == "recommend":
        annual_km = route.get("annual_km") or 12000
        region = route.get("region") if route.get("region") in REGIONS else "서울"
        budget = (route.get("budget_manwon") or 3000) * 10_000
        fuel_pref = [f for f in (route.get("fuel_pref") or []) if f in FUEL_CHOICES]

        df = recommend_cars(annual_km, region, 0, budget, fuel_pref, "전체", [], 40, 40, 20)
        if df.empty:
            return "조건에 맞는 차량을 찾지 못했어요. 예산이나 선호 연료를 다르게 말씀해 주시겠어요?"

        profile = (
            f"연간 {annual_km:,}km · {region} 거주 · 예산 {budget:,}원 · "
            f"선호연료 {', '.join(fuel_pref) if fuel_pref else '전체'}"
        )
        table = ["| 순위 | 차량 | 연료 | 연간 연료비 | 실구매가 | 종합점수 |", "|---|---|---|---|---|---|"]
        for i, row in df.head(3).iterrows():
            table.append(
                f"| {i+1} | {row['브랜드']} {row['모델명']} | {row['연료']} | "
                f"{row['annual_fuel_cost']:,.0f}원 | {row['effective_price']:,.0f}원 | {row['종합점수']:.1f}점 |"
            )
        summary = build_recommend_summary(profile, df)
        explanation = ask_gemini(
            "아래는 사용자 조건에 맞춰 계산한 추천 차량 상위 목록이다. "
            "1위 차량이 왜 적합한지 3~4문장으로 친절히 설명해줘. 숫자에 근거해서만 말해줘.\n\n" + summary
        )
        return (
            f"**조건: {profile}**\n\n"
            + "\n".join(table)
            + f"\n\n{explanation}\n\n"
            "조건을 더 세밀하게 조정하고 싶으면 '자동차 추천 시스템' 메뉴도 이용해 보세요."
        )

    if intent == "faq":
        related = db.find_related_faqs(user_msg, limit=5)
        if related:
            context = "\n\n".join(
                f"[{i}] 질문: {r['question']}\n답변: {r['answer']}\n(출처: {r['source']})"
                for i, r in enumerate(related, 1)
            )
        else:
            context = "(관련 FAQ를 찾지 못했음)"
        prompt = (
            "너는 현대·기아·BMW·벤츠 등 17개 브랜드 FAQ 안내 챗봇이다. 아래 [참고 FAQ]에 관련 내용이 있으면 "
            "그것을 우선 근거로 답하고, 없으면 일반적인 자동차 지식으로 최대한 도움이 되게 답하되 "
            "답변 끝에 '※ 공식 FAQ에는 없는 내용이라 참고용으로만 봐주세요.' 를 붙여라. "
            "정확한 수치(가격·기간·전화번호 등)는 근거 없으면 추측하지 말고 확인 방법을 안내해라.\n\n"
            f"[참고 FAQ]\n{context}\n\n[사용자 질문]\n{user_msg}"
        )
        return ask_gemini(prompt)

    return ask_gemini(f"{CHATBOT_SYSTEM_NOTE}\n\n최근 대화:\n{history_text}\n\n사용자: {user_msg}")


def render_chatbot_menu():
    st.header("AI 챗봇")
    st.caption("차량 추천, 17개 브랜드 FAQ, 그 외 자동차 관련 궁금증까지 편하게 물어보세요.")

    if "chat_msgs" not in st.session_state:
        st.session_state["chat_msgs"] = [
            {
                "role": "assistant",
                "content": "안녕하세요! 차량 추천이나 17개 브랜드 FAQ, 그 외 궁금한 점을 편하게 물어보세요",
            }
        ]

    for m in st.session_state["chat_msgs"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    user_msg = st.chat_input("메시지를 입력하세요 (예: 서울 사는데 연간 만km 타는 전기차 추천해줘)")
    if user_msg:
        st.session_state["chat_msgs"].append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.markdown(user_msg)
        with st.chat_message("assistant"):
            with st.spinner("생각하는 중..."):
                reply = chatbot_answer(user_msg)
            st.markdown(reply)
        st.session_state["chat_msgs"].append({"role": "assistant", "content": reply})

    if len(st.session_state["chat_msgs"]) > 1:
        if st.button("대화 초기화"):
            st.session_state["chat_msgs"] = []
            st.rerun()


# 자동차 추천 시스템 (추천받기 + 통계 확인) ============================================================
@st.cache_data(show_spinner="실제 차량·지역 데이터를 불러오는 중...", ttl=3600)
def _load_recommend_data():
    DOMESTIC_BRANDS = {"현대", "기아", "제네시스", "KGM", "르노코리아"}
    PROD_CODE = {"휘발유": "B027", "경유": "D047", "LPG": "K015"}
    REGION_ORDER = [
        "서울",
        "부산",
        "대구",
        "인천",
        "대전",
        "울산",
        "세종",
        "경기",
        "강원",
        "충북",
        "충남",
        "전북",
        "전남광주",
        "경북",
        "경남",
        "제주",
    ]

    oil_rows = db.fetch_all(
        "SELECT sido_nm, prod_cd, price FROM sido_oil_price WHERE prod_cd IN ('B027','D047','K015')"
    )
    oil_by_region: dict = {}
    for r in oil_rows:
        oil_by_region.setdefault(r["sido_nm"], {})[r["prod_cd"]] = float(r["price"])
    regions = [r for r in REGION_ORDER if r in oil_by_region]
    gas_price_base = {
        fuel: round(oil_by_region.get("전국", {}).get(code, 0)) for fuel, code in PROD_CODE.items()
    }

    ev_subsidy = {
        r["sido"]: r["max_subsidy_passenger"] * 10_000
        for r in db.fetch_all(
            "SELECT sido, max_subsidy_passenger FROM electric_car_subsidies WHERE sido != '전국'"
        )
    }

    ev_registration = {
        r["sido"]: r["vehicle_count"]
        for r in db.fetch_all("SELECT sido, vehicle_count FROM electric_vehicles")
    }
    ev_chargers = {
        r["sido"]: r["charger_count"]
        for r in db.fetch_all("SELECT sido, charger_count FROM ev_chargers")
    }

    cars = []
    for r in db.get_car_info():
        eff_str = str(r["avg_efficiency"]) if r["avg_efficiency"] is not None else ""
        m = re.match(r"([\d.]+)", eff_str)
        eff_val = float(m.group(1)) if m else None
        fuel_type = str(r["fuel_type"])
        fuel = "전기" if "전기" in fuel_type else fuel_type.split("+")[0]
        is_ev = fuel == "전기"
        cars.append(
            dict(
                모델명=r["car_name"],
                브랜드=r["brand"],
                세그먼트=r["car_type"],
                연료=fuel,
                연료형태원본=fuel_type,
                연비=(None if is_ev else eff_val),
                전비=(eff_val if is_ev else None),
                출고가=int(r["price_num"]) * 10_000,
                국산차=("국산차" if r["brand"] in DOMESTIC_BRANDS else "수입차"),
            )
        )

    return (
        regions,
        oil_by_region,
        gas_price_base,
        ev_subsidy,
        ev_registration,
        ev_chargers,
        cars,
    )


(
    REGIONS,
    _OIL_PRICE_BY_REGION,
    GAS_PRICE_BASE,
    EV_SUBSIDY,
    EV_REGISTRATION,
    EV_CHARGERS,
    SAMPLE_CARS,
) = _load_recommend_data()


@st.cache_data(show_spinner="차량×지역별 점수 데이터를 불러오는 중...", ttl=3600)
def _load_score_lookup() -> dict:
    lookup = {}
    for r in db.fetch_all("SELECT * FROM view_car_recommend"):
        key = (r["브랜드"], r["차량명"], r["연료형태"], r["sido_nm"])
        try:
            subsidy = float(r["지원받은 보조금"])
        except (TypeError, ValueError):
            subsidy = 0.0
        lookup[key] = dict(
            km_cost=float(r["km당 연료비"]),
            fuel_score=float(r["연비점수"]),
            infra_score=float(r["인프라 점수"]),
            price_score=float(r["실구매가 점수"]),
            infra_note=str(r["인프라 상황"]),
            subsidy=subsidy * 10_000,
        )
    return lookup


SCORE_LOOKUP = _load_score_lookup()

FUEL_CHOICES = ["가솔린", "디젤", "LPG", "하이브리드", "전기"]
ORIGIN_CHOICES = ["전체", "국산차", "수입차"]
CAR_SEGMENTS = sorted({c["세그먼트"] for c in SAMPLE_CARS})


def compute_car_metrics(car: dict, annual_km: int, region: str) -> dict:
    key = (car["브랜드"], car["모델명"], car["연료형태원본"], region)
    info = SCORE_LOOKUP.get(key)
    if info is None:
        return dict(
            annual_fuel_cost=0.0,
            subsidy=0.0,
            effective_price=car["출고가"],
            infra_score=0.0,
            infra_note="",
            연료비점수=0.0,
            가격점수=0.0,
            인프라점수=0.0,
        )
    annual_fuel_cost = info["km_cost"] * annual_km
    subsidy = info["subsidy"]
    effective_price = max(car["출고가"] - subsidy, 0)
    return dict(
        annual_fuel_cost=annual_fuel_cost,
        subsidy=subsidy,
        effective_price=effective_price,
        infra_score=info["infra_score"],
        infra_note=info["infra_note"],
        연료비점수=info["fuel_score"],
        가격점수=info["price_score"],
        인프라점수=info["infra_score"],
    )


def recommend_cars(
    annual_km: int,
    region: str,
    price_min: int,
    price_max: int,
    fuel_pref: list[str],
    origin_pref: str,
    size_pref: list[str],
    w_fuel: float,
    w_price: float,
    w_infra: float,
) -> pd.DataFrame:
    candidates = [
        c
        for c in SAMPLE_CARS
        if (not fuel_pref or c["연료"] in fuel_pref)
        and (origin_pref == "전체" or c["국산차"] == origin_pref)
        and (not size_pref or c["세그먼트"] in size_pref)
    ]
    rows = []
    for car in candidates:
        m = compute_car_metrics(car, annual_km, region)
        rows.append({**car, **m})
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    if price_max:
        within = df[
            (df["effective_price"] >= (price_min or 0)) & (df["effective_price"] <= price_max)
        ]
        df = within if not within.empty else df

    total_w = w_fuel + w_price + w_infra
    if total_w == 0:
        w_fuel = w_price = w_infra = 1
        total_w = 3

    df["종합점수"] = (
        df["연료비점수"] * w_fuel + df["가격점수"] * w_price + df["인프라점수"] * w_infra
    ) / total_w
    return df.sort_values("종합점수", ascending=False).reset_index(drop=True)


def reco_score_breakdown(row: pd.Series, w_fuel: float, w_price: float, w_infra: float) -> dict:
    total_w = w_fuel + w_price + w_infra
    if total_w == 0:
        w_fuel = w_price = w_infra = 1
        total_w = 3
    return dict(
        fuel=row["연료비점수"] * w_fuel / total_w,
        price=row["가격점수"] * w_price / total_w,
        infra=row["인프라점수"] * w_infra / total_w,
        total=row["종합점수"],
    )


def _mini_score_ring_html(value: float, color: str, label: str) -> str:
    value = max(0.0, min(100.0, value))
    deg = value / 100 * 360
    size = 64
    return f"""
<div style="display:flex; flex-direction:column; align-items:center; gap:4px;">
  <div style="
      width:{size}px; height:{size}px; border-radius:50%; flex:0 0 {size}px;
      background: conic-gradient({color} {deg}deg, rgba(200,200,200,0.25) 0deg);
      display:flex; align-items:center; justify-content:center;
  ">
    <div style="
        width:{size - 16}px; height:{size - 16}px; border-radius:50%;
        background: var(--background-color, #fff);
        display:flex; align-items:center; justify-content:center;
        font-size:13px; font-weight:600; color:#333;
    ">{value:.0f}</div>
  </div>
  <div style="font-size:12px; color:#888;">{label}</div>
</div>
"""


def build_reco_reason(
    row: pd.Series, w_fuel: float, w_price: float, w_infra: float, df: pd.DataFrame
) -> str:
    total_w = w_fuel + w_price + w_infra
    if total_w == 0:
        w_fuel = w_price = w_infra = 1
        total_w = 3
    contrib = {
        "연료비": row["연료비점수"] * w_fuel / total_w,
        "가격": row["가격점수"] * w_price / total_w,
        "전기차 인프라": row["인프라점수"] * w_infra / total_w,
    }
    top_factor = max(contrib, key=contrib.get)

    highlights = []
    if row["annual_fuel_cost"] == df["annual_fuel_cost"].min():
        highlights.append("연간 연료비가 후보 중 가장 저렴")
    if row["effective_price"] == df["effective_price"].min():
        highlights.append("실구매가 부담이 후보 중 가장 적음")
    if row["연료"] == "전기" and row["infra_score"] == df["infra_score"].max():
        highlights.append("전기차 충전 인프라 점수가 후보 중 가장 높음")

    if highlights:
        reason = ", ".join(highlights)
    else:
        reason = f"세 요소 중 '{top_factor}' 항목 점수가 특히 높게 계산됨"

    return (
        f"{reason} — 설정하신 우선순위(연료비:가격:인프라 = {w_fuel:.0f}:{w_price:.0f}:{w_infra:.0f}) 기준으로 "
        f"종합점수 {row['종합점수']:.1f}점을 받았습니다."
    )


def extract_reco_conditions(user_msg: str, history_text: str) -> dict:
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_KEY") or "").strip()
    if not api_key:
        return {"in_scope": True}
    try:
        from google import genai
    except ImportError:
        return {"in_scope": True}

    prompt = (
        "너는 '자동차 추천 시스템' 챗봇의 의도 분석기다. 사용자 메시지를 분석해서 JSON 하나만 "
        "출력해라 (설명이나 코드블록 없이 JSON 텍스트만).\n\n"
        '{"in_scope":<true|false>,"region":<지역명|null>,"commute_km":<편도 출퇴근 거리(km)|null>,'
        '"annual_km":<연간 주행거리(km, 명시된 경우만)|null>,"budget_manwon":<예산 상한(만원)|null>,'
        '"origin_pref":<"국산차"|"수입차"|null>,"size_pref":[<언급된 차량 크기만>],"fuel_pref":[<언급된 연료만>]}\n\n'
        "in_scope 는 차량 추천/구매 관련 요청(조건 언급, 추천 요청 등)이면 true, 보증·정비·멤버십 등 "
        "FAQ성 질문이거나 자동차와 무관한 잡담이면 false 로 판단해라. 언급 안 된 값은 null "
        "(리스트는 빈 리스트)로 둬라. '왕복 30km'처럼 왕복으로 말하면 commute_km 는 그 절반(편도) 값으로 넣어라.\n\n"
        f"사용 가능한 지역명: {REGIONS}\n사용 가능한 차량 크기: {CAR_SEGMENTS}\n사용 가능한 연료: {FUEL_CHOICES}\n\n"
        f"최근 대화:\n{history_text}\n\n사용자 메시지: {user_msg}"
    )
    try:
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        text = (resp.text or "").strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(text)
    except Exception:
        return {"in_scope": True}


def render_recommend_menu():
    st.header("자동차 추천 시스템")

    tab1, tab2 = st.tabs(["추천 받기", "통계 확인"])

    with tab1:
        st.subheader("내 맞춤 차량 추천")
        with st.form("recommend_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                annual_km = st.number_input(
                    "연간 주행거리 (km)", min_value=1000, max_value=100000, value=15000, step=1000
                )
                region = st.selectbox("거주 지역", REGIONS, index=0)
            with col2:
                budget_max_man = st.number_input(
                    "최대 예산 (만원, 0은 제한없음)",
                    min_value=0,
                    max_value=20000,
                    value=5000,
                    step=500,
                )
                fuel_pref = st.multiselect("선호 연료", FUEL_CHOICES, default=[])
            with col3:
                origin_pref = st.selectbox("제조사 구분", ORIGIN_CHOICES, index=0)
                size_pref = st.multiselect("차종 크기", CAR_SEGMENTS, default=[])

            st.write("**우선순위 가중치 설정**")
            w_col1, w_col2, w_col3 = st.columns(3)
            with w_col1:
                w_fuel = st.slider("연료비 중요도", 0, 100, 40)
            with w_col2:
                w_price = st.slider("가격 중요도", 0, 100, 40)
            with w_col3:
                w_infra = st.slider("인프라 중요도", 0, 100, 20)

            submitted = st.form_submit_button("차량 추천받기 🚗")

        budget_bytes = budget_max_man * 10000 if budget_max_man > 0 else 0
        df_reco = recommend_cars(
            annual_km=annual_km,
            region=region,
            price_min=0,
            price_max=budget_bytes,
            fuel_pref=fuel_pref,
            origin_pref=origin_pref,
            size_pref=size_pref,
            w_fuel=w_fuel,
            w_price=w_price,
            w_infra=w_infra,
        )

        if df_reco.empty:
            st.warning("조건에 맞는 추천 차량이 없습니다. 검색 조건을 변경해 보세요.")
        else:
            st.subheader("TOP 추천 차량 목록")
            for rank, row in enumerate(df_reco.head(5).itertuples(), 1):
                row_dict = row._asdict()
                with st.expander(
                    f"[{rank}위] {row_dict['브랜드']} {row_dict['모델명']} ({row_dict['연료']}) - 종합 {row_dict['종합점수']:.1f}점",
                    expanded=(rank == 1),
                ):
                    c1, c2, c3 = st.columns([2, 2, 3])
                    with c1:
                        st.write(f"**출고가:** {row_dict['출고가']//10000:,} 만원")
                        st.write(f"**보조금:** {int(row_dict['subsidy'])//10000:,} 만원")
                        st.write(f"**실구매가:** {int(row_dict['effective_price'])//10000:,} 만원")
                        st.write(f"**연간 예상 연료비:** {int(row_dict['annual_fuel_cost']):,} 원")
                    with c2:
                        st.write(f"• 연료비 점수: {row_dict['연료비점수']:.1f}점")
                        st.write(f"• 가격 점수: {row_dict['가격점수']:.1f}점")
                        st.write(f"• 인프라 점수: {row_dict['인프라점수']:.1f}점")
                        if row_dict["infra_note"]:
                            st.caption(f"인프라 참고: {row_dict['infra_note']}")
                    with c3:
                        reason = build_reco_reason(
                            pd.Series(row_dict), w_fuel, w_price, w_infra, df_reco
                        )
                        st.info(f"**추천 이유:**\n{reason}")

    with tab2:
        st.subheader("지역별 & 연료별 차량 데이터 통계")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**지역별 휘발유/디젤 평균 유가 (원)**")
            oil_data = []
            for reg, p in _OIL_PRICE_BY_REGION.items():
                if reg != "전국":
                    oil_data.append(
                        {"지역": reg, "휘발유": p.get("B027", 0), "경유": p.get("D047", 0)}
                    )
            df_oil = pd.DataFrame(oil_data)
            if not df_oil.empty:
                fig_oil = px.bar(
                    df_oil, x="지역", y=["휘발유", "경유"], barmode="group", title="지역별 유가 현황"
                )
                st.plotly_chart(fig_oil, use_container_width=True)

        with col2:
            st.write("**지역별 전기차 보조금 상한 (만원)**")
            df_ev = pd.DataFrame(
                [{"지역": k, "보조금(만원)": v // 10000} for k, v in EV_SUBSIDY.items()]
            )
            if not df_ev.empty:
                fig_ev = px.bar(
                    df_ev, x="지역", y="보조금(만원)", color="보조금(만원)", title="지역별 전기차 승용 보조금"
                )
                st.plotly_chart(fig_ev, use_container_width=True)


# 기업 FAQ 메뉴 ============================================================
def render_faq_menu():
    st.header("기업 FAQ 조회")
    st.caption("17개 주요 자동차 브랜드의 FAQ를 조회하고 AI 상담사에게 문의하세요.")

    brands = [
        "전체",
        "현대",
        "기아",
        "제네시스",
        "KGM",
        "르노코리아",
        "BMW",
        "메르세데스-벤츠",
        "아우디",
        "폭스바겐",
        "볼보",
        "미니",
        "랜드로버",
        "테슬라",
        "토요타",
        "렉서스",
        "혼다",
        "포드",
    ]

    col1, col2 = st.columns([1, 2])
    with col1:
        selected_brand = st.selectbox("브랜드 선택", brands)
    with col2:
        search_term = st.text_input("FAQ 검색어 입력", placeholder="예: 보증기간, 엔진오일, 충전")

    try:
        sql = "SELECT source, question, answer FROM faqs WHERE 1=1"
        params = []
        if selected_brand != "전체":
            sql += " AND source LIKE %s"
            params.append(f"%{selected_brand}%")
        if search_term:
            sql += " AND (question LIKE %s OR answer LIKE %s)"
            params.append(f"%{search_term}%")
            params.append(f"%{search_term}%")
        sql += f" LIMIT {MAX_FAQ_SHOWN}"

        faqs = db.fetch_all(sql, tuple(params))
    except Exception:
        faqs = []

    if faqs:
        st.subheader(f"FAQ 검색 결과 ({len(faqs)}건)")
        for faq in faqs:
            with st.expander(f"[{faq.get('source', '공통')}] {faq.get('question', '')}"):
                st.write(faq.get("answer", ""))
    else:
        st.info("조건에 일치하는 FAQ가 없습니다.")

    st.divider()
    st.subheader("AI FAQ 상담사")
    faq_q = st.text_input("공식 FAQ에 대해 궁금한 점을 AI에게 직접 질문해보세요", key="faq_ai_q")
    if st.button("AI에게 질문하기", key="faq_ai_btn") and faq_q:
        with st.spinner("AI가 답변을 생성 중입니다..."):
            related = (
                db.find_related_faqs(faq_q, limit=5) if hasattr(db, "find_related_faqs") else []
            )
            context = (
                "\n\n".join(
                    f"[{i}] 질문: {r.get('question')}\n답변: {r.get('answer')}\n(출처: {r.get('source')})"
                    for i, r in enumerate(related, 1)
                )
                if related
                else "(관련 FAQ를 찾지 못했음)"
            )

            prompt = (
                "너는 자동차 기업 FAQ 전문 AI 상담사다. 아래 [참고 FAQ]를 기반으로 사용자의 질문에 친절히 답해줘.\n\n"
                f"[참고 FAQ]\n{context}\n\n[사용자 질문]\n{faq_q}"
            )
            answer = ask_gemini(prompt)
            st.markdown(answer)


# 월납입금 계산기 ============================================================
def render_calc_menu():
    st.header("월납입금 계산기")
    st.caption("차량 가격과 할부 조건을 입력하여 월 납입금과 총 이자를 계산해보세요.")

    col1, col2 = st.columns(2)
    with col1:
        car_price_man = st.number_input(
            "차량 가격 (만원)", min_value=100, max_value=50000, value=3500, step=100
        )
        down_payment_man = st.number_input(
            "선납금 / 선수금 (만원)",
            min_value=0,
            max_value=car_price_man,
            value=500,
            step=50,
        )
        interest_rate = st.number_input(
            "연 이자율 (%)", min_value=0.0, max_value=20.0, value=4.5, step=0.1
        )
        loan_months = st.selectbox("할부 기간 (개월)", [12, 24, 36, 48, 60, 72], index=2)

    principal = (car_price_man - down_payment_man) * 10000

    if principal <= 0:
        st.success("선납금이 차량 가격 이상이므로 대출금/할부금이 없습니다.")
        return

    monthly_rate = (interest_rate / 100) / 12
    if monthly_rate > 0:
        monthly_payment = (
            principal
            * (monthly_rate * ((1 + monthly_rate) ** loan_months))
            / (((1 + monthly_rate) ** loan_months) - 1)
        )
    else:
        monthly_payment = principal / loan_months

    total_payment = monthly_payment * loan_months
    total_interest = total_payment - principal

    with col2:
        st.subheader("계산 결과")
        st.metric("예상 월 납입금", f"{int(monthly_payment):,} 원")

        m1, m2 = st.columns(2)
        m1.metric("대출 원금", f"{int(principal):,} 원")
        m2.metric("총 예상 이자", f"{int(total_interest):,} 원")
        st.metric(
            "총 납입 금액", f"{int(total_payment + down_payment_man * 10000):,} 원"
        )

        df_chart = pd.DataFrame(
            {"구분": ["대출 원금", "총 이자"], "금액": [principal, total_interest]}
        )
        fig = px.pie(
            df_chart,
            values="금액",
            names="구분",
            title="원금 및 이자 비중",
            hole=0.4,
            color_discrete_sequence=["#2b6cb0", "#ff6b6b"],
        )
        fig.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)


# 메인 앱 라우팅 및 사이드바 설정 ============================================================
qp_menu = st.query_params.get("menu")
if qp_menu in MENU_BY_QUERY:
    st.session_state["menu"] = MENU_BY_QUERY[qp_menu]
elif "menu" not in st.session_state:
    st.session_state["menu"] = HOME_MENU

st.sidebar.title("메뉴 Navigation")
menu_options = [HOME_MENU, RECOMMEND_MENU, CHATBOT_MENU, FAQ_MENU, CALC_MENU]

selected_menu = st.sidebar.radio(
    "이동할 메뉴를 선택하세요",
    menu_options,
    index=menu_options.index(st.session_state["menu"])
    if st.session_state["menu"] in menu_options
    else 0,
    key="nav_radio",
)

if selected_menu != st.session_state["menu"]:
    st.session_state["menu"] = selected_menu
    inv_map = {v: k for k, v in MENU_BY_QUERY.items()}
    if selected_menu in inv_map:
        st.query_params["menu"] = inv_map[selected_menu]
    st.rerun()

current_menu = st.session_state["menu"]
if current_menu == HOME_MENU:
    render_home()
elif current_menu == RECOMMEND_MENU:
    render_recommend_menu()
elif current_menu == CHATBOT_MENU:
    render_chatbot_menu()
elif current_menu == FAQ_MENU:
    render_faq_menu()
elif current_menu == CALC_MENU:
    render_calc_menu()