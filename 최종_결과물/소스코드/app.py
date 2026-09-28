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
# (streamlit run 을 다른 위치에서 실행해도 같은 폴더의 db.py를 찾도록 경로를 추가함)
sys.path.insert(0, str(Path(__file__).resolve().parent))

import db  # noqa: E402  (.env 도 여기서 읽는다) — MySQL DB 연결/조회 함수 모음 (db.py 파일)

# 웹페이지 제목과 화면 폭(레이아웃)을 설정. 이 줄은 앱 시작할 때 딱 한 번만 실행됨.
st.set_page_config(page_title="자동차 추천 시스템 및 기업FAQ 조회", layout="wide")

# Bootstrap Icons — AI 상담사 버튼/AI 챗봇 메뉴에 아이콘을 쓰기 위해 CDN에서 아이콘 폰트를 불러온다.
# (st.button 라벨 안에는 HTML이 안 먹히므로, 버튼 바로 옆에 이 아이콘을 별도로 그려서 붙여준다)
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
GEMINI_MODEL = os.getenv("GEMINI_MODEL") or "gemini-3.6-flash"  # .env 에 없으면 기본 모델 사용
FALLBACK_MODELS = ["gemini-3.6-flash"]  # 위 모델이 없어졌을 때(404) 대신 시도할 모델 목록
# 아래 문구들이 에러 메시지에 포함되면 "서버가 잠깐 바쁜 것"으로 보고 재시도한다
RETRYABLE_MARKERS = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "overloaded")
RETRY_DELAYS = (1, 2, 4)  # 초 단위: 모델 하나당 최대 3번 재시도 (1초→2초→4초 대기)
MAX_FAQ_SHOWN = 50  # FAQ 검색 결과를 화면에 몇 건까지만 보여줄지 (너무 많으면 화면이 느려짐)


# 제미나이 (무료 AI) ============================================================
# 이 섹션 전체가 딱 하나의 함수(ask_gemini)로만 되어 있고,
# 나머지 모든 메뉴(챗봇/추천/FAQ)가 AI 답변이 필요할 때마다 이 함수를 가져다 쓴다.
def ask_gemini(prompt: str) -> str:
    """제미나이 호출. 키가 없거나 오류가 나도 앱이 멈추지 않고 안내 문구를 돌려준다.
    503(서버 과부하)/429(요청 한도) 처럼 일시적인 오류는 잠깐 쉬었다가 자동 재시도한다."""
    # 1) .env 파일에서 API 키를 읽어온다. 키가 아예 없으면 AI 호출을 시도하지 않고 바로 안내 문구 반환
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_KEY") or "").strip()
    if not api_key:
        return "AI 키가 설정되지 않았습니다. .env 파일에 GEMINI_API_KEY 를 넣어주세요."
    try:
        from google import genai  # 필요할 때만 불러온다 (패키지가 없어도 앱 전체가 죽지 않게)
    except ImportError:
        return "google-genai 패키지가 없습니다. `pip install google-genai` 후 다시 실행하세요."

    client = genai.Client(api_key=api_key)
    # .env 의 모델이 종료됐거나 없으면(404) 기본 최신 모델로 자동 재시도
    # → GEMINI_MODEL을 먼저 시도하고, 안 되면 FALLBACK_MODELS 순서대로 하나씩 더 시도
    models = [GEMINI_MODEL] + [m for m in FALLBACK_MODELS if m != GEMINI_MODEL]
    last_error = None
    for model in models:  # 모델을 하나씩 바꿔가며 시도
        error = None
        for delay in (0,) + RETRY_DELAYS:  # 같은 모델로 최대 4번(즉시+3번) 재시도
            if delay:
                time.sleep(delay)  # 재시도 전에 잠깐 대기 (서버 부담을 줄이기 위해)
            try:
                resp = client.models.generate_content(model=model, contents=prompt)
                return resp.text or "(AI가 빈 답변을 돌려줬습니다. 다시 시도해 주세요.)"
            except Exception as e:  # 모델명 오류, 무료 한도 초과, 네트워크 오류, 일시적 과부하 등
                error = e
                if any(marker in str(e) for marker in RETRYABLE_MARKERS):
                    continue  # 일시적 오류(과부하/한도) → 같은 모델로 잠깐 쉬었다가 재시도
                break  # 일시적 오류가 아니면 재시도해도 소용없음

        last_error = error
        is_bad_model = "404" in str(error) or "NOT_FOUND" in str(error)
        is_transient = any(marker in str(error) for marker in RETRYABLE_MARKERS)
        if not (is_bad_model or is_transient):
            break  # 모델 문제도 일시적 과부하도 아니면 다른 모델로 바꿔도 소용없다

    # 2) 여기까지 왔다는 건 모든 모델 시도가 다 실패했다는 뜻 → 사용자에게 보여줄 오류 문구 결정
    if last_error is not None and any(marker in str(last_error) for marker in RETRYABLE_MARKERS):
        return "지금 AI 서버가 많이 붐빕니다 (일시적 과부하). 잠시 후 다시 시도해 주세요."
    return f"[AI 답변 오류] {last_error}"


# 메인(홈) 페이지 ============================================================
# 사이드바에서 고를 수 있는 4개 메뉴의 "이름표(문자열)"를 여기서 한 번만 정의해두고,
# 다른 모든 곳(사이드바, 홈 화면 카드, 맨 아래 라우팅)에서는 이 변수만 갖다 쓴다.
# → 나중에 메뉴 이름을 바꾸고 싶으면 이 4줄만 고치면 됨.
HOME_MENU = "Main Page"
RECOMMEND_MENU = "자동차 추천 시스템"
CHATBOT_MENU = "AI 챗봇"
FAQ_MENU = "기업FAQ 조회"
CALC_MENU = "월납입금 계산기"
# 홈 화면의 카드를 누르면 주소가 "?menu=recommend" 처럼 바뀌는데,
# 이 딕셔너리로 "recommend" 라는 글자 → RECOMMEND_MENU 실제 메뉴이름 으로 변환한다.
# (아래 순서는 사이드바에 메뉴탭이 나오는 순서와 동일하게 맞춰뒀다: 홈 → 챗봇 → 추천 → FAQ → 계산기)
MENU_BY_QUERY = {
    "home": HOME_MENU, "chat": CHATBOT_MENU, "recommend": RECOMMEND_MENU,
    "faq": FAQ_MENU, "calc": CALC_MENU,
}

# 카드에 넣을 사진: 이 폴더에 car.jpg / building.jpg 를 넣으면 자동으로 사용된다.
# 사진이 없으면 아래의 기본 일러스트(SVG 그림)가 대신 표시된다.
STATIC_DIR = Path(__file__).resolve().parent / "static"
HOME_IMAGES = {
    "car": ("car.jpg", "car.jpeg", "car.png", "car.webp"),
    "building": ("building.jpg", "building.jpeg", "building.png", "building.webp"),
    "hyundai": ("hyundai.jpg", "hyundai.jpeg", "hyundai.png", "hyundai.webp"),
    "kia": ("kia.jpg", "kia.jpeg", "kia.png", "kia.webp"),
    # 기업FAQ 나머지 15개 브랜드 전용 사진 자리 (파일명 = BRAND_INFO 의 "query" 값과 동일).
    # static/ 폴더에 아래 파일명으로 사진(로고/차량 사진 등)을 넣으면 카드 배경으로 자동 사용되고,
    # 없으면 기본 BUILDING_SVG 일러스트가 대신 나온다.
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
    # "자동차 추천 시스템" 안의 "추천 받기"/"통계 확인" 카드 전용 사진 자리
    # (메인페이지의 car.jpg/building.jpg 와 겹치지 않게 따로 둔다. 실제 사진을 여기 파일명으로
    #  static/ 폴더에 넣으면 아래 직접 그린 SVG 대신 그 사진이 자동으로 쓰인다)
    "reco_form": ("reco_form.jpg", "reco_form.jpeg", "reco_form.png", "reco_form.webp"),
    "reco_stats": ("reco_stats.jpg", "reco_stats.jpeg", "reco_stats.png", "reco_stats.webp"),
}

# 아래 CAR_SVG / BUILDING_SVG 는 사진이 없을 때 대신 보여줄 "직접 그린 그림"이다.
# SVG는 그림을 좌표·도형으로 표현하는 방식이라 코드가 길어 보이지만, 내용을 몰라도 무방하다.
# (사진 파일을 static/ 폴더에 넣으면 이 SVG 대신 그 사진이 자동으로 쓰인다.)
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
    """CAR_SVG의 색상 코드만 바꿔서 현대용/기아용처럼 다른 색깔의 차 그림을 만들어낸다."""
    return (CAR_SVG.replace("#0f2a5c", sky1).replace("#2b6cb0", sky2).replace("#183a73", mountain)
            .replace("#ff6b6b", body1).replace("#d63447", body2))


# 위 함수로 현대차/기아차 브랜드 색상의 차 그림을 미리 만들어둔다 (FAQ 브랜드 카드에서 사용)
HYUNDAI_SVG = _recolor_car("#0b1f4b", "#2f6fd0", "#14306b", "#eef2f9", "#a9b7cf")
KIA_SVG = _recolor_car("#17171c", "#8a2233", "#2a1a20", "#ffffff", "#c4c4c4")

# "자동차 추천 받기" 카드 전용 일러스트 — 실사 사진이 없어서 이름(AI 추천)에 어울리게 직접 그렸다.
# 보라색 밤하늘 배경 위에 반짝이는 별(마법/AI 느낌) + 차량 실루엣을 함께 그렸다.
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

# "자동차 통계 확인" 카드 전용 일러스트 — 상승하는 막대그래프 + 꺾은선 추세를 그려서 "통계"라는
# 이름에 어울리게 만들었다.
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

# 홈 화면 카드(마우스를 올리면 확대되는 효과 등)에 쓰이는 CSS 디자인 코드.
# st.markdown(..., unsafe_allow_html=True) 로 화면에 그대로 삽입해서 사용한다.
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


# AI 챗봇 ============================================================
# 사이드바 "AI 챗봇" 메뉴 전용 대화창. 사용자가 뭘 물어보든 일단 받아서,
# 내용을 보고 "차량 추천 요청인지 / FAQ 질문인지 / 그냥 일반 대화인지"를 자동으로 구분해 답한다.
CHATBOT_SYSTEM_NOTE = (
    "너는 '자동차 추천 시스템 및 기업FAQ 조회' 사이트의 AI 챗봇이다. "
    "이 사이트는 (1) 주행거리·지역·예산·선호연료 조건으로 차량을 추천하는 기능과 "
    "(2) 현대·기아·BMW·벤츠 등 17개 브랜드 FAQ 검색 기능을 제공한다. "
    "차량 추천이나 FAQ와 관련 없는 일반적인 질문에도 친절하게 답하되, "
    "차량 구매·FAQ 관련 질문이면 위 두 기능과 자연스럽게 연결지어 안내해줘."
)


def _recent_chat_text(n: int = 6) -> str:
    """최근 대화 n개를 "역할: 내용" 형태의 짧은 텍스트로 합쳐서 반환한다.
    AI에게 프롬프트를 보낼 때 "지금까지 무슨 얘기를 나눴는지" 맥락으로 함께 넣어준다."""
    msgs = st.session_state.get("chat_msgs", [])[-n:]
    return "\n".join(f"{m['role']}: {m['content'][:200]}" for m in msgs)


def classify_chat_intent(user_msg: str, history_text: str) -> dict:
    """사용자 메시지를 recommend / faq / general 중 하나로 분류하고,
    recommend 면 대화에서 언급된 조건(주행거리·지역·예산·연료)까지 함께 뽑아낸다.
    (AI에게 "JSON 형식으로만 답해줘"라고 프롬프트로 요청한 뒤, 그 결과를 json.loads로 파싱한다)"""
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
        "- \"recommend\": 차량 구매/추천을 원하는 경우 (예: 차 추천해줘, 전기차 살까 고민, 연비 좋은 차 뭐있어)\n"
        "- \"faq\": 현대차·기아차 이용 중 궁금한 점 (보증, 정비, 충전, 멤버십 등)\n"
        "- \"general\": 그 외 일반 대화/질문\n\n"
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


def chatbot_answer(user_msg: str) -> str:
    """사용자가 챗봇에 메시지를 보내면 실제 답변을 만들어주는 함수.
    1) classify_chat_intent 로 의도(recommend/faq/general) 파악
    2) 의도에 맞춰 다른 방식으로 답을 계산해서 돌려준다."""
    history_text = _recent_chat_text()
    route = classify_chat_intent(user_msg, history_text)
    intent = route.get("intent", "general")

    if intent == "recommend":  # "차 추천해줘" 같은 요청 → 추천 로직(recommend_cars) 실행
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
            f"**조건: {profile}**\n\n" + "\n".join(table) + f"\n\n{explanation}\n\n"
            "조건을 더 세밀하게 조정하고 싶으면 '자동차 추천 시스템' 메뉴도 이용해 보세요."
        )

    if intent == "faq":  # 17개 브랜드 이용 관련 질문 → DB에서 비슷한 FAQ를 찾아 근거로 답변
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

    # intent 가 "general"(그 외 일반 대화)이면 그냥 AI에게 자유롭게 답변을 맡긴다
    return ask_gemini(f"{CHATBOT_SYSTEM_NOTE}\n\n최근 대화:\n{history_text}\n\n사용자: {user_msg}")


