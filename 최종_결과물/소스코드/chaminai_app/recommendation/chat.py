"""AI chat embedded in the recommendation page."""
import json
import os

import streamlit as st

from ..ai import ask_gemini
from ..config import FUEL_CHOICES, RECOMMEND_CHAT_SYSTEM_NOTE

from .core import build_recommend_summary, recommend_cars
from .data import CAR_SEGMENTS, ORIGIN_CHOICES, REGIONS

def extract_reco_conditions(user_msg: str, history_text: str) -> dict:
    """(추천 시스템 안의 상담 챗봇 전용) 대화 속 메시지가 차량 추천 요청인지 판단하고,
    언급된 조건(지역·출퇴근거리·예산·국산차수입차·선호크기·선호연료)을 뽑아낸다.
    FAQ성 질문/잡담이면 in_scope=False 를 반환해서, 이 채팅창은 답하지 않고 다른 메뉴로 안내하게 한다."""
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_KEY") or "").strip()
    if not api_key:
        return {"in_scope": True}
    try:
        from google import genai
    except ImportError:
        return {"in_scope": True}

    prompt = (
        "너는 '자동차 추천 시스템' 챗봇의 의도 분석기다. 사용자 메시지를 분석해서 JSON 하나만 "
        "출력해라 (설명이나 코드블록 없이 JSON 텍스트만).\n\n"
        '{"in_scope":<true|false>,"region":<지역명|null>,"commute_km":<편도 출퇴근 거리(km)|null>,'
        '"annual_km":<연간 주행거리(km, 명시된 경우만)|null>,"budget_manwon":<예산 상한(만원)|null>,'
        '"origin_pref":<"국산차"|"수입차"|null>,"size_pref":[<언급된 차량 크기만>],"fuel_pref":[<언급된 연료만>]}\n\n'
        "in_scope 는 차량 추천/구매 관련 요청(조건 언급, 추천 요청 등)이면 true, 보증·정비·멤버십 등 "
        "FAQ성 질문이거나 자동차와 무관한 잡담이면 false 로 판단해라. 언급 안 된 값은 null "
        "(리스트는 빈 리스트)로 둬라. '왕복 30km'처럼 왕복으로 말하면 commute_km 는 그 절반(편도) 값으로 넣어라.\n\n"
        f"사용 가능한 지역명: {REGIONS}\n사용 가능한 차량 크기: {CAR_SEGMENTS}\n사용 가능한 연료: {FUEL_CHOICES}\n\n"
        f"최근 대화:\n{history_text}\n\n사용자 메시지: {user_msg}"
    )
    try:
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        text = (resp.text or "").strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(text)
        data.setdefault("in_scope", True)
        return data
    except Exception:
        return {"in_scope": True}


