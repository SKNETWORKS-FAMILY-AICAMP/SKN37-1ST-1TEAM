import os
import requests
import pandas as pd
from urllib.parse import unquote
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# .env 파일에서 API 키 가져오기
raw_service_key = os.getenv("공공데이터포털")
if not raw_service_key:
    raise ValueError(".env 파일에서 '공공데이터포털' 키를 찾을 수 없습니다.")

service_key = unquote(raw_service_key)

# API Endpoint URL
url = "https://api.odcloud.kr/api/15142951/v1/uddi:4b80ee12-8cb5-4ac9-b08b-fd58b7dac635"

page = 1
per_page = 1000  # 한 번에 최대한 많은 데이터 요청
all_data = []

print("전체 데이터 수집을 시작합니다...")

while True:
    params = {
        "page": page,
        "perPage": per_page,
        "serviceKey": service_key
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        res_json = response.json()
        
        data = res_json.get("data", [])
        if not data:
            break
            
        all_data.extend(data)
        
        total_count = res_json.get("totalCount", 0)
        print(f"[{page} 페이지] 누적 수집 건수: {len(all_data):,}/{total_count:,}건")
        
        if len(all_data) >= total_count:
            break
            
        page += 1

    except requests.exceptions.RequestException as e:
        print(f"API 호출 중 오류 발생: {e}")
        break

# --- 데이터 처리 및 시도별 총합 집계 ---
if all_data:
    df = pd.DataFrame(all_data)
    
    # 1. 원본 데이터 CSV 저장
    raw_filename = "ev_car_registered_all.csv"
    df.to_csv(raw_filename, index=False, encoding="utf-8-sig")
    print(f"\n전체 원본 데이터 저장 완료: '{raw_filename}'")
    
    # 2. '계' 컬럼 및 '시군구' 컬럼 찾기
    count_col = '계' if '계' in df.columns else next((col for col in df.columns if "계" in col or "대수" in col), None)
    region_col = next((col for col in df.columns if "시군구" in col or "지역" in col or "시도" in col), None)

    if count_col and region_col:
        # '계' 컬럼을 숫자형으로 변환
        df[count_col] = pd.to_numeric(df[count_col], errors="coerce").fillna(0)
        
        # 3. '서울 중구' -> '서울' 형태로 시도명 추출 및 전남/광주 통합 함수
        def extract_sido(region_str):
            region_str = str(region_str).strip()
            
            # 전남 및 광주 통합 처리
            if region_str.startswith("전남") or "전라남도" in region_str or region_str.startswith("광주"):
                return "전남광주"
            
            # 첫 번째 단어(시도명) 추출 (예: '서울 중구' -> '서울')
            sido_first_word = region_str.split()[0] if region_str else ""
            
            # 광역지자체 단위 정규화
            if "서울" in sido_first_word: return "서울"
            if "경기" in sido_first_word: return "경기"
            if "인천" in sido_first_word: return "인천"
            if "부산" in sido_first_word: return "부산"
            if "대구" in sido_first_word: return "대구"
            if "대전" in sido_first_word: return "대전"
            if "울산" in sido_first_word: return "울산"
            if "세종" in sido_first_word: return "세종"
            if "강원" in sido_first_word: return "강원"
            if "충북" in sido_first_word or "충청북도" in sido_first_word: return "충북"
            if "충남" in sido_first_word or "충청남도" in sido_first_word: return "충남"
            if "전북" in sido_first_word or "전라북도" in sido_first_word: return "전북"
            if "경북" in sido_first_word or "경상북도" in sido_first_word: return "경북"
            if "경남" in sido_first_word or "경상남도" in sido_first_word: return "경남"
            if "제주" in sido_first_word: return "제주"
            
            return sido_first_word if sido_first_word else region_str

        # 시도명 추출 적용
        df["시도명"] = df[region_col].apply(extract_sido)
        
        # 4. 시도명 기준 '계' 컬럼 합산
        summary_df = df.groupby("시도명", as_index=False)[count_col].sum()
        summary_df.rename(columns={count_col: "전기차총합"}, inplace=True)
        
        # 등록대수 내림차순 정렬
        summary_df = summary_df.sort_values(by="전기차총합", ascending=False)
        
        # 결과 CSV 저장
        summary_filename = "C:/Users/playdata2/SKN_1ST_Project/최종_결과물/사용_데이터/오픈API/ev_car_count_by_sido.csv"
        summary_df.to_csv(summary_filename, index=False, encoding="utf-8-sig")
        
        print(f"\n시도별 전기차 총합 요약 저장 완료: '{summary_filename}'")
        print("\n=== 시도별 전기차 총합 (전남/광주 통합) ===")
        print(summary_df.to_string(index=False))
    else:
        print(f"\n컬럼 인식 실패: 수량컬럼({count_col}), 지역컬럼({region_col})")
        print("전체 컬럼 목록:", list(df.columns))
else:
    print("수집된 데이터가 없습니다.")