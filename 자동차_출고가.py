import csv
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def classify_car_category(raw_segment):
    """차종 정보(raw_segment)를 확인하여 지정된 태그로 분류합니다.

    - '경차' 포함 -> 초소형
    - '트럭', '픽업', '화물' 포함 -> 화물
    - 그 외 -> 승용
    """
    if "경차" in raw_segment:
        return "초소형"
    elif any(keyword in raw_segment for keyword in ["트럭", "픽업", "화물"]):
        return "화물"
    else:
        return "승용"


def calculate_avg_efficiency(raw_text):
    """'복합전비 5.4~5.6km/kWh' 또는 '복합연비 9.3~15.7km/ℓ'에서
    최소/최대값의 평균을 구하여 '5.5km/kWh', '12.5km/ℓ' 형태로 반환합니다.
    """
    if not raw_text:
        return "-"

    clean_text = raw_text.replace("복합전비", "").replace("복합연비", "").strip()

    # 1. 범위형 형태 처리
    match_range = re.search(r"([\d\.]+)\s*~\s*([\d\.]+)\s*(.+)", clean_text)
    if match_range:
        min_val = float(match_range.group(1))
        max_val = float(match_range.group(2))
        unit = match_range.group(3).strip()

        avg_val = round((min_val + max_val) / 2, 2)
        avg_str = f"{avg_val:g}"
        return f"{avg_str}{unit}"

    # 2. 단일 수치 형태 처리
    match_single = re.search(r"([\d\.]+)\s*(.+)", clean_text)
    if match_single:
        val = float(match_single.group(1))
        unit = match_single.group(2).strip()
        val_str = f"{val:g}"
        return f"{val_str}{unit}"

    return clean_text


def parse_price_to_int(price_str):
    """'1억 4,900만원', '6,888만원' 형태의 문자열을 만원 단위 정수로 변환합니다."""
    if not price_str:
        return 0

    clean = price_str.replace(",", "").replace("만원", "").strip()

    total = 0
    if "억" in clean:
        parts = clean.split("억")
        eok_part = parts[0].strip()
        man_part = parts[1].strip() if len(parts) > 1 else ""

        if eok_part.isdigit():
            total += int(eok_part) * 10000

        if man_part and man_part.isdigit():
            total += int(man_part)
    else:
        if clean.isdigit():
            total = int(clean)

    return total


# 1. 브라우저 설정 및 웹페이지 접속
options = webdriver.ChromeOptions()
# options.add_argument('--headless') # 헤드리스 모드 필요 시 주석 해제
driver = webdriver.Chrome(options=options)

url = "https://auto.danawa.com/newcar/?listSortType=1&tab=all&rangeMinPrice=&rangeMaxPrice=&searchKeyword=&listCount=30&page=1&brandList=303,307,304,321,326,312,362,349,611,486,371,491,376,367,399,587,569,459,500&segmentList=&attributeList="
driver.get(url)

car_data_list = []

try:
    # 1페이지부터 9페이지까지 순회
    for page_num in range(1, 10):
        print(f"--- {page_num} 페이지 수집 중 ---")

        if page_num > 1:
            page_btn_xpath = (
                f'//ul[@class="list__pagination"]//a[@page="{page_num}"]'
            )
            page_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, page_btn_xpath))
            )
            driver.execute_script("arguments[0].click();", page_btn)
            time.sleep(2)

        items = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, '//div[@class="detail"]')
            )
        )

        for item in items:
            try:
                # 1. 브랜드 및 차량명 추출
                name_elem = item.find_element(
                    By.XPATH, './/a[@name="modelDetailLink"]'
                )
                brand_img = name_elem.find_element(By.XPATH, "./img")

                brand = brand_img.get_attribute("alt").strip()
                full_title = name_elem.text.strip()
                car_name = full_title.replace(brand, "").strip()

                # 2. 차종 정보 추출 및 분류 (경차 -> 초소형, 트럭/픽업/화물 -> 화물, 그외 -> 승용)
                segment_elem = item.find_element(
                    By.XPATH, './/div[@class="spec "]/span[2]'
                )
                raw_segment = segment_elem.text.strip()
                car_category = classify_car_category(raw_segment)

                # 3. 연료 형태 추출 및 수소전기차 제외
                fuel_elem = item.find_element(
                    By.XPATH, './/div[@class="spec "]/span[3]'
                )
                fuel_raw = fuel_elem.text.strip()

                if "수소" in fuel_raw:
                    continue

                fuel_list = [
                    f.strip() for f in fuel_raw.split(",") if f.strip()
                ]

                # 4. 연비/전비 동적 탐색 및 '측정중' 차량 제외
                spec_spans = item.find_elements(
                    By.XPATH, './/div[@class="spec "]/span'
                )
                raw_efficiency = ""
                for span in spec_spans:
                    text = span.text.strip()
                    if "복합전비" in text or "복합연비" in text:
                        raw_efficiency = text
                        break

                if not raw_efficiency or "인증中" in raw_efficiency:
                    continue

                avg_efficiency = calculate_avg_efficiency(raw_efficiency)

                # 5. 가격 정보 추출 및 정수형 변환 (할인가/출고가 수식어 정제)
                parent_row = item.find_element(
                    By.XPATH, "./ancestor::tr | ./ancestor::li | .."
                )

                try:
                    price_box = parent_row.find_element(
                        By.XPATH, './/div[contains(@class, "box__selling")]'
                    )
                    price_text = price_box.text.strip()

                    if "할인가" in price_text:
                        price_text = price_text.split("할인가")[-1]
                    elif "출고가" in price_text:
                        price_text = price_text.split("출고가")[-1]

                    price_text = price_text.replace("~", "").strip()

                    price_formatted = re.sub(r"\s+", " ", price_text)
                    price_formatted = price_formatted.replace(
                        " 억 ", "억 "
                    ).replace(" 만원", "만원")

                    if "만원" not in price_formatted:
                        price_formatted = f"{price_formatted}만원"

                    price_int = parse_price_to_int(price_formatted)

                except Exception:
                    continue

                # 6. 각 연료 종류별 개별 행 저장
                for fuel in fuel_list:
                    if "수소" in fuel:
                        continue
                    car_data_list.append(
                        {
                            "brand": brand,
                            "car_name": car_name,
                            "car_category": car_category,
                            "fuel_type": fuel,
                            "price_str": price_formatted,
                            "price_num": price_int,
                            "avg_efficiency": avg_efficiency,
                        }
                    )

            except Exception:
                continue

        time.sleep(1)

finally:
    driver.quit()

# 7. CSV 파일 저장
csv_filename = "danawa_car_list.csv"
fieldnames = [
    "brand",
    "car_name",
    "car_category",
    "fuel_type",
    "price_str",
    "price_num",
    "avg_efficiency",
]

with open(csv_filename, mode="w", encoding="utf-8-sig", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(car_data_list)

print(
    f"수집 완료! 총 {len(car_data_list)}개의 데이터가 {csv_filename}에 저장되었습니다."
)