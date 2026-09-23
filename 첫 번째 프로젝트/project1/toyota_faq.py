import csv
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 1. 저장 경로 설정 및 디렉토리 생성 (C:\project1 경로 반영)
save_dir = r"C:\project1"
os.makedirs(save_dir, exist_ok=True)  # 지정 폴더가 없을 경우 자동 생성
file_path = os.path.join(save_dir, "toyota_faq.csv")

# 2. 크롬 드라이버 실행 및 토요타 FAQ 페이지 접속
driver = webdriver.Chrome()
driver.maximize_window()
target_url = "https://global.toyota/en/faq/"
driver.get(target_url)

wait = WebDriverWait(driver, 15)
time.sleep(3)  # 전체 동적 로딩 대기

faq_data = []
seq = 1

try:
    # 3. 페이지 내의 각 섹션(카테고리) 영역 탐색
    sections = driver.find_elements(By.CSS_SELECTOR, ".contents_body .section")
    
    print(f"[탐지된 섹션 수]: {len(sections)}개\n")

    for section in sections:
        try:
            # 카테고리 이름(h2 태그) 추출
            h2_elems = section.find_elements(By.TAG_NAME, "h2")
            if not h2_elems:
                continue
            cat_name = h2_elems[0].text.strip()
            if not cat_name:
                continue
            
            print(f"=== [{cat_name}] 카테고리 수집 시작 ===")
            
            # 해당 섹션 내의 FAQ 아이템(dl 태그들) 탐색
            dl_items = section.find_elements(By.CSS_SELECTOR, ".acbox dl")
            if not dl_items:
                print(f"  └ [{cat_name}]에 수집할 FAQ 항목이 없습니다.")
                continue

            for dl in dl_items:
                try:
                    # 질문(dt) 요소 탐색
                    dt_elem = dl.find_element(By.CSS_SELECTOR, "dt.acbox_label")
                    question_text = dt_elem.text.strip().replace("\n", " ")
                    if not question_text:
                        continue

                    # 질문 클릭하여 답변 펼치기
                    driver.execute_script("arguments[0].click();", dt_elem)
                    time.sleep(0.4)  # 답변 펼쳐짐 대기

                    # 답변(dd) 요소 탐색
                    dd_elem = dl.find_element(By.CSS_SELECTOR, "dd.acbox_body")
                    answer_text = dd_elem.text.strip().replace("\n", " ")

                    if question_text and answer_text:
                        faq_data.append([seq, cat_name, question_text, answer_text])
                        print(f"  [{seq}] ({cat_name}) {question_text[:35]}...")
                        seq += 1

                except Exception as e:
                    continue

        except Exception as e:
            print(f"  └ 섹션 처리 중 에러 발생: {e}")
            continue

    # 4. 지정 폴더에 CSV 파일로 저장
    with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["순번", "카테고리", "질문", "답변"])
        writer.writerows(faq_data)

    print(f"\n[완료] 총 {len(faq_data)}건의 토요타 FAQ 데이터를 저장했습니다.")
    print(f"저장 위치: {file_path}")

finally:
    driver.quit()