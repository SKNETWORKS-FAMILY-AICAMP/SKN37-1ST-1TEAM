"""Enterprise FAQ UI."""
import pandas as pd
import streamlit as st
import db

from .ai import ask_gemini
from .config import BRAND_INFO, BRAND_BY_QUERY, HOME_CSS, MAX_FAQ_SHOWN
from .ui_assets import _home_card

def _faq_display_name(source: str) -> str:
    """"~FAQ" 라벨에 쓸 짧은 브랜드 표기. 현대자동차/기아자동차는 "현대"/"기아"로 줄이고,
    나머지 브랜드는 원래 이름(BRAND_INFO 의 key) 그대로 쓴다."""
    return {"현대자동차": "현대", "기아자동차": "기아"}.get(source, source)


def _faq_source_for_brand(brand: str) -> str | None:
    """추천 결과의 '브랜드'(예: 현대/기아/BMW)를 기업FAQ 쪽 브랜드명(예: 현대자동차/기아자동차)으로
    바꿔준다. FAQ 테이블이 없는 브랜드(제네시스/KGM/르노코리아 등)면 None을 돌려준다."""
    if brand in ("현대", "현대자동차"):
        return "현대자동차"
    if brand in ("기아", "기아자동차"):
        return "기아자동차"
    return brand if brand in BRAND_INFO else None


def brand_logo_url(domain: str, size: int = 128) -> str:
    """도메인만 넣으면 그 회사 로고(파비콘)를 가져와주는 구글 서비스 주소를 만들어 반환한다.
    (직접 로고 이미지 파일을 우리가 들고 있지 않아도, 브라우저가 실행될 때 구글에서 받아온다 —
     그래서 이 서버(스트림릿 실행 PC)에 인터넷이 연결돼 있어야 실제로 보인다)"""
    return f"https://www.google.com/s2/favicons?sz={size}&domain={domain}"


def _render_faq_feedback(feedback_id: str, source: str, question: str):
    """AI가 생성한 FAQ 답변 아래에 👍/👎 버튼을 그리고, 누른 결과를 세션에 기록해둔다.
    (DB 스키마 변경 없이 세션 동안만 집계 — 한 번 누르면 '이미 평가함' 문구로 바뀐다)"""
    st.session_state.setdefault("faq_feedback", {})
    voted = st.session_state["faq_feedback"].get(feedback_id)
    if voted:
        icon = "👍" if voted == "up" else "👎"
        st.caption(f"{icon} 이 답변에 대한 피드백을 남겨주셨습니다. 감사합니다!")
        return
    fb1, fb2, _ = st.columns([1, 1, 4])
    if fb1.button("👍 도움됨", key=f"fbup_{feedback_id}"):
        st.session_state["faq_feedback"][feedback_id] = "up"
        st.session_state.setdefault("faq_feedback_log", []).append(
            {"source": source, "question": question, "feedback": "up"}
        )
        st.rerun()
    if fb2.button("👎 아쉬워요", key=f"fbdown_{feedback_id}"):
        st.session_state["faq_feedback"][feedback_id] = "down"
        st.session_state.setdefault("faq_feedback_log", []).append(
            {"source": source, "question": question, "feedback": "down"}
        )
        st.rerun()


