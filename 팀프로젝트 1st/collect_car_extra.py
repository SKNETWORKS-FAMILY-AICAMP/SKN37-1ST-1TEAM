"""
신규등록 API 의 '조건별 전국 합계' 수집 스크립트
- 국산/외산, 사용연료, 용도, 성별, 연령대, 배기량별로 월별 전국 신규등록 대수를 받아 MySQL 에 저장한다.
- 한 달에 39번 호출 (2020-01 ~ 2026-08 이면 약 3,100번 → 하루 한도 때문에 이틀에 나눠 받는다).
- 하루 한도에 닿으면 알아서 멈춘다. 다음 날 같은 명령을 다시 실행하면 이어서 받는다.

사용법
    python collect_car_extra.py                        # 2020-01 ~ 2026-09 (공개된 달까지)
    python collect_car_extra.py --from 2025-01 --to 2025-06
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import collect_car_data as base
import db

CREATE_DIM_TABLE = """
CREATE TABLE IF NOT EXISTS car_registration_dim (
    연도     INT         NOT NULL,
    월       INT         NOT NULL,
    구분     VARCHAR(20) NOT NULL,
    코드     VARCHAR(20) NOT NULL,
    값명     VARCHAR(40) NOT NULL,
    그룹명   VARCHAR(40) NOT NULL,
    등록대수 INT         NOT NULL,
    PRIMARY KEY (연도, 월, 구분, 코드)
) DEFAULT CHARSET=utf8mb4
"""

INSERT_SQL = """
    INSERT INTO car_registration_dim (연도, 월, 구분, 코드, 값명, 그룹명, 등록대수)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE 등록대수 = VALUES(등록대수)
