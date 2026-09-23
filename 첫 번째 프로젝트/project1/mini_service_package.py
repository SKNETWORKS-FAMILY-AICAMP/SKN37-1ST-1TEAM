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
file_path = os.path.join(save_dir, "mini_service_package.csv")

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
target_url = (
    "https://www.mini.co.kr/ko_KR/home/services-and-parts/services/msi-xl-and-fix-warranty.html"
)
driver.get(target_url)

wait = WebDriverWait(driver, 15)
time.sleep(4)  # 초기 페이지 로딩 대기

# 3. 쿠키 동의 팝업 처리 (Accept All Cookies 클릭 또는 배너 제거)
try:
  accept_btn = wait.until(
      EC.element_to_be_clickable((By.CSS_SELECTOR, "#onetrust-accept-btn-handler"))
  )
  driver.execute_script("arguments[0].click();", accept_btn)
  print("[안내] 쿠키 동의 버튼을 클릭하여 창을 닫았습니다.")
  time.sleep(1.5)
except Exception:
  try:
    driver.execute_script(
        "document.getElementById('onetrust-banner-sdk').remove();"
    )
    print("[안내] 쿠키 배너 요소를 강제로 제거했습니다.")
  except:
    pass

# 4. 페이지 맨 밑까지 부드럽게 스크롤을 내려 모든 동적 콘텐츠 로딩 유도
print("[안내] 페이지 맨 아래까지 스크롤을 진행하여 전체 데이터를 로드합니다...")
last_height = driver.execute_script("return document.body.scrollHeight")

while True:
  # 화면 하단으로 스크롤 이동
  driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
  time.sleep(2.5)  # 로딩 대기 시간

  new_height = driver.execute_script("return document.body.scrollHeight")
  if new_height == last_height:
    print("[안내] 페이지 최하단 도달 완료.")
    break
  last_height = new_height

# 스크롤 완료 후 데이터 추출을 위해 다시 상단으로 이동 후 안정화
driver.execute_script("window.scrollTo(0, 0);")
time.sleep(1.5)

extracted_data = []
seq = 1
category_name = "MINI SERVICE PACKAGE"

try:
  # 페이지 메인 제목 추출 시도
  try:
    h2_elem = driver.find_element(
        By.CSS_SELECTOR, "h2.md-heading-h2, div.heading h2"
    )
    if h2_elem:
      category_name = h2_elem.get_attribute("textContent").strip()
  except:
    pass

  print(f"=== [{category_name}] 전체 정보 수집 시작 ===")

  # 5. 페이지 전체에 있는 모든 컨텐츠 블록 및 섹션 탐색
  sections = driver.find_elements(
      By.CSS_SELECTOR,
      "div.parsys-column, div.md-component, div.text.parbase, div.genericlist,"
      " section",
  )
  print(f"[탐지된 전체 섹션 수]: {len(sections)}개\n")

  for sec in sections:
    try:
      # 소제목(h2, h3, h5) 영역 탐색
      headings = sec.find_elements(By.CSS_SELECTOR, "h2, h3, h5")
      title_text = ""
      if headings:
        title_text = (
            headings[0].get_attribute("textContent").strip().replace("\n", " ")
        )

      content_parts = []

      # 본문 단락(p, md-std-txt) 탐색
      p_elems = sec.find_elements(
          By.CSS_SELECTOR, "p, div.md-std-txt, div.parbase p"
      )
      for p in p_elems:
        ptxt = p.get_attribute("textContent").strip().replace("\n", " ")
        if ptxt and ptxt not in content_parts and ptxt != title_text:
          content_parts.append(ptxt)

      # 소모품 체크리스트 항목 탐색 (에어필터, 마이크로필터 등)
      li_elems = sec.find_elements(
          By.CSS_SELECTOR, "ul.md-gen-list li.md-gen-item, div.genericlist li"
      )
      for li in li_elems:
        litxt = li.get_attribute("textContent").strip().replace("\n", " ")
        if litxt and litxt not in content_parts:
          content_parts.append("✓ " + litxt)

      body_text = " ".join(content_parts) if content_parts else ""

      if title_text and body_text:
        is_duplicate = any(item[2] == title_text for item in extracted_data)
        if not is_duplicate and title_text != category_name:
          extracted_data.append([seq, category_name, title_text, body_text])
          print(f"  [{seq}] {title_text[:30]}... (내용 길이: {len(body_text)}자)")
          seq += 1

    except Exception:
      continue

  # 6. 혹시 누락된 체크리스트나 하단 부가 정보가 있을 경우 대비한 보완 수집
  try:
    generic_lists = driver.find_elements(By.CSS_SELECTOR, "div.genericlist")
    for gl in generic_lists:
      items = gl.find_elements(By.CSS_SELECTOR, "li.md-gen-item")
      if items:
        check_items = [
            "✓ " + li.get_attribute("textContent").strip().replace("\n", " ")
            for li in items
        ]
        check_text = " ".join(check_items)

        if not any(check_text in item[3] for item in extracted_data):
          extracted_data.append(
              [seq, category_name, "서비스 내용 (주요 소모품 교환 항목)", check_text]
          )
          print(
              f"  [{seq}] 서비스 내용 (주요 소모품 교환 항목) [추가 체크리스트"
              " 병합]"
          )
          seq += 1
  except:
    pass

  # 7. 지정 폴더에 CSV 파일로 저장
  with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["순번", "카테고리", "제목", "내용"])
    writer.writerows(extracted_data)

  print(
      f"\n[완료] 총 {len(extracted_data)}건의 MINI 서비스 패키지 전체 데이터를"
      " 저장했습니다."
  )
  print(f"저장 위치: {file_path}")

finally:
  driver.quit()