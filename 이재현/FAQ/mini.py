import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# 1. 드라이버 설정
options = webdriver.ChromeOptions()
# options.add_argument('--headless') # 필요 시 주석 해제

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

url = "https://www.mini.co.kr/ko_KR/home/services/my-mini-apps/faq.html"
driver.get(url)
time.sleep(4)

# 2. 방해 요소(쿠키/오버레이 배너) 강제 제거
driver.execute_script("""
    var overlays = document.querySelectorAll('[id*="cookie"], [class*="cookie"], [class*="overlay"], [class*="banner"]');
    overlays.forEach(el => el.remove());
""")

# 3. 아코디언 아이템 탐색
accordion_items = driver.find_elements(By.CSS_SELECTOR, '.md-accordion-item')
print(f"감지된 FAQ 항목 개수: {len(accordion_items)}개")

faq_data = []

# 4. 순차적 스크롤 -> 클릭 -> 텍스트 추출 (textContent 방식 적용)
for index, item in enumerate(accordion_items, start=1):
    try:
        # 화면 중앙으로 스크롤 이동 (동적 렌더링 활성화)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", item)
        time.sleep(0.2)

        # 질문 추출
        q_elements = item.find_elements(By.CSS_SELECTOR, 'span.md-heading')
        if not q_elements:
            continue
        
        question_text = q_elements[0].get_attribute('textContent').strip()
        if not question_text:
            continue

        # 아코디언 펼치기
        headers = item.find_elements(By.CSS_SELECTOR, '.md-accordion-item__header')
        if headers:
            driver.execute_script("arguments[0].click();", headers[0])
            time.sleep(0.3)  # 펼쳐짐 애니메이션 대기

        # 직전 카테고리(h2) 매핑
        try:
            prev_h2 = item.find_element(By.XPATH, "./preceding::h2[@data-component-name='heading-item'][1]")
            raw_category = prev_h2.get_attribute('textContent').strip()
        except Exception:
            raw_category = "기타"

        # 카테고리 번호 제거 ("1. 가입 / 탈퇴" -> "가입 / 탈퇴")
        clean_category = re.sub(r'^\d+\.\s*', '', raw_category)

        # 답변(p 태그) 추출 - textContent 활용으로 hidden 상태 누락 방지
        p_elements = item.find_elements(By.TAG_NAME, 'p')
        answer_lines = []
        for p in p_elements:
            txt = p.get_attribute('textContent').strip()
            if txt:
                answer_lines.append(txt)
        
        answer_text = "\n".join(answer_lines)

        # p 태그로 수집되지 않을 경우 백업 처리
        if not answer_text:
            full_text = item.get_attribute('textContent').strip()
            answer_text = full_text.replace(question_text, "").strip()

        faq_data.append({
            "순번": index,
            "카테고리": clean_category,
            "질문": question_text,
            "답변": answer_text
        })

    except Exception as e:
        print(f"{index}번째 항목 수집 도중 예외 발생: {e}")
        continue

driver.quit()

# 5. DataFrame 생성 및 CSV 저장
df = pd.DataFrame(faq_data)

# 중복 제거 및 순번 정리
df.drop_duplicates(subset=['카테고리', '질문'], keep='first', inplace=True)
df['순번'] = range(1, len(df) + 1)

df.to_csv("mini_faq.csv", index=False, encoding="utf-8-sig")
print(f"수집 완료! 총 {len(df)}건의 질문 및 답변 데이터가 'mini_faq.csv'로 저장되었습니다.")