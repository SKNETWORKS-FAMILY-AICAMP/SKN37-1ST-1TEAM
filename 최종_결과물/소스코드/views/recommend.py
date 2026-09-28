import re
import pandas as pd
import streamlit as st

from db.connection import fetch_all
from db.car import get_car_info
from config import FUEL_CHOICES, ORIGIN_CHOICES
from ai_service import ask_gemini

# 1. 데이터 로딩 함수
@st.cache_data(show_spinner="데이터 불러오는 중...", ttl=3600)
def load_recommend_data():
    DOMESTIC_BRANDS = {"현대", "기아", "제네시스", "KGM", "르노코리아"}
    REGION_ORDER = ["서울", "부산", "대구", "인천", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남광주", "경북", "경남", "제주"]

    oil_rows = fetch_all("SELECT sido_nm, prod_cd, price FROM sido_oil_price WHERE prod_cd IN ('B027','D047','K015')")
    oil_by_region = {}
    for r in oil_rows:
        oil_by_region.setdefault(r["sido_nm"], {})[r["prod_cd"]] = float(r["price"])
    regions = [r for r in REGION_ORDER if r in oil_by_region]

    cars = []
    for r in get_car_info():
        eff_str = str(r["avg_efficiency"]) if r["avg_efficiency"] is not None else ""
        m = re.match(r"([\d.]+)", eff_str)
        eff_val = float(m.group(1)) if m else None
        fuel_type = str(r["fuel_type"])
        fuel = "전기" if "전기" in fuel_type else fuel_type.split("+")[0]
        cars.append(dict(
            모델명=r["car_name"], 브랜드=r["brand"], 세그먼트=r["car_type"], 연료=fuel,
            연료형태원본=fuel_type, 연비=(None if fuel == "전기" else eff_val),
            출고가=int(r["price_num"]) * 10_000,
            국산차=("국산차" if r["brand"] in DOMESTIC_BRANDS else "수입차")
        ))
    return regions, cars

# 2. 점수 및 보조금 데이터 로딩 함수
@st.cache_data(show_spinner="점수 데이터 불러오는 중...", ttl=3600)
def load_score_lookup():
    lookup = {}
    for r in fetch_all("SELECT * FROM view_car_recommend"):
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
            subsidy=subsidy * 10_000,
        )
    return lookup

