"""Application configuration and immutable UI/data constants.

This module keeps constants that were originally defined in CHAMINAI.py.
The values/text are intentionally preserved.
"""
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent

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

# Original static/ directory lives beside the Streamlit entry script.
STATIC_DIR = PROJECT_ROOT / "static"
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


CHATBOT_SYSTEM_NOTE = (
    "너는 '자동차 추천 시스템 및 기업FAQ 조회' 사이트의 AI 챗봇이다. "
    "이 사이트는 (1) 주행거리·지역·예산·선호연료 조건으로 차량을 추천하는 기능과 "
    "(2) 현대·기아·BMW·벤츠 등 17개 브랜드 FAQ 검색 기능을 제공한다. "
    "차량 추천이나 FAQ와 관련 없는 일반적인 질문에도 친절하게 답하되, "
    "차량 구매·FAQ 관련 질문이면 위 두 기능과 자연스럽게 연결지어 안내해줘."
)


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


STATS_ANALYSIS_GAS = "지역별 주유소 평균가격"
STATS_ANALYSIS_SUBSIDY = "전기차 보조금"
STATS_ANALYSIS_EV_RAW = "전기차 등록·충전소 현황"
STATS_ANALYSIS_FUEL_EFF = "연료별 평균 연비 비교"
STATS_ANALYSIS_ORIGIN_PRICE = "국산차 vs 수입차 가격대"
STATS_ANALYSIS_OPTIONS = [
    STATS_ANALYSIS_GAS, STATS_ANALYSIS_SUBSIDY,
    STATS_ANALYSIS_EV_RAW, STATS_ANALYSIS_FUEL_EFF, STATS_ANALYSIS_ORIGIN_PRICE,
]


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

# config.py 하단에 추가
DINO_ICON_HTML = '<i class="bi bi-controller" style="font-size:1.3rem;"></i>'
DINO_MENU = "공룡 게임 🦖"

# MENU_BY_QUERY에 항목 추가
MENU_BY_QUERY = {
    "home": HOME_MENU,
    "chat": CHATBOT_MENU,
    "recommend": RECOMMEND_MENU,
    "faq": FAQ_MENU,
    "calc": CALC_MENU,
    "dino": DINO_MENU,
}