"""

# 구분 이름 → (API 파라미터 이름, [(파라미터 값, 값 이름, 그룹 이름), ...])
# 그룹 이름은 화면에서 묶어서 보여줄 때 쓴다 (예: 휘발유 3종 → 휘발유)
DIMENSIONS = {
    "국산·외산": ("hmmdImpSeNm", [("국산", "국산", "국산"), ("외산", "외산", "외산")]),
    "연료": ("useFuelCode", [
        ("1", "CNG", "CNG"), ("2", "경유", "경유"), ("3", "수소", "수소"), ("4", "LPG", "LPG"),
        ("5", "전기", "전기"), ("6", "하이브리드(CNG+전기)", "하이브리드"),
        ("7", "하이브리드(휘발유+전기)", "하이브리드"), ("8", "휘발유", "휘발유"),
        ("9", "휘발유(무연)", "휘발유"), ("10", "휘발유(유연)", "휘발유"), ("11", "기타연료", "기타연료"),
    ]),
    "용도": ("prposSeNm", [("1", "자가용", "자가용"), ("2", "영업용", "영업용"), ("3", "관용", "관용")]),
    "성별": ("sexdstn", [("남자", "남자", "남자"), ("여자", "여자", "여자"), ("법인", "법인", "법인")]),
    "연령대": ("agrde", [
        ("0", "법인", "법인"), ("1", "10대", "10대"), ("2", "20대", "20대"), ("3", "30대", "30대"),
        ("4", "40대", "40대"), ("5", "50대", "50대"), ("6", "60대", "60대"), ("7", "70대", "70대"),
        ("8", "80대", "80대"),
    ]),
    "배기량": ("dsplvlCode", [
        ("1", "800cc미만", "800cc미만"), ("2", "1000cc미만", "1000cc미만"),
        ("3", "1500cc미만", "1500cc미만"), ("4", "2000cc미만", "2000cc미만"),
        ("5", "2500cc미만", "2500cc미만"), ("6", "3000cc미만", "3000cc미만"),
        ("7", "3500cc미만", "3500cc미만"), ("8", "4000cc미만", "4000cc미만"),
        ("9", "4500cc미만", "4500cc미만"), ("10", "5000cc미만", "5000cc미만"),
        ("11", "5000cc이상", "5000cc이상"),
    ]),
}

# (구분, 코드) → 호출에 필요한 정보
ITEMS = [
    (dim, value, name, group, param)
    for dim, (param, values) in DIMENSIONS.items()
    for value, name, group in values
]


def ensure_table():
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_DIM_TABLE)
        conn.commit()
    finally:
        conn.close()


def already_saved(conn, year: int, month: int) -> set[tuple[str, str]]:
    with conn.cursor() as cur:
        cur.execute("SELECT 구분, 코드 FROM car_registration_dim WHERE 연도=%s AND 월=%s",
                    (year, month))
        return set(cur.fetchall())


def fetch_month(year: int, month: int, todo: list):
    """한 달치 조건들을 동시에 호출한다. (결과 dict, 하루한도 초과 여부)"""
    results = {}
    limit_hit = False
    with ThreadPoolExecutor(max_workers=base.WORKERS) as ex:
        futures = {
            ex.submit(base.fetch_stat, year, month, {param: value}): (dim, value)
            for dim, value, _name, _group, param in todo
        }
        for fut in as_completed(futures):
            key = futures[fut]
            try:
                results[key] = fut.result()
            except base.DailyLimitExceeded:
                limit_hit = True
    return results, limit_hit


def collect_range(start, end, max_calls: int):
    if not base.SERVICE_KEY:
        print("DATA_GO_KR_KEY 가 없습니다. .env 파일에 공공데이터포털 인증키를 넣어주세요.")
        return
    if not base.BASE_URL:
        print("API 주소를 자동으로 찾는 중...")
        base.BASE_URL = base.find_working_url() or ""
        if not base.BASE_URL:
            print("맞는 API 주소를 찾지 못했습니다. 인증키와 인터넷 연결을 확인하세요.")
            return
        print(f"  → 사용할 주소: {base.BASE_URL}")

    ensure_table()
    months = list(base.months_between(start, end))
    print(f"수집 범위: {start[0]}-{start[1]:02d} ~ {end[0]}-{end[1]:02d} ({len(months)}개월), "
          f"한 달 {len(ITEMS)}회, 오늘 최대 호출 {max_calls}회\n")

    conn = db.get_conn()
    calls = saved_months = 0
    stopped = ""
    try:
        for year, month in months:
            done = already_saved(conn, year, month)
            todo = [it for it in ITEMS if (it[0], it[1]) not in done]
            if not todo:
                continue
            if calls + len(todo) > max_calls:
                stopped = "limit"
                break

            results, limit_hit = fetch_month(year, month, todo)
            calls += len(todo)
            ok = {k: v for k, v in results.items() if v is not None}

            if not ok and not limit_hit:
                print("이 달은 전부 실패했습니다. 인증키/API 주소를 확인하세요. (중단)")
                stopped = "fail"
                break
            # 전부 0건이면 아직 공개 전인 달 → 저장하지 않고 멈춘다
            if len(ok) == len(todo) and sum(ok.values()) == 0 and not done:
                print(f"{year}-{month:02d}: 아직 데이터가 없는 달입니다. 여기까지만 저장합니다.")
                stopped = "nodata"
                break

            meta = {(dim, value): (name, group) for dim, value, name, group, _p in ITEMS}
            rows = [(year, month, dim, value, meta[(dim, value)][0], meta[(dim, value)][1], cnt)
                    for (dim, value), cnt in ok.items()]
            with conn.cursor() as cur:
                cur.executemany(INSERT_SQL, rows)
            conn.commit()
            saved_months += 1
            missing = len(todo) - len(ok)
            note = f", 실패 {missing}건(다시 실행하면 이어서 받음)" if missing else ""
            print(f"{year}-{month:02d}: {len(rows)}건 저장 (오늘 호출 {calls}/{max_calls}){note}")
            if limit_hit:
                stopped = "limit"
                break
    finally:
        conn.close()

    print(f"\n이번 실행: {saved_months}개월 저장, API 호출 {calls}회")
    if stopped == "limit":
        print("하루 호출 한도에 가까워서 여기서 멈췄습니다.")
        print("→ 내일 같은 명령(python collect_car_extra.py)을 다시 실행하면 이어서 받습니다.")
    elif stopped == "":
        print("요청한 기간을 모두 저장했습니다.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="국산/외산·연료 등 조건별 전국 신규등록 수집")
    parser.add_argument("--from", dest="start", default=base.PERIOD_START, help="시작 월 (예: 2020-01)")
    parser.add_argument("--to", dest="end", default="", help="끝 월 (기본: 2026-09 또는 조회 가능한 가장 최근 달)")
    parser.add_argument("--max-calls", type=int, default=base.DEFAULT_MAX_CALLS)
    args = parser.parse_args()
    end_ym = base.parse_ym(args.end) if args.end else base.default_end()
    collect_range(base.parse_ym(args.start), end_ym, args.max_calls)
