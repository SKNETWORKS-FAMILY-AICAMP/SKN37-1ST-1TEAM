import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 1. 저장 경로 설정 및 폴더 생성
save_dir = r"C:\Users\playdata2\work\SKN\데이터수집\크롤링"
os.makedirs(save_dir, exist_ok=True)
csv_filepath = os.path.join(save_dir, "hyundai_faq_result.csv")

# 2. 웹드라이버 실행
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 10)

faq_data = []
seq = 1  # 전체 누적 순번 counter

def change_select_jQuery(driver_obj, select_selector, index):
    """jQuery가 탑재된 사이트에서 셀렉트박스 값을 변경하고 change 이벤트를 확실히 발생시키는 함수"""
    script = """
        var idx = arguments[0];
        var selector = arguments[1];
        var $select = $(selector);
        if ($select.length > 0) {
            $select.prop('selectedIndex', idx);
            $select.trigger('change');
            if ($.fn.selectBox) {
                try { $select.selectBox('refresh'); } catch(e) {}
            }
            return true;
        }
        return false;
    """
    driver_obj.execute_script(script, index, select_selector)
    time.sleep(1)

try:
    url = "https://www.hyundai.com/kr/ko/faq.html"
    driver.get(url)
    time.sleep(3)  # 초기 페이지 로딩 대기

    # 대분류 select 요소 탐색
    depth1_elem = wait.until(EC.presence_of_element_located((By.NAME, "category_depth1")))
    depth1_select = Select(depth1_elem)
    depth1_options = [option.text.strip() for option in depth1_select.options]

    for d1_idx, d1_text in enumerate(depth1_options):
        # 기본 안내 문구 옵션 제외
        if d1_idx == 0 or not d1_text or d1_text in ["(대분류)", "대분류", "카테고리 선택"]:
            continue

        # jQuery로 대분류 선택 및 이벤트 실행
        change_select_jQuery(driver, "select[name='category_depth1']", d1_idx)

        # 소분류 select 옵션 탐색
        try:
            depth2_elem = driver.find_element(By.NAME, "category_depth2")
            depth2_select = Select(depth2_elem)
            depth2_options = [option.text.strip() for option in depth2_select.options]
        except Exception:
            depth2_options = []

        # 유효한 소분류 인덱스 추출
        valid_d2_indices = [
            idx for idx, text in enumerate(depth2_options)
            if idx != 0 and text not in ["(소분류)", "소분류", "하위 카테고리 선택"]
        ]

        if not valid_d2_indices:
            loop_targets = [(0, "-")]
        else:
            loop_targets = [(idx, depth2_options[idx]) for idx in valid_d2_indices]

        for d2_idx, d2_text in loop_targets:
            # 대분류 및 소분류 선택
            change_select_jQuery(driver, "select[name='category_depth1']", d1_idx)
            if d2_text != "-":
                change_select_jQuery(driver, "select[name='category_depth2']", d2_idx)

            # [확인] 버튼 클릭
            try:
                driver.execute_script("""
                    var btns = $('button, a').filter(function() {
                        return $(this).text().trim() === '확인';
                    });
                    if (btns.length > 0) {
                        btns[0].click();
                    }
                """)
            except Exception:
                pass

            time.sleep(2)  # 조회 결과 로딩 대기

            page_num = 1
            prev_first_q = ""  # 중복 수집 방지용 변수

            while True:
                # 질문을 담고 있는 목록 요소(li 또는 dl)를 먼저 수집
                item_elements = driver.find_elements(By.CSS_SELECTOR, "ul.faq_list > li, div.faq_list > div, dl.faq_list > dt")
                
                # 위 셀렉터로 안 잡힐 경우 개별 brief 탐색
                if not item_elements:
                    question_elements = driver.find_elements(By.CSS_SELECTOR, "span.brief")
                else:
                    question_elements = [item.find_element(By.CSS_SELECTOR, "span.brief") for item in item_elements if item.find_elements(By.CSS_SELECTOR, "span.brief")]

                # 데이터가 없으면 탈출
                if not question_elements:
                    print(f"[{d1_text} > {d2_text}] 질문 데이터가 없습니다.")
                    break

                # 동일한 첫 질문이 연속으로 나올 경우 무한루프 방지
                current_first_q = question_elements[0].text.strip()
                if current_first_q == prev_first_q and page_num > 1:
                    break
                prev_first_q = current_first_q

                page_collected_count = 0

                for i in range(len(question_elements)):
                    try:
                        # DOM 변화를 대비해 요소를 매번 재탐색
                        q_elems = driver.find_elements(By.CSS_SELECTOR, "span.brief")
                        if i >= len(q_elems):
                            break

                        q_elem = q_elems[i]
                        question_text = q_elem.text.strip()

                        # 1. 화면 스크롤 이동
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", q_elem)
                        time.sleep(0.2)

                        # 2. 질문 클릭 (아코디언 열기)
                        driver.execute_script("arguments[0].click();", q_elem)

                        # 3. 답변 항목이 보일 때까지 대기
                        parent = q_elem.find_element(By.XPATH, "./ancestor::li | ./ancestor::dl | ./ancestor::div[contains(@class,'item')]")
                        
                        # div.exp 또는 .answer 등 답변 컨테이너 추출
                        answer_text = ""
                        try:
                            # 1.5초 동안 답변 영역에 텍스트가 채워지거나 노출되기를 대기
                            WebDriverWait(parent, 2).until(
                                lambda p: p.find_element(By.CSS_SELECTOR, "div.exp").is_displayed()
                            )
                            answer_elem = parent.find_element(By.CSS_SELECTOR, "div.exp")
                            answer_text = answer_elem.text.strip()
                        except Exception:
                            # 만약 is_displayed() 체크가 안 될 경우 text 바로 추출 시도
                            try:
                                answer_elem = parent.find_element(By.CSS_SELECTOR, "div.exp")
                                answer_text = answer_elem.text.strip()
                            except Exception:
                                answer_text = ""

                        faq_data.append({
                            "순번": seq,
                            "대분류": d1_text,
                            "소분류": d2_text,
                            "질문": question_text,
                            "답변": answer_text
                        })
                        seq += 1
                        page_collected_count += 1

                    except Exception as e:
                        print(f"[{d1_text} > {d2_text}] {i+1}번째 질문 수집 중 오류: {e}")
                        continue

                print(f"[{d1_text} > {d2_text}] {page_num}번째 페이지 {page_collected_count}건 수집완료! (전체 누적: {seq - 1}건)")

                # [다음 페이지] 버튼 처리
                try:
                    next_btn = driver.find_element(By.CSS_SELECTOR, "button.navi.next, a.next")

                    is_disabled = (
                        next_btn.get_attribute("disabled") is not None or
                        "disabled" in (next_btn.get_attribute("class") or "") or
                        not next_btn.is_enabled()
                    )

                    if is_disabled:
                        break

                    driver.execute_script("arguments[0].click();", next_btn)
                    time.sleep(2)  # 페이지 이동 후 로딩 대기

                    page_num += 1

                except Exception:
                    break

finally:
    driver.quit()

# 3. 데이터프레임 생성 및 CSV 저장 (UTF-8-SIG 권장: 엑셀 한글 깨짐 방지)
df = pd.DataFrame(faq_data)
df.to_csv(csv_filepath, index=False, encoding="utf-8-sig")

print("\n==================================================")
print(f"전체 크롤링 완료! 총 {len(df)}건 저장됨")
print(f"파일 저장 위치: {csv_filepath}")
print("==================================================")