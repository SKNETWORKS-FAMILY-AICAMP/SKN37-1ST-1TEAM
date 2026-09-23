"""
현대차/기아차 FAQ CSV → DB 적재 스크립트
사용법: python load_faqs.py
(db.py 와 동일 디렉토리에서 실행, .env 있어야 함)
"""
import csv
import sys
from pathlib import Path

# db.py 가 같은 폴더에 있다고 가정
sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import replace_faqs

# CSV 도 이 스크립트와 같은 폴더에 둔다 (app.py, db.py 등과 동일 위치)
HYUNDAI_CSV = Path(__file__).resolve().parent / "hyundai_faq_result.csv"
KIA_CSV     = Path(__file__).resolve().parent / "kia_faq_all_categories.csv"


def load_hyundai(path: Path) -> list[tuple]:
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            seq = r.get("순번", "").strip()
            cat = r.get("대분류", "").strip()
            q   = r.get("질문", "").strip()
            a   = r.get("답변", "").strip()
            if not seq or not q:          # 질문 없는 행skip
                continue
            ext_key = f"hyundai-{seq}"
            rows.append((ext_key, cat, q, a, "현대자동차"))
    return rows


def load_kia(path: Path) -> list[tuple]:
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            seq = r.get("순번", "").strip()
            cat = r.get("카테고리", "").strip()
            q   = r.get("질문", "").strip()
            a   = r.get("답변", "").strip()
            if not seq or not q:
                continue
            ext_key = f"kia-{seq}"
            rows.append((ext_key, cat, q, a, "기아자동차"))
    return rows


def main():
    if not HYUNDAI_CSV.exists():
        print(f"파일을 찾을 수 없습니다: {HYUNDAI_CSV}")
        return
    if not KIA_CSV.exists():
        print(f"파일을 찾을 수 없습니다: {KIA_CSV}")
        return

    hyundai_rows = load_hyundai(HYUNDAI_CSV)
    kia_rows     = load_kia(KIA_CSV)

    print(f"현대 FAQ 읽어옴: {len(hyundai_rows)}건")
    print(f"기아 FAQ 읽어옴: {len(kia_rows)}건")

    total = hyundai_rows + kia_rows
    if not total:
        print("적재할 데이터가 없습니다.")
        return

    # 기존 FAQ(샘플 FAQ, 기업마당 공고 등)는 전부 지우고 이 데이터로 교체한다
    n = replace_faqs(total)
    print(f"DB 교체 완료: 기존 FAQ 삭제 후 {n}건 적재")


if __name__ == "__main__":
    main()
