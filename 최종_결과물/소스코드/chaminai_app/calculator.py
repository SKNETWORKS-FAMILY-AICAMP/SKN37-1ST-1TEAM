"""Monthly payment calculator."""
import json
import os

import plotly.express as px
import pandas as pd
import streamlit as st

from .config import GEMINI_MODEL
from .recommendation.data import SAMPLE_CARS

def _amortization_schedule(principal: float, annual_rate_pct: float, months: int) -> "pd.DataFrame":
    """원리금균등상환 스케줄(회차별 원금/이자/잔액)을 계산해서 표로 돌려준다."""
    r = (annual_rate_pct / 100) / 12  # 월 이자율
    if r == 0:
        monthly = principal / months
    else:
        monthly = principal * r * (1 + r) ** months / ((1 + r) ** months - 1)

    rows, balance = [], principal
    for m in range(1, months + 1):
        interest = balance * r
        principal_paid = monthly - interest
        balance = max(balance - principal_paid, 0)
        rows.append({"회차": m, "월 납입금": monthly, "원금": principal_paid, "이자": interest, "잔액": balance})
    return pd.DataFrame(rows)


# ---- 계산기 안에 들어가는 AI 상담 챗봇 (자연어로 "쏘나타 36개월 계약금 0원 연이자율 5%" 처럼
#      물어보면 조건을 읽어서 바로 계산해준다) ----------------------------------------------
def extract_calc_conditions(user_msg: str) -> dict:
    """(계산기 챗봇 전용) 메시지에서 차종 키워드/할부개월/계약금/연이자율 조건을 뽑아낸다."""
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_KEY") or "").strip()
    if not api_key:
        return {}
    try:
        from google import genai
    except ImportError:
        return {}

    prompt = (
        "너는 '월납입금 계산기' 챗봇의 조건 추출기다. 사용자 메시지를 분석해서 JSON 하나만 "
        "출력해라 (설명이나 코드블록 없이 JSON 텍스트만).\n\n"
        '{"model_keyword":<차량 모델명 또는 브랜드 키워드(예: "쏘나타")|null>,'
        '"months":<할부 개월수(숫자만)|null>,"down_payment_manwon":<계약금(만원 단위 숫자)|null>,'
        '"annual_rate_pct":<연이자율(% 단위 숫자)|null>}\n\n'
        "언급 안 된 값은 null 로 둬라. '5퍼센트', '5%', '연 5부' 등은 모두 5(숫자)로 변환해라.\n\n"
        f"사용자 메시지: {user_msg}"
    )
    try:
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        text = (resp.text or "").strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(text)
    except Exception:
        return {}