# 3. 차량 추천 계산 로직 함수
def recommend_cars(annual_km: int, region: str, price_min: int, price_max: int, fuel_pref: list,
                   origin_pref: str, size_pref: list, w_fuel: float, w_price: float, w_infra: float,
                   sample_cars: list, score_lookup: dict) -> pd.DataFrame:
    candidates = [
        c for c in sample_cars
        if (not fuel_pref or c["연료"] in fuel_pref)
        and (origin_pref == "전체" or c["국산차"] == origin_pref)
        and (not size_pref or c["세그먼트"] in size_pref)
    ]
    
    rows = []
    for car in candidates:
        key = (car["브랜드"], car["모델명"], car["연료형태원본"], region)
        info = score_lookup.get(key, dict(km_cost=0, fuel_score=0, infra_score=0, price_score=0, subsidy=0))
        
        annual_fuel_cost = info["km_cost"] * annual_km
        effective_price = max(car["출고가"] - info["subsidy"], 0)
        
        rows.append({
            **car,
            "annual_fuel_cost": annual_fuel_cost,
            "effective_price": effective_price,
            "연료비점수": info["fuel_score"],
            "가격점수": info["price_score"],
            "인프라점수": info["infra_score"],
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    if price_max:
        within = df[(df["effective_price"] >= price_min) & (df["effective_price"] <= price_max)]
        if not within.empty:
            df = within

    total_w = w_fuel + w_price + w_infra or 3
    df["종합점수"] = (df["연료비점수"] * w_fuel + df["가격점수"] * w_price + df["인프라점수"] * w_infra) / total_w
    return df.sort_values("종합점수", ascending=False).reset_index(drop=True)

# 4. 추천 화면 UI 렌더링 함수
def render_recommend_menu(regions: list, sample_cars: list, score_lookup: dict, recommend_fn):
    st.header("🚗 맞춤형 자동차 추천 시스템")
    st.caption("고객님의 주행 패턴, 예산, 선호도 및 지역별 보조금/유가를 반영하여 최적의 차량을 추천합니다.")

    # 입력 폼
    with st.form("recommend_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            annual_km = st.number_input("연간 예상 주행거리 (km)", min_value=1000, max_value=100000, value=15000, step=1000)
            region = st.selectbox("거주 지역 (유가 및 보조금 기준)", options=regions, index=0)
            origin_pref = st.selectbox("차량 국산/수입 선호", options=ORIGIN_CHOICES, index=0)
            
            all_segments = sorted(list({c["세그먼트"] for c in sample_cars if c.get("세그먼트")}))
            size_pref = st.multiselect("차종/세그먼트 선택 (복수 가능)", options=all_segments, default=[])

        with col2:
            price_range = st.slider("최대 예산 범위 (만원)", min_value=1000, max_value=20000, value=(1000, 8000), step=500)
            fuel_pref = st.multiselect("선호 연료 타입 (미선택 시 전체)", options=FUEL_CHOICES, default=[])
            
            st.markdown("**가중치 설정 (총합 고려)**")
            w_fuel = st.slider("연비/연료비 가중치", 1, 5, 3)
            w_price = st.slider("차량 가격 가중치", 1, 5, 3)
            w_infra = st.slider("충전/정비 인프라 가중치", 1, 5, 2)

        submitted = st.form_submit_button("🔍 추천 차량 검색하기", use_container_width=True)

    # 결과 출력
    if submitted or "last_recommend_df" in st.session_state:
        if submitted:
            price_min_won = price_range[0] * 10_000
            price_max_won = price_range[1] * 10_000
            
            df = recommend_fn(
                annual_km, region, price_min_won, price_max_won,
                fuel_pref, origin_pref, size_pref,
                w_fuel, w_price, w_infra
            )
            st.session_state["last_recommend_df"] = df
            st.session_state["last_recommend_params"] = {
                "annual_km": annual_km, "region": region, "budget": price_range[1]
            }
        else:
            df = st.session_state["last_recommend_df"]

        if df.empty:
            st.warning("선택하신 조건에 부합하는 차량이 없습니다. 예산 범위나 선택 항목을 넓혀보세요.")
            return

        st.divider()
        st.subheader("📊 추천 검색 결과")

        display_df = df[["브랜드", "모델명", "세그먼트", "연료", "출고가", "effective_price", "annual_fuel_cost", "종합점수"]].copy()
        display_df.columns = ["브랜드", "모델명", "차종", "연료", "출고가(원)", "실구매가(보조금 반영)", "연간 예상 연료비", "종합점수"]
        
        display_df["출고가(원)"] = display_df["출고가(원)"].map("{:,.0f}원".format)
        display_df["실구매가(보조금 반영)"] = display_df["실구매가(보조금 반영)"].map("{:,.0f}원".format)
        display_df["연간 예상 연료비"] = display_df["연간 예상 연료비"].map("{:,.0f}원".format)
        display_df["종합점수"] = display_df["종합점수"].map("{:.1f}점".format)

        st.dataframe(display_df, use_container_width=True)

        st.markdown("### 🏆 TOP 3 추천 차량 상세")
        top3 = df.head(3)
        cols = st.columns(len(top3))
        
        for idx, (c_idx, row) in enumerate(top3.iterrows()):
            with cols[idx]:
                st.info(f"**{idx+1}위. {row['브랜드']} {row['모델명']}**")
                st.write(f"- **연료:** {row['연료']}")
                st.write(f"- **실구매가:** {row['effective_price']:,.0f} 원")
                st.write(f"- **연간 연료비:** {row['annual_fuel_cost']:,.0f} 원")
                st.write(f"- **종합점수:** {row['종합점수']:.1f} / 100 점")

        st.divider()
        if st.button("🤖 AI에게 이 추천 결과 상세 분석 요청하기"):
            with st.spinner("AI가 분석 리포트를 작성 중입니다..."):
                prompt = (
                    f"사용자 조건: 연간 주행거리 {st.session_state['last_recommend_params']['annual_km']:,}km, "
                    f"거주지역 {st.session_state['last_recommend_params']['region']}, "
                    f"예산 상한 {st.session_state['last_recommend_params']['budget']:,}만원.\n\n"
                    f"상위 추천 차량 목록:\n{top3[['브랜드', '모델명', '연료', 'effective_price', 'annual_fuel_cost', '종합점수']].to_string()}\n\n"
                    "이 고객에게 상위 3개 차량이 왜 최적인지, 각 차량의 장단점과 유지비 관점에서의 이점을 친절하게 설명해줘."
                )
                ai_report = ask_gemini(prompt)
                st.markdown("### 📝 AI 분석 리포트")
                st.write(ai_report)