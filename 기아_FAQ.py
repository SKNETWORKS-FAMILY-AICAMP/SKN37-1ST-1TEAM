import csv
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 1. 저장 경로 설정 및 디렉토리 생성
save_dir = r"C:/Users/playdata2/work/SKN/데이터수집/크롤링"
os.makedirs(save_dir, exist_ok=True)  # 지정 폴더가 없을 경우 자동 생성
file_path = os.path.join(save_dir, "kia_faq.csv")

# 2. 크롬 드라이버 실행 및 기아 FAQ 페이지 접속
driver = webdriver.Chrome()
driver.maximize_window()
target_url = "https://www.kia.com/kr/customer-service/center/faq"
driver.get(target_url)

wait = WebDriverWait(driver, 15)
time.sleep(3)  # 전체 동적 로딩 대기

faq_data = []
seq = 1

try:
    # 3. cmp-faq-search-tab 영역에서 전체 카테고리 탭 버튼 탐색
    tab_container = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, "cmp-faq-search-tab"))
    )
    
    cat_buttons = tab_container.find_elements(By.CSS_SELECTOR, "button, a, .cmp-faq-search-tab__button")
    
    # 중복 제거된 카테고리 이름 목록 추출
    cat_names = []
    for btn in cat_buttons:
        name = btn.text.strip()
        if name and name not in cat_names:
            cat_names.append(name)

    print(f"[수집 대상 카테고리 ({len(cat_names)}개)]: {cat_names}\n")

    # 4. 각 카테고리별 순회 수집
    for cat_name in cat_names:
        print(f"=== [{cat_name}] 카테고리 수집 시작 ===")
        
        # 카테고리 탭 클릭
        try:
            tab_element = driver.find_element(
                By.XPATH, 
                f"//*[contains(@class, 'cmp-faq-search-tab')]//*[contains(text(), '{cat_name}')]"
            )
            driver.execute_script("arguments[0].click();", tab_element)
            time.sleep(2)  # 탭 이동 후 accordion-specification 동적 갱신 대기
        except Exception as e:
            print(f"  └ [{cat_name}] 탭 클릭 실패: {e}")
            continue

        page_num = 1
        while True:
            # accordion-specification 영역 확인
            try:
                accordion_container = wait.until(
                    EC.presence_of_element_located((By.ID, "accordion-specification"))
                )
            except Exception:
                print(f"  └ [{cat_name}] accordion-specification 영역을 로딩하지 못했습니다.")
                break

            # 질문(.cmp-accordion__title) 요소 탐색
            titles = accordion_container.find_elements(By.CSS_SELECTOR, ".cmp-accordion__title")
            
            if not titles:
                break

            for title in titles:
                try:
                    # 질문 텍스트 추출
                    question_text = title.text.strip().replace("\n", " ")
                    if not question_text:
                        continue

                    # 질문 클릭하여 답변 펼치기
                    driver.execute_script("arguments[0].click();", title)
                    time.sleep(0.4)

                    # 답변 패널 영역 추출 (.cmp-accordion__panel 또는 인접 content)
                    try:
                        parent_item = title.find_element(By.XPATH, "./ancestor::*[contains(@class, 'cmp-accordion__item')][1]")
                        answer_elem = parent_item.find_element(By.CSS_SELECTOR, ".cmp-accordion__panel, .cmp-accordion__content")
                    except Exception:
                        answer_elem = title.find_element(By.XPATH, "./following-sibling::*[contains(@class, 'panel') or contains(@class, 'content')][1]")

                    answer_text = answer_elem.text.strip().replace("\n", " ")

                    if question_text and answer_text:
                        faq_data.append([seq, cat_name, question_text, answer_text])
                        print(f"  [{seq}] ({cat_name}) {question_text[:35]}...")
                        seq += 1

                except Exception:
                    continue

            # 카테고리 내 다음 페이지 번호 버튼 확인 및 이동
            next_page_num = page_num + 1
            try:
                next_btn = driver.find_element(
                    By.XPATH, 
                    f"//a[text()='{next_page_num}'] | //button[text()='{next_page_num}']"
                )
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(2)
                page_num += 1
            except Exception:
                # 다음 페이지 버튼이 존재하지 않으면 다음 카테고리로 이동
                break

    # 5. 지정 폴더에 CSV 파일로 저장
    with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["순번", "카테고리", "질문", "답변"])
        writer.writerows(faq_data)

    print(f"\n[완료] 모든 카테고리 총 {len(faq_data)}건의 FAQ 데이터를 저장했습니다.")
    print(f"저장 위치: {file_path}")

finally:
    driver.quit()