def calc_chat_answer(user_msg: str) -> str:
    """계산기 챗봇 답변 생성기. 메시지에서 조건을 뽑아 직접 계산하고, 결과를 아래쪽
    계산기 입력칸(session_state)에도 그대로 반영한다."""
    cond = extract_calc_conditions(user_msg)

    kw = (cond.get("model_keyword") or "").strip()
    matched = None
    if kw:
        candidates = [c for c in SAMPLE_CARS if kw in c["모델명"] or kw in c["브랜드"]]
        matched = candidates[0] if candidates else None

    if not matched:
        return (
            "차량 모델을 정확히 못 찾았어요 :( '쏘나타 36개월 계약금 0원 연이자율 5%' 처럼 "
            "실제 차량 모델명을 포함해서 다시 물어봐 주시겠어요?"
        )

    months_options = [12, 24, 36, 48, 60, 72]
    months = cond.get("months")
    if months not in months_options:
        months = min(months_options, key=lambda m: abs(m - months)) if months else 36

    down_payment_manwon = cond.get("down_payment_manwon")
    down_payment_manwon = int(down_payment_manwon) if down_payment_manwon else 0

    annual_rate = cond.get("annual_rate_pct")
    annual_rate = float(annual_rate) if annual_rate is not None else 5.9

    car_price_manwon = int(round(matched["출고가"] / 10_000))
    down_payment_manwon = min(down_payment_manwon, car_price_manwon)
    principal = (car_price_manwon - down_payment_manwon) * 10_000

    if principal <= 0:
        return "계약금이 차량 가격 이상이라 할부 원금이 없어요. 계약금을 조금 낮춰서 다시 물어봐 주시겠어요?"

    schedule = _amortization_schedule(principal, annual_rate, months)
    monthly_payment = schedule["월 납입금"].iloc[0]
    total_payment = schedule["월 납입금"].sum()
    total_interest = schedule["이자"].sum()

    # 아래쪽 계산기 입력칸에도 같은 조건을 그대로 반영해준다
    st.session_state["calc_car_price"] = car_price_manwon
    st.session_state["calc_down_payment"] = down_payment_manwon
    st.session_state["calc_months"] = months
    st.session_state["calc_rate"] = annual_rate

    return (
        f"네, 확인해드릴게요 :) **{matched['브랜드']} {matched['모델명']} · {months}개월 · "
        f"계약금 {down_payment_manwon:,}만원 · 연이자율 {annual_rate}%**\n\n"
        f"- 차량 가격: {matched['출고가']:,.0f}원\n"
        f"- 할부 원금: {principal:,.0f}원\n"
        f"- **월 납입금: {monthly_payment:,.0f}원**\n"
        f"- 총 납입액: {total_payment:,.0f}원\n"
        f"- 총 이자: {total_interest:,.0f}원\n\n"
        "아래 계산기 입력칸에도 같은 조건을 반영해 놨어요. 조건을 더 정확히 조정하고 싶으면 아래에서 직접 바꿔보셔도 돼요."
    )


