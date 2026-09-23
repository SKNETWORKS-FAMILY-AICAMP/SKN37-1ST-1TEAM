"""
한국교통안전공단_자동차 종합정보 신규등록정보 서비스 수집 스크립트
- 월별 × 지역(17) × 차종(4) = 한 달에 68번 API 를 호출해서 MySQL 에 저장한다.
- 개발계정은 하루 3,000번까지라서, 하루 한도에 닿으면 알아서 멈춘다.
  → 다음 날 같은 명령을 다시 실행하면 저장된 달은 건너뛰고 이어서 받는다.

사용법
    python collect_car_data.py                          # 2020-01 ~ 2026-09 (공개된 달까지) 전부
    python collect_car_data.py --from 2023-01 --to 2023-06
"""
import argparse
import datetime
import os
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

import db  # .env 를 여기서 읽어온다

SERVICE_KEY = os.getenv("DATA_GO_KR_KEY", "")  # 공공데이터포털 '일반 인증키(Decoding)'

# API 주소: 공공데이터포털 활용명세(Swagger)에 나온 값
#   Base URL : apis.data.go.kr/B553881/newRegistlnfoService_02
#   오퍼레이션: /getnewRegistInfoService02
# 화면에서는 소문자 l 과 대문자 I 가 똑같이 보여서, 가능한 조합을 자동으로 시험해 맞는 주소를 고른다.
# (.env 에 CAR_API_URL 을 적으면 그 주소를 그대로 사용)
CANDIDATE_URLS = [
    f"https://apis.data.go.kr/B553881/{svc}/{op}"
    for svc in ("newRegistlnfoService_02", "newRegistInfoService_02")
    for op in ("getnewRegistInfoService02", "getnewRegistlnfoService02")
]
BASE_URL = os.getenv("CAR_API_URL") or ""

REGION_CODES = {
    1: "서울", 2: "부산", 3: "대구", 4: "인천", 5: "광주", 6: "대전", 7: "울산",
    8: "세종", 9: "경기", 10: "강원", 11: "충북", 12: "충남", 13: "전북",
    14: "전남", 15: "경북", 16: "경남", 17: "제주",
}
VEHICLE_TYPE_CODES = {1: "승용", 2: "승합", 3: "화물", 4: "특수"}

PERIOD_START = "2020-01"       # 수집 시작 월
PERIOD_END = (2026, 9)         # 수집 끝 월 (아직 공개 전인 달은 자동으로 건너뛴다)

WORKERS = 4                # 동시에 호출하는 수 (너무 크면 초당 제한에 걸린다)
DEFAULT_MAX_CALLS = 2800   # 하루 한도(3,000) 안쪽에서 멈추기 위한 여유값

_warned = 0


class DailyLimitExceeded(Exception):
    """하루 호출 한도 초과"""


def warn(msg: str):
    """오류 메시지는 처음 몇 개만 보여준다 (화면이 도배되지 않도록)."""
    global _warned
    _warned += 1
    if _warned <= 8:
        print(msg)
    elif _warned == 9:
        print("  (이후 오류 메시지는 생략합니다)")


def find_working_url() -> str | None:
    """후보 주소 중 '서비스 없음(코드 12)'이 아닌 주소를 찾는다."""
    test = {"serviceKey": SERVICE_KEY, "registYy": "2025", "registMt": "01",
            "registGrcCode": "1", "vhctyAsortCode": "1"}
    for url in CANDIDATE_URLS:
        try:
            r = requests.get(url, params=test, timeout=10)
        except requests.RequestException:
            continue
        if "NO_OPENAPI_SERVICE_ERROR" in r.text:
            continue
        if any(t in r.text for t in ("<dtaCo>", "<resultCode>", "OpenAPI_ServiceResponse")):
            return url
    return None


