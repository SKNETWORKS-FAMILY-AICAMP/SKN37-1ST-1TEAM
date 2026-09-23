"""
기업마당(bizinfo.go.kr) 지원사업 공고 API 수집 → faqs 테이블 저장
- 기업마당에는 '자동차 회사 FAQ' API가 따로 없어서, 지원사업 공고를
  (질문=사업명 / 답변=신청기간·기관·대상·요약) 형태의 FAQ 카드로 바꿔서 저장한다.
- --keyword 로 자동차 관련 공고만 골라 담을 수 있다.

사용법
    python collect_faq_data.py                                   # 최신 공고 100건
    python collect_faq_data.py --keyword 자동차 --count 300      # 자동차 관련 공고만
    python collect_faq_data.py --keyword 전기차 --count 300

※ 기업마당 API 인증키(BIZINFO_API_KEY)는 기업마당에서 별도로 신청해야 한다.
"""
import argparse
import html
import os
import re

import requests

import db

API_KEY = os.getenv("BIZINFO_API_KEY", "")
BASE_URL = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"
SITE = "https://www.bizinfo.go.kr"
CATEGORY = "지원사업 공고"


def clean_text(raw: str | None) -> str:
    """HTML 태그/엔티티 제거 후 공백 정리."""
    if not raw:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", raw, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"[ \t]+", " ", text).strip()


def fetch_notices(count: int, keyword: str = "") -> list[dict]:
    params = {"crtfcKey": API_KEY, "dataType": "json", "searchCnt": str(count)}
    if keyword:
        params["hashtags"] = keyword  # 해시태그 검색 (안 먹어도 아래에서 다시 걸러낸다)
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    try:
        data = resp.json()
    except ValueError:
        snippet = " ".join(resp.text.split())[:200].replace(API_KEY, "***")
        raise RuntimeError(f"JSON 이 아닌 응답이 왔습니다: {snippet}")
    if data.get("reqErr"):
        raise RuntimeError(f"기업마당 API 오류: {data['reqErr']}")
    return data.get("jsonArray", [])


def matches(item: dict, keyword: str) -> bool:
    """제목·요약·해시태그·지원대상·분야에 키워드가 들어 있는지."""
    fields = ("pblancNm", "bsnsSumryCn", "hashtags", "trgetNm",
              "pldirSportRealmLclasCodeNm", "pldirSportRealmMlsfcCodeNm")
    text = " ".join(clean_text(item.get(f)) for f in fields)
    return keyword.lower() in text.lower()


def to_faq_row(item: dict, category: str = CATEGORY) -> tuple:
    title = clean_text(item.get("pblancNm"))
    period = clean_text(item.get("reqstBeginEndDe")) or "공고문 확인"
    org = clean_text(item.get("jrsdInsttNm")) or "-"
    exec_org = clean_text(item.get("excInsttNm")) or "-"
    target = clean_text(item.get("trgetNm"))
    tags = clean_text(item.get("hashtags"))
    summary = clean_text(item.get("bsnsSumryCn"))

    lines = [
        f"신청기간: {period}",
        f"소관부처·지자체: {org}",
        f"사업수행기관: {exec_org}",
    ]
    if target:
        lines.append(f"지원대상: {target}")
    if tags:
        lines.append(f"해시태그: {tags}")
    answer = ("\n".join(lines) + "\n\n" + summary).strip()

    url = item.get("pblancUrl") or ""
    if url.startswith("/"):
        url = SITE + url
    source = url or "기업마당(bizinfo.go.kr)"

    return (f"bizinfo-{item.get('pblancId', title)}", category, title[:500], answer, source[:300])


def main(count: int, keyword: str):
    if not API_KEY:
        print("BIZINFO_API_KEY 가 없습니다. .env 파일에 기업마당 API 인증키를 넣어주세요.")
        return
    items = fetch_notices(count, keyword)
    print(f"기업마당에서 공고 {len(items)}건을 받았습니다.")
    if keyword:
        items = [it for it in items if matches(it, keyword)]
        print(f"  '{keyword}' 관련 공고: {len(items)}건")
        if not items:
            print("  관련 공고가 없습니다. --count 를 늘리거나 다른 키워드(예: 자동차부품, 전기차, 모빌리티)를 써보세요.")
            return
    category = f"{keyword} 지원사업" if keyword else CATEGORY
    rows = [to_faq_row(it, category) for it in items if it.get("pblancNm")]
    n = db.upsert_faqs(rows)
    print(f"저장 완료: {n}건 (앱의 '기업FAQ 조회' → 분류 '{category}')")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="기업마당 지원사업 공고 수집")
    parser.add_argument("--count", type=int, default=100, help="가져올 공고 수")
    parser.add_argument("--keyword", default="", help="예: 자동차")
    args = parser.parse_args()
    main(args.count, args.keyword.strip())
