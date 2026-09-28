from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    StaleElementReferenceException
)

import pandas as pd
import time
import re


# =========================================================
# 1. URL
# =========================================================

url = "https://auto.hondakorea.co.kr/support/faq?faqType=0"


# =========================================================
# 2. Chrome 실행
# =========================================================

driver = webdriver.Chrome()
driver.set_window_size(1920, 1080)

wait = WebDriverWait(driver, 15)

driver.get(url)


# =========================================================
# 3. 페이지 로딩 대기
# =========================================================

try:

    wait.until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "//*[contains(normalize-space(), '자주 묻는 질문(FAQ)')]"
            )
        )
    )

except TimeoutException:

    print("❌ 혼다 FAQ 페이지를 불러오지 못했습니다.")

    driver.quit()
    exit()


time.sleep(2)


# =========================================================
# 4. 더보기 버튼 계속 클릭
# =========================================================

print("더보기 버튼 확인 중...")


while True:

    try:

        buttons = driver.find_elements(
            By.XPATH,
            "//*[self::button or self::a][normalize-space()='더보기']"
        )


        visible_buttons = []

        for button in buttons:

            try:

                if button.is_displayed():
                    visible_buttons.append(button)

            except StaleElementReferenceException:
                continue


        if not visible_buttons:
            break


        button = visible_buttons[-1]


        driver.execute_script(
            """
            arguments[0].scrollIntoView({
                block: 'center'
            });
            """,
            button
        )

        time.sleep(0.5)


        try:

            button.click()

        except ElementClickInterceptedException:

            driver.execute_script(
                "arguments[0].click();",
                button
            )


        print("✅ 더보기 클릭")

        time.sleep(1.5)


    except StaleElementReferenceException:

        time.sleep(1)
        continue


    except Exception as e:

        print("더보기 처리 종료:", e)
        break


# =========================================================
# 5. FAQ 영역의 숨겨진 답변까지 textContent로 가져오기
#
# .text 사용 X
# textContent 사용 O
# =========================================================

body_text = driver.execute_script("""
    const body = document.body.cloneNode(true);

    // JavaScript / CSS 등 필요 없는 내용 제거
    body.querySelectorAll(
        'script, style, noscript, template, svg'
    ).forEach(el => el.remove());

    return body.textContent || '';
""")


# =========================================================
# 6. FAQ 영역만 자르기
# =========================================================

start_text = "자주 묻는 질문(FAQ)"
end_text = "고객문의 / 24시간 긴급서비스"


start_index = body_text.find(start_text)

if start_index != -1:
    body_text = body_text[start_index:]


end_index = body_text.find(end_text)

if end_index != -1:
    body_text = body_text[:end_index]


# =========================================================
# 7. 줄 단위 정리
# =========================================================

lines = []

for line in body_text.splitlines():

    line = re.sub(
        r"\s+",
        " ",
        line
    ).strip()

    if line:
        lines.append(line)


# =========================================================
# 8. 결과 저장용
# =========================================================

data = []

current_category = None
current_question = None
answer_lines = []


# =========================================================
# 9. 현재 FAQ 저장 함수
# =========================================================

def save_current_faq():

    if current_question is None:
        return


    answer = "\n".join(
        answer_lines
    ).strip()


    # 답변 끝에 필요 없는 글자가 있으면 제거
    answer = re.sub(
        r"\n?더보기$",
        "",
        answer
    ).strip()


    data.append({
        "카테고리": current_category,
        "질문": current_question,
        "답변": answer
    })


# =========================================================
# 10. 질문 / 답변 분리
# =========================================================

for line in lines:

    # -----------------------------------------------------
    # 질문 찾기
    #
    # [서비스] 서비스센터의 위치를 알고 싶습니다.
    # [부품] 부품 주문은 어떻게 하나요?
    # [App] 'My Honda App'은 무엇인가요?
    # -----------------------------------------------------

    match = re.match(
        r"^\[([^\]]+)\]\s*(.+)$",
        line
    )


    if match:

        # 이전 FAQ 저장
        save_current_faq()


        current_category = (
            match.group(1).strip()
        )


        current_question = (
            match.group(2).strip()
        )


        answer_lines = []

        continue


    # 첫 질문 전의 내용은 무시
    if current_question is None:
        continue


    # -----------------------------------------------------
    # 필요 없는 메뉴/버튼 텍스트 제거
    # -----------------------------------------------------

    ignore_lines = [
        "더보기",
        "삭제",
        "검색",
        "자주묻는 질문 TOP10",
        "구매 및 배송",
        "취소 및 환불",
        "서비스(AS)",
        "부품",
        "리콜 및 대고객특별서비스",
        "홈페이지 이용",
        "기타"
    ]


    if line in ignore_lines:
        continue


    # 답변 추가
    answer_lines.append(line)


# 마지막 FAQ 저장
save_current_faq()


# =========================================================
# 11. 브라우저 종료
# =========================================================

driver.quit()


# =========================================================
# 12. DataFrame 생성
# =========================================================

df = pd.DataFrame(
    data,
    columns=[
        "카테고리",
        "질문",
        "답변"
    ]
)


# =========================================================
# 13. 중복 제거
# =========================================================

df = df.drop_duplicates(
    subset=[
        "카테고리",
        "질문"
    ],
    keep="first"
)


df = df.reset_index(
    drop=True
)


# =========================================================
# 14. 순번 추가
# =========================================================

df.insert(
    0,
    "순번",
    range(1, len(df) + 1)
)


# =========================================================
# 15. 결과 확인
# =========================================================

print()
print("=" * 70)
print("혼다코리아 FAQ 크롤링 완료")
print("=" * 70)

print()

print(
    df.head(20).to_string(
        index=False
    )
)


print()
print("총 FAQ 개수:", len(df))


# =========================================================
# 16. 답변 없는 FAQ 확인
# =========================================================

empty_answers = df[
    df["답변"].fillna("").str.strip() == ""
]


print()

if len(empty_answers) == 0:

    print("✅ 모든 FAQ에 답변이 있습니다.")

else:

    print(
        "⚠️ 답변 없는 FAQ:",
        len(empty_answers),
        "개"
    )

    print(
        empty_answers[
            [
                "순번",
                "카테고리",
                "질문"
            ]
        ].to_string(
            index=False
        )
    )


# =========================================================
# 17. 카테고리별 개수
# =========================================================

print()
print("카테고리별 FAQ 개수")
print("-" * 40)

print(
    df["카테고리"].value_counts()
)


# =========================================================
# 18. CSV 저장
# =========================================================

df.to_csv(
    "honda_korea_faq.csv",
    index=False,
    encoding="utf-8-sig"
)


print()
print("✅ honda_korea_faq.csv 저장 완료")