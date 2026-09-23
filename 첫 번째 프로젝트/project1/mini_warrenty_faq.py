import csv
import os
import requests

# 1. 저장 경로 설정 (C:\project1 경로 반영)
save_dir = r"C:\project1"
os.makedirs(save_dir, exist_ok=True)
file_path = os.path.join(save_dir, "car_dealerships.csv")

# 카카오 디벨로퍼스에서 복사한 REST API 키 입력
KAKAO_API_KEY = "c8a662def42e27f8a7a2d6c80abb9a13"

url = "https://dapi.kakao.com/v2/local/search/keyword.json"
headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}

# 브랜드별 검색 키워드 세분화 ('대리점'과 '전시장' 동시 공략)
target_queries = {
    "현대": ["현대자동차 대리점", "현대자동차 전시장"],
    "기아": ["기아 대리점", "기아 전시장"],
    "MINI": ["MINI 전시장"],
    "지프": ["지프 전시장"],
}

# 서울 25개 자치구 (밀집 지역 누락 방지)
seoul_gus = [
    "강남구",
    "강동구",
    "강북구",
    "강서구",
    "관악구",
    "광진구",
    "구로구",
    "금천구",
    "노원구",
    "도봉구",
    "동대문구",
    "동작구",
    "마포구",
    "서대문구",
    "서초구",
    "성동구",
    "성북구",
    "송파구",
    "양천구",
    "영등포구",
    "용산구",
    "은평구",
    "종로구",
    "중구",
    "중랑구",
]

# 경기도 주요 시 단위
gyeonggi_cities = [
    "수원시",
    "성남시",
    "고양시",
    "용인시",
    "부천시",
    "안산시",
    "안양시",
    "남양주시",
    "화성시",
    "평택시",
    "의정부시",
    "시흥시",
    "파주시",
    "광명시",
    "김포시",
    "광주시",
    "군포시",
    "오산시",
    "이천시",
    "양주시",
    "안성시",
    "구리시",
    "포천시",
    "의왕시",
    "하남시",
]

# 기타 광역시 및 도 단위
other_regions = [
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "세종",
    "강원",
    "충북",
    "충남",
    "전북",
    "전남",
    "경북",
    "경남",
    "제주",
]

dealership_data = []
seq = 1

print("=== 카카오 API 지역별 정밀 전시장 데이터 수집 시작 ===")

for brand, keywords in target_queries.items():
  print(f"\n[{brand} 브랜드 수집 중...]")
  for keyword in keywords:
    # 1. 서울은 구 단위로 쪼개서 검색 (45개 제한 우회)
    for gu in seoul_gus:
      query_str = f"{gu} {keyword}"
      fetch_data(query_str, brand, headers, url, dealership_data, seq)

    # 2. 경기도는 시 단위로 쪼개서 검색
    for city in gyeonggi_cities:
      query_str = f"{city} {keyword}"
      fetch_data(query_str, brand, headers, url, dealership_data, seq)

    # 3. 그 외 지역은 시/도 단위로 검색
    for reg in other_regions:
      query_str = f"{reg} {keyword}"
      fetch_data(query_str, brand, headers, url, dealership_data, seq)


# API 호출 및 데이터 가공 함수
def fetch_data(query_str, brand, headers, url, data_list, start_seq):
  params = {"query": query_str, "size": 15}
  response = requests.get(url, headers=headers, params=params)

  if response.status_code == 200:
    documents = response.json().get("documents", [])
    for doc in documents:
      name = doc["place_name"]
      address = (
          doc["road_address_name"]
          if doc["road_address_name"]
          else doc["address_name"]
      )
      lat = float(doc["y"])
      lon = float(doc["x"])
      phone = doc["phone"] if doc["phone"] else "정보 없음"

      # 중복 지점명 방지
      if not any(d[2] == name for d in data_list):
        data_list.append(
            [len(data_list) + 1, brand, name, address, lat, lon, phone]
        )


# 3. CSV 파일로 최종 저장
with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
  writer = csv.writer(f)
  writer.writerow(["순번", "브랜드", "지점명", "주소", "lat", "lon", "전화번호"])
  writer.writerows(dealership_data)

print(
    f"\n[완료] 총 {len(dealership_data)}개의 누락 없는 전시장 데이터를 수집하여"
    f" {file_path}에 저장했습니다."
)