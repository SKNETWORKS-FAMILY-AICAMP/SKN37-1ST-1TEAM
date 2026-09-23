import csv
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# 1. 저장 경로 설정 및 디렉토리 생성 (C:\project1 경로 반영)
save_dir = r"C:\project1"
os.makedirs(save_dir, exist_ok=True)
file_path = os.path.join(save_dir, "jeep_faq.csv")

# 2. 크롬 드라이버 설정 (봇 탐지 우회 옵션 적용)
options = webdriver.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

driver = webdriver.Chrome(options=options)
driver.maximize_window()
target_url = "https://www.jeep.com/za/after-sales/faq.html"
driver.get(target_url)

wait = WebDriverWait(driver, 15)
time.sleep(3)  # 초기 페이지 로딩 대기

# 3. 'Accept All Cookies' 버튼 클릭하여 쿠키 창 닫기 (스크린샷 ID 반영)
try:
  accept_btn = wait.until(
      EC.element_to_be_clickable((By.CSS_SELECTOR, "#onetrust-accept-btn-handler"))
  )
  driver.execute_script("arguments[0].click();", accept_btn)
  print("[안내] 'Accept All Cookies' 버튼을 클릭하여 쿠키 창을 닫았습니다.")
  time.sleep(2)  # 팝업이 완전히 사라질 때까지 대기
except Exception as e:
  print(f"[안내] 버튼 클릭 중 예외 발생, 백업 조치 실행: {e}")
  try:
    # 예외 발생 시 쿠키 배너 요소 자체를 DOM에서 강제 삭제
    driver.execute_script(
        "document.getElementById('onetrust-banner-sdk').remove();"
    )
    print("[안내] 쿠키 배너를 강제로 제거했습니다.")
    time.sleep(1)
  except:
    pass

faq_data = []
seq = 1

try:
  # 4. 페이지 내의 각 카테고리 섹션 영역 탐색
  sections = driver.find_elements(
      By.CSS_SELECTOR, "div.copy-box-wrapper-standard, div.copy-block"
  )
  print(f"[탐지된 섹션 수]: {len(sections)}개\n")

  for section in sections:
    try:
      # 카테고리 이름(h4.box-title) 추출
      h4_elems = section.find_elements(By.CSS_SELECTOR, "h4.box-title")
      if not h4_elems:
        continue
      cat_name = (
          h4_elems[0].get_attribute("textContent").strip().replace("\n", " ")
      )
      if not cat_name:
        continue

      print(f"=== [{cat_name}] 카테고리 수집 시작 ===")

      # 해당 섹션 내의 FAQ 아코디언 버튼(a 태그) 탐색
      expando_links = section.find_elements(
          By.CSS_SELECTOR, "a[data-lpos='expando-group']"
      )
      print(f"  - 발견된 FAQ 항목 수: {len(expando_links)}개")

      for link in expando_links:
        try:
          # 요소를 화면 중앙으로 스크롤 이동
          driver.execute_script(
              "arguments[0].scrollIntoView({block: 'center'});", link
          )
          time.sleep(0.4)

          # 질문(label) 텍스트 추출
          label_elem = link.find_element(
              By.CSS_SELECTOR, "label.expando-heading-title"
          )
          question_text = (
              label_elem.get_attribute("textContent").strip().replace("\n", " ")
          )
          if not question_text:
            continue

          # 아코디언 박스가 닫혀있는 경우 클릭하여 열기
          aria_expanded = link.get_attribute("aria-expanded")
          if aria_expanded != "true":
            driver.execute_script("arguments[0].click();", link)
            time.sleep(0.8)  # 펼쳐지는 애니메이션 대기

          # 부모 컨테이너를 통해 열린 답변(div.expando-content) 영역 탐색
          parent_row = link.find_element(
              By.XPATH,
              "./ancestor::div[contains(@class, 'expando-row') or"
              " contains(@class, 'copy-block') or contains(@class,"
              " 'sdp-row')]",
          )
          content_elem = parent_row.find_element(
              By.CSS_SELECTOR, "div.expando-content"
          )
          answer_text = (
              content_elem.get_attribute("textContent").strip().replace("\n", " ")
          )

          if question_text and answer_text:
            faq_data.append([seq, cat_name, question_text, answer_text])
            print(f"  [{seq}] ({cat_name}) {question_text[:35]}...")
            seq += 1

        except Exception:
          continue

    except Exception as e:
      print(f"  └ 섹션 처리 중 에러 발생: {e}")
      continue

  # 5. 지정 폴더에 CSV 파일로 저장
  with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["순번", "카테고리", "질문", "답변"])
    writer.writerows(faq_data)

  print(f"\n[완료] 총 {len(faq_data)}건의 지프 FAQ 데이터를 저장했습니다.")
  print(f"저장 위치: {file_path}")

finally:
  driver.quit()