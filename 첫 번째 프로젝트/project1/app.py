import os
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

st.title("🚗 전국 공식 전시장 및 대리점 안내")
st.markdown(
    "저장된 전시장 데이터를 기반으로 브랜드별 오프라인 상담 거점을 지도에서"
    " 확인해 보세요!"
)

# 파일 경로 설정 (C:\project1 경로 반영)
csv_path = r"C:\project1\car_dealerships.csv"

if os.path.exists(csv_path):
  # CSV 파일 불러오기
  df = pd.read_csv(csv_path)

  # [핵심] 한글 컬럼명이나 다른 이름으로 되어있을 경우 영문으로 자동 통일
  column_mapping = {
      "브랜드": "brand",
      "지점명": "name",
      "주소": "address",
      "전화번호": "phone",
  }
  df.rename(columns=column_mapping, inplace=True)

  # 만약 brand 컬럼이 아예 없다면 기본값 처리
  if "brand" not in df.columns:
    df["brand"] = "현대"

  # 위도(lat), 경도(lon) 컬럼이 없는 경우를 위한 안전 장치 (기본 서울 좌표 부여)
  if "lat" not in df.columns:
    df["lat"] = 37.5172
  if "lon" not in df.columns:
    df["lon"] = 127.0473

  # 상단 브랜드 선택 필터 (selectbox)
  brands = ["전체"] + list(df["brand"].dropna().unique())
  selected_brand = st.selectbox("전시장 브랜드 선택", brands)

  # 선택된 브랜드에 따른 데이터 필터링
  if selected_brand != "전체":
    filtered_df = df[df["brand"] == selected_brand]
  else:
    filtered_df = df

  # 지도 중심 설정
  if not filtered_df.empty:
    mean_lat = filtered_df["lat"].mean()
    mean_lon = filtered_df["lon"].mean()
    m = folium.Map(
        location=[mean_lat, mean_lon], zoom_start=11, tiles="OpenStreetMap"
    )
  else:
    m = folium.Map(location=[37.5172, 127.0473], zoom_start=11, tiles="OpenStreetMap")

  # 브랜드별 마커 색상 지정 딕셔너리
  brand_colors = {
      "현대": "blue",
      "기아": "red",
      "MINI": "green",
      "지프": "orange",
  }

  # 필터링된 전시장 위치를 지도에 마커로 표시
  for _, row in filtered_df.iterrows():
    brand_name = str(row.get("brand", "현대"))
    color = brand_colors.get(brand_name, "gray")
    place_name = str(row.get("name", "전시장"))
    address = str(row.get("address", "주소 없음"))
    phone = str(row.get("phone", "정보 없음"))

    popup_html = f"""
        <div style="font-family: 'Malgun Gothic'; width: 210px; padding: 5px;">
            <h4 style="margin: 0; color: #333;"><b>[{brand_name}] {place_name}</b></h4>
            <hr style="margin: 5px 0;">
            <p style="margin: 3px 0; font-size: 11px;"><b>주소:</b> {address}</p>
            <p style="margin: 3px 0; font-size: 11px;"><b>전화:</b> {phone}</p>
        </div>
        """

    folium.Marker(
        location=[row["lat"], row["lon"]],
        popup=folium.Popup(popup_html, max_width=300),
        tooltip=place_name,
        icon=folium.Icon(color=color, icon="car", prefix="fa"),
    ).add_to(m)

  # Streamlit 화면에 지도 렌더링
  st_folium(m, use_container_width=True, height=550)
  st.success(f"현재 지도에 총 **{len(filtered_df)}개**의 전시장이 표시됩니다.")

  # 하단에 상세 데이터 테이블 제공
  with st.expander("📋 전시장 상세 목록 및 연락처 보기"):
    st.dataframe(filtered_df.reset_index(drop=True), use_container_width=True)

else:
  st.error(
      f"⚠️ `{csv_path}` 경로에서 파일을 찾을 수 없습니다. 파일을 확인해 주세요!"
  )