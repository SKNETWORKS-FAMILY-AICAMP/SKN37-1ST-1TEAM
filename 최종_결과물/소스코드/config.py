import os
from pathlib import Path

# 파일 및 경로 설정
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# AI 모델 및 설정
GEMINI_MODEL = os.getenv("GEMINI_MODEL") or "gemini-3.6-flash"
FALLBACK_MODELS = ["gemini-3.6-flash"]
RETRYABLE_MARKERS = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "overloaded")
RETRY_DELAYS = (1, 2, 4)

# 메뉴 상수
HOME_MENU = "Main Page"
RECOMMEND_MENU = "자동차 추천 시스템"
CHATBOT_MENU = "AI 챗봇"
FAQ_MENU = "기업FAQ 조회"
CALC_MENU = "월납입금 계산기"

MENU_BY_QUERY = {
    "home": HOME_MENU,
    "chat": CHATBOT_MENU,
    "recommend": RECOMMEND_MENU,
    "faq": FAQ_MENU,
    "calc": CALC_MENU,
}

# 공통 설정값
FUEL_CHOICES = ["가솔린", "디젤", "LPG", "하이브리드", "전기"]
ORIGIN_CHOICES = ["전체", "국산차", "수입차"]
EV_CHARGE_COST_PER_KWH = 320

# SVG 및 디자인 자원
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
    return (CAR_SVG.replace("#0f2a5c", sky1).replace("#2b6cb0", sky2).replace("#183a73", mountain)
            .replace("#ff6b6b", body1).replace("#d63447", body2))

HYUNDAI_SVG = _recolor_car("#0b1f4b", "#2f6fd0", "#14306b", "#eef2f9", "#a9b7cf")
KIA_SVG = _recolor_car("#17171c", "#8a2233", "#2a1a20", "#ffffff", "#c4c4c4")

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