@st.dialog("AI에게 질문하기", width="large")
def _faq_ai_dialog(source: str):
    """render_brand_faq 의 "AI에게 질문" 기능을 팝업(모달)으로 띄운다.
    자유 질문을 입력하면 관련 FAQ를 근거로 AI가 답변한다."""
    st.write(f"**{source}** — 궁금한 내용을 물어보면, 이 브랜드 FAQ 중 관련된 것을 우선 참고해서 답해줍니다.")
    qa_key = f"faq_qa_{source}"
    question = st.text_area(
        "질문", placeholder="예: 정기 점검 주기는 어떻게 되나요?", key=f"faq_q_{source}",
    )
    if st.button("AI에게 물어보기", key=f"ask_btn_{source}") and question.strip():
        related = db.find_related_faqs(question, limit=5, source=source)
        if related:
            context = "\n\n".join(
                f"[{i}] 질문: {r['question']}\n답변: {r['answer']}"
                for i, r in enumerate(related, 1)
            )
        else:
            context = "(관련 FAQ를 찾지 못했음)"
        prompt = (
            f"너는 {source} 차량 관련 안내 도우미다. 아래 [참고 FAQ]는 질문과 관련 있어 보이는 "
            "사내 FAQ 목록이다.\n"
            "- 참고 FAQ에 관련 내용이 있으면 그 내용을 우선 근거로 답해줘.\n"
            "- 참고 FAQ에 없는 내용이어도 무조건 모른다고 하지 말고, 네가 알고 있는 일반적인 "
            "자동차/자동차회사 관련 지식으로 최대한 도움이 되게 답변해줘. 다만 이 경우 답변 끝에 "
            "'※ 공식 FAQ에는 없는 내용이라 참고용으로만 봐주세요.' 라고 꼭 덧붙여줘.\n"
            "- 정확한 수치(가격, 보증기간, 전화번호 등)처럼 추측하면 위험한 내용은 참고 FAQ에 "
            "없으면 추측하지 말고, 대신 어디서 확인하면 좋을지 안내해줘.\n"
            "- 이 챗봇은 'FAQ' 전용이다. 사용자가 '어떤 차 사야 할지 추천해줘'처럼 차량 추천을 "
            "요청하면 직접 추천하지 말고, '자동차 추천 시스템' 메뉴를 이용해 달라고 한 문장으로 "
            "부드럽게 안내만 해줘. 자동차와 무관한 질문이면 'AI 챗봇' 메뉴를 이용해 달라고 안내해줘.\n\n"
            f"[참고 FAQ]\n{context}\n\n[사용자 질문]\n{question.strip()}"
        )
        with st.spinner("AI 답변 생성 중..."):
            answer = ask_gemini(prompt)
        st.session_state[qa_key] = (answer, related)

    if qa_key in st.session_state:
        answer, related = st.session_state[qa_key]
        st.info(answer)
        if related:
            st.caption("참고한 FAQ: " + " / ".join(r["question"][:40] for r in related))
        _render_faq_feedback(f"qa_{source}", source, question.strip())


def render_brand_faq(source: str):
    """특정 브랜드(source="현대자동차" 또는 "기아자동차") 안에서 분류 목록 + 검색 화면.
    "AI에게 질문"은 더 이상 탭이 아니라 버튼을 누르면 팝업(모달) 채팅창으로 열린다."""
    try:
        categories = ["전체"] + db.get_categories(source)
    except Exception as e:
        st.error(f"DB 연결 오류: {e}")
        st.info("car_recommend.sql 을 DB에 import 해 두었는지 확인해 주세요.")
        return

    top_l, top_r = st.columns([2, 7])
    with top_l:
        if st.button("AI에게 질문하기", key=f"open_faq_ai_{source}",
                     icon=":material/android:", use_container_width=True):
            _faq_ai_dialog(source)

    # ---------------- 키워드 + 분류(pills)로 DB에서 FAQ를 검색해서 목록으로 보여준다
    keyword = st.text_input(
        "FAQ 검색어 입력", placeholder="예: 보증, 정비예약, 충전",
        key=f"kw_{source}",
    )
    category = st.pills(
        "분류", categories, default=categories[0], key=f"cat_{source}",
    )
    if category is None:  # 이미 선택된 pill을 다시 눌러 선택 해제한 경우
        category = "전체"

    results = db.get_faqs(keyword.strip(), category, source)
    if not results:
        st.info("검색 결과가 없습니다.")
    else:
        st.caption(f"검색 결과 {len(results)}건"
                   + (f" (상위 {MAX_FAQ_SHOWN}건만 표시)" if len(results) > MAX_FAQ_SHOWN else ""))
        for item in results[:MAX_FAQ_SHOWN]:
            with st.expander(f"{item['category']} · {item['question']}"):
                st.write("**답변**")
                st.markdown(item["answer"].replace("\n", "  \n"))
                st.caption(f"출처: {item['source']}")

                ai_key = f"faq_ai_{item['id']}"
                if st.button("AI 요약/추가 설명", key=f"btn_{item['id']}"):
                    prompt = (
                        "다음 FAQ 내용을 바탕으로 사용자에게 친절하고 쉽게 설명해줘. "
                        "FAQ에 없는 내용은 지어내지 말아줘.\n\n"
                        f"질문: {item['question']}\n답변: {item['answer']}"
                    )
                    with st.spinner("AI 답변 생성 중..."):
                        st.session_state[ai_key] = ask_gemini(prompt)
                if ai_key in st.session_state:
                    st.info(st.session_state[ai_key])
                    _render_faq_feedback(f"ai_{item['id']}", source, item["question"])