def fetch_stat(year: int, month: int, extra: dict) -> int | None:
    """연/월 + 추가 조건(extra)에 맞는 신규등록 건수를 조회한다. 실패하면 None."""
    params = {
        "serviceKey": SERVICE_KEY,
        "registYy": str(year),
        "registMt": f"{month:02d}",
        **extra,
    }
    label = f"{year}-{month:02d} " + " ".join(f"{k}={v}" for k, v in extra.items())

    resp = None
    for attempt in range(4):
        try:
            resp = requests.get(BASE_URL, params=params, timeout=15)
        except requests.RequestException as e:
            # 주소(URL)에는 인증키가 들어 있어서 출력하지 않는다
            if attempt < 3:
                time.sleep(1 + attempt)
                continue
            warn(f"  [통신 오류] {label}: {type(e).__name__}")
            return None
        text = resp.text
        if "REQUESTS_PER_SECOND_EXCEEDS" in text:      # 초당 호출 초과 → 잠깐 쉬고 재시도
            time.sleep(1.5 * (attempt + 1))
            resp = None
            continue
        if "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR" in text:
            raise DailyLimitExceeded()
        break
    if resp is None:
        warn(f"  [초당 호출 제한] {label}")
        return None

    if resp.status_code != 200:
        body = " ".join(resp.text.split())[:400].replace(SERVICE_KEY, "***")
        warn(f"  [HTTP {resp.status_code}] {label}\n    서버 응답: {body}")
        return None

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError:
        body = " ".join(resp.text.split())[:400].replace(SERVICE_KEY, "***")
        warn(f"  [응답 해석 오류] {label}\n    서버 응답: {body}")
        return None

    result_code = root.findtext(".//resultCode")
    if result_code == "03":  # NODATA_ERROR: 해당 조건의 데이터 없음 → 0건
        return 0
    if result_code != "00":
        msg = root.findtext(".//resultMsg") or root.findtext(".//returnAuthMsg")
        warn(f"  [API 오류] {label}: {result_code} {msg}")
        return None

    dta_co = root.findtext(".//dtaCo")
    return int(dta_co) if dta_co is not None else 0


def fetch_count(year: int, month: int, region_code: int, vhcty_code: int) -> int | None:
    """지역 × 차종 조합의 신규등록 건수."""
    return fetch_stat(year, month, {"registGrcCode": str(region_code),
                                    "vhctyAsortCode": str(vhcty_code)})


def already_saved(conn, year: int, month: int) -> set[tuple[int, int]]:
    """이미 저장된 (지역코드, 차종코드) 조합 → 다시 호출하지 않아 호출 한도를 아낀다."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 지역코드, 차종코드 FROM car_registration WHERE 연도=%s AND 월=%s",
            (year, month),
        )
        return set(cur.fetchall())


def parse_ym(text: str) -> tuple[int, int]:
    y, m = text.split("-")
    return int(y), int(m)


def months_between(start: tuple[int, int], end: tuple[int, int]):
    y, m = start
    while (y, m) <= end:
        yield y, m
        m += 1
        if m > 12:
            y, m = y + 1, 1


def latest_available_month(today: datetime.date | None = None) -> tuple[int, int]:
    """전월 데이터는 매월 2일부터 조회 가능 → 오늘 기준 조회 가능한 가장 최근 달."""
    today = today or datetime.date.today()
    y, m = today.year, today.month
    m -= 1 if today.day >= 2 else 2
    while m < 1:
        m += 12
        y -= 1
    return y, m


def default_end() -> tuple[int, int]:
    """조회 가능한 가장 최근 달과 PERIOD_END 중 이른 쪽."""
    return min(latest_available_month(), PERIOD_END)


INSERT_SQL = """
    INSERT INTO car_registration
        (연도, 월, 지역코드, 지역명, 차종코드, 차종명, 등록대수)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE 등록대수 = VALUES(등록대수)
