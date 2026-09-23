"""
처음 한 번만 실행: DB 만들기 → 테이블 만들기 → 샘플 FAQ 넣기
    python setup_db.py
"""
import db


def main():
    conn = db.get_conn(with_db=False)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db.DB_NAME}` "
                "DEFAULT CHARACTER SET utf8mb4"
            )
        conn.commit()
    finally:
        conn.close()
    print(f"[1/3] 데이터베이스 준비 완료: {db.DB_NAME}")

    db.create_tables()
    print("[2/3] 테이블 준비 완료: car_registration, faqs")

    n = db.seed_sample_faqs()
    print(f"[3/3] 샘플 FAQ {n}건 저장 완료")


if __name__ == "__main__":
    main()
