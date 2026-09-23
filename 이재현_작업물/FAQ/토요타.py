import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 웹드라이버 설정
options = webdriver.ChromeOptions()
# options.add_argument('--headless') # 창 없이 실행하려면 주석 해제
driver = webdriver.Chrome(options=options)

url = "https://www.toyota.co.kr/toyota-connect/guide/faq/"  # 해당 FAQ URL
driver.get(url)
wait = WebDriverWait(driver, 10)
actions = ActionChains(driver)

faq_data = []
total_pages = 7
item_number = 1  # 1번째 컬럼으로 사용할 순번 변수

try:
    for page in range(1, total_pages + 1):
        print(f"--- {page} 페이지 수집 중 ---")
        time.sleep(2)  # 페이지 및 동적 요소 로딩 대기

        # 1. 질문 요소들 찾기
        questions = driver.find_elements(By.CLASS_NAME, "eqq8jq65")
        
        # 2. 답변 버튼 찾기 (부모 클릭 가능 요소)
        buttons = driver.find_elements(By.XPATH, "//*[contains(@class, 'ecosthy0')]/ancestor::button | //*[contains(@class, 'ecosthy0')]/..")
        
        for idx in range(len(questions)):
            question_text = questions[idx].text.strip()
            
            # 첫 번째 페이지의 첫 번째 질문은 이미 열려 있는 상태 처리
            if not (page == 1 and idx == 0):
                try:
                    btn = buttons[idx]
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(0.3)
                    actions.move_to_element(btn).click().perform()
                    time.sleep(0.5)
                except Exception:
                    try:
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.5)
                    except Exception as e:
                        print(f"{item_number}번 질문 답변 버튼 클릭 실패:", e)

            # 3. 답변 가져오기
            try:
                answers = driver.find_elements(By.CLASS_NAME, "eqq8jq62")
                answer_text = answers[idx].text.strip()
            except Exception:
                answer_text = ""

            # 1번째 컬럼을 페이지가 아닌 순번(item_number)으로 저장
            faq_data.append({
                "순번": item_number,
                "질문": question_text,
                "답변": answer_text
            })
            item_number += 1  # 순번 1씩 증가

        # 4. 다음 페이지 이동 (페이지네이션 컨트롤 보완)
        if page < total_pages:
            next_page_num = page + 1
            moved = False

            # [방법 1] 다음 페이지 번호버튼(예: 6)을 직접 찾아서 클릭
            try:
                page_btn = driver.find_element(By.XPATH, f"//a[text()='{next_page_num}'] | //button[text()='{next_page_num}'] | //*[text()='{next_page_num}']")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", page_btn)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", page_btn)
                moved = True
                print(f"{next_page_num}페이지 번호 직접 클릭 성공")
            except Exception:
                pass

            # [방법 2] 페이지 번호 직접 클릭 실패 시 (5페이지 이후 번호 범위 전환 시) '다음(>)' 화살표 클릭
            if not moved:
                try:
                    next_arrow = driver.find_element(
                        By.XPATH, 
                        "//*[local-name()='path' and contains(@d, 'M6.38942')]/ancestor::a | "
                        "//*[local-name()='path' and contains(@d, 'M6.38942')]/ancestor::button | "
                        "//a[contains(@class, 'next')] | //button[contains(@class, 'next')]"
                    )
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_arrow)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", next_arrow)
                    moved = True
                    print("다음 화살표(>) 클릭 성공")
                except Exception as e:
                    print(f"{next_page_num}페이지 이동 실패:", e)
                    break

finally:
    driver.quit()

# CSV 파일 저장
df = pd.DataFrame(faq_data)
df.to_csv("toyota_faq_result.csv", index=False, encoding="utf-8-sig")
print("크롤링 완료 및 toyota_faq_result.csv 저장 완료!")