def render_calc_chatbot():
    """계산기 화면 위쪽에 들어가는 미니 상담 채팅창을 그린다.
    AI 챗봇 메뉴/추천 상담창과는 완전히 별개로 session_state["calc_chat_msgs"] 에 따로 저장한다."""
    if "calc_chat_msgs" not in st.session_state:
        st.session_state["calc_chat_msgs"] = []

    for m in st.session_state["calc_chat_msgs"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    user_msg = st.chat_input(
        "예: 쏘나타 36개월 계약금 0원 연이자율 5%", key="calc_chat_input",
    )
    if user_msg:
        st.session_state["calc_chat_msgs"].append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.markdown(user_msg)
        with st.chat_message("assistant"):
            with st.spinner("계산하고 있어요..."):
                reply = calc_chat_answer(user_msg)
            st.markdown(reply)
        st.session_state["calc_chat_msgs"].append({"role": "assistant", "content": reply})

    if len(st.session_state["calc_chat_msgs"]) > 1:
        if st.button("상담 대화 초기화", key="calc_chat_clear"):
            st.session_state["calc_chat_msgs"] = []
            st.rerun()


@st.dialog("AI 상담사 — 월납입금 계산", width="large")
def _calc_chat_dialog():
    """render_calc_chatbot() 을 팝업(모달) 창 안에 그대로 그려서, 채팅방처럼 열고 닫을 수 있게 한다."""
    render_calc_chatbot()


def render_calc_menu():
    """[월납입금 계산기] 화면: 차량가격·계약금·할부기간·연이자율을 입력하면
    원리금균등상환 기준 월 납입금과 회차별 상환 스케줄을 계산해 보여준다."""
    st.caption("차량가격·계약금·할부기간·연이자율을 입력하면 원리금균등상환 기준 월 납입금을 계산해드려요.")

    # AI 상담사에게 자연어로 물어보면("쏘나타 36개월 계약금 0원 연이자율 5%") 바로 계산해준다
    unread = len(st.session_state.get("calc_chat_msgs", []))
    chat_label = "AI 상담사에게 물어보기" + (f" ({unread}개 대화 중)" if unread > 1 else "")
    if st.button(chat_label, key="open_calc_chat", type="primary",
                 icon=":material/android:", use_container_width=True):
        _calc_chat_dialog()

    st.divider()

    # ---- 차량 가격 불러오기: 전체 차량 직접 검색 ----
    st.session_state.setdefault("calc_car_price", 4000)  # 만원 단위, "차량 가격" 입력창의 시작값
    st.markdown("**차량 검색해서 가격 불러오기** (선택 사항 — 직접 입력해도 됩니다)")
    keyword = st.text_input(
        "모델명 또는 브랜드로 검색", placeholder="예: 아반떼, 쏘나타, 스포티지, 현대",
        key="calc_search_kw",
    )
    kw = keyword.strip()
    if kw:
        matches = [c for c in SAMPLE_CARS if kw in c["모델명"] or kw in c["브랜드"]]
        if not matches:
            st.caption("검색 결과가 없습니다.")
        else:
            match_options = {
                f"{c['브랜드']} {c['모델명']} ({c['세그먼트']}·{c['연료']}) — 출고가 {c['출고가']:,.0f}원": c["출고가"]
                for c in matches[:30]
            }
            st.caption(f"검색 결과 {len(matches)}건" + (" (상위 30건만 표시)" if len(matches) > 30 else ""))
            picked_search = st.selectbox(
                "검색된 차량에서 선택", list(match_options.keys()),
                index=None, placeholder="차량을 선택하세요", key="calc_search_pick",
            )
            if picked_search and st.button("이 차량 가격 불러오기", key="calc_search_apply"):
                st.session_state["calc_car_price"] = int(round(match_options[picked_search] / 10_000))
                st.rerun()

    st.divider()
    c1, c2 = st.columns(2)
    car_price_manwon = c1.number_input(
        "차량 가격 (만원)", min_value=0, max_value=100_000, step=100, key="calc_car_price",
    )
    down_payment_manwon = c2.number_input(
        "계약금 (만원)", min_value=0, max_value=car_price_manwon, step=100, value=0, key="calc_down_payment",
    )

    c3, c4 = st.columns(2)
    months = c3.selectbox("할부 기간 (개월)", [12, 24, 36, 48, 60, 72], index=2, key="calc_months")
    annual_rate = c4.number_input(
        "연이자율 (%)", min_value=0.0, max_value=30.0, step=0.1, value=5.9, key="calc_rate",
    )

    principal = (car_price_manwon - down_payment_manwon) * 10_000
    if principal <= 0:
        st.info("계약금이 차량 가격 이상이라 할부 원금이 없습니다.")
        return

    schedule = _amortization_schedule(principal, annual_rate, months)
    monthly_payment = schedule["월 납입금"].iloc[0]
    total_payment = schedule["월 납입금"].sum()
    total_interest = schedule["이자"].sum()

    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("월 납입금", f"{monthly_payment:,.0f}원")
    m2.metric("총 납입액", f"{total_payment:,.0f}원")
    m3.metric("총 이자", f"{total_interest:,.0f}원")

    # 회차별 원금/이자 구성 — 누적 막대그래프 (뒤로 갈수록 원금 비중이 커지는 걸 한눈에 보여준다)
    fig = px.bar(
        schedule, x="회차", y=["원금", "이자"], barmode="stack",
        color_discrete_map={"원금": "#4fc3c3", "이자": "#f06a6a"},
        title="회차별 원금·이자 구성",
    )
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=40, b=10), yaxis_title="금액(원)")
    st.plotly_chart(fig, use_container_width=True)

    # 잔액이 줄어드는 추이 — 선그래프
    fig2 = px.line(schedule, x="회차", y="잔액", title="잔여 원금 추이")
    fig2.update_traces(line=dict(color="#8a7fd6", width=3))
    fig2.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10), yaxis_title="잔액(원)")
    st.plotly_chart(fig2, use_container_width=True)

    with st.expander("회차별 상환 스케줄 전체 보기"):
        show = schedule.copy()
        for col in ["월 납입금", "원금", "이자", "잔액"]:
            show[col] = show[col].round(0).astype(int)
        st.dataframe(show, hide_index=True)
        st.download_button(
            "⬇️ 상환 스케줄 CSV로 다운로드", data=show.to_csv(index=False).encode("utf-8-sig"),
            file_name="월납입금_상환스케줄.csv", mime="text/csv", key="download_calc_csv",
        )
