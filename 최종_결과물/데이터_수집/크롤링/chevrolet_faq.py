from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

import pandas as pd
import time
import re


# =========================================================
# 1. Chrome 실행
# =========================================================

driver = webdriver.Chrome()

wait = WebDriverWait(driver, 10)


# =========================================================
# 2. 쉐보레 FAQ 카테고리
# =========================================================

categories = {

    "구매 관련":
        "https://www.chevrolet.co.kr/faq/purchasing-related",

    "차량 관리":
        "https://www.chevrolet.co.kr/faq/product-maintenance",

    "오토카드":
        "https://www.chevrolet.co.kr/faq/autocard",

    "통합계정 및 홈페이지 이용":
        "https://www.chevrolet.co.kr/faq/website",

    "장애인 차량":
        "https://www.chevrolet.co.kr/faq/disabled-vehicles",

    "마이링크":
        "https://www.chevrolet.co.kr/faq/mylink",

    "내비 업데이트":
        "https://www.chevrolet.co.kr/faq/navigation",

    "Android Auto / Apple CarPlay":
        "https://www.chevrolet.co.kr/faq/android-auto-apple-carplay",

    "Online Shop":
        "https://www.chevrolet.co.kr/faq/online-shop",

    "EV 리콜":
        "https://www.chevrolet.co.kr/faq/ev-recall"
}


# =========================================================
# 3. 결과 저장 리스트
# =========================================================

data = []


# =========================================================
# 4. 카테고리별 크롤링
# =========================================================

for category, url in categories.items():

    print()
    print("=" * 60)
    print(f"{category} 크롤링 시작")
    print("=" * 60)

    driver.get(url)

    try:

        # FAQ 질문(h6)이 나타날 때까지 기다림
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "h6")
            )
        )

    except TimeoutException:

        print(f"❌ {category} 페이지에서 FAQ를 찾지 못했습니다.")
        print("URL:", driver.current_url)

        # 오류가 나도 다음 카테고리 진행
        continue


    # 페이지가 완전히 렌더링될 시간을 조금 줌
    time.sleep(1)


    # =====================================================
    # 5. 질문 가져오기
    # =====================================================

    questions = driver.find_elements(
        By.CSS_SELECTOR,
        "h6"
    )

    print("질문 개수:", len(questions))

    category_count = 0


    # =====================================================
    # 6. 질문 하나씩 처리
    # =====================================================

    for q in questions:

        original_question = q.text.strip()

        # 빈 h6 제외
        if not original_question:
            continue


        # -------------------------------------------------
        # [구매관련], [차량관리] 같은 앞부분 제거
        # -------------------------------------------------

        question = re.sub(
            r"^\[[^\]]+\]\s*",
            "",
            original_question
        ).strip()


        # =================================================
        # 7. 답변 가져오기
        #
        # 현재 h6부터 다음 h6 전까지의 내용 추출
        # =================================================

        answer = driver.execute_script("""
            const currentQuestion = arguments[0];

            // 페이지의 모든 FAQ 질문
            const questions = Array.from(
                document.querySelectorAll("h6")
            );

            const currentIndex =
                questions.indexOf(currentQuestion);

            if (currentIndex === -1) {
                return "";
            }


            // 다음 질문
            const nextQuestion =
                questions[currentIndex + 1];


            // 현재 질문 ~ 다음 질문 사이 범위 생성
            const range =
                document.createRange();


            range.setStartAfter(
                currentQuestion
            );


            // 다음 질문이 있는 경우
            if (nextQuestion) {

                range.setEndBefore(
                    nextQuestion
                );

            }

            // 마지막 질문인 경우
            else {

                const footer =
                    document.querySelector("footer");


                if (footer) {

                    range.setEndBefore(
                        footer
                    );

                }

                else {

                    range.setEnd(
                        document.body,
                        document.body.childNodes.length
                    );

                }
            }


            // 범위 복사
            const fragment =
                range.cloneContents();


            const container =
                document.createElement("div");


            container.appendChild(
                fragment
            );


            // =============================================
            // 필요 없는 코드 / 요소 제거
            // =============================================

            container.querySelectorAll(
                "script, style, noscript, template, svg"
            ).forEach(
                element => element.remove()
            );


            // 링크 URL 등이 아니라
            // 화면에 표시되는 텍스트만 반환
            return container.textContent || "";

        """, q)


        # =================================================
        # 8. 답변 정리
        # =================================================

        answer_lines = []


        for line in answer.splitlines():

            # 탭 / 여러 공백 정리
            line = re.sub(
                r"\s+",
                " ",
                line
            ).strip()


            # 빈 줄 제외
            if line:
                answer_lines.append(line)


        # 중복되는 줄 제거
        cleaned_lines = []

        for line in answer_lines:

            if line not in cleaned_lines:
                cleaned_lines.append(line)


        answer = "\n".join(
            cleaned_lines
        ).strip()


        # =================================================
        # 9. 혹시 JavaScript 코드가 남으면 제거
        # =================================================

        javascript_keywords = [
            "function downloadJSAtOnload",
            "document.createElement",
            "window.addEventListener",
            "window.attachEvent",
            "window.onload",
            "_satellite.pageBottom",
            "trackRenderedExperience",
            "sessionStorage.setItem"
        ]


        clean_answer_lines = []


        for line in answer.splitlines():

            # JS 코드가 시작되면 이후 내용은 버림
            if any(
                keyword in line
                for keyword in javascript_keywords
            ):
                break

            clean_answer_lines.append(line)


        answer = "\n".join(
            clean_answer_lines
        ).strip()


        # =================================================
        # 10. 답변 없는 경우
        # =================================================

        if not answer:

            print(
                f"⚠️ 답변 없음: {question}"
            )

            continue


        # =================================================
        # 11. 데이터 저장
        # =================================================

        data.append({

            "카테고리": category,

            "질문": question,

            "답변": answer

        })


        category_count += 1


        print(
            f"{category_count}. {question}"
        )


    print()

    print(
        f"✅ {category} : "
        f"{category_count}개 저장"
    )


# =========================================================
# 12. 브라우저 종료
# =========================================================

driver.quit()


# =========================================================
# 13. DataFrame 생성
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
# 14. 결과 확인
# =========================================================

print()
print("=" * 60)
print("크롤링 완료")
print("=" * 60)

print()

print(
    df.head(10).to_string(
        index=False
    )
)

print()

print(
    "총 FAQ 개수:",
    len(df)
)


# =========================================================
# 15. 카테고리별 개수 확인
# =========================================================

print()
print("카테고리별 FAQ 개수")

print(
    df["카테고리"].value_counts()
)


# =========================================================
# 16. CSV 저장
# =========================================================

df.to_csv(

    "C:/Users/playdata2/SKN_1ST_Project/최종_결과물/사용_데이터/크롤링/chevrolet_faq.csv",

    index=False,

    encoding="utf-8-sig"

)


print()
print(
    "✅ chevrolet_faq.csv 저장 완료"
)