def render_chatbot_menu():
    """AI 챗봇 화면 전체를 그린다: 대화 기록 표시 → 입력창 → 답변 생성 → 대화 초기화 버튼."""
    st.header("AI 챗봇")
    st.caption("차량 추천, 17개 브랜드 FAQ, 그 외 자동차 관련 궁금증까지 편하게 물어보세요.")

    # session_state["chat_msgs"] 에 지금까지의 대화 목록을 저장해둔다.
    # 처음 들어오면 이 목록이 없으므로, 인삿말 1개로 시작한다.
    if "chat_msgs" not in st.session_state:
        st.session_state["chat_msgs"] = [
            {"role": "assistant",
             "content": "안녕하세요! 차량 추천이나 17개 브랜드 FAQ, 그 외 궁금한 점을 편하게 물어보세요"}
        ]

    # 지금까지 저장된 대화를 화면에 순서대로 그린다 (새로고침될 때마다 이 for문이 다시 실행됨)
    for m in st.session_state["chat_msgs"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    user_msg = st.chat_input("메시지를 입력하세요 (예: 서울 사는데 연간 만km 타는 전기차 추천해줘)")
    if user_msg:  # 사용자가 메시지를 입력하고 엔터를 눌렀을 때만 아래 코드 실행
        st.session_state["chat_msgs"].append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.markdown(user_msg)
        with st.chat_message("assistant"):
            with st.spinner("생각하는 중..."):  # AI 응답을 기다리는 동안 로딩 표시
                reply = chatbot_answer(user_msg)
            st.markdown(reply)
        st.session_state["chat_msgs"].append({"role": "assistant", "content": reply})

    if len(st.session_state["chat_msgs"]) > 1:
        if st.button("대화 초기화"):
            st.session_state["chat_msgs"] = []
            st.rerun()


# 자동차 추천 시스템 (추천받기 + 통계 확인) ============================================================
# ※ 아래 데이터는 전부 실제 DB 테이블(car_recommend.sql 스키마)에서 읽어온 값입니다.
#   - 차량 카탈로그(브랜드/모델/차종/연료/출고가/평균연비)는 car_info 테이블에서 읽어옵니다.
#   - 그 외(주유소가격/보조금/전기차 등록·충전소 현황)는 electric_car_subsidies / electric_vehicles /
#     ev_chargers / sido_oil_price 테이블에서 읽어옵니다 — 팀원이 만들어 올린 car_recommend.sql 을
#     DB(.env 의 DB_NAME)에 import 해두면 아래 _load_recommend_data() 가 그 값을 읽어옵니다.
#   단, "전기차 충전비"만은 오픈API/DB에 없어서 전국 평균 고정값을 그대로 사용합니다.


@st.cache_data(show_spinner="실제 차량·지역 데이터를 불러오는 중...", ttl=3600)
def _load_recommend_data():
    """DB에서 추천 시스템에 필요한 데이터를 전부 읽어와 정리해서 돌려준다.
    (예전에는 이 자리가 전부 하드코딩된 샘플 상수였는데, 이제 실제 DB 값을 읽어와 채운다)
    돌려주는 값 6개: 지역목록, 지역별 유가표(내부용), 연료별 전국평균가, 지역별 보조금,
                    지역별 전기차등록대수, 지역별 충전기수, 차량목록(SAMPLE_CARS 대체)"""
    # 국내 브랜드 목록 (이 목록에 없으면 "수입차"로 분류) — 국산차/수입차 구분용
    DOMESTIC_BRANDS = {"현대", "기아", "제네시스", "KGM", "르노코리아"}
    # 오피넷(오일 가격) 제품 코드: B027=보통휘발유, D047=자동차경유, K015=자동차부탄(LPG)
    PROD_CODE = {"휘발유": "B027", "경유": "D047", "LPG": "K015"}
    # 화면에 보여줄 지역 순서 (특별시·광역시 → 도 순). DB에 있는 지역만 실제로 채택한다.
    REGION_ORDER = [
        "서울", "부산", "대구", "인천", "대전", "울산", "세종", "경기",
        "강원", "충북", "충남", "전북", "전남광주", "경북", "경남", "제주",
    ]

    # 1) 시도별 주유소 평균가격 (원/L) — sido_oil_price 테이블
    oil_rows = db.fetch_all(
        "SELECT sido_nm, prod_cd, price FROM sido_oil_price WHERE prod_cd IN ('B027','D047','K015')"
    )
    oil_by_region: dict = {}
    for r in oil_rows:
        oil_by_region.setdefault(r["sido_nm"], {})[r["prod_cd"]] = float(r["price"])
    regions = [r for r in REGION_ORDER if r in oil_by_region]
    # "전국" 행 = 연료별 전국 평균가 (통계 탭의 연료 종류 라디오 버튼에도 사용)
    gas_price_base = {
        fuel: round(oil_by_region.get("전국", {}).get(code, 0)) for fuel, code in PROD_CODE.items()
    }

    # 2) 전기차 보조금 (승용 기준 시도별 최대보조금, 단위: 만원 → 원으로 환산)
    ev_subsidy = {
        r["sido"]: r["max_subsidy_passenger"] * 10_000
        for r in db.fetch_all(
            "SELECT sido, max_subsidy_passenger FROM electric_car_subsidies WHERE sido != '전국'"
        )
    }

    # 3) 전기차 등록대수 / 충전기수 (시도별) — 인프라 점수 계산용
    ev_registration = {r["sido"]: r["vehicle_count"] for r in db.fetch_all(
        "SELECT sido, vehicle_count FROM electric_vehicles")}
    ev_chargers = {r["sido"]: r["charger_count"] for r in db.fetch_all(
        "SELECT sido, charger_count FROM ev_chargers")}

    # 4) 차량 카탈로그 (출고가·연비/전비) — car_info 테이블에서 직접 읽어온다
    cars = []
    for r in db.get_car_info():
        eff_str = str(r["avg_efficiency"]) if r["avg_efficiency"] is not None else ""
        m = re.match(r"([\d.]+)", eff_str)          # "12.5㎞/ℓ" → 12.5 / "5.5㎞/kWh" → 5.5
        eff_val = float(m.group(1)) if m else None
        fuel_type = str(r["fuel_type"])
        fuel = "전기" if "전기" in fuel_type else fuel_type.split("+")[0]  # "LPG+가솔린"→"LPG"
        # 전기차 여부는 "연료구분" 컬럼을 기준으로 판단한다 (연비 단위 텍스트로 판단하면,
        # 실제 데이터 중 일부 오타 — 연료는 전기인데 단위가 ㎞/ℓ로 잘못 적힌 행 — 에서
        # 전비 값이 None이 되어 계산이 죽어버리는 문제가 있었음)
        is_ev = fuel == "전기"
        cars.append(dict(
            모델명=r["car_name"], 브랜드=r["brand"], 세그먼트=r["car_type"], 연료=fuel,
            연료형태원본=fuel_type,  # "LPG+가솔린"처럼 원본 그대로 — DB view_car_recommend 조인용 키
            연비=(None if is_ev else eff_val), 전비=(eff_val if is_ev else None),
            출고가=int(r["price_num"]) * 10_000,     # price_num 단위가 "만원" → 원으로 환산
            국산차=("국산차" if r["brand"] in DOMESTIC_BRANDS else "수입차"),
        ))

    return regions, oil_by_region, gas_price_base, ev_subsidy, ev_registration, ev_chargers, cars


(REGIONS, _OIL_PRICE_BY_REGION, GAS_PRICE_BASE, EV_SUBSIDY,
 EV_REGISTRATION, EV_CHARGERS, SAMPLE_CARS) = _load_recommend_data()


@st.cache_data(show_spinner="차량×지역별 점수 데이터를 불러오는 중...", ttl=3600)
def _load_score_lookup() -> dict:
    """팀에서 DB에 만들어둔 view_car_recommend 뷰를 그대로 읽어온다.
    이 뷰가 (차량, 지역)별로 km당 연료비 / 연비점수 / 인프라 점수 / 실구매가 점수를
    이미 다 계산해서 갖고 있으므로, 앱에서 따로 계산하지 않고 그대로 가져다 쓴다.
    (연비점수·인프라점수·실구매가점수 = 연료비/인프라/가격 세 가지 추천 점수로 그대로 쓰임)"""
    lookup = {}
    for r in db.fetch_all("SELECT * FROM view_car_recommend"):
        key = (r["브랜드"], r["차량명"], r["연료형태"], r["sido_nm"])
        try:
            subsidy = float(r["지원받은 보조금"])
        except (TypeError, ValueError):
            subsidy = 0.0  # "해당사항 없음" / "예산 소진" 같은 문자열이면 보조금 0원 처리
        lookup[key] = dict(
            km_cost=float(r["km당 연료비"]),
            fuel_score=float(r["연비점수"]),
            infra_score=float(r["인프라 점수"]),
            price_score=float(r["실구매가 점수"]),
            infra_note=str(r["인프라 상황"]),
            subsidy=subsidy * 10_000,  # 만원 → 원
        )
    return lookup


SCORE_LOOKUP = _load_score_lookup()

# 시도청(대표 도시) 소재지 기준 대략 좌표 (지도형 시각화용, 정밀도 낮음)
# "전남광주"는 전남+광주가 합쳐진 통계 구분이라, 대표로 광주광역시 좌표를 사용한다.
REGION_COORDS = {
    "서울": (37.5665, 126.9780), "부산": (35.1796, 129.0756), "대구": (35.8714, 128.6014),
    "인천": (37.4563, 126.7052), "대전": (36.3504, 127.3845), "울산": (35.5384, 129.3114),
    "세종": (36.4801, 127.2890), "경기": (37.4138, 127.5183), "강원": (37.8228, 128.1555),
    "충북": (36.6357, 127.4917), "충남": (36.5184, 126.8000), "전북": (35.7175, 127.1530),
    "전남광주": (35.1595, 126.8526), "경북": (36.4919, 128.8889), "경남": (35.4606, 128.2132),
    "제주": (33.4996, 126.5312),
}

FUEL_CHOICES = ["가솔린", "디젤", "LPG", "하이브리드", "전기"]  # 추천 폼/통계 탭에서 고를 수 있는 연료 종류

# 전기차 충전비: 오픈API/DB에 없는 항목이라, 충전소별 편차가 크지 않다는 전제로 전국 평균 고정값을 그대로 쓴다.
EV_CHARGE_COST_PER_KWH = 320  # 원/kWh


def gas_price(fuel: str, region: str) -> int:
    """지역별 실제 주유소 평균가격(원/L)을 DB(sido_oil_price)에서 찾아온다.
    해당 지역 데이터가 없으면 전국 평균으로 대체한다."""
    prod_code = {
        "휘발유": "B027", "가솔린": "B027", "하이브리드": "B027",
        "경유": "D047", "디젤": "D047", "LPG": "K015",
    }
    code = prod_code.get(fuel, "B027")
    region_prices = _OIL_PRICE_BY_REGION.get(region) or _OIL_PRICE_BY_REGION.get("전국", {})
    return round(region_prices.get(code) or GAS_PRICE_BASE.get("휘발유", 0))


# ---- 다) 출고가·연비: 위 _load_recommend_data() 가 DB car_info 테이블에서 읽어온 실제 차량 목록 ----

ORIGIN_CHOICES = ["전체", "국산차", "수입차"]
# SAMPLE_CARS 안의 "세그먼트" 값들을 중복 없이 뽑아서 정렬 (예: 경차, 준중형, 중형 ...)
CAR_SEGMENTS = sorted({c["세그먼트"] for c in SAMPLE_CARS})


def compute_car_metrics(car: dict, annual_km: int, region: str) -> dict:
    """차량 1대에 대한 연간 연료비 / 실구매가 / 연료비·가격·인프라 점수를 계산한다.
    DB의 view_car_recommend 뷰(SCORE_LOOKUP)가 (차량, 지역) 조합별로 이미 다 계산해둔 값을
    그대로 가져다 쓴다 — 앱에서 따로 min-max/평균 같은 정규화를 하지 않는다."""
    key = (car["브랜드"], car["모델명"], car["연료형태원본"], region)
    info = SCORE_LOOKUP.get(key)
    if info is None:
        # 혹시 뷰에 없는 조합이면(데이터 불일치 등) 화면이 죽지 않도록 0점으로 안전 처리
        return dict(annual_fuel_cost=0.0, subsidy=0.0, effective_price=car["출고가"],
                    infra_score=0.0, infra_note="", 연료비점수=0.0, 가격점수=0.0, 인프라점수=0.0)
    annual_fuel_cost = info["km_cost"] * annual_km
    subsidy = info["subsidy"]
    effective_price = max(car["출고가"] - subsidy, 0)
    return dict(
        annual_fuel_cost=annual_fuel_cost, subsidy=subsidy, effective_price=effective_price,
        infra_score=info["infra_score"], infra_note=info["infra_note"],
        연료비점수=info["fuel_score"], 가격점수=info["price_score"], 인프라점수=info["infra_score"],
    )


def recommend_cars(annual_km: int, region: str, price_min: int, price_max: int, fuel_pref: list[str],
                    origin_pref: str, size_pref: list[str],
                    w_fuel: float, w_price: float, w_infra: float) -> "pd.DataFrame":
    """추천 시스템의 핵심 계산 함수. 조건에 맞는 차량들을 골라서,
    "연료비 점수 × 가중치 + 가격 점수 × 가중치 + 인프라 점수 × 가중치" 로 종합점수를 매긴 뒤
    점수가 높은 순으로 정렬한 표(DataFrame)를 돌려준다.
    연료비점수/가격점수/인프라점수는 DB view_car_recommend 뷰가 이미 계산해둔 값을 그대로 쓴다
    (앱에서 따로 정규화하지 않음).
    w_fuel/w_price/w_infra 는 "연료비/가격/인프라 중 뭘 더 중요하게 볼지"를 나타내는 가중치(중요도)다."""
    # 1) 연료·국산/수입·크기 조건에 맞는 차량만 먼저 골라낸다 (조건을 안 고르면 = 전부 통과)
    candidates = [
        c for c in SAMPLE_CARS
        if (not fuel_pref or c["연료"] in fuel_pref)
        and (origin_pref == "전체" or c["국산차"] == origin_pref)
        and (not size_pref or c["세그먼트"] in size_pref)
    ]
    # 2) 골라낸 차량마다 연료비·실구매가·연료비점수/가격점수/인프라점수를 뷰에서 가져와 표로 합친다
    rows = []
    for car in candidates:
        m = compute_car_metrics(car, annual_km, region)
        rows.append({**car, **m})  # 차량 정보 dict + 계산 결과 dict 를 합친다
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # 3) 가격대(price_min~price_max) 안에 드는 차량만 남긴다. 단, 아무도 안 맞으면 필터를 풀고 전체 비교
    if price_max:
        within = df[(df["effective_price"] >= (price_min or 0)) & (df["effective_price"] <= price_max)]
        df = within if not within.empty else df  # 가격대에 맞는 차량이 없으면 전체에서 비교

    # 4) 가중치가 전부 0이면(사용자가 우선순위를 다 0으로 설정) 셋 다 동일하게 취급
    total_w = w_fuel + w_price + w_infra
    if total_w == 0:
        w_fuel = w_price = w_infra = 1
        total_w = 3

    # 5) 세 점수를 가중평균해서 최종 "종합점수" 산출
    df["종합점수"] = (
        df["연료비점수"] * w_fuel + df["가격점수"] * w_price + df["인프라점수"] * w_infra
    ) / total_w
    return df.sort_values("종합점수", ascending=False).reset_index(drop=True)  # 점수 높은 순 정렬


def reco_score_breakdown(row: "pd.Series", w_fuel: float, w_price: float, w_infra: float) -> dict:
    """종합점수가 '연료비/가격/인프라 각각 몇 점씩 더해져서' 나온 건지 가중치를 반영한 기여 점수로 쪼개준다.
    (세 값을 더하면 종합점수와 같아지도록 계산 — 예: 연료비 30점 + 가격 20점 + 인프라 30점 = 종합점수 80점)"""
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
    """연료비/가격/인프라/종합 점수(0~100) 하나를 CSS conic-gradient 원형 게이지 HTML로 만든다.
    (Plotly 대신 순수 CSS로 그려서 카드 폭이 좁아져도 항상 정원(круг) 비율이 유지된다)"""
    value = max(0.0, min(100.0, value))
    deg = value / 100 * 360
    size = 64  # px, 항상 정사각형(가로=세로)이라 원이 절대 찌그러지지 않는다
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


def build_reco_reason(row: "pd.Series", w_fuel: float, w_price: float, w_infra: float,
                       df: "pd.DataFrame") -> str:
    """AI 호출 없이, 계산된 점수만으로 '왜 이 차가 추천됐는지'를 즉시 한 문장으로 만든다.
    (연료비/가격/인프라 중 가중치를 감안했을 때 이 차량 점수에 가장 크게 기여한 요소 + 후보군 내 1등 항목을 짚어준다)"""
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

    # 후보군 내에서 실제로 1등인 항목이 있으면 그걸 우선 근거로 든다 (더 구체적이고 설득력 있음)
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


# ---- 추천 메뉴 안에 들어가는 AI 상담 챗봇 (기업 FAQ 챗봇처럼 부드러운 말투) ----------------------
RECOMMEND_CHAT_SYSTEM_NOTE = (
    "너는 '자동차 추천 시스템' 화면 안에 있는 AI 상담 챗봇이다. 실제 기업 고객센터 상담원처럼 "
    "항상 부드럽고 친절한 해요체로 답해라. 정보를 딱딱하게 나열만 하지 말고, "
    "'네, 확인해드릴게요 :)', '그 부분 궁금하실 수 있어요' 같은 공감·쿠션어를 자연스럽게 섞어서 "
    "대화하듯 답해라. 확실하지 않은 수치나 사실은 추측하지 말고, "
    "전기차 충전비만 전국 평균 고정값이고 나머지 수치(주유소가격·보조금·연비·출고가 등)는 "
    "실제 DB 데이터라는 점을 필요할 때만 살짝 짚어줘라.\n\n"
    "이 챗봇은 '차량 추천' 전용이다. 아래처럼 추천과 무관한 질문에는 직접 답하지 말고, "
    "해당 내용은 다른 메뉴에서 도와드릴 수 있다고 한 문장으로 부드럽게 안내만 하고 끝내라:\n"
    "- 보증·정비·멤버십·충전 예약 등 브랜드 이용 중 FAQ성 질문 → '기업FAQ 조회' 메뉴를 이용해 달라고 안내\n"
    "- 자동차와 무관한 일반 잡담·다른 주제 질문 → 'AI 챗봇' 메뉴에서 편하게 물어봐 달라고 안내"
)


def extract_reco_conditions(user_msg: str, history_text: str) -> dict:
    """(추천 시스템 안의 상담 챗봇 전용) 대화 속 메시지가 차량 추천 요청인지 판단하고,
    언급된 조건(지역·출퇴근거리·예산·국산차수입차·선호크기·선호연료)을 뽑아낸다.
    FAQ성 질문/잡담이면 in_scope=False 를 반환해서, 이 채팅창은 답하지 않고 다른 메뉴로 안내하게 한다."""
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
        data = json.loads(text)
        data.setdefault("in_scope", True)
        return data
    except Exception:
        return {"in_scope": True}


def reco_chat_answer(user_msg: str) -> str:
    """추천 시스템 안의 상담 챗봇 답변 생성기. 조건을 뽑아 recommend_cars 로 계산하고,
    상위 3대 표 + AI의 부드러운 설명을 합쳐서 답변 문자열을 만든다."""
    history = st.session_state.get("reco_chat_msgs", [])[-6:]
    history_text = "\n".join(f"{m['role']}: {m['content'][:200]}" for m in history)

    cond = extract_reco_conditions(user_msg, history_text)

    if not cond.get("in_scope", True):  # 추천과 무관한 질문(FAQ/잡담)이면 안내만 하고 끝

        prompt = (
            f"{RECOMMEND_CHAT_SYSTEM_NOTE}\n\n[최근 대화]\n{history_text}\n\n[사용자 메시지]\n{user_msg}"
        )
        return ask_gemini(prompt)

    region = cond.get("region") if cond.get("region") in REGIONS else "서울"
    commute_km = cond.get("commute_km")
    annual_km = cond.get("annual_km")
    if not annual_km:
        annual_km = max(commute_km * 2 * 260, 1000) if commute_km else 12000
    budget_manwon = cond.get("budget_manwon") or 3000
    price_max = int(budget_manwon) * 10_000
    origin_pref = cond.get("origin_pref") if cond.get("origin_pref") in ORIGIN_CHOICES else "전체"
    size_pref = [s for s in (cond.get("size_pref") or []) if s in CAR_SEGMENTS]
    fuel_pref = [f for f in (cond.get("fuel_pref") or []) if f in FUEL_CHOICES]

    df = recommend_cars(annual_km, region, 0, price_max, fuel_pref, origin_pref, size_pref, 40, 40, 20)
    if df.empty:
        return "조건에 맞는 차량을 찾지 못했어요 :( 예산이나 선호 조건을 조금 다르게 말씀해 주시겠어요?"

    profile = (
        f"{region} 거주 · 연간 약 {annual_km:,}km 주행 · 예산 {price_max:,}원 이하 · {origin_pref} · "
        f"선호크기 {', '.join(size_pref) if size_pref else '전체'} · "
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
        f"{RECOMMEND_CHAT_SYSTEM_NOTE}\n\n"
        "아래는 사용자 조건에 맞춰 계산한 추천 차량 상위 목록이다. 1위 차량이 왜 "
        "적합한지 부드럽고 친절한 상담원 말투로 3~4문장 설명해줘. 숫자에 근거해서만 말하고, "
        "언급 안 된 조건은 기본값(가정)을 썼다는 점을 한 번 짚어줘.\n\n" + summary
    )

    # 위쪽 조건 입력 화면의 추천 카드에도 같은 결과를 반영해준다
    st.session_state["reco_result"] = df
    st.session_state["reco_profile"] = profile

    return (
        f"네, 확인해드릴게요 :) **조건: {profile}**\n\n" + "\n".join(table) + f"\n\n{explanation}\n\n"
        "위쪽 추천 카드에도 결과를 반영해 놨어요. 조건을 더 정확히 입력하고 싶으면 위 칸에서 직접 바꿔보셔도 돼요."
    )


def render_reco_chatbot():
    """추천 폼(render_recommend_form) 위쪽에 들어가는 미니 상담 채팅창을 그린다.
    AI 챗봇 메뉴의 대화기록과는 완전히 별개로 session_state["reco_chat_msgs"] 에 따로 저장한다."""
    if "reco_chat_msgs" not in st.session_state:
        st.session_state["reco_chat_msgs"] = []

    for m in st.session_state["reco_chat_msgs"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    user_msg = st.chat_input(
        "AI 상담사한테 추천받기 (예: 예산을 낮추면 어떤 차가 좋아요?)", key="reco_chat_input",
    )
    if user_msg:
        st.session_state["reco_chat_msgs"].append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.markdown(user_msg)
        with st.chat_message("assistant"):
            with st.spinner("답변을 준비하고 있어요..."):
                reply = reco_chat_answer(user_msg)
            st.markdown(reply)
        st.session_state["reco_chat_msgs"].append({"role": "assistant", "content": reply})

    if len(st.session_state["reco_chat_msgs"]) > 1:
        if st.button("상담 대화 초기화", key="reco_chat_clear"):
            st.session_state["reco_chat_msgs"] = []
            st.rerun()


@st.dialog("AI 상담사 — 차량 추천", width="large")
def _reco_chat_dialog():
    """render_reco_chatbot() 을 팝업(모달) 창 안에 그대로 그려서, 채팅방처럼 열고 닫을 수 있게 한다."""
    render_reco_chatbot()


def build_recommend_summary(profile: str, df: "pd.DataFrame") -> str:
    """추천 결과 상위 5대를 사람이 읽기 좋은 줄글로 요약한다.
    이 요약 텍스트를 AI에게 그대로 넘겨서 "왜 이 차가 좋은지" 설명을 만들게 한다."""
    lines = [f"사용자 조건: {profile}", ""]
    for i, row in df.head(5).iterrows():
        lines.append(
            f"{i+1}위 {row['브랜드']} {row['모델명']}({row['연료']}) · 종합점수 {row['종합점수']:.1f}점 · "
            f"연간 연료비 약 {row['annual_fuel_cost']:,.0f}원 · 실구매가 {row['effective_price']:,.0f}원 · "
            f"인프라점수 {row['infra_score']:.1f}점"
        )
    return "\n".join(lines)


# 추천 시스템 선택 화면(카드 2장)에 쓰이는 정보.
# "form" = 추천 받기 화면, "stats" = 통계 확인 화면. FAQ의 BRAND_INFO 와 같은 역할.
RECO_VIEW_INFO = {
    "form": dict(
        query="form", kind="reco_form", tag="AI 추천",
        title="자동차 추천 받기",
        desc="나이·지역·출퇴근거리·가격대·선호연료를 입력하면 연료비·구매부담·전기차 인프라를 "
             "종합해서 AI가 차량을 추천해드려요.",
        cta="추천받으러 가기 →",
        icon='<i class="bi bi-magic" style="font-size:1.4rem;"></i>'),
    "stats": dict(
        query="stats", kind="reco_stats", tag="데이터 · 통계",
        title="자동차 통계 확인",
        desc="개인 조건 없이, 지역별 주유소 가격·전기차 보조금·인프라 현황부터 브랜드·세그먼트·연비 "
             "비교까지 10가지 통계를 직접 둘러볼 수 있어요.",
        cta="통계 보러가기 →",
        icon='<i class="bi bi-bar-chart-line" style="font-size:1.4rem;"></i>'),
}
RECO_VIEW_BY_QUERY = {info["query"]: key for key, info in RECO_VIEW_INFO.items()}


def render_recommend_select():
    """추천 시스템 기본 화면: 아직 사이드바에서 추천받기/통계확인 중 아무것도 안 골랐을 때 보여주는
    카드 2장짜리 화면. 사이드바에는 더 이상 "선택 화면"이라는 라디오 항목이 없지만,
    "자동차 추천 시스템" 버튼을 누르면(=아직 하위 항목을 안 골랐으면) 이 화면이 대신 뜬다."""
    hero = (
        '<div class="home-hero"><h1>사용자 특성별 자동차 추천 시스템</h1>'
        "<p>실제 DB 데이터(차량 스펙·지역별 유가·전기차 보조금·인프라 현황) 기준으로 추천해드려요.</p></div>"
    )
    cards = ""
    for key, info in RECO_VIEW_INFO.items():
        cards += _home_card(f"?menu=recommend&amp;view={info['query']}", info["kind"],
                            info["tag"], info["title"], info["desc"], info["cta"],
                            icon_html=info.get("icon", ""))
    st.markdown(HOME_CSS + hero + '<div class="home-grid">' + cards + "</div>", unsafe_allow_html=True)


def render_recommend_menu():
    """사이드바 "자동차 추천 시스템" 메뉴의 진입점.
    사이드바 하위 라디오(추천받기 / 통계확인)에서 아직 아무것도 안 골랐으면 선택 화면을,
    골랐으면 해당 화면을 보여준다."""
    view = st.session_state.get("reco_view")
    if view not in RECO_VIEW_INFO:
        render_recommend_select()
        return
    info = RECO_VIEW_INFO[view]
    st.header(f"사용자 특성별 자동차 추천 시스템 — {info['title']}")
    if view == "form":
        render_recommend_form()      # ── (추천받기) 사용자가 조건을 입력하고 추천받는 화면
    else:
        render_recommend_stats()     # ── (통계 확인) 조회 조건을 골라서 통계만 보는 화면


def render_recommend_form():
    """[추천 받기] 화면: 나이/지역/예산 등 입력 → 추천 계산 → 상위 차량 카드로 결과 표시."""
    st.caption(
        "지역·출퇴근 거리·가격대·국산차/수입차·선호 차량 크기를 "
        "바탕으로 연료비·구매부담·전기차 인프라를 종합해 실제 데이터 기준으로 추천합니다."
    )

    # 채팅창을 화면에 바로 펼쳐두는 대신, 버튼을 누르면 팝업(모달)으로 열리게 한다
    # (실제 클릭 이벤트를 받아야 하는 진짜 st.button이라 HTML 아이콘은 못 넣고,
    #  대신 스트림릿이 기본 제공하는 아이콘(Material Symbols)을 버튼 안에 직접 넣는다)
    unread = len(st.session_state.get("reco_chat_msgs", []))
    chat_label = "AI 상담사에게 물어보기" + (f" ({unread}개 대화 중)" if unread > 1 else "")
    if st.button(chat_label, key="open_reco_chat", type="primary",
                 icon=":material/android:", use_container_width=True):
        _reco_chat_dialog()
    st.divider()

    # ---- 즐겨찾기한 차량 (세션 동안 유지) ----------------------------------------------
    st.session_state.setdefault("favorites", {})
    favorites = st.session_state["favorites"]
    with st.expander(f"즐겨찾기한 차량 ({len(favorites)}건)", expanded=False):
        if not favorites:
            st.caption("추천 카드에서 '☆ 즐겨찾기' 버튼을 누르면 여기에 저장됩니다.")
        else:
            fav_df = pd.DataFrame([
                {
                    "브랜드": r["브랜드"], "모델명": r["모델명"], "세그먼트": r["세그먼트"], "연료": r["연료"],
                    "연간 연료비(원)": r["annual_fuel_cost"], "실구매가(원)": r["effective_price"],
                    "종합점수": r["종합점수"],
                }
                for r in favorites.values()
            ])
            st.dataframe(fav_df, hide_index=True)
            st.download_button(
                "즐겨찾기 CSV로 다운로드", data=fav_df.to_csv(index=False).encode("utf-8-sig"),
                file_name="즐겨찾기_차량.csv", mime="text/csv", key="download_fav_csv",
            )
            if st.button("즐겨찾기 전체 비우기", key="clear_favorites"):
                st.session_state["favorites"] = {}
                st.rerun()

    st.subheader("내 정보 입력")
    # st.columns(2) 로 화면을 가로 2칸으로 나눠서 입력창을 나란히 배치한다
    c1, c2 = st.columns(2)
    region = c1.selectbox("거주 지역", REGIONS)
    commute_km = c2.number_input("편도 출퇴근 거리 (km)", min_value=0, max_value=100, value=10, step=1)

    origin_pref = st.selectbox("국산차 / 수입차", ORIGIN_CHOICES)

    pc1, pc2 = st.columns(2)
    price_min = pc1.number_input("최소 가격대 (만원)", min_value=0, max_value=100_000, value=2000, step=100)
    price_max = pc2.number_input("최대 가격대 (만원)", min_value=0, max_value=100_000, value=5000, step=100)
    if price_min > price_max:
        price_min, price_max = price_max, price_min  # 사용자가 반대로 입력해도 자동으로 바로잡음
    price_min, price_max = price_min * 10_000, price_max * 10_000

    size_pref = st.multiselect("선호 차량 크기", CAR_SEGMENTS, placeholder="선택 안 함 (전체)")
    fuel_pref = st.multiselect(
        "선호 연료 (비워두면 전체 연료 대상)", FUEL_CHOICES, placeholder="선택 안 함 (전체)",
    )

    # 우선순위(가중치)는 연료비:가격:인프라 = 40:40:20 으로 고정 (사용자가 직접 조정하지 않음)
    w_fuel, w_price, w_infra = 40, 40, 20

    # 편도 출퇴근 거리를 왕복·연간(약 260 근무일) 기준 연간 주행거리로 환산 (샘플 가정)
    annual_km = max(commute_km * 2 * 260, 1000)

    if st.button("차량 추천받기", type="primary"):  # 버튼을 누른 순간에만 아래 계산을 실행
        result = recommend_cars(
            annual_km, region, price_min, price_max, fuel_pref, origin_pref, size_pref,
            w_fuel, w_price, w_infra,
        )
        profile = (
            f"{region} 거주 · 편도 출퇴근 {commute_km}km(연간 약 {annual_km:,}km) · "
            f"가격대 {price_min:,}~{price_max:,}원 · {origin_pref} · "
            f"선호크기 {', '.join(size_pref) if size_pref else '전체'} · "
            f"선호연료 {', '.join(fuel_pref) if fuel_pref else '전체'} · "
            f"중요도(연료비:가격:인프라)={w_fuel}:{w_price}:{w_infra}"
        )
        st.session_state["reco_result"] = result   # 다음에 화면이 다시 그려져도 결과가 안 사라지게 저장
        st.session_state["reco_profile"] = profile
        st.session_state["reco_weights"] = (w_fuel, w_price, w_infra)  # 추천 이유 문구가 그때의 가중치를 그대로 쓰도록 같이 저장

    # 버튼을 누른 적이 있으면(session_state 에 결과가 있으면) 그 결과를 계속 화면에 보여준다
    result = st.session_state.get("reco_result")
    if result is not None and not result.empty:
        profile = st.session_state.get("reco_profile", "")
        st.caption(f"조건: {profile}")
        st.divider()

        # 차량 하나를 여러 탭/랭킹에서도 같은 차로 알아볼 수 있게 만드는 고유 id
        # (즐겨찾기·비교선택 모두 이 id를 기준으로 저장한다)
        def _car_id(row) -> str:
            return f"{row['브랜드']}|{row['모델명']}|{row['세그먼트']}|{row['연료']}"

        st.session_state.setdefault("favorites", {})     # car_id -> 저장 당시 row(dict)
        st.session_state.setdefault("compare_selected", {})  # car_id -> 저장 당시 row(dict), 비교용 (최대 3대)

        def _render_reco_card(col, rank, row, key_ns: str, show_actions: bool = False):
            badge = "1위" if rank == 0 else f"{rank+1}위"
            car_id = _car_id(row)
            with col:
                with st.container(border=True):
                    st.markdown(f"**{badge} · {row['브랜드']} {row['모델명']}** ({row['세그먼트']} · {row['연료']})")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("연간 예상 연료비", f"{row['annual_fuel_cost']:,.0f}원")
                    m2.metric("실구매가", f"{row['effective_price']:,.0f}원")
                    m3.metric("종합점수", f"{row['종합점수']:.1f}점")

                    # 연료비/가격/인프라/종합 점수(0~100)를 작은 원형 게이지 4개로 보여준다 (종합점수를 맨 앞에)
                    g1, g2, g3, g4 = st.columns(4)
                    for gcol, glabel, gvalue, gcolor in (
                        (g1, "종합", row["종합점수"], "#8a7fd6"),
                        (g2, "연료비", row["연료비점수"], "#f06a6a"),
                        (g3, "가격", row["가격점수"], "#4fc3c3"),
                        (g4, "인프라", row["인프라점수"], "#f5a95f"),
                    ):
                        with gcol:
                            st.markdown(_mini_score_ring_html(gvalue, gcolor, glabel), unsafe_allow_html=True)

                    used_w_fuel, used_w_price, used_w_infra = st.session_state.get(
                        "reco_weights", (w_fuel, w_price, w_infra)
                    )
                    bd = reco_score_breakdown(row, used_w_fuel, used_w_price, used_w_infra)
                    st.caption(
                        f"연료비 {bd['fuel']:.1f}점 + 가격 {bd['price']:.1f}점 + "
                        f"인프라 {bd['infra']:.1f}점 = 종합점수 {bd['total']:.1f}점"
                    )
                    st.caption("추천 이유: " + build_reco_reason(row, used_w_fuel, used_w_price, used_w_infra, result))

                    # ---- 즐겨찾기 + 비교선택 (모든 탭 카드에 공통으로 표시) ----
                    a1, a2 = st.columns(2)
                    is_fav = car_id in st.session_state["favorites"]
                    fav_label = "★ 즐겨찾기 해제" if is_fav else "☆ 즐겨찾기"
                    if a1.button(fav_label, key=f"fav_{key_ns}_{rank}_{car_id}", use_container_width=True):
                        if is_fav:
                            st.session_state["favorites"].pop(car_id, None)
                        else:
                            st.session_state["favorites"][car_id] = row.to_dict()
                        st.rerun()

                    # 비교선택 버튼은 "종합점수 순위" 탭에서만 보여준다.
                    # (같은 차가 탭마다 중복 렌더링되므로, 위젯 key 충돌을 피하고 헷갈리지 않게 하나의 탭에서ㄴ만 고르게 함)
                    if show_actions:
                        is_cmp = car_id in st.session_state["compare_selected"]
                        cmp_label = "비교 해제" if is_cmp else "비교에 추가"
                        cmp_disabled = (not is_cmp) and len(st.session_state["compare_selected"]) >= 3
                        if a2.button(cmp_label, key=f"cmp_{key_ns}_{rank}_{car_id}",
                                     use_container_width=True, disabled=cmp_disabled):
                            if is_cmp:
                                st.session_state["compare_selected"].pop(car_id, None)
                            else:
                                st.session_state["compare_selected"][car_id] = row.to_dict()
                            st.rerun()
                        if cmp_disabled:
                            a2.caption("최대 3대까지 비교 가능해요")
                    else:
                        a2.caption("비교선택은 '종합점수 순위' 탭에서")

                    # ---- 🏢 같은 브랜드 FAQ 보기 + 🧮 이 차량으로 월납입금계산하기 ----
                    b1, b2 = st.columns(2)
                    faq_source = _faq_source_for_brand(row["브랜드"])
                    if faq_source:
                        if b1.button(f"{row['브랜드']} FAQ 보기", key=f"faq_{key_ns}_{rank}_{car_id}",
                                     use_container_width=True):
                            st.session_state["faq_brand"] = faq_source
                            st.session_state["menu"] = FAQ_MENU
                            st.rerun()
                    else:
                        b1.caption("FAQ 미제공 브랜드")

                    if b2.button("이 차량으로 월납입금 계산하기", key=f"calc_{key_ns}_{rank}_{car_id}",
                                 use_container_width=True):
                        st.session_state["calc_car_price"] = int(round(row["출고가"] / 10_000))
                        st.session_state["menu"] = CALC_MENU
                        st.rerun()

        def _render_reco_grid(df_sorted: "pd.DataFrame", key_ns: str, show_actions: bool = False):
            """순위를 1·2 / 3·4 / 5·6 ... 처럼 2열로 배열해서 보여준다 (상위 10대까지)."""
            top_rows = list(df_sorted.head(10).reset_index(drop=True).iterrows())
            for pair_start in range(0, len(top_rows), 2):
                pair = top_rows[pair_start:pair_start + 2]
                cols = st.columns(2)
                for col, (rank, row) in zip(cols, pair):
                    _render_reco_card(col, rank, row, key_ns, show_actions)

        def _render_reco_chart(df_sorted: "pd.DataFrame", chart_key: str):
            """df_sorted 순서 그대로(상위 10대) 점수 구성 누적 막대그래프를 그린다."""
            used_w_fuel, used_w_price, used_w_infra = st.session_state.get(
                "reco_weights", (w_fuel, w_price, w_infra)
            )
            chart_rows = []
            chart_order = []  # x축 순서를 순위대로 고정 (동명 차량이 있어도 막대가 안 겹치게)
            for rank, (_, row) in enumerate(df_sorted.head(10).iterrows(), start=1):
                bd = reco_score_breakdown(row, used_w_fuel, used_w_price, used_w_infra)
                label = f"{rank}위 {row['브랜드']} {row['모델명']}"
                chart_order.append(label)
                chart_rows.append({"차량": label, "항목": "연료비", "점수": bd["fuel"], "표시값": f"{bd['fuel']:.1f}점"})
                chart_rows.append({"차량": label, "항목": "가격", "점수": bd["price"], "표시값": f"{bd['price']:.1f}점"})
                chart_rows.append({"차량": label, "항목": "인프라", "점수": bd["infra"], "표시값": f"{bd['infra']:.1f}점"})
            chart_df = pd.DataFrame(chart_rows)
            fig = px.bar(
                chart_df, x="차량", y="점수", color="항목", barmode="stack", text="표시값",
                category_orders={"차량": chart_order},
            )
            fig.update_traces(textposition="inside")
            fig.update_layout(
                height=420, margin=dict(l=10, r=10, t=20, b=10), bargap=0.4,
                yaxis_title="종합점수까지 누적된 점수", xaxis_title=None,
            )
            st.plotly_chart(fig, use_container_width=True, key=chart_key)

        # 어떤 점수 기준으로 순위를 볼지 탭으로 나눠서 보여준다 (종합점수 순위가 맨 앞)
        # 탭을 바꾸면 카드 순서뿐 아니라 아래 "점수 구성 그래프"도 그 탭 기준 순서로 같이 바뀐다.
        tab_total, tab_fuel, tab_price = st.tabs(
            ["종합점수 순위", "연료비점수 순위", "가격점수 순위"]
        )
        with tab_total:
            _render_reco_grid(result, "total", show_actions=True)  # result 는 이미 종합점수 내림차순으로 정렬돼 있음
            st.divider()
            st.subheader("점수 구성 그래프 (상위 10대)")
            _render_reco_chart(result, "reco_chart_total")
        with tab_fuel:
            fuel_sorted = result.sort_values("연료비점수", ascending=False)
            _render_reco_grid(fuel_sorted, "fuel", show_actions=False)
            st.divider()
            st.subheader("점수 구성 그래프 (상위 10대)")
            _render_reco_chart(fuel_sorted, "reco_chart_fuel")
        with tab_price:
            price_sorted = result.sort_values("가격점수", ascending=False)
            _render_reco_grid(price_sorted, "price", show_actions=False)
            st.divider()
            st.subheader("점수 구성 그래프 (상위 10대)")
            _render_reco_chart(price_sorted, "reco_chart_price")

        with st.expander("전체 후보 비교표"):
            show_cols = ["브랜드", "모델명", "세그먼트", "연료", "annual_fuel_cost",
                         "effective_price", "infra_score", "종합점수"]
            show = result[show_cols].rename(columns={
                "annual_fuel_cost": "연간 연료비(원)", "effective_price": "실구매가(원)",
                "infra_score": "인프라점수",
            })
            st.dataframe(show, hide_index=True)
            st.download_button(
                "⬇️ 추천 결과 CSV로 다운로드", data=show.to_csv(index=False).encode("utf-8-sig"),
                file_name="차량추천결과.csv", mime="text/csv", key="download_reco_csv",
            )

        st.divider()
        st.subheader("AI 추천 이유 설명")
        if st.button("제미나이에게 추천 이유 물어보기"):
            summary = build_recommend_summary(profile, result)
            prompt = (
                "아래는 자동차 추천 시스템이 실제 데이터로 계산한 상위 후보 목록이다. "
                "1위 차량이 왜 이 사용자에게 적합한지, 2~3위와 비교해서 4~5문장으로 친절하게 설명해줘. "
                "숫자에 근거해서만 설명해줘.\n\n"
                f"{summary}"
            )
            with st.spinner("AI 답변 생성 중..."):
                st.session_state["reco_ai_text"] = ask_gemini(prompt)
        if "reco_ai_text" in st.session_state:
            st.info(st.session_state["reco_ai_text"])

        # ---- 차량 비교 (레이더 차트 + 표) ----------------------------------------------
        st.divider()
        st.subheader("차량 비교")
        compare_map = st.session_state.get("compare_selected", {})
        if len(compare_map) < 2:
            st.caption("위 '종합점수 순위' 탭의 카드에서 차량 2~3대의 '비교에 추가' 버튼을 누르면 여기에 비교 결과가 나타납니다.")
        else:
            compare_rows = list(compare_map.values())[:3]  # 최대 3대까지만 비교
            if len(compare_map) > 3:
                st.caption("※ 최대 3대까지 비교합니다. 먼저 선택한 3대만 표시돼요.")

            # 레이더(스파이더) 차트: 연료비/가격/인프라/종합 점수를 축으로 선형(채우기 없이)으로 겹쳐 그린다
            # 가시성 좋은 고대비 색상(색약 배려 팔레트, Okabe-Ito 기반)만 사용
            RADAR_COLORS = ["#E69F00", "#0072B2", "#009E73"]  # 주황 / 파랑 / 초록
            categories = ["연료비점수", "가격점수", "인프라점수", "종합점수"]
            fig = go.Figure()
            for i, r in enumerate(compare_rows):
                values = [r["연료비점수"], r["가격점수"], r["인프라점수"], r["종합점수"]]
                color = RADAR_COLORS[i % len(RADAR_COLORS)]
                fig.add_trace(go.Scatterpolar(
                    r=values + values[:1], theta=categories + categories[:1],
                    fill="none", mode="lines+markers",
                    line=dict(color=color, width=3), marker=dict(color=color, size=7),
                    name=f"{r['브랜드']} {r['모델명']}",
                ))
            fig.update_layout(
                polar=dict(
                    bgcolor="rgba(0,0,0,0)",
                    radialaxis=dict(visible=True, range=[0, 100], gridcolor="rgba(150,150,150,0.35)"),
                    angularaxis=dict(gridcolor="rgba(150,150,150,0.35)"),
                ),
                height=420, margin=dict(l=30, r=30, t=30, b=30), showlegend=True,
            )
            st.plotly_chart(fig, use_container_width=True, key="compare_radar")

            # 나란히 비교하는 표
            cmp_df = pd.DataFrame([
                {
                    "차량": f"{r['브랜드']} {r['모델명']}", "세그먼트": r["세그먼트"], "연료": r["연료"],
                    "연간 연료비(원)": r["annual_fuel_cost"], "실구매가(원)": r["effective_price"],
                    "연료비점수": r["연료비점수"], "가격점수": r["가격점수"],
                    "인프라점수": r["인프라점수"], "종합점수": r["종합점수"],
                }
                for r in compare_rows
            ])
            st.dataframe(cmp_df, hide_index=True)

            if st.button("비교 선택 초기화", key="clear_compare"):
                st.session_state["compare_selected"] = {}
                st.rerun()
    elif result is not None:
        st.info("조건에 맞는 차량이 없습니다. 예산이나 연료 선호도를 조정해 보세요.")

    st.divider()
    with st.expander("이 화면이 사용하는 실제 데이터 출처"):
        st.markdown(
            f"- **차량 연비/출고가** — DB `car_info` 테이블 ({len(SAMPLE_CARS)}종)\n"
            "- **연료비점수 / 인프라점수 / 실구매가점수** — DB 뷰 `view_car_recommend` "
            "(차량×지역별로 이미 계산되어 있는 점수를 그대로 가져와 씀)\n"
            "- **시도별 주유소 평균가격 / 전기차 보조금 / 등록현황 / 충전소 현황** — "
            "`view_car_recommend` 뷰가 내부적으로 `sido_oil_price` / `electric_car_subsidies` / "
            "`electric_vehicles` / `ev_chargers` 테이블을 조인해서 계산함"
        )


# ---- [통계 확인] 화면에서 고를 수 있는 4가지 통계 종류 ----------------------------
# 이 문자열들이 그대로 화면의 라디오 버튼 선택지로 쓰인다.
STATS_ANALYSIS_GAS = "지역별 주유소 평균가격"
STATS_ANALYSIS_SUBSIDY = "전기차 보조금"
STATS_ANALYSIS_EV_RAW = "전기차 등록·충전소 현황"
STATS_ANALYSIS_FUEL_EFF = "연료별 평균 연비 비교"
STATS_ANALYSIS_ORIGIN_PRICE = "국산차 vs 수입차 가격대"
STATS_ANALYSIS_OPTIONS = [
    STATS_ANALYSIS_GAS, STATS_ANALYSIS_SUBSIDY,
    STATS_ANALYSIS_EV_RAW, STATS_ANALYSIS_FUEL_EFF, STATS_ANALYSIS_ORIGIN_PRICE,
]


def _ranked_bar(series: "pd.Series", value_label: str, color_scale: str = "Blues"):
    """지역/모델별 값을 정렬된 막대그래프로 (색상=값 크기).
    통계 탭의 여러 항목(주유소가격/보조금 등)이 공통으로 이 함수를 재사용한다."""
    df = series.reset_index()
    df.columns = ["구분", value_label]
    fig = px.bar(
        df, x="구분", y=value_label, color=value_label,
        color_continuous_scale=color_scale, text_auto=".2s",
    )
    fig.update_layout(showlegend=False, coloraxis_showscale=False, height=380,
                       margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)


def _region_bubble_map(series: "pd.Series", value_label: str, color_scale: str = "Blues"):
    """지역별 값을 버블(원 크기·색)로 지도 위에 표시 (근사 좌표 기반)."""
    rows = [
        {"지역": r, value_label: v, "lat": REGION_COORDS[r][0], "lon": REGION_COORDS[r][1]}
        for r, v in series.items() if r in REGION_COORDS
    ]
    if not rows:
        return
    mdf = pd.DataFrame(rows)
    if hasattr(px, "scatter_map"):
        # plotly >= 5.24: 신규 MapLibre 기반 API (scatter_mapbox 대체)
        fig = px.scatter_map(
            mdf, lat="lat", lon="lon", size=value_label, color=value_label,
            color_continuous_scale=color_scale, size_max=38, zoom=5.2,
            center={"lat": 36.3, "lon": 127.8}, hover_name="지역",
            map_style="open-street-map", height=400,
        )
    else:
        # plotly 구버전 호환
        fig = px.scatter_mapbox(
            mdf, lat="lat", lon="lon", size=value_label, color=value_label,
            color_continuous_scale=color_scale, size_max=38, zoom=5.2,
            center={"lat": 36.3, "lon": 127.8}, hover_name="지역",
            mapbox_style="open-street-map", height=400,
        )
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("※ 지도는 시도청 소재지 기준 근사 좌표이며, 원의 크기·색이 클수록 값이 큽니다.")


def render_recommend_stats():
    """[통계 확인] 화면: 볼 통계 종류를 고르면 그 아래에 해당 통계만 보여주는 화면.
    흐름: ① 볼 통계 종류 선택(버튼) → ② 선택한 종류에 맞는 지표·그래프·표를 그리고 → ③ AI 해설 버튼.
    (예전에는 여기에 "조회 조건"(지역/연료/국산·수입 멀티셀렉트) 이 있었는데 삭제함 —
     이제 아래 각 통계는 항상 "전체" 기준으로 보여준다.)"""
    regions_sel = REGIONS
    fuels_sel = FUEL_CHOICES
    origin_sel = ORIGIN_CHOICES[1:]  # ["국산차", "수입차"] — "전체" 통계에선 이 둘을 다 합쳐서 본다

    # 통계 종류 버튼: 여러 개 중 하나를 누르면 그 항목만 선택된 상태(primary)로 표시되고,
    # 아래 if/elif 중 해당 블록만 실행되어 그 통계에 맞는 지표·그래프·표가 그려진다.
    st.write("**통계 종류 선택**")
    st.session_state.setdefault("stats_analysis_pick", STATS_ANALYSIS_OPTIONS[0])
    BTN_PER_ROW = 5
    for row_start in range(0, len(STATS_ANALYSIS_OPTIONS), BTN_PER_ROW):
        row_opts = STATS_ANALYSIS_OPTIONS[row_start:row_start + BTN_PER_ROW]
        cols = st.columns(BTN_PER_ROW)
        for col, opt in zip(cols, row_opts):
            is_sel = st.session_state["stats_analysis_pick"] == opt
            if col.button(opt, key=f"stat_btn_{opt}", use_container_width=True,
                          type="primary" if is_sel else "secondary"):
                st.session_state["stats_analysis_pick"] = opt
                st.rerun()
    analysis = st.session_state["stats_analysis_pick"]
    st.markdown(f"#### {analysis}")

    ai_block = ""  # 맨 아래 "AI 해설" 버튼에 넘겨줄 데이터 텍스트 (각 분기에서 채워짐)

    if analysis == STATS_ANALYSIS_GAS:  # ---- 지역별 주유소 평균가격 ----
        price_view = st.radio("연료 종류", list(GAS_PRICE_BASE.keys()), horizontal=True, key="stats_fuel_pick")
        price_series = pd.Series(
            {r: gas_price(price_view, r) for r in regions_sel}, name=f"{price_view}(원/L)"
        ).sort_values(ascending=False)
        m1, m2 = st.columns(2)
        m1.metric("선택 지역 평균가격", f"{price_series.mean():,.0f}원")
        m2.metric("최고-최저 지역 차이", f"{price_series.max() - price_series.min():,.0f}원")
        c1, c2 = st.columns([3, 2])
        with c1:
            _ranked_bar(price_series, f"{price_view}(원/L)", color_scale="OrRd")
        with c2:
            _region_bubble_map(price_series, f"{price_view}(원/L)", color_scale="OrRd")
        st.dataframe(price_series.reset_index().rename(columns={"index": "지역"}), hide_index=True)
        ai_block = f"[선택 지역 {price_view} 가격]\n{price_series.to_csv()}"

    elif analysis == STATS_ANALYSIS_SUBSIDY:  # ---- 전기차 보조금 ----
        subsidy_series = pd.Series(
            {r: EV_SUBSIDY.get(r, 0) for r in regions_sel}, name="보조금(원)"
        ).sort_values(ascending=False)
        m1, m2 = st.columns(2)
        m1.metric("선택 지역 평균 보조금", f"{subsidy_series.mean():,.0f}원")
        m2.metric("최고 지역", f"{subsidy_series.idxmax()} ({subsidy_series.max():,.0f}원)")
        c1, c2 = st.columns([3, 2])
        with c1:
            _ranked_bar(subsidy_series, "보조금(원)", color_scale="Greens")
        with c2:
            _region_bubble_map(subsidy_series, "보조금(원)", color_scale="Greens")
        st.dataframe(subsidy_series.reset_index().rename(columns={"index": "지역"}), hide_index=True)
        ai_block = f"[선택 지역 전기차 보조금]\n{subsidy_series.to_csv()}"

    elif analysis == STATS_ANALYSIS_EV_RAW:  # ---- 전기차 등록·충전소 현황(원본 수치) ----
        ev_df = pd.DataFrame({
            "전기차 등록대수": [EV_REGISTRATION[r] for r in regions_sel],
            "충전기 수": [EV_CHARGERS[r] for r in regions_sel],
        }, index=regions_sel).sort_values("전기차 등록대수", ascending=False)
        m1, m2 = st.columns(2)
        m1.metric("선택 지역 전기차 등록대수 합", f"{ev_df['전기차 등록대수'].sum():,}대")
        m2.metric("선택 지역 충전기 수 합", f"{ev_df['충전기 수'].sum():,}기")
        c1, c2 = st.columns(2)
        with c1:
            _ranked_bar(ev_df["전기차 등록대수"], "전기차 등록대수", color_scale="Blues")
        with c2:
            _ranked_bar(ev_df["충전기 수"], "충전기 수", color_scale="Greens")
        st.dataframe(ev_df.reset_index(names="지역"), hide_index=True)
        ai_block = f"[선택 지역 전기차 등록대수/충전기수]\n{ev_df.to_csv()}"

    elif analysis == STATS_ANALYSIS_FUEL_EFF:  # ---- 연료별 평균 연비/전비 비교 ----
        spec_df = pd.DataFrame(SAMPLE_CARS)
        view = spec_df[spec_df["국산차"].isin(origin_sel)].copy()
        eff_rows = []
        for fuel in FUEL_CHOICES:
            sub = view[view["연료"] == fuel]
            if sub.empty:
                continue
            if fuel == "전기":
                eff_rows.append({"연료": fuel, "평균 효율": round(sub["전비"].mean(), 2), "단위": "km/kWh"})
            else:
                eff_rows.append({"연료": fuel, "평균 효율": round(sub["연비"].mean(), 2), "단위": "km/L"})
        eff_df = pd.DataFrame(eff_rows)
        if not eff_df.empty:
            m1, m2 = st.columns(2)
            best = eff_df.loc[eff_df["평균 효율"].idxmax()]
            m1.metric("비교 연료 수", f"{len(eff_df)}종")
            m2.metric("효율 1위 연료", f"{best['연료']} ({best['평균 효율']} {best['단위']})")
            fig = px.bar(
                eff_df, x="연료", y="평균 효율", color="단위", text="평균 효율",
                color_discrete_sequence=["#4fc3c3", "#f5a95f"],
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(eff_df, hide_index=True)
        ai_block = f"[연료별 평균 연비(km/L)·전비(km/kWh)]\n{eff_df.to_csv(index=False)}"

    elif analysis == STATS_ANALYSIS_ORIGIN_PRICE:  # ---- 국산차 vs 수입차 가격대 ----
        spec_df = pd.DataFrame(SAMPLE_CARS)
        view = spec_df[spec_df["연료"].isin(fuels_sel)].copy()
        dom = view[view["국산차"] == "국산차"]["출고가"]
        imp = view[view["국산차"] == "수입차"]["출고가"]
        m1, m2 = st.columns(2)
        m1.metric("국산차 평균 출고가", f"{dom.mean():,.0f}원" if not dom.empty else "-")
        m2.metric("수입차 평균 출고가", f"{imp.mean():,.0f}원" if not imp.empty else "-")
        if not view.empty:
            fig = px.box(
                view, x="국산차", y="출고가", color="국산차",
                color_discrete_sequence=["#4fc3c3", "#f06a6a"], title="국산차 vs 수입차 출고가 분포",
            )
            fig.update_layout(height=380, margin=dict(l=10, r=10, t=40, b=10), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        origin_stat = view.groupby("국산차")["출고가"].agg(["mean", "median", "min", "max", "count"]).rename(
            columns={"mean": "평균", "median": "중앙값", "min": "최저", "max": "최고", "count": "대수"}
        )
        st.dataframe(origin_stat.reset_index(), hide_index=True)
        ai_block = f"[국산차/수입차 출고가 비교]\n{origin_stat.to_csv()}"

    st.divider()
    ai_key = "recommend_stats_ai"
    if st.button("제미나이로 이 통계 해설받기", key="recommend_stats_ai_btn"):  # 누를 때만 AI 호출(비용 절약)
        prompt = (
            "아래는 자동차 추천 시스템의 '자동차 통계 확인' 화면에서 사용자가 고른 통계 종류에 "
            "맞춰 나온 실제 통계다(전체 지역·전체 연료·국산+수입 기준). "
            "숫자에 근거해서만 3~4문장으로 눈에 띄는 특징을 짚어줘.\n\n"
            + ai_block
        )
        with st.spinner("AI 답변 생성 중..."):
            st.session_state[ai_key] = ask_gemini(prompt)
    if ai_key in st.session_state:
        st.info(st.session_state[ai_key])


# 기업 FAQ 메뉴 (17개 브랜드) ============================================================
# 참고: 브랜드마다 별도 함수를 두지 않고, source 값(브랜드 한글명)을
# 매개변수로 받는 함수 하나(render_brand_faq)가 모든 브랜드를 동일한 방식으로 처리한다.
# (코드 중복을 피하기 위한 구조라서, 실제로는 "브랜드 선택 → 같은 화면에 다른 데이터"인 셈)

# 브랜드 선택 카드(_home_card)에 쓰이는 정보: 주소 쿼리값, 그림 종류, 태그, 소개 문구 등
# ※ 딕셔너리 key 는 반드시 db.py 의 FAQ_BRAND_TABLES 와 동일한 브랜드명(한글)이어야 한다.
BRAND_INFO = {
    "현대자동차": dict(
        query="hyundai", kind="hyundai", tag="HYUNDAI", domain="hyundai.com",
        desc="차량 구매·정비·블루링크·디지털 키 등 현대자동차 FAQ를 검색하고 AI에게 물어보세요.",
        cta="현대 FAQ 보러가기 →"),
    "기아자동차": dict(
        query="kia", kind="kia", tag="KIA", domain="kia.com",
        desc="차량 구매·정비·기아멤버스·PBV 등 기아자동차 FAQ를 검색하고 AI에게 물어보세요.",
        cta="기아 FAQ 보러가기 →"),
    "BMW": dict(
        query="bmw", kind="bmw", tag="BMW", domain="bmw.com",
        desc="차량 구매·정비·보증 등 BMW FAQ를 검색하고 AI에게 물어보세요.",
        cta="BMW FAQ 보러가기 →"),
    "벤츠": dict(
        query="benz", kind="benz", tag="MERCEDES-BENZ", domain="mercedes-benz.com",
        desc="차량 구매·정비·보증 등 벤츠 FAQ를 검색하고 AI에게 물어보세요.",
        cta="벤츠 FAQ 보러가기 →"),
    "아우디": dict(
        query="audi", kind="audi", tag="AUDI", domain="audi.com",
        desc="차량 구매·정비·보증 등 아우디 FAQ를 검색하고 AI에게 물어보세요.",
        cta="아우디 FAQ 보러가기 →"),
    "폭스바겐": dict(
        query="volkswagen", kind="volkswagen", tag="VOLKSWAGEN", domain="vw.com",
        desc="차량 구매·정비·보증 등 폭스바겐 FAQ를 검색하고 AI에게 물어보세요.",
        cta="폭스바겐 FAQ 보러가기 →"),
    "볼보": dict(
        query="volvo", kind="volvo", tag="VOLVO", domain="volvocars.com",
        desc="차량 구매·정비·보증 등 볼보 FAQ를 검색하고 AI에게 물어보세요.",
        cta="볼보 FAQ 보러가기 →"),
    "미니": dict(
        query="mini", kind="mini", tag="MINI", domain="mini.com",
        desc="차량 구매·정비·보증 등 미니 FAQ를 검색하고 AI에게 물어보세요.",
        cta="MINI FAQ 보러가기 →"),
    "랜드로버": dict(
        query="landrover", kind="landrover", tag="LAND ROVER", domain="landrover.com",
        desc="차량 구매·정비·보증 등 랜드로버 FAQ를 검색하고 AI에게 물어보세요.",
        cta="랜드로버 FAQ 보러가기 →"),
    "테슬라": dict(
        query="tesla", kind="tesla", tag="TESLA", domain="tesla.com",
        desc="차량 구매·정비·충전 등 테슬라 FAQ를 검색하고 AI에게 물어보세요.",
        cta="테슬라 FAQ 보러가기 →"),
    "토요타": dict(
        query="toyota", kind="toyota", tag="TOYOTA", domain="toyota.com",
        desc="차량 구매·정비·보증 등 토요타 FAQ를 검색하고 AI에게 물어보세요.",
        cta="토요타 FAQ 보러가기 →"),
    "렉서스": dict(
        query="lexus", kind="lexus", tag="LEXUS", domain="lexus.com",
        desc="차량 구매·정비·보증 등 렉서스 FAQ를 검색하고 AI에게 물어보세요.",
        cta="렉서스 FAQ 보러가기 →"),
    "혼다": dict(
        query="honda", kind="honda", tag="HONDA", domain="honda.com",
        desc="차량 구매·정비·보증 등 혼다 FAQ를 검색하고 AI에게 물어보세요.",
        cta="혼다 FAQ 보러가기 →"),
    "쉐보레": dict(
        query="chevrolet", kind="chevrolet", tag="CHEVROLET", domain="chevrolet.com",
        desc="차량 구매·정비·보증 등 쉐보레 FAQ를 검색하고 AI에게 물어보세요.",
        cta="쉐보레 FAQ 보러가기 →"),
    "포드": dict(
        query="ford", kind="ford", tag="FORD", domain="ford.com",
        desc="차량 구매·정비·보증 등 포드 FAQ를 검색하고 AI에게 물어보세요.",
        cta="포드 FAQ 보러가기 →"),
    "지프": dict(
        query="jeep", kind="jeep", tag="JEEP", domain="jeep.com",
        desc="차량 구매·정비·보증 등 지프 FAQ를 검색하고 AI에게 물어보세요.",
        cta="지프 FAQ 보러가기 →"),
    "르노": dict(
        query="renault", kind="renault", tag="RENAULT", domain="renault.com",
        desc="차량 구매·정비·보증 등 르노 FAQ를 검색하고 AI에게 물어보세요.",
        cta="르노 FAQ 보러가기 →"),
}
BRAND_BY_QUERY = {info["query"]: source for source, info in BRAND_INFO.items()}


def _faq_display_name(source: str) -> str:
    """"~FAQ" 라벨에 쓸 짧은 브랜드 표기. 현대자동차/기아자동차는 "현대"/"기아"로 줄이고,
    나머지 브랜드는 원래 이름(BRAND_INFO 의 key) 그대로 쓴다."""
    return {"현대자동차": "현대", "기아자동차": "기아"}.get(source, source)


def _faq_source_for_brand(brand: str) -> str | None:
    """추천 결과의 '브랜드'(예: 현대/기아/BMW)를 기업FAQ 쪽 브랜드명(예: 현대자동차/기아자동차)으로
    바꿔준다. FAQ 테이블이 없는 브랜드(제네시스/KGM/르노코리아 등)면 None을 돌려준다."""
    if brand in ("현대", "현대자동차"):
        return "현대자동차"
    if brand in ("기아", "기아자동차"):
        return "기아자동차"
    return brand if brand in BRAND_INFO else None


def brand_logo_url(domain: str, size: int = 128) -> str:
    """도메인만 넣으면 그 회사 로고(파비콘)를 가져와주는 구글 서비스 주소를 만들어 반환한다.
    (직접 로고 이미지 파일을 우리가 들고 있지 않아도, 브라우저가 실행될 때 구글에서 받아온다 —
     그래서 이 서버(스트림릿 실행 PC)에 인터넷이 연결돼 있어야 실제로 보인다)"""
    return f"https://www.google.com/s2/favicons?sz={size}&domain={domain}"


def _render_faq_feedback(feedback_id: str, source: str, question: str):
    """AI가 생성한 FAQ 답변 아래에 👍/👎 버튼을 그리고, 누른 결과를 세션에 기록해둔다.
    (DB 스키마 변경 없이 세션 동안만 집계 — 한 번 누르면 '이미 평가함' 문구로 바뀐다)"""
    st.session_state.setdefault("faq_feedback", {})
    voted = st.session_state["faq_feedback"].get(feedback_id)
    if voted:
        icon = "👍" if voted == "up" else "👎"
        st.caption(f"{icon} 이 답변에 대한 피드백을 남겨주셨습니다. 감사합니다!")
        return
    fb1, fb2, _ = st.columns([1, 1, 4])
    if fb1.button("👍 도움됨", key=f"fbup_{feedback_id}"):
        st.session_state["faq_feedback"][feedback_id] = "up"
        st.session_state.setdefault("faq_feedback_log", []).append(
            {"source": source, "question": question, "feedback": "up"}
        )
        st.rerun()
    if fb2.button("👎 아쉬워요", key=f"fbdown_{feedback_id}"):
        st.session_state["faq_feedback"][feedback_id] = "down"
        st.session_state.setdefault("faq_feedback_log", []).append(
            {"source": source, "question": question, "feedback": "down"}
        )
        st.rerun()


@st.dialog("AI에게 질문하기", width="large")
def _faq_ai_dialog(source: str):
    """render_brand_faq 의 "AI에게 질문" 기능을 팝업(모달)으로 띄운다.
    자유 질문을 입력하면 관련 FAQ를 근거로 AI가 답변한다."""
    st.write(f"**{source}** — 궁금한 내용을 물어보면, 이 브랜드 FAQ 중 관련된 것을 우선 참고해서 답해줍니다.")
    qa_key = f"faq_qa_{source}"
    question = st.text_area(
        "질문", placeholder="예: 정기 점검 주기는 어떻게 되나요?", key=f"faq_q_{source}",
    )
    if st.button("AI에게 물어보기", key=f"ask_btn_{source}") and question.strip():
        related = db.find_related_faqs(question, limit=5, source=source)
        if related:
            context = "\n\n".join(
                f"[{i}] 질문: {r['question']}\n답변: {r['answer']}"
                for i, r in enumerate(related, 1)
            )
        else:
            context = "(관련 FAQ를 찾지 못했음)"
        prompt = (
            f"너는 {source} 차량 관련 안내 도우미다. 아래 [참고 FAQ]는 질문과 관련 있어 보이는 "
            "사내 FAQ 목록이다.\n"
            "- 참고 FAQ에 관련 내용이 있으면 그 내용을 우선 근거로 답해줘.\n"
            "- 참고 FAQ에 없는 내용이어도 무조건 모른다고 하지 말고, 네가 알고 있는 일반적인 "
            "자동차/자동차회사 관련 지식으로 최대한 도움이 되게 답변해줘. 다만 이 경우 답변 끝에 "
            "'※ 공식 FAQ에는 없는 내용이라 참고용으로만 봐주세요.' 라고 꼭 덧붙여줘.\n"
            "- 정확한 수치(가격, 보증기간, 전화번호 등)처럼 추측하면 위험한 내용은 참고 FAQ에 "
            "없으면 추측하지 말고, 대신 어디서 확인하면 좋을지 안내해줘.\n"
            "- 이 챗봇은 'FAQ' 전용이다. 사용자가 '어떤 차 사야 할지 추천해줘'처럼 차량 추천을 "
            "요청하면 직접 추천하지 말고, '자동차 추천 시스템' 메뉴를 이용해 달라고 한 문장으로 "
            "부드럽게 안내만 해줘. 자동차와 무관한 질문이면 'AI 챗봇' 메뉴를 이용해 달라고 안내해줘.\n\n"
            f"[참고 FAQ]\n{context}\n\n[사용자 질문]\n{question.strip()}"
        )
        with st.spinner("AI 답변 생성 중..."):
            answer = ask_gemini(prompt)
        st.session_state[qa_key] = (answer, related)

    if qa_key in st.session_state:
        answer, related = st.session_state[qa_key]
        st.info(answer)
        if related:
            st.caption("참고한 FAQ: " + " / ".join(r["question"][:40] for r in related))
        _render_faq_feedback(f"qa_{source}", source, question.strip())


def render_brand_faq(source: str):
    """특정 브랜드(source="현대자동차" 또는 "기아자동차") 안에서 분류 목록 + 검색 화면.
    "AI에게 질문"은 더 이상 탭이 아니라 버튼을 누르면 팝업(모달) 채팅창으로 열린다."""
    try:
        categories = ["전체"] + db.get_categories(source)
    except Exception as e:
        st.error(f"DB 연결 오류: {e}")
        st.info("car_recommend.sql 을 DB에 import 해 두었는지 확인해 주세요.")
        return

    top_l, top_r = st.columns([2, 7])
    with top_l:
        if st.button("AI에게 질문하기", key=f"open_faq_ai_{source}",
                     icon=":material/android:", use_container_width=True):
            _faq_ai_dialog(source)

    # ---------------- 키워드 + 분류(pills)로 DB에서 FAQ를 검색해서 목록으로 보여준다
    keyword = st.text_input(
        "FAQ 검색어 입력", placeholder="예: 보증, 정비예약, 충전",
        key=f"kw_{source}",
    )
    category = st.pills(
        "분류", categories, default=categories[0], key=f"cat_{source}",
    )
    if category is None:  # 이미 선택된 pill을 다시 눌러 선택 해제한 경우
        category = "전체"

    results = db.get_faqs(keyword.strip(), category, source)
    if not results:
        st.info("검색 결과가 없습니다.")
    else:
        st.caption(f"검색 결과 {len(results)}건"
                   + (f" (상위 {MAX_FAQ_SHOWN}건만 표시)" if len(results) > MAX_FAQ_SHOWN else ""))
        for item in results[:MAX_FAQ_SHOWN]:
            with st.expander(f"{item['category']} · {item['question']}"):
                st.write("**답변**")
                st.markdown(item["answer"].replace("\n", "  \n"))
                st.caption(f"출처: {item['source']}")

                ai_key = f"faq_ai_{item['id']}"
                if st.button("AI 요약/추가 설명", key=f"btn_{item['id']}"):
                    prompt = (
                        "다음 FAQ 내용을 바탕으로 사용자에게 친절하고 쉽게 설명해줘. "
                        "FAQ에 없는 내용은 지어내지 말아줘.\n\n"
                        f"질문: {item['question']}\n답변: {item['answer']}"
                    )
                    with st.spinner("AI 답변 생성 중..."):
                        st.session_state[ai_key] = ask_gemini(prompt)
                if ai_key in st.session_state:
                    st.info(st.session_state[ai_key])
                    _render_faq_feedback(f"ai_{item['id']}", source, item["question"])


def _faq_counts() -> dict:
    """브랜드별 FAQ 개수를 DB에서 세어온다 (브랜드 선택 카드에 "FAQ 123건"처럼 표시하기 위함).
    DB 연결이 안 되면 그냥 빈 딕셔너리 반환 (앱이 죽지 않게)."""
    try:
        return db.faq_counts()
    except Exception:
        return {}


def render_faq_brand_select():
    """기업FAQ 기본 화면: 아직 사이드바에서 브랜드를 안 골랐을 때 보여주는 카드 2장짜리 화면.
    사이드바에는 더 이상 "선택 화면" 라디오 항목이 없지만, "기업FAQ 조회" 버튼을 누르면
    (=아직 브랜드를 안 골랐으면) 이 화면이 대신 뜬다."""
    counts = _faq_counts()
    hero = (
        '<div class="home-hero"><h1>기업 FAQ 조회</h1>'
        "<p>브랜드를 선택하면 FAQ 검색과 AI 질문을 사용할 수 있어요.</p></div>"
    )
    st.markdown(HOME_CSS + hero, unsafe_allow_html=True)

    # 브랜드가 17개나 돼서 한눈에 찾기 어려우니, 이름(한글/영문 태그)으로 검색해서 걸러낼 수 있게 한다
    keyword = st.text_input(
        "브랜드 검색", placeholder="예: 현대, BMW, 벤츠 ...",
        key="faq_brand_search", label_visibility="collapsed",
    ).strip()

    if keyword:
        items = [
            (source, info) for source, info in BRAND_INFO.items()
            if keyword.lower() in source.lower() or keyword.lower() in info["tag"].lower()
        ]
    else:
        items = list(BRAND_INFO.items())

    if not items:
        st.info(f"'{keyword}' 와(과) 일치하는 브랜드가 없어요.")
        return

    cards = ""
    for source, info in items:
        n = counts.get(source)
        tag = f"{info['tag']} · FAQ {n:,}건" if n else info["tag"]
        cards += _home_card(f"?menu=faq&amp;brand={info['query']}", info["kind"],
                            tag, source, info["desc"], info["cta"],
                            logo_url=brand_logo_url(info["domain"]))
    st.markdown('<div class="home-grid">' + cards + "</div>", unsafe_allow_html=True)


def render_faq_menu():
    """사이드바 "기업FAQ 조회" 메뉴의 진입점.
    사이드바 하위 라디오(현대 FAQ / 기아 FAQ)에서 아직 브랜드를 안 골랐으면 선택 화면을,
    골랐으면 render_brand_faq(선택한 브랜드)를 보여준다."""
    brand = st.session_state.get("faq_brand")
    if brand not in BRAND_INFO:
        render_faq_brand_select()
        return
    st.header(f"{_faq_display_name(brand)} FAQ")
    log = st.session_state.get("faq_feedback_log", [])
    if log:
        up_n = sum(1 for f in log if f["feedback"] == "up")
        down_n = sum(1 for f in log if f["feedback"] == "down")
        with st.expander(f"📊 AI 답변 피드백 현황 (👍 {up_n} / 👎 {down_n})"):
            fb_df = pd.DataFrame(log)
            st.dataframe(fb_df, hide_index=True)
    render_brand_faq(brand)  # brand 값(브랜드 한글명)에 따라 같은 함수가 다른 데이터를 보여줌


# 월납입금 계산기 ============================================================
# 원리금균등상환(매달 같은 금액을 내는 방식) 기준으로 월 납입금을 계산한다.
# 자동차 추천 결과/즐겨찾기에 있는 차량의 "실구매가"를 그대로 불러와서 계산할 수도 있다.
def _amortization_schedule(principal: float, annual_rate_pct: float, months: int) -> "pd.DataFrame":
    """원리금균등상환 스케줄(회차별 원금/이자/잔액)을 계산해서 표로 돌려준다."""
    r = (annual_rate_pct / 100) / 12  # 월 이자율
    if r == 0:
        monthly = principal / months
    else:
        monthly = principal * r * (1 + r) ** months / ((1 + r) ** months - 1)

    rows, balance = [], principal
    for m in range(1, months + 1):
        interest = balance * r
        principal_paid = monthly - interest
        balance = max(balance - principal_paid, 0)
        rows.append({"회차": m, "월 납입금": monthly, "원금": principal_paid, "이자": interest, "잔액": balance})
    return pd.DataFrame(rows)


# ---- 계산기 안에 들어가는 AI 상담 챗봇 (자연어로 "쏘나타 36개월 계약금 0원 연이자율 5%" 처럼
#      물어보면 조건을 읽어서 바로 계산해준다) ----------------------------------------------
def extract_calc_conditions(user_msg: str) -> dict:
    """(계산기 챗봇 전용) 메시지에서 차종 키워드/할부개월/계약금/연이자율 조건을 뽑아낸다."""
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_KEY") or "").strip()
    if not api_key:
        return {}
    try:
        from google import genai
    except ImportError:
        return {}

    prompt = (
        "너는 '월납입금 계산기' 챗봇의 조건 추출기다. 사용자 메시지를 분석해서 JSON 하나만 "
        "출력해라 (설명이나 코드블록 없이 JSON 텍스트만).\n\n"
        '{"model_keyword":<차량 모델명 또는 브랜드 키워드(예: "쏘나타")|null>,'
        '"months":<할부 개월수(숫자만)|null>,"down_payment_manwon":<계약금(만원 단위 숫자)|null>,'
        '"annual_rate_pct":<연이자율(% 단위 숫자)|null>}\n\n'
        "언급 안 된 값은 null 로 둬라. '5퍼센트', '5%', '연 5부' 등은 모두 5(숫자)로 변환해라.\n\n"
        f"사용자 메시지: {user_msg}"
    )
    try:
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        text = (resp.text or "").strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(text)
    except Exception:
        return {}


def calc_chat_answer(user_msg: str) -> str:
    """계산기 챗봇 답변 생성기. 메시지에서 조건을 뽑아 직접 계산하고, 결과를 아래쪽
    계산기 입력칸(session_state)에도 그대로 반영한다."""
    cond = extract_calc_conditions(user_msg)

    kw = (cond.get("model_keyword") or "").strip()
    matched = None
    if kw:
        candidates = [c for c in SAMPLE_CARS if kw in c["모델명"] or kw in c["브랜드"]]
        matched = candidates[0] if candidates else None

    if not matched:
        return (
            "차량 모델을 정확히 못 찾았어요 :( '쏘나타 36개월 계약금 0원 연이자율 5%' 처럼 "
            "실제 차량 모델명을 포함해서 다시 물어봐 주시겠어요?"
        )

    months_options = [12, 24, 36, 48, 60, 72]
    months = cond.get("months")
    if months not in months_options:
        months = min(months_options, key=lambda m: abs(m - months)) if months else 36

    down_payment_manwon = cond.get("down_payment_manwon")
    down_payment_manwon = int(down_payment_manwon) if down_payment_manwon else 0

    annual_rate = cond.get("annual_rate_pct")
    annual_rate = float(annual_rate) if annual_rate is not None else 5.9

    car_price_manwon = int(round(matched["출고가"] / 10_000))
    down_payment_manwon = min(down_payment_manwon, car_price_manwon)
    principal = (car_price_manwon - down_payment_manwon) * 10_000

    if principal <= 0:
        return "계약금이 차량 가격 이상이라 할부 원금이 없어요. 계약금을 조금 낮춰서 다시 물어봐 주시겠어요?"

    schedule = _amortization_schedule(principal, annual_rate, months)
    monthly_payment = schedule["월 납입금"].iloc[0]
    total_payment = schedule["월 납입금"].sum()
    total_interest = schedule["이자"].sum()

    # 아래쪽 계산기 입력칸에도 같은 조건을 그대로 반영해준다
    st.session_state["calc_car_price"] = car_price_manwon
    st.session_state["calc_down_payment"] = down_payment_manwon
    st.session_state["calc_months"] = months
    st.session_state["calc_rate"] = annual_rate

    return (
        f"네, 확인해드릴게요 :) **{matched['브랜드']} {matched['모델명']} · {months}개월 · "
        f"계약금 {down_payment_manwon:,}만원 · 연이자율 {annual_rate}%**\n\n"
        f"- 차량 가격: {matched['출고가']:,.0f}원\n"
        f"- 할부 원금: {principal:,.0f}원\n"
        f"- **월 납입금: {monthly_payment:,.0f}원**\n"
        f"- 총 납입액: {total_payment:,.0f}원\n"
        f"- 총 이자: {total_interest:,.0f}원\n\n"
        "아래 계산기 입력칸에도 같은 조건을 반영해 놨어요. 조건을 더 정확히 조정하고 싶으면 아래에서 직접 바꿔보셔도 돼요."
    )


def render_calc_chatbot():
    """계산기 화면 위쪽에 들어가는 미니 상담 채팅창을 그린다.
    AI 챗봇 메뉴/추천 상담창과는 완전히 별개로 session_state["calc_chat_msgs"] 에 따로 저장한다."""
    if "calc_chat_msgs" not in st.session_state:
        st.session_state["calc_chat_msgs"] = []

    for m in st.session_state["calc_chat_msgs"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    user_msg = st.chat_input(
        "예: 쏘나타 36개월 계약금 0원 연이자율 5%", key="calc_chat_input",
    )
    if user_msg:
        st.session_state["calc_chat_msgs"].append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.markdown(user_msg)
        with st.chat_message("assistant"):
            with st.spinner("계산하고 있어요..."):
                reply = calc_chat_answer(user_msg)
            st.markdown(reply)
        st.session_state["calc_chat_msgs"].append({"role": "assistant", "content": reply})

    if len(st.session_state["calc_chat_msgs"]) > 1:
        if st.button("상담 대화 초기화", key="calc_chat_clear"):
            st.session_state["calc_chat_msgs"] = []
            st.rerun()


@st.dialog("AI 상담사 — 월납입금 계산", width="large")
def _calc_chat_dialog():
    """render_calc_chatbot() 을 팝업(모달) 창 안에 그대로 그려서, 채팅방처럼 열고 닫을 수 있게 한다."""
    render_calc_chatbot()


def render_calc_menu():
    """[월납입금 계산기] 화면: 차량가격·계약금·할부기간·연이자율을 입력하면
    원리금균등상환 기준 월 납입금과 회차별 상환 스케줄을 계산해 보여준다."""
    st.caption("차량가격·계약금·할부기간·연이자율을 입력하면 원리금균등상환 기준 월 납입금을 계산해드려요.")

    # AI 상담사에게 자연어로 물어보면("쏘나타 36개월 계약금 0원 연이자율 5%") 바로 계산해준다
    unread = len(st.session_state.get("calc_chat_msgs", []))
    chat_label = "AI 상담사에게 물어보기" + (f" ({unread}개 대화 중)" if unread > 1 else "")
    if st.button(chat_label, key="open_calc_chat", type="primary",
                 icon=":material/android:", use_container_width=True):
        _calc_chat_dialog()

    st.divider()

    # ---- 차량 가격 불러오기: 전체 차량 직접 검색 ----
    st.session_state.setdefault("calc_car_price", 4000)  # 만원 단위, "차량 가격" 입력창의 시작값
    st.markdown("**차량 검색해서 가격 불러오기** (선택 사항 — 직접 입력해도 됩니다)")
    keyword = st.text_input(
        "모델명 또는 브랜드로 검색", placeholder="예: 아반떼, 쏘나타, 스포티지, 현대",
        key="calc_search_kw",
    )
    kw = keyword.strip()
    if kw:
        matches = [c for c in SAMPLE_CARS if kw in c["모델명"] or kw in c["브랜드"]]
        if not matches:
            st.caption("검색 결과가 없습니다.")
        else:
            match_options = {
                f"{c['브랜드']} {c['모델명']} ({c['세그먼트']}·{c['연료']}) — 출고가 {c['출고가']:,.0f}원": c["출고가"]
                for c in matches[:30]
            }
            st.caption(f"검색 결과 {len(matches)}건" + (" (상위 30건만 표시)" if len(matches) > 30 else ""))
            picked_search = st.selectbox(
                "검색된 차량에서 선택", list(match_options.keys()),
                index=None, placeholder="차량을 선택하세요", key="calc_search_pick",
            )
            if picked_search and st.button("이 차량 가격 불러오기", key="calc_search_apply"):
                st.session_state["calc_car_price"] = int(round(match_options[picked_search] / 10_000))
                st.rerun()

    st.divider()
    c1, c2 = st.columns(2)
    car_price_manwon = c1.number_input(
        "차량 가격 (만원)", min_value=0, max_value=100_000, step=100, key="calc_car_price",
    )
    down_payment_manwon = c2.number_input(
        "계약금 (만원)", min_value=0, max_value=car_price_manwon, step=100, value=0, key="calc_down_payment",
    )

    c3, c4 = st.columns(2)
    months = c3.selectbox("할부 기간 (개월)", [12, 24, 36, 48, 60, 72], index=2, key="calc_months")
    annual_rate = c4.number_input(
        "연이자율 (%)", min_value=0.0, max_value=30.0, step=0.1, value=5.9, key="calc_rate",
    )

    principal = (car_price_manwon - down_payment_manwon) * 10_000
    if principal <= 0:
        st.info("계약금이 차량 가격 이상이라 할부 원금이 없습니다.")
        return

    schedule = _amortization_schedule(principal, annual_rate, months)
    monthly_payment = schedule["월 납입금"].iloc[0]
    total_payment = schedule["월 납입금"].sum()
    total_interest = schedule["이자"].sum()

    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("월 납입금", f"{monthly_payment:,.0f}원")
    m2.metric("총 납입액", f"{total_payment:,.0f}원")
    m3.metric("총 이자", f"{total_interest:,.0f}원")

    # 회차별 원금/이자 구성 — 누적 막대그래프 (뒤로 갈수록 원금 비중이 커지는 걸 한눈에 보여준다)
    fig = px.bar(
        schedule, x="회차", y=["원금", "이자"], barmode="stack",
        color_discrete_map={"원금": "#4fc3c3", "이자": "#f06a6a"},
        title="회차별 원금·이자 구성",
    )
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=40, b=10), yaxis_title="금액(원)")
    st.plotly_chart(fig, use_container_width=True)

    # 잔액이 줄어드는 추이 — 선그래프
    fig2 = px.line(schedule, x="회차", y="잔액", title="잔여 원금 추이")
    fig2.update_traces(line=dict(color="#8a7fd6", width=3))
    fig2.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10), yaxis_title="잔액(원)")
    st.plotly_chart(fig2, use_container_width=True)

    with st.expander("회차별 상환 스케줄 전체 보기"):
        show = schedule.copy()
        for col in ["월 납입금", "원금", "이자", "잔액"]:
            show[col] = show[col].round(0).astype(int)
        st.dataframe(show, hide_index=True)
        st.download_button(
            "⬇️ 상환 스케줄 CSV로 다운로드", data=show.to_csv(index=False).encode("utf-8-sig"),
            file_name="월납입금_상환스케줄.csv", mime="text/csv", key="download_calc_csv",
        )


# 메뉴 ============================================================
# 여기서부터는 함수 정의가 아니라, 앱이 시작될 때 "지금 바로" 실행되는 코드다.
# 위에서 만든 함수들(render_home, render_chatbot_menu 등) 중 어떤 걸 부를지 결정한다.

# 사이드바 하위 라디오를 "새로 고침"시키기 위한 카운터. 대분류 메뉴를 옮길 때마다 1씩 늘려서,
# 하위 라디오의 key 를 매번 새 값으로 만든다 → 스트림릿이 완전히 새 위젯으로 취급해서
# 아무것도 선택되지 않은 상태(index=None)로 다시 그려진다 (= "선택 화면" 처럼 보이는 효과).
st.session_state.setdefault("reco_nav_gen", 0)
st.session_state.setdefault("faq_nav_gen", 0)

# 카드를 누르면 주소가 ?menu=faq&brand=kia 처럼 바뀌면서 들어온다 → 해당 화면으로 이동
# (사이드바 메뉴 아이콘 버튼도 홈 카드와 똑같이 이 방식(HTML 링크)으로 동작한다)
_target = st.query_params.get("menu")
if _target in MENU_BY_QUERY:
    # 카드/사이드바 버튼을 눌러서 들어온 경우: 주소창의 ?menu=... 값을 읽어서 session_state 에 반영
    st.session_state["menu"] = MENU_BY_QUERY[_target]
    if _target == "faq":
        st.session_state["faq_brand"] = BRAND_BY_QUERY.get(st.query_params.get("brand"))
        st.session_state["faq_nav_gen"] += 1
    if _target == "recommend":
        st.session_state["reco_view"] = RECO_VIEW_BY_QUERY.get(st.query_params.get("view"))
        st.session_state["reco_nav_gen"] += 1
    st.query_params.clear()  # 주소창의 ?menu=... 를 지워서 새로고침해도 같은 동작이 반복 안 되게 함
if "menu" not in st.session_state:
    st.session_state["menu"] = HOME_MENU  # 맨 처음 앱을 열었을 때는 홈 화면부터 시작

# ---- 사이드바 메뉴 (쇼핑몰의 "상의 누르면 그 자리에 바로 아웃터/셔츠/티셔츠가 펼쳐지는" 방식) ----
# st.radio 하나로는 항목 "사이"에 하위 메뉴를 끼워 넣을 수 없어서(라디오는 항상 한 덩어리로 그려짐),
# 대분류를 각각 "버튼처럼 보이는 HTML 링크"로 따로 그리고, 그 버튼 바로 아래에서 눌린 버튼일 때만
# 하위 라디오를 끼워 넣는 방식으로 만든다.
# (st.button 라벨 안에는 아이콘 HTML이 안 들어가므로, 홈 화면 카드와 같은 방식 — ?menu=... 로
#  주소를 바꾸는 HTML 링크 — 을 써서 아이콘을 버튼 "안에" 진짜로 넣는다)
st.sidebar.markdown("**메뉴 선택**")

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
st.sidebar.markdown(SIDEBAR_NAV_CSS, unsafe_allow_html=True)

QUERY_BY_MENU = {v: k for k, v in MENU_BY_QUERY.items()}  # HOME_MENU → "home" 처럼 반대 방향 매핑


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


_nav_button(HOME_MENU, HOME_MENU, "nav_home", icon_html=HOME_ICON_HTML)
_nav_button(CHATBOT_MENU, CHATBOT_MENU, "nav_chat", icon_html=AI_ICON_HTML)
_nav_button(RECOMMEND_MENU, RECOMMEND_MENU, "nav_reco", icon_html=RECO_ICON_HTML)

# "자동차 추천 시스템" 버튼 바로 아래 — 그 버튼이 지금 선택되어 있을 때만 하위 메뉴가 나타난다
if st.session_state.get("menu") == RECOMMEND_MENU:
    RECO_SUB_OPTIONS = ["자동차 추천 받기", "자동차 통계 확인"]
    RECO_SUB_TO_VIEW = {"자동차 추천 받기": "form", "자동차 통계 확인": "stats"}
    RECO_VIEW_TO_SUB = {v: k for k, v in RECO_SUB_TO_VIEW.items()}
    current_reco_sub = RECO_VIEW_TO_SUB.get(st.session_state.get("reco_view"))  # 없으면 None → 아무것도 선택 안 됨
    picked_reco_sub = st.sidebar.radio(
        "　", RECO_SUB_OPTIONS,
        index=(RECO_SUB_OPTIONS.index(current_reco_sub) if current_reco_sub else None),
        key=f"sidebar_reco_sub_{st.session_state['reco_nav_gen']}", label_visibility="collapsed",
    )
    if picked_reco_sub is not None:  # 사용자가 실제로 하나를 고른 경우에만 반영 (안 골랐으면 선택 화면 유지)
        st.session_state["reco_view"] = RECO_SUB_TO_VIEW[picked_reco_sub]

_nav_button(FAQ_MENU, FAQ_MENU, "nav_faq", icon_html=FAQ_ICON_HTML)

# "기업FAQ 조회" 버튼 바로 아래 — 그 버튼이 지금 선택되어 있을 때만 나타난다
# (CALC_MENU 버튼보다 먼저 그려야, 이 하위 목록이 "월납입금 계산기" 버튼 밑이 아니라
#  "기업FAQ 조회" 버튼 바로 아래에 나온다)
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

menu = st.session_state["menu"]  # 버튼/하위 라디오 반영이 끝난 최종 메뉴값

# 최종적으로 menu 값에 따라 각 메뉴의 함수를 딱 하나만 호출해서 화면을 그린다
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
else:  # FAQ_MENU
    st.title("")
    render_faq_menu()

st.divider()
st.caption("자동차 추천 시스템 및 기업FAQ 조회 시스템")
