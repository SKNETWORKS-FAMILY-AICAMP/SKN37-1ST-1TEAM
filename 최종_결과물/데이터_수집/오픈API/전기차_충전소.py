import os
import math
import requests
import xml.etree.ElementTree as ET
from urllib.parse import unquote
import pandas as pd
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# API 키 가져오기 및 디코딩
raw_service_key = os.getenv("공공데이터포털")
if not raw_service_key:
    raise ValueError(".env 파일에서 '공공데이터포털' 키를 찾을 수 없습니다.")

service_key = unquote(raw_service_key)
url = "https://apis.data.go.kr/B552584/EvCharger/getChargerInfo"

num_of_rows = 9999
page_no = 1
total_count = None
all_items = []

print("전기차 충전소 전체 데이터 수집을 시작합니다...")

while True:
    params = {
        "serviceKey": service_key,
        "pageNo": str(page_no),
        "numOfRows": str(num_of_rows)
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        root = ET.fromstring(response.text)
        
        if total_count is None:
            total_count_elem = root.find(".//totalCount")
            if total_count_elem is not None and total_count_elem.text:
                total_count = int(total_count_elem.text)
                total_pages = math.ceil(total_count / num_of_rows)
                print(f"전체 데이터 건수: {total_count:,}건 (총 {total_pages} 페이지)")
            else:
                print("totalCount 정보를 찾을 수 없어 조회를 종료합니다.")
                break

        items = root.findall(".//item")
        if not items:
            break

        for item in items:
            item_dict = {child.tag: child.text for child in item}
            all_items.append(item_dict)

        print(f"[{page_no}/{total_pages}] 페이지 수집 완료 ({len(all_items):,}/{total_count:,}건)")

        if len(all_items) >= total_count:
            break

        page_no += 1

    except requests.exceptions.RequestException as e:
        print(f"API 호출 중 오류 발생: {e}")
        break
    except ET.ParseError as e:
        print(f"XML 파싱 오류 발생: {e}")
        break

# --- 데이터 저장 및 강력한 지역명 파싱 ---
if all_items:
    df = pd.DataFrame(all_items)

    # 1. 원본 데이터 CSV 저장
    raw_output = "ev_charger_info_all.csv"
    df.to_csv(raw_output, index=False, encoding="utf-8-sig")
    print(f"\n전체 원본 데이터 저장 완료: '{raw_output}'")

    # 2. 주소(addr) 및 zcode 컬럼 확인
    addr_col = 'addr' if 'addr' in df.columns else next((col for col in df.columns if "주소" in col or "addr" in col.lower()), None)

    # 고도화된 지역 추출 함수
    def parse_region(row):
        addr_str = str(row.get(addr_col, '')).strip() if addr_col else ''
        zcode = str(row.get('zcode', '')).strip()
        
        # 1. 전남 / 광주 통합 우선 처리
        if any(keyword in addr_str for keyword in ["전남", "전라남도", "광주"]):
            return "전남광주"
        if zcode in ["29", "46"]: # 광주(29), 전남(46) zcode
            return "전남광주"

        # 2. 주소 전체 텍스트 내 광역시/도 키워드 검사 (오탈자 포함)
        if "서울" in addr_str: return "서울"
        if "경기" in addr_str: return "경기"
        if "인천" in addr_str: return "인천"
        if "부산" in addr_str: return "부산"
        if "대구" in addr_str: return "대구"
        if "대전" in addr_str: return "대전"
        if "울산" in addr_str: return "울산"
        if "세종" in addr_str or "다정중앙로" in addr_str: return "세종"  # 세종시 도로명 예외 처리
        if "강원" in addr_str: return "강원"
        if "충북" in addr_str or "충청북도" in addr_str or any(k in addr_str for k in ["청주시", "진천군", "괴산군", "충주시", "제천시"]): return "충북"
        if "충남" in addr_str or "충청남도" in addr_str: return "충남"
        if "전북" in addr_str or "전라북도" in addr_str: return "전북"
        if "경북" in addr_str or "경상북도" in addr_str or "경산북도" in addr_str or "경산시" in addr_str: return "경북"
        if "경남" in addr_str or "경상남도" in addr_str or "거제시" in addr_str: return "경남"
        if "제주" in addr_str or "서귀포시" in addr_str: return "제주"
        if "강서구" in addr_str: return "부산" # 강서구 기본 매핑 (필요시 서울/부산 구분 가능)

        # 3. 주소 분석 실패 시 zcode(지역코드) 기반 보완 매핑
        zcode_map = {
            "11": "서울", "26": "부산", "27": "대구", "28": "인천",
            "30": "대전", "31": "울산", "36": "세종", "41": "경기",
            "42": "강원", "43": "충북", "44": "충남", "45": "전북",
            "47": "경북", "48": "경남", "50": "제주"
        }
        if zcode in zcode_map:
            return zcode_map[zcode]

        return "기타/미분류"

    # 지역명 파싱 적용
    df["지역명"] = df.apply(parse_region, axis=1)

    # 3. 충전소수 및 충전기수 집계
    if "statId" in df.columns:
        summary_df = df.groupby("지역명").agg(
            충전소수=("statId", "nunique"),
            충전기수=("statId", "count")
        ).reset_index()
    else:
        summary_df = df.groupby("지역명").size().reset_index(name="충전기수")

    # 충전기 수 기준 내림차순 정렬
    summary_df = summary_df.sort_values(by="충전기수", ascending=False)

    summary_output = "C:/Users/playdata2/SKN_1ST_Project/최종_결과물/사용_데이터/오픈API/ev_charger_summary_by_region.csv"
    summary_df.to_csv(summary_output, index=False, encoding="utf-8-sig")
    
    print(f"\n정제된 지역명 기준 요약 저장 완료: '{summary_output}'")
    print("\n=== 지역별 전기차 충전소/충전기 요약 (전남/광주 통합) ===")
    print(summary_df.to_string(index=False))

else:
    print("수집된 데이터가 없습니다.")