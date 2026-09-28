import os
from pathlib import Path
import pymysql
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

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
    """SELECT 실행 후 딕셔너리 리스트로 반환"""
    conn = get_conn()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(sql, params or ())
            return list(cur.fetchall())
    finally:
        conn.close()