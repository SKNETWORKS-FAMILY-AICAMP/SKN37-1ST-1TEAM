import csv
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

# 1. 저장 경로 설정 및 디렉토리 생성
save_dir = r"C:\project1"
os.makedirs(save_dir, exist_ok=True)
file_path = os.path.join(save_dir, "landrover_faq.csv")

# 2. 크롬 드라이버 실행 및 랜드로버 FAQ 페이지 접속
driver = webdriver.Chrome()
driver.maximize_window()
target_url = "https://www.landroverkorea.co.kr/ownership/contact-us/faq.html"
driver.get(target_url)

# 페이지 로딩 및 쿠키 팝업 등을 위해 넉넉히 대기
time.sleep(5)

faq_data = []
seq = 1

try:
    # 3. 언더바 2개(__)가 들어간 정확한 클래스명으로 섹션 탐색
    sections = driver.find_elements(By.CSS_SELECTOR, "details.cmp-faqmodel__accordion__section")
    print(f"[탐지된 섹션 수]: {len(sections)}개\n")

    for section in sections:
        try:
            # 카테고리(summary) 이름 추출
            header_elem = section.find_element(By.CSS_SELECTOR, "summary.cmp-faqmodel__accordion__header")
            
            # .text 대신 .get_attribute("textContent")를 사용해 숨겨진 텍스트도 강제 추출
            cat_name = header_elem.get_attribute("textContent").strip().replace("\n", " ")
            if not cat_name:
                cat_name = "기타"

            print(f"=== [{cat_name}] 카테고리 수집 시작 ===")

            # 아코디언이 접혀있다면(open 속성이 없다면) 열기
            if section.get_attribute("open") is None:
                driver.execute_script("arguments[0].click();", header_elem)
                time.sleep(0.5)  # 열리는 애니메이션 대기

            # 해당 섹션 내의 FAQ 아이템(li 태그들) 탐색
            li_items = section.find_elements(By.CSS_SELECTOR, "li.cmp-faqmodel__list__item")
            if not li_items:
                print(f"  └ [{cat_name}]에 수집할 FAQ 항목이 없습니다.")
                continue

            for li in li_items:
                try:
                    # 질문(h3) 및 답변(div) 요소 탐색
                    h3_elem = li.find_element(By.CSS_SELECTOR, "h3.cmp-faqmodel__list__title")
                    div_elem = li.find_element(By.CSS_SELECTOR, "div.cmp-faqmodel__list__content")

                    question_text = h3_elem.get_attribute("textContent").strip().replace("\n", " ")
                    answer_text = div_elem.get_attribute("textContent").strip().replace("\n", " ")

                    if question_text and answer_text:
                        faq_data.append([seq, cat_name, question_text, answer_text])
                        print(f"  [{seq}] ({cat_name}) {question_text[:35]}...")
                        seq += 1

                except Exception as e:
                    # 항목 에러 발생 시 무시하고 다음 항목으로
                    continue

        except Exception as e:
            print(f"  └ 섹션 처리 중 에러 발생: {e}")
            continue

    # 4. CSV 파일로 저장
    with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["순번", "카테고리", "질문", "답변"])
        writer.writerows(faq_data)

    print(f"\n[완료] 총 {len(faq_data)}건의 랜드로버 FAQ 데이터를 저장했습니다.")
    print(f"저장 위치: {file_path}")

finally:
    driver.quit()