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
file_path = os.path.join(save_dir, "mini_faq.csv")

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
    "https://www.mini.co.kr/ko_KR/home/services-and-parts/services/why-service"
    "-with-MINI.html"
)
driver.get(target_url)

wait = WebDriverWait(driver, 15)
time.sleep(4)

# 3. 쿠키 팝업 처리 (존재할 경우 자동 수락 또는 제거)
try:
  accept_btn = wait.until(
      EC.element_to_be_clickable(
          (
              By.CSS_SELECTOR,
              "#onetrust-accept-btn-handler, button#accept-all, button.cookie-accept",
          )
      )
  )
  driver.execute_script("arguments[0].click();", accept_btn)
  print("[안내] 쿠키 동의 버튼을 클릭하여 닫았습니다.")
  time.sleep(1.5)
except:
  try:
    driver.execute_script(
        "const b = document.getElementById('onetrust-banner-sdk'); if(b)"
        " b.remove();"
    )
  except:
    pass

faq_data = []
seq = 1

try:
  # 4. 상단 네비게이션 메뉴 탭들의 링크 수집
  nav_elements = driver.find_elements(
      By.CSS_SELECTOR, "li.md-fsm-navigation__level3-item"
  )
  print(f"[탐지된 상단 네비게이션 탭 수]: {len(nav_elements)}개\n")

  tabs_info = []
  for item in nav_elements:
    try:
      a_tag = item.find_element(By.CSS_SELECTOR, "a")
      tab_name = a_tag.get_attribute("textContent").strip().replace("\n", " ")
      tab_href = a_tag.get_attribute("href")
      if tab_name and tab_href:
        tabs_info.append((tab_name, tab_href))
    except:
      continue

  # 'WHY SERVICE WITH MINI'부터 '고장 및 사고 관리' 탭까지의 구간만 필터링
  target_tabs = []
  capturing = False
  for name, href in tabs_info:
    if "WHY SERVICE WITH MINI" in name.upper():
      capturing = True
    if capturing:
      target_tabs.append((name, href))
      if any(
          kw in name
          for kw in ["고장", "사고", "모빌리티", "긴급", "ROAD", "ASSISTANCE"]
      ):
        break

  # 동적 탐색 실패 시를 대비한 주요 서비스 탭 URL 백업 리스트
  if len(target_tabs) <= 1:
    target_tabs = [
        ("WHY SERVICE WITH MINI", target_url),
        (
            "MINI SERVICE PACKAGE",
            (
                "https://www.mini.co.kr/ko_KR/home/services-and-parts/services"
                "/msi-xl-and-fix-warranty.html"
            ),
        ),
        (
            "MINI WARRANTY PLUS",
            (
                "https://www.mini.co.kr/ko_KR/home/services-and-parts/services"
                "/mini-warranty-plus.html"
            ),
        ),
        (
            "고장 및 사고 관리",
            (
                "https://www.mini.co.kr/ko_KR/home/services-and-parts/services"
                "/mini-road-assistance.html"
            ),
        ),
    ]

  print(f"--- 수집 대상 탭 목록 ({len(target_tabs)}개) ---")
  for name, href in target_tabs:
    print(f" - {name}: {href}")
  print("-" * 40)

  # 5. 각 탭 페이지를 순회하며 내용 수집
  for cat_name, href in target_tabs:
    print(f"\n=== [{cat_name}] 페이지 수집 시작 ===")
    driver.get(href)
    time.sleep(4)  # 페이지 로딩 대기

    try:
      # 페이지 내의 주요 컨텐츠 섹션(제목과 본문 구조) 탐색
      sections = driver.find_elements(
          By.CSS_SELECTOR,
          "div.md-component, div.parsys-column, div.text.parbase, section",
      )

      page_item_count = 0
      for sec in sections:
        try:
          headings = sec.find_elements(By.CSS_SELECTOR, "h2, h3, h4")
          if not headings:
            continue
          q_text = headings[0].get_attribute("textContent").strip().replace(
              "\n", " "
          )
          if not q_text or len(q_text) < 2:
            continue

          body_elems = sec.find_elements(
              By.CSS_SELECTOR,
              "p, div.md-std-txt, div.parbase p, div.content",
          )
          ans_texts = []
          for b in body_elems:
            txt = b.get_attribute("textContent").strip().replace("\n", " ")
            if txt and txt not in ans_texts and txt != q_text:
              ans_texts.append(txt)

          a_text = " ".join(ans_texts) if ans_texts else "내용 참조"

          if q_text and a_text:
            if [
                seq,
                cat_name,
                q_text,
                a_text[:500],
            ] not in faq_data and q_text != cat_name:
              faq_data.append([seq, cat_name, q_text, a_text[:1000]])
              print(f"  [{seq}] {q_text[:30]}... ({len(a_text)}자)")
              seq += 1
              page_item_count += 1
        except:
          continue

      print(f"  └ [{cat_name}]에서 총 {page_item_count}건 수집 완료")

    except Exception as e:
      print(f"  └ [{cat_name}] 페이지 처리 중 에러: {e}")
      continue

  # 6. 지정 폴더에 CSV 파일로 저장
  with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["순번", "카테고리", "질문", "답변"])
    writer.writerows(faq_data)

  print(f"\n[완료] 총 {len(faq_data)}건의 MINI 서비스 데이터를 저장했습니다.")
  print(f"저장 위치: {file_path}")

finally:
  driver.quit()