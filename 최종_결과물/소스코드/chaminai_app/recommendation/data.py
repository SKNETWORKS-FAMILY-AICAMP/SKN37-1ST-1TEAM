"""Recommendation data loading and DB-backed lookups."""
import re

import streamlit as st
import db

from ..config import FUEL_CHOICES

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
