import pandas as pd
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# 1. API 호출 및 전체 데이터 가져오기
url = "https://api.odcloud.kr/api/15039172/v1/uddi:30352622-49f8-4856-8bcd-c671c10cc251_201909191317"
service_key = os.getenv("전기차보조금현황")

# 전체 데이터 개수 확인
res = requests.get(
    url, params={"page": 1, "perPage": 1, "serviceKey": service_key}
).json()
total_count = res.get("totalCount", 0)

# 전체 데이터 요청
all_res = requests.get(
    url,
    params={"page": 1, "perPage": total_count, "serviceKey": service_key},
).json()
raw_data = all_res.get("data", [])

# 2. DataFrame 생성
df = pd.DataFrame(raw_data)

# 3. '시도' 컬럼에서 전남/광주 항목을 '전남광주'로 통합
# API 응답 표기에 따라 '전라남도', '광주광역시', '전남', '광주' 등을 모두 매핑
sido_mapping = {
    "전라남도": "전남광주",
    "광주광역시": "전남광주",
    "전남": "전남광주",
    "광주": "전남광주",
}
df["시도"] = df["시도"].replace(sido_mapping)

# 4. 숫자형 컬럼 전처리
numeric_cols = [
    "민간공고대수",
    "접수대수",
    "출고대수",
    "출고잔여대수",
    "최대보조금(만원)_승용",
    "최대보조금(만원)_초소형",
    "최대보조금(만원)_화물",
]

for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# 5. 집계 규칙 설정 (대수: 합계, 보조금: 최댓값)
agg_dict = {
    "민간공고대수": "sum",
    "접수대수": "sum",
    "출고대수": "sum",
    "출고잔여대수": "sum",
    "최대보조금(만원)_승용": "max",
    "최대보조금(만원)_초소형": "max",
    "최대보조금(만원)_화물": "max",
}
agg_dict = {col: func for col, func in agg_dict.items() if col in df.columns}

# 6. 시도별 그룹화 및 집계
df_grouped = df.groupby("시도", as_index=False).agg(agg_dict)

# 7. CSV 파일로 저장
file_name = "전기차구매보조금지급현황_시도별집계_전남광주통합.csv"
df_grouped.to_csv(file_name, index=False, encoding="utf-8-sig")

print("전남/광주 통합 시도별 집계 완료:")
print(df_grouped)
print(f"\n'{file_name}' 파일로 저장되었습니다.")