def reco_chat_answer(user_msg: str) -> str:
    """추천 시스템 안의 상담 챗봇 답변 생성기. 조건을 뽑아 recommend_cars 로 계산하고,
    상위 3대 표 + AI의 부드러운 설명을 합쳐서 답변 문자열을 만든다."""
    history = st.session_state.get("reco_chat_msgs", [])[-6:]
    history_text = "\n".join(f"{m['role']}: {m['content'][:200]}" for m in history)

    cond = extract_reco_conditions(user_msg, history_text)

    if not cond.get("in_scope", True):  # 추천과 무관한 질문(FAQ/잡담)이면 안내만 하고 끝

        prompt = (
            f"{RECOMMEND_CHAT_SYSTEM_NOTE}\n\n[최근 대화]\n{history_text}\n\n[사용자 메시지]\n{user_msg}"
        )
        return ask_gemini(prompt)

    region = cond.get("region") if cond.get("region") in REGIONS else "서울"
    commute_km = cond.get("commute_km")
    annual_km = cond.get("annual_km")
    if not annual_km:
        annual_km = max(commute_km * 2 * 260, 1000) if commute_km else 12000
    budget_manwon = cond.get("budget_manwon") or 3000
    price_max = int(budget_manwon) * 10_000
    origin_pref = cond.get("origin_pref") if cond.get("origin_pref") in ORIGIN_CHOICES else "전체"
    size_pref = [s for s in (cond.get("size_pref") or []) if s in CAR_SEGMENTS]
    fuel_pref = [f for f in (cond.get("fuel_pref") or []) if f in FUEL_CHOICES]

    df = recommend_cars(annual_km, region, 0, price_max, fuel_pref, origin_pref, size_pref, 40, 40, 20)
    if df.empty:
        return "조건에 맞는 차량을 찾지 못했어요 :( 예산이나 선호 조건을 조금 다르게 말씀해 주시겠어요?"

    profile = (
        f"{region} 거주 · 연간 약 {annual_km:,}km 주행 · 예산 {price_max:,}원 이하 · {origin_pref} · "
        f"선호크기 {', '.join(size_pref) if size_pref else '전체'} · "
        f"선호연료 {', '.join(fuel_pref) if fuel_pref else '전체'}"
    )
    table = ["| 순위 | 차량 | 연료 | 연간 연료비 | 실구매가 | 종합점수 |", "|---|---|---|---|---|---|"]
    for i, row in df.head(3).iterrows():
        table.append(
            f"| {i+1} | {row['브랜드']} {row['모델명']} | {row['연료']} | "
            f"{row['annual_fuel_cost']:,.0f}원 | {row['effective_price']:,.0f}원 | {row['종합점수']:.1f}점 |"
        )
    summary = build_recommend_summary(profile, df)
    explanation = ask_gemini(
        f"{RECOMMEND_CHAT_SYSTEM_NOTE}\n\n"
        "아래는 사용자 조건에 맞춰 계산한 추천 차량 상위 목록이다. 1위 차량이 왜 "
        "적합한지 부드럽고 친절한 상담원 말투로 3~4문장 설명해줘. 숫자에 근거해서만 말하고, "
        "언급 안 된 조건은 기본값(가정)을 썼다는 점을 한 번 짚어줘.\n\n" + summary
    )

    # 위쪽 조건 입력 화면의 추천 카드에도 같은 결과를 반영해준다
    st.session_state["reco_result"] = df
    st.session_state["reco_profile"] = profile

    return (
        f"네, 확인해드릴게요 :) **조건: {profile}**\n\n" + "\n".join(table) + f"\n\n{explanation}\n\n"
        "위쪽 추천 카드에도 결과를 반영해 놨어요. 조건을 더 정확히 입력하고 싶으면 위 칸에서 직접 바꿔보셔도 돼요."
    )


def render_reco_chatbot():
    """추천 폼(render_recommend_form) 위쪽에 들어가는 미니 상담 채팅창을 그린다.
    AI 챗봇 메뉴의 대화기록과는 완전히 별개로 session_state["reco_chat_msgs"] 에 따로 저장한다."""
    if "reco_chat_msgs" not in st.session_state:
        st.session_state["reco_chat_msgs"] = []

    for m in st.session_state["reco_chat_msgs"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    user_msg = st.chat_input(
        "AI 상담사한테 추천받기 (예: 예산을 낮추면 어떤 차가 좋아요?)", key="reco_chat_input",
    )
    if user_msg:
        st.session_state["reco_chat_msgs"].append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.markdown(user_msg)
        with st.chat_message("assistant"):
            with st.spinner("답변을 준비하고 있어요..."):
                reply = reco_chat_answer(user_msg)
            st.markdown(reply)
        st.session_state["reco_chat_msgs"].append({"role": "assistant", "content": reply})

    if len(st.session_state["reco_chat_msgs"]) > 1:
        if st.button("상담 대화 초기화", key="reco_chat_clear"):
            st.session_state["reco_chat_msgs"] = []
            st.rerun()


@st.dialog("AI 상담사 — 차량 추천", width="large")
def _reco_chat_dialog():
    """render_reco_chatbot() 을 팝업(모달) 창 안에 그대로 그려서, 채팅방처럼 열고 닫을 수 있게 한다."""
    render_reco_chatbot()