"""


def fetch_month(year: int, month: int, todo: list[tuple[int, int]]):
    """한 달치를 동시에 여러 개 호출한다. (결과 dict, 하루한도 초과 여부)"""
    results: dict[tuple[int, int], int | None] = {}
    limit_hit = False
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(fetch_count, year, month, rc, vc): (rc, vc) for rc, vc in todo}
        for fut in as_completed(futures):
            key = futures[fut]
            try:
                results[key] = fut.result()
            except DailyLimitExceeded:
                limit_hit = True
    return results, limit_hit


def collect_range(start: tuple[int, int], end: tuple[int, int], max_calls: int):
    global BASE_URL
    if not SERVICE_KEY:
        print("DATA_GO_KR_KEY 가 없습니다. .env 파일에 공공데이터포털 인증키를 넣어주세요.")
        return
    if not BASE_URL:
        print("API 주소를 자동으로 찾는 중...")
        BASE_URL = find_working_url() or ""
        if not BASE_URL:
            print("맞는 API 주소를 찾지 못했습니다. 인증키(활용신청 승인 여부)와 인터넷 연결을 확인하세요.")
            return
        print(f"  → 사용할 주소: {BASE_URL}")

    months = list(months_between(start, end))
    print(f"수집 범위: {start[0]}-{start[1]:02d} ~ {end[0]}-{end[1]:02d} ({len(months)}개월), "
          f"오늘 최대 호출 {max_calls}회\n")

    conn = db.get_conn()
    calls = saved_months = 0
    stopped_reason = ""
    try:
        for year, month in months:
            done = already_saved(conn, year, month)
            todo = [(rc, vc) for rc in REGION_CODES for vc in VEHICLE_TYPE_CODES
                    if (rc, vc) not in done]
            if not todo:
                continue  # 이미 다 저장된 달

            if calls + len(todo) > max_calls:
                stopped_reason = "limit"
                break

            results, limit_hit = fetch_month(year, month, todo)
            calls += len(todo)
            ok = {k: v for k, v in results.items() if v is not None}

            # 성공한 조합이 하나도 없으면 주소/키 문제 → 계속 해봐야 소용없다
            if not ok and not limit_hit:
                print("이 달은 전부 실패했습니다. 인증키/API 주소를 확인하세요. (중단)")
                stopped_reason = "fail"
                break

            # 68개 전부 0건이면 아직 공개 전인 달로 보고 저장하지 않는다
            if len(ok) == len(todo) and sum(ok.values()) == 0 and not done:
                print(f"{year}-{month:02d}: 아직 데이터가 없는 달입니다. 여기까지만 저장합니다.")
                stopped_reason = "nodata"
                break

            rows = [(year, month, rc, REGION_CODES[rc], vc, VEHICLE_TYPE_CODES[vc], cnt)
                    for (rc, vc), cnt in ok.items()]
            with conn.cursor() as cur:
                cur.executemany(INSERT_SQL, rows)
            conn.commit()  # 월 단위로 저장 → 중간에 멈춰도 앞부분은 남는다
            saved_months += 1
            missing = len(todo) - len(ok)
            note = f", 실패 {missing}건(다시 실행하면 이어서 받음)" if missing else ""
            print(f"{year}-{month:02d}: {len(rows)}건 저장 (오늘 호출 {calls}/{max_calls}){note}")

            if limit_hit:
                stopped_reason = "limit"
                break
    finally:
        conn.close()

    print(f"\n이번 실행: {saved_months}개월 저장, API 호출 {calls}회")
    if stopped_reason == "limit":
        print("하루 호출 한도에 가까워서 여기서 멈췄습니다.")
        print("→ 내일 같은 명령(python collect_car_data.py)을 다시 실행하면 이어서 받습니다.")
    elif stopped_reason == "":
        print("요청한 기간을 모두 저장했습니다.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="자동차 신규등록 현황 수집")
    parser.add_argument("--from", dest="start", default=PERIOD_START, help="시작 월 (예: 2020-01)")
    parser.add_argument("--to", dest="end", default="", help="끝 월 (기본: 2026-09 또는 조회 가능한 가장 최근 달)")
    parser.add_argument("--max-calls", type=int, default=DEFAULT_MAX_CALLS,
                        help="이번 실행의 최대 API 호출 수")
    args = parser.parse_args()
    end_ym = parse_ym(args.end) if args.end else default_end()
    collect_range(parse_ym(args.start), end_ym, args.max_calls)
