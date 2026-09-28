import os
import re
from pathlib import Path

import pymysql
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

DB_NAME = os.getenv("DB_NAME", "car_recommend")


def _config(with_db: bool = True) -> dict:
    cfg = dict(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        charset="utf8mb4",
    )
    if with_db:
        cfg["database"] = DB_NAME
    return cfg


def get_conn(with_db: bool = True):
    return pymysql.connect(**_config(with_db))


def fetch_all(sql: str, params=None) -> list[dict]:
    """SELECT 실행 후 딕셔너리 리스트로 돌려준다."""
    conn = get_conn()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(sql, params or ())
            return list(cur.fetchall())
    finally:
        conn.close()


# ---------------------------------------------------------------- 차량 카탈로그 (car_info)
def get_car_info() -> list[dict]:
    """car_info 테이블 전체를 읽어온다 (브랜드/모델명/차종/연료형태/출고가/평균연비).
    app.py 의 _load_recommend_data() 가 이 값을 SAMPLE_CARS 로 가공해서 쓴다."""
    return fetch_all(
        "SELECT id, brand, car_name, car_type, fuel_type, price_str, price_num, avg_efficiency "
        "FROM car_info"
    )


# ---------------------------------------------------------------- FAQ (브랜드별 테이블)
# 브랜드(한글 표기) → 실제 테이블명
FAQ_BRAND_TABLES = {
    "현대자동차": "hyundai_faq",
    "기아자동차": "kia_faq",
    "BMW": "bmw_faq",
    "벤츠": "benz_faq",
    "아우디": "audi_faq",
    "폭스바겐": "volkswagen_faq",
    "볼보": "volvo_faq",
    "미니": "mini_faq",
    "랜드로버": "landrover_faq",
    "테슬라": "tesla_faq",
    "토요타": "toyota_faq",
    "렉서스": "lexus_faq",
    "혼다": "honda_faq",
    "쉐보레": "chevrolet_faq",
    "포드": "ford_faq",
    "지프": "jeep_faq",
    "르노": "renault_faq",
}

# 테이블별 실제 컬럼 구조가 달라서, 표준화된 SELECT 문을 미리 만들어 둔다.
# 항상 결과가 id / category / question / answer 4개 컬럼으로 나오도록 별칭(AS)을 준다.
# hyundai_faq 는 category_major(대분류)/category_minor(소분류) 두 컬럼으로 나뉘어 있는데,
# "모젠서비스 > 사용법", "모젠서비스 > 결제"처럼 대분류가 같아도 소분류가 다르면 분류(pill)가
# 전부 따로 생겨서 목록이 너무 잘게 쪼개지는 문제가 있었다. 그래서 분류(category)는
# category_major 하나로만 묶고, category_minor 는 정보가 사라지지 않도록 질문 앞에
# "[소분류] " 형태로 붙여준다.
_HYUNDAI_SELECT = (
    "SELECT seq_no AS id, "
    "NULLIF(category_major, '') AS category, "
    "CASE WHEN NULLIF(category_minor, '') IS NOT NULL "
    "THEN CONCAT('[', category_minor, '] ', question) ELSE question END AS question, "
    "answer FROM hyundai_faq"
)
_KIA_SELECT = "SELECT seq_no AS id, category, question, answer FROM kia_faq"


def _select_sql_for(table: str) -> str:
    if table == "hyundai_faq":
        return _HYUNDAI_SELECT
    if table == "kia_faq":
        return _KIA_SELECT
    # 나머지 15개 브랜드: 한글 컬럼명 (백틱으로 감싸야 함)
    return f"SELECT `순번` AS id, `카테고리` AS category, `질문` AS question, `답변` AS answer FROM `{table}`"


def get_categories(source: str | None = None) -> list[str]:
    """source: FAQ_BRAND_TABLES 의 key (브랜드 한글명). None 이면 전체 브랜드 통틀어서."""
    tables = [FAQ_BRAND_TABLES[source]] if source else list(FAQ_BRAND_TABLES.values())
    cats: set[str] = set()
    for table in tables:
        sql = f"SELECT DISTINCT category FROM ({_select_sql_for(table)}) t"
        for r in fetch_all(sql):
            if r["category"]:
                cats.add(r["category"])
    return sorted(cats)


def get_faqs(keyword: str = "", category: str = "전체", source: str | None = None) -> list[dict]:
    """source 를 지정하지 않으면 17개 브랜드 테이블을 모두 조회해서 합친 결과를 돌려준다."""
    tables = [FAQ_BRAND_TABLES[source]] if source else list(FAQ_BRAND_TABLES.values())
    brand_by_table = {v: k for k, v in FAQ_BRAND_TABLES.items()}

    results: list[dict] = []
    for table in tables:
        sql = f"SELECT id, category, question, answer FROM ({_select_sql_for(table)}) t WHERE 1=1"
        params: list = []
        if keyword:
            sql += " AND (question LIKE %s OR answer LIKE %s OR category LIKE %s)"
            like = f"%{keyword}%"
            params += [like, like, like]
        if category != "전체":
            sql += " AND category = %s"
            params.append(category)
        sql += " ORDER BY id"
        for r in fetch_all(sql, params):
            r["source"] = brand_by_table[table]
            results.append(r)
    return results


def faq_counts() -> dict:
    """브랜드별 FAQ 건수 (브랜드 선택 카드에 "FAQ 123건"처럼 표시하기 위함)."""
    counts: dict[str, int] = {}
    for brand, table in FAQ_BRAND_TABLES.items():
        rows = fetch_all(f"SELECT COUNT(*) AS n FROM `{table}`")
        counts[brand] = int(rows[0]["n"]) if rows else 0
    return counts


def _stems(word: str) -> list[str]:
    """'지원사업은' → ['지원사업은', '지원사업', '지원사'] (한국어 조사 대응용 간단 처리)"""
    return [s for s in (word, word[:-1], word[:-2]) if len(s) >= 2]


def find_related_faqs(question: str, limit: int = 5, source: str | None = None) -> list[dict]:
    """질문과 관련 있어 보이는 FAQ 를 점수로 골라 AI 에게 넘길 근거 자료로 쓴다."""
    words = re.findall(r"[가-힣A-Za-z0-9]+", question)
    words = [w for w in words if len(w) >= 2]
    if not words:
        return []

    scored = []
    for row in get_faqs(source=source):
        text = f"{row['category']} {row['question']} {row['answer']}"
        score = sum(1 for w in words if any(s in text for s in _stems(w)))
        if score:
            scored.append((score, row))
    scored.sort(key=lambda x: -x[0])
    return [row for _, row in scored[:limit]]
