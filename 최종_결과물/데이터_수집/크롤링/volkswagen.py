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

url = "https://www.volkswagen.co.kr/ko/owners-and-services/Need-help/faq.html"


# =========================================================
# 2. Chrome 실행
# =========================================================

driver = webdriver.Chrome()
wait = WebDriverWait(driver, 15)

driver.get(url)


# =========================================================
# 3. FAQ 페이지 로딩 대기
# =========================================================

try:

    wait.until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "//h2[contains(normalize-space(), '자주 묻는 질문')]"
            )
        )
    )

except TimeoutException:

    print("❌ 폭스바겐 FAQ 페이지를 불러오지 못했습니다.")

    driver.quit()
    exit()


time.sleep(2)


# =========================================================
# 4. Show More 버튼 클릭
# =========================================================

while True:

    try:

        show_more_buttons = driver.find_elements(
            By.XPATH,
            "//button[contains(., 'Show More')]"
            " | "
            "//*[contains(@role, 'button') and contains(., 'Show More')]"
        )

        # 화면에 보이는 버튼만
        show_more_buttons = [
            btn for btn in show_more_buttons
            if btn.is_displayed()
        ]

        if not show_more_buttons:
            break

        button = show_more_buttons[0]

        # 버튼 위치로 이동
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});",
            button
        )

        time.sleep(1)

        try:

            button.click()

        except ElementClickInterceptedException:

            driver.execute_script(
                "arguments[0].click();",
                button
            )

        print("Show More 클릭")

        time.sleep(2)

    except (
        StaleElementReferenceException,
        TimeoutException
    ):

        time.sleep(1)
        continue

    except Exception:

        break


# =========================================================
# 5. FAQ 질문 가져오기
#
# 자주 묻는 질문 h2 이후
# Next steps h2 이전에 있는 h3만 가져오기
# =========================================================

questions = driver.execute_script("""
    const headings = Array.from(
        document.querySelectorAll("h2")
    );

    const faqTitle = headings.find(el =>
        el.textContent.trim().includes("자주 묻는 질문")
    );

    if (!faqTitle) {
        return [];
    }


    const nextSteps = headings.find(el =>
        el.textContent.trim() === "Next steps" &&
        faqTitle.compareDocumentPosition(el)
        & Node.DOCUMENT_POSITION_FOLLOWING
    );


    const allH3 = Array.from(
        document.querySelectorAll("h3")
    );


    return allH3.filter(el => {

        const afterFaq =
            faqTitle.compareDocumentPosition(el)
            & Node.DOCUMENT_POSITION_FOLLOWING;

        if (!afterFaq) {
            return false;
        }


        if (nextSteps) {

            const beforeNextSteps =
                el.compareDocumentPosition(nextSteps)
                & Node.DOCUMENT_POSITION_FOLLOWING;

            if (!beforeNextSteps) {
                return false;
            }

        }


        return true;

    });
""")


print()
print("FAQ 질문 후보 개수:", len(questions))


# =========================================================
# 6. 결과 저장
# =========================================================

data = []


# =========================================================
# 7. 질문 / 답변 가져오기
# =========================================================

for index, q in enumerate(questions):

    question = q.text.strip()

    if not question:
        continue


    # -----------------------------------------------------
    # 다음 FAQ 질문
    # -----------------------------------------------------

    next_question = None

    if index + 1 < len(questions):
        next_question = questions[index + 1]


    # =====================================================
    # 현재 h3 이후부터 다음 h3 전까지 답변 추출
    # =====================================================

    answer = driver.execute_script("""
        const current = arguments[0];
        const nextQuestion = arguments[1];


        const range = document.createRange();

        range.setStartAfter(current);


        if (nextQuestion) {

            range.setEndBefore(nextQuestion);

        }

        else {

            // 마지막 FAQ인 경우 Next steps 전까지만
            const nextSteps = Array.from(
                document.querySelectorAll("h2")
            ).find(el =>
                el.textContent.trim() === "Next steps" &&
                current.compareDocumentPosition(el)
                & Node.DOCUMENT_POSITION_FOLLOWING
            );


            if (nextSteps) {

                range.setEndBefore(nextSteps);

            }

            else {

                const footer =
                    document.querySelector("footer");

                if (footer) {

                    range.setEndBefore(footer);

                }

                else {

                    range.setEnd(
                        document.body,
                        document.body.childNodes.length
                    );

                }

            }

        }


        const fragment =
            range.cloneContents();


        const container =
            document.createElement("div");


        container.appendChild(fragment);


        // 필요 없는 요소 제거
        container.querySelectorAll(
            "script, style, noscript, template, svg, button"
        ).forEach(el => el.remove());


        return container.innerText ||
               container.textContent ||
               "";

    """, q, next_question)


    # =====================================================
    # 8. 답변 정리
    # =====================================================

    answer_lines = []

    for line in answer.splitlines():

        line = re.sub(
            r"\s+",
            " ",
            line
        ).strip()

        if not line:
            continue


        # Show More 같은 텍스트가 섞이면 제거
        if line.startswith("Show More"):
            continue


        answer_lines.append(line)


    # 중복 줄 제거
    cleaned_lines = []

    for line in answer_lines:

        if line not in cleaned_lines:
            cleaned_lines.append(line)


    answer = "\n".join(cleaned_lines).strip()


    # =====================================================
    # 9. 답변 없는 항목 제외
    # =====================================================

    if not answer:

        print(
            f"⚠️ 답변 없음: {question}"
        )

        continue


    # =====================================================
    # 10. 저장
    # =====================================================

    data.append({

        "카테고리": "폭스바겐 FAQ",

        "질문": question,

        "답변": answer

    })


    print(
        f"{len(data)}. {question}"
    )


# =========================================================
# 11. Chrome 종료
# =========================================================

driver.quit()


# =========================================================
# 12. DataFrame
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
# 13. 결과 확인
# =========================================================

print()
print("=" * 60)
print("폭스바겐 FAQ 크롤링 완료")
print("=" * 60)

print()

print(
    df.head(10).to_string(
        index=False
    )
)

print()
print("총 FAQ 개수:", len(df))


# =========================================================
# 14. CSV 저장
# =========================================================

df.to_csv(
    "C:/Users/playdata2/SKN_1ST_Project/최종_결과물/사용_데이터/크롤링/volkswagen_faq.csv",
    index=False,
    encoding="utf-8-sig"
)


print()
print("✅ volkswagen_faq.csv 저장 완료")