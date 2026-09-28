import re
from db.connection import fetch_all

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
    return f"SELECT `순번` AS id, `카테고리` AS category, `질문` AS question, `답변` AS answer FROM `{table}`"

def get_categories(source: str | None = None) -> list[str]:
    tables = [FAQ_BRAND_TABLES[source]] if source else list(FAQ_BRAND_TABLES.values())
    cats: set[str] = set()
    for table in tables:
        sql = f"SELECT DISTINCT category FROM ({_select_sql_for(table)}) t"
        for r in fetch_all(sql):
            if r["category"]:
                cats.add(r["category"])
    return sorted(cats)

def get_faqs(keyword: str = "", category: str = "전체", source: str | None = None) -> list[dict]:
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
    counts: dict[str, int] = {}
    for brand, table in FAQ_BRAND_TABLES.items():
        rows = fetch_all(f"SELECT COUNT(*) AS n FROM `{table}`")
        counts[brand] = int(rows[0]["n"]) if rows else 0
    return counts

def _stems(word: str) -> list[str]:
    return [s for s in (word, word[:-1], word[:-2]) if len(s) >= 2]

def find_related_faqs(question: str, limit: int = 5, source: str | None = None) -> list[dict]:
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

def get_faqs_by_brand(
    brand: str, keyword: str = "", limit: int | None = None
) -> list[dict]:
  """특정 브랜드의 FAQ 목록을 키워드 및 개수 제한(limit)과 함께 조회합니다."""
  faqs = get_faqs(keyword=keyword, source=brand)
  return faqs[:limit] if limit else faqs