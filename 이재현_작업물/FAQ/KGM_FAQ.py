import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def get_first_question_text(driver):
  """현재 페이지의 첫 번째 질문 텍스트 반환 (페이지 전환 감지용)"""
  try:
    el = driver.find_element(
        By.XPATH, "(//span[contains(@class, 'label-sticker')]/following::p[1])[1]"
    )
    return el.text.strip()
  except:
    return ''


def crawl_kgm_faq():
  options = Options()
  options.add_argument('--start-maximized')
  options.add_argument(
      'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
  )

  driver = webdriver.Chrome(options=options)
  wait = WebDriverWait(driver, 10)

  # FAQ 페이지 URL
  url = 'https://www.kg-mobility.com/sr/online-center/faq'
  driver.get(url)
  time.sleep(2)

  faq_list = []
  total_pages = 12

  for page_num in range(1, total_pages + 1):
    print(f'[{page_num} / {total_pages}] 페이지 수집 중...')

    # 카테고리 태그 로딩 대기
    wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'span.label-sticker')
        )
    )
    time.sleep(0.5)

    category_elements = driver.find_elements(
        By.CSS_SELECTOR, 'span.label-sticker'
    )
    items_count = len(category_elements)

    for i in range(items_count):
      try:
        # DOM 재참조 (Stale Element 방지)
        cat_el = driver.find_elements(By.CSS_SELECTOR, 'span.label-sticker')[i]

        # 1. 카테고리 추출
        category = cat_el.text.strip()

        # 2. 질문 추출
        question_el = cat_el.find_element(By.XPATH, './following::p[1]')
        question = question_el.text.strip()

        # 3. 질문 클릭 (아코디언 열기)
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", question_el
        )
        time.sleep(0.2)
        driver.execute_script('arguments[0].click();', question_el)

        # 4. 동적으로 생성되는 accordion-body 렌더링 대기 후 답변 추출
        answer_el = wait.until(
            EC.visibility_of_element_located((By.CLASS_NAME, 'accordion-body'))
        )
        answer = answer_el.text.strip()

        # '페이지' 대신 누적 '순번' 저장
        faq_list.append({
            '순번': len(faq_list) + 1,
            '카테고리': category,
            '질문': question,
            '답변': answer,
        })

      except Exception as e:
        print(f'  - {i+1}번째 항목 수집 중 오류: {e}')

    # 페이지 이동 처리
    if page_num < total_pages:
      current_first_q = get_first_question_text(driver)
      next_target_page = page_num + 1

      try:
        page_btn_xpath = (
            f"//button[text()='{next_target_page}'] |"
            f" //a[text()='{next_target_page}'] |"
            f" //li[text()='{next_target_page}']"
        )
        page_btns = driver.find_elements(By.XPATH, page_btn_xpath)

        if page_btns and page_btns[0].is_displayed():
          target_btn = page_btns[0]
        else:
          target_btn = wait.until(
              EC.element_to_be_clickable(
                  (By.XPATH, "//button[contains(text(), '다음 페이지')]")
              )
          )

        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", target_btn
        )
        time.sleep(0.3)
        driver.execute_script('arguments[0].click();', target_btn)

        # 비동기 페이지 전환 대기
        wait.until(lambda d: get_first_question_text(d) != current_first_q)
        time.sleep(0.8)

      except Exception as e:
        print(f'{next_target_page}페이지 이동 실패: {e}')
        break

  driver.quit()

  # DataFrame 생성 및 CSV 저장
  df = pd.DataFrame(faq_list)
  output_filename = 'kgm_faq_data.csv'
  df.to_csv(output_filename, index=False, encoding='utf-8-sig')
  print(
      f'\n크롤링 완료! 총 {len(df)}건의 FAQ 데이터가 "{output_filename}" 파일로'
      ' 저장되었습니다.'
  )


if __name__ == '__main__':
  crawl_kgm_faq()