def _faq_counts() -> dict:
    """브랜드별 FAQ 개수를 DB에서 세어온다 (브랜드 선택 카드에 "FAQ 123건"처럼 표시하기 위함).
    DB 연결이 안 되면 그냥 빈 딕셔너리 반환 (앱이 죽지 않게)."""
    try:
        return db.faq_counts()
    except Exception:
        return {}


def render_faq_brand_select():
    """기업FAQ 기본 화면: 아직 사이드바에서 브랜드를 안 골랐을 때 보여주는 카드 2장짜리 화면.
    사이드바에는 더 이상 "선택 화면" 라디오 항목이 없지만, "기업FAQ 조회" 버튼을 누르면
    (=아직 브랜드를 안 골랐으면) 이 화면이 대신 뜬다."""
    counts = _faq_counts()
    hero = (
        '<div class="home-hero"><h1>기업 FAQ 조회</h1>'
        "<p>브랜드를 선택하면 FAQ 검색과 AI 질문을 사용할 수 있어요.</p></div>"
    )
    st.markdown(HOME_CSS + hero, unsafe_allow_html=True)

    # 브랜드가 17개나 돼서 한눈에 찾기 어려우니, 이름(한글/영문 태그)으로 검색해서 걸러낼 수 있게 한다
    keyword = st.text_input(
        "브랜드 검색", placeholder="예: 현대, BMW, 벤츠 ...",
        key="faq_brand_search", label_visibility="collapsed",
    ).strip()

    if keyword:
        items = [
            (source, info) for source, info in BRAND_INFO.items()
            if keyword.lower() in source.lower() or keyword.lower() in info["tag"].lower()
        ]
    else:
        items = list(BRAND_INFO.items())

    if not items:
        st.info(f"'{keyword}' 와(과) 일치하는 브랜드가 없어요.")
        return

    cards = ""
    for source, info in items:
        n = counts.get(source)
        tag = f"{info['tag']} · FAQ {n:,}건" if n else info["tag"]
        cards += _home_card(f"?menu=faq&amp;brand={info['query']}", info["kind"],
                            tag, source, info["desc"], info["cta"],
                            logo_url=brand_logo_url(info["domain"]))
    st.markdown('<div class="home-grid">' + cards + "</div>", unsafe_allow_html=True)


def render_faq_menu():
    """사이드바 "기업FAQ 조회" 메뉴의 진입점.
    사이드바 하위 라디오(현대 FAQ / 기아 FAQ)에서 아직 브랜드를 안 골랐으면 선택 화면을,
    골랐으면 render_brand_faq(선택한 브랜드)를 보여준다."""
    brand = st.session_state.get("faq_brand")
    if brand not in BRAND_INFO:
        render_faq_brand_select()
        return
    st.header(f"{_faq_display_name(brand)} FAQ")
    log = st.session_state.get("faq_feedback_log", [])
    if log:
        up_n = sum(1 for f in log if f["feedback"] == "up")
        down_n = sum(1 for f in log if f["feedback"] == "down")
        with st.expander(f"📊 AI 답변 피드백 현황 (👍 {up_n} / 👎 {down_n})"):
            fb_df = pd.DataFrame(log)
            st.dataframe(fb_df, hide_index=True)
    render_brand_faq(brand)  # brand 값(브랜드 한글명)에 따라 같은 함수가 다른 데이터를 보여줌
