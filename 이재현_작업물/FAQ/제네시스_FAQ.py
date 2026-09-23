import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# 1. 드라이버 설정 및 페이지 이동
options = webdriver.ChromeOptions()
# options.add_argument('--headless') # 창을 띄우지 않고 실행할 경우 주석 해제
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

url = "https://www.genesis.com/kr/ko/support/faq.html"
driver.get(url)
driver.implicitly_wait(5)

# 데이터를 저장할 리스트
faq_data = []

try:
    # 2. 아코디언 항목 전체 탐색
    # 질문과 카테고리를 포함하는 요소를 가져옵니다.
    items = driver.find_elements(By.CLASS_NAME, "accordion-title")
    
    # 3. 반복문을 통한 크롤링 진행
    for i in range(len(items)):
        # 동적 페이지 특성상 요소를 다시 참조합니다.
        current_titles = driver.find_elements(By.CLASS_NAME, "accordion-title")
        current_labels = driver.find_elements(By.CLASS_NAME, "accordion-label")
        current_buttons = driver.find_elements(By.CLASS_NAME, "ico-accordion")
        
        # 카테고리 및 질문 텍스트 추출
        category = current_labels[i].text.strip() if i < len(current_labels) else ""
        question = current_titles[i].text.strip()
        
        # 답변을 열기 위해 버튼 클릭 (자바스크립트 클릭 사용으로 요솟에 의한 클릭 방해 예방)
        btn = current_buttons[i]
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(0.5) # 아코디언이 펼쳐질 때까지 대기
        
        # 펼쳐진 답변 요소 접근 (accordion-panel 내 accordion-panel-inner)
        panels = driver.find_elements(By.CLASS_NAME, "accordion-panel-inner")
        answer = panels[i].text.strip()
        
        # 데이터 저장
        faq_data.append({
            "카테고리": category,
            "질문": question,
            "답변": answer
        })
        
        print(f"[{i+1}] {category} | {question[:20]}... 수집 완료")

finally:
    driver.quit()

# 4. Pandas를 활용하여 데이터프레임 생성 및 CSV 저장
df = pd.DataFrame(faq_data)
df.to_csv("genesis_faq.csv", index=False, encoding="utf-8-sig")

print("\n크롤링이 완료되었으며 'genesis_faq.csv'로 저장되었습니다.")