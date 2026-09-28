import pandas as pd

"""Pure recommendation scoring logic."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

from .data import SCORE_LOOKUP, SAMPLE_CARS

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
