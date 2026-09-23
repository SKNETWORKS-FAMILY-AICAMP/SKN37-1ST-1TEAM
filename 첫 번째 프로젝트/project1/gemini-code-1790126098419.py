import streamlit as st
import pandas as pd
import sqlite3

st.set_page_config(page_title="자동차 맞춤 추천 시스템", page_icon="🚗", layout="wide")

st.title("🚗 자동차 맞춤 추천 시스템")
st.caption("평가 가중치: 출고가(실구매가) 40% | 연료비(주행비용) 40% | 인프라 편의성 20%")

# --- 1. 가중치 정수 정의 ---
W_PRICE = 0.40
W_COST = 0.40
W_INFRA = 0.20

# --- 2. 검색 조건 사이드바 ---
st.sidebar.header("⚙️ 조건 선택")
region = st.sidebar.selectbox(
    "거주 지역", 
    ["서울", "경기", "부산", "대구", "인천", "대전", "광주", "울산", "세종", "제주"]
)
annual_km = st.sidebar.number_input("연간 예상 주행거리 (km)", value=15000, step=1000)

# --- 3. 데이터 베이스 로드 ---
@st.cache_data
def load_data():
    conn = sqlite3.connect('car_recommend.db')
    cars = pd.read_sql("SELECT * FROM car_info", conn)
    oil = pd.read_sql("SELECT * FROM sido_oil_price", conn)
    subsidy = pd.read_sql("SELECT * FROM electric_car_subsidies", conn)
    chargers = pd.read_sql("SELECT * FROM ev_per_charger_view", conn)
    conn.close()
    return cars, oil, subsidy, chargers

cars_df, oil_df, sub_df, charger_df = load_data()

# --- 4. 추천도 산출 로직 ---
def get_recommendations(cars, oil, sub, chargers, target_sido, annual_km):
    df = cars.copy()
    
    # 연비/전비 숫자 데이터 추출
    df['efficiency_num'] = df['avg_efficiency'].str.extract(r'([\d\.]+)').astype(float)
    
    # 1) 지역별 보조금 및 실구매가 계산
    sub_row = sub[sub['sido'] == target_sido]
    max_sub = sub_row['max_subsidy_passenger'].values[0] if not sub_row.empty else 1700
    
    df['net_price'] = df.apply(
        lambda x: max(0, x['price_num'] - max_sub) if '전기' in str(x['fuel_type']) else x['price_num'], 
        axis=1
    )
    
    # 2) km당 주행비용 계산
    # 유가 추출 (해당 지역 유가 정보가 없을 경우 전국 평균 사용)
    gas_row = oil[(oil['sido_nm'] == target_sido) & (oil['prod_cd'] == 'B027')]
    die_row = oil[(oil['sido_nm'] == target_sido) & (oil['prod_cd'] == 'D047')]
    lpg_row = oil[(oil['sido_nm'] == target_sido) & (oil['prod_cd'] == 'K015')]
    
    gas_price = gas_row['price'].values[0] if not gas_row.empty else 1904.3
    die_price = die_row['price'].values[0] if not die_row.empty else 1886.4
    lpg_price = lpg_row['price'].values[0] if not lpg_row.empty else 1156.1
    ev_price = 347.2  # 전기차 평균 충전 단가 (원/kWh)

    def calc_cost(row):
        f_type = str(row['fuel_type'])
        eff = row['efficiency_num']
        if eff == 0 or pd.isna(eff): return 9999
        
        if '가솔린' in f_type or '하이브리드' in f_type: return gas_price / eff
        elif '디젤' in f_type: return die_price / eff
        elif 'LPG' in f_type: return lpg_price / eff
        elif '전기' in f_type: return ev_price / eff
        return 200

    df['cost_per_km'] = df.apply(calc_cost, axis=1)
    
    # 3) 지표별 100점 만점 정규화 점수 계산
    p_min, p_max = df['net_price'].min(), df['net_price'].max()
    c_min, c_max = df['cost_per_km'].min(), df['cost_per_km'].max()
    
    df['score_price'] = (1 - (df['net_price'] - p_min) / (p_max - p_min)) * 100
    df['score_cost'] = (1 - (df['cost_per_km'] - c_min) / (c_max - c_min)) * 100
    
    # 전기차 인프라 점수 계산 (충전기당 전기차 수)
    ch_row = chargers[chargers['시도'] == target_sido]
    ev_per_ch = ch_row['충전기당_전기차수'].values[0] if not ch_row.empty else 1.5
    all_ch_max = chargers['충전기당_전기차수'].max() if not chargers.empty else 6.0
    all_ch_min = chargers['충전기당_전기차수'].min() if not chargers.empty else 0.5
    
    ev_infra_score = (1 - (ev_per_ch - all_ch_min) / (all_ch_max - all_ch_min)) * 100
    
    df['score_infra'] = df['fuel_type'].apply(lambda x: ev_infra_score if '전기' in str(x) else 100.0)
    
    # 4) 최종 가중치 적용 (40:40:20)
    df['total_score'] = (
        df['score_price'] * W_PRICE + 
        df['score_cost'] * W_COST + 
        df['score_infra'] * W_INFRA
    ).round(1)
    
    df['annual_cost'] = ((df['cost_per_km'] * annual_km) / 10000).round(1)
    
    return df.sort_values(by='total_score', ascending=False)

# 계산 실행
results = get_recommendations(cars_df, oil_df, sub_df, charger_df, region, annual_km)

# --- 5. 결과 출력 ---
st.subheader(f"🏆 {region} 지역 추천 차량 TOP 10")

top10 = results.head(10)[['brand', 'car_name', 'fuel_type', 'net_price', 'cost_per_km', 'annual_cost', 'total_score']]
top10.columns = ['브랜드', '모델명', '연료 타입', '실구매가(만원)', 'km당 비용(원)', f'연간 유지비({annual_km:,}km)', '종합 점수']
top10.reset_index(drop=True, inplace=True)
top10.index += 1

st.dataframe(top10, use_container_width=True)
st.bar_chart(top10.set_index('모델명')['종합 점수'])