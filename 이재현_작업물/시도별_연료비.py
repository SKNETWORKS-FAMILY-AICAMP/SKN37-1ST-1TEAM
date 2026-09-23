import requests
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

# 1. API 요청 설정
API_URL = "https://www.opinet.co.kr/api/avgSidoPrice.do"
API_KEY = os.getenv("오피넷")

params = {
    'code': API_KEY,
    'out': 'json'  # sido 및 prodcd 생략 시 모든 시도, 모든 연료 조회
}

# 2. API 호출
response = requests.get(API_URL, params=params)

if response.status_code == 200:
    data = response.json()
    
    # 3. 데이터 추출 (오피넷 API는 RESULT -> OIL 리스트 구조)
    oil_list = data.get('RESULT', {}).get('OIL', [])
    
    if oil_list:
        # 4. DataFrame 변환 및 컬럼명 정리
        df = pd.DataFrame(oil_list)
        
        # 반환값 항목에 맞춘 컬럼명 변경 (선택사항)
        column_mapping = {
            'SIDOCD': '시도코드',
            'SIDONM': '시도명',
            'PRODCD': '제품코드',
            'PRICE': '평균가격',
        }
        df = df.rename(columns=column_mapping)
        
        # 5. CSV 파일로 저장 (한글 깨짐 방지를 위해 utf-8-sig 사용)
        output_filename = "sido_fuel_prices.csv"
        df.to_csv(output_filename, index=False, encoding='utf-8-sig')
        
        print(f"성공적으로 데이터를 저장했습니다: {output_filename}")
        print(df.head())
    else:
        print("조회된 데이터가 없습니다.")
else:
    print(f"API 호출 실패 (상태 코드: {response.status_code})")