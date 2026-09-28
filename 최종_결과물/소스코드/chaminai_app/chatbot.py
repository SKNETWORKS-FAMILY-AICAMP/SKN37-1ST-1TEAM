"""General AI chatbot page."""
import json
import os

import streamlit as st
import db

from .ai import ask_gemini
from .config import CHATBOT_SYSTEM_NOTE, FUEL_CHOICES, GEMINI_MODEL
from .recommendation.data import REGIONS
from .recommendation.core import build_recommend_summary, recommend_cars

def _recent_chat_text(n: int = 6) -> str:
    """최근 대화 n개를 "역할: 내용" 형태의 짧은 텍스트로 합쳐서 반환한다.
    AI에게 프롬프트를 보낼 때 "지금까지 무슨 얘기를 나눴는지" 맥락으로 함께 넣어준다."""
    msgs = st.session_state.get("chat_msgs", [])[-n:]
    return "\n".join(f"{m['role']}: {m['content'][:200]}" for m in msgs)


def classify_chat_intent(user_msg: str, history_text: str) -> dict:
    """사용자 메시지를 recommend / faq / general 중 하나로 분류하고,
    recommend 면 대화에서 언급된 조건(주행거리·지역·예산·연료)까지 함께 뽑아낸다.
    (AI에게 "JSON 형식으로만 답해줘"라고 프롬프트로 요청한 뒤, 그 결과를 json.loads로 파싱한다)"""
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_KEY") or "").strip()
    if not api_key:
        return {"intent": "general"}
    try:
        from google import genai
    except ImportError:
        return {"intent": "general"}

    prompt = (
        "사용자 메시지를 분석해서 의도를 아래 중 하나로 분류하고, JSON 하나만 출력해라 "
        "(설명이나 코드블록 없이 JSON 텍스트만).\n\n"
        "- \"recommend\": 차량 구매/추천을 원하는 경우 (예: 차 추천해줘, 전기차 살까 고민, 연비 좋은 차 뭐있어)\n"
        "- \"faq\": 현대차·기아차 이용 중 궁금한 점 (보증, 정비, 충전, 멤버십 등)\n"
        "- \"general\": 그 외 일반 대화/질문\n\n"
        "recommend 인 경우 대화 속에서 실제 언급된 값만 채우고, 언급 안 됐으면 null(연료는 빈 리스트):\n"
        '{"intent":"recommend","annual_km":<int|null>,"region":<지역명|null>,'
        '"budget_manwon":<int|null>,"fuel_pref":[<언급된 연료만>]}\n'
        'faq 면 {"intent":"faq"}, general 이면 {"intent":"general"}\n\n'
        f"사용 가능한 지역명: {REGIONS}\n사용 가능한 연료: {FUEL_CHOICES}\n\n"
        f"최근 대화:\n{history_text}\n\n사용자 메시지: {user_msg}"
    )
    try:
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        text = (resp.text or "").strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(text)
    except Exception:
        return {"intent": "general"}


def chatbot_answer(user_msg: str) -> str:
    """사용자가 챗봇에 메시지를 보내면 실제 답변을 만들어주는 함수.
    1) classify_chat_intent 로 의도(recommend/faq/general) 파악
    2) 의도에 맞춰 다른 방식으로 답을 계산해서 돌려준다."""
    history_text = _recent_chat_text()
    route = classify_chat_intent(user_msg, history_text)
    intent = route.get("intent", "general")

    if intent == "recommend":  # "차 추천해줘" 같은 요청 → 추천 로직(recommend_cars) 실행
        annual_km = route.get("annual_km") or 12000
        region = route.get("region") if route.get("region") in REGIONS else "서울"
        budget = (route.get("budget_manwon") or 3000) * 10_000
        fuel_pref = [f for f in (route.get("fuel_pref") or []) if f in FUEL_CHOICES]

        df = recommend_cars(annual_km, region, 0, budget, fuel_pref, "전체", [], 40, 40, 20)
        if df.empty:
            return "조건에 맞는 차량을 찾지 못했어요. 예산이나 선호 연료를 다르게 말씀해 주시겠어요?"

        profile = (
            f"연간 {annual_km:,}km · {region} 거주 · 예산 {budget:,}원 · "
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
            "아래는 사용자 조건에 맞춰 계산한 추천 차량 상위 목록이다. "
            "1위 차량이 왜 적합한지 3~4문장으로 친절히 설명해줘. 숫자에 근거해서만 말해줘.\n\n" + summary
        )
        return (
            f"**조건: {profile}**\n\n" + "\n".join(table) + f"\n\n{explanation}\n\n"
            "조건을 더 세밀하게 조정하고 싶으면 '자동차 추천 시스템' 메뉴도 이용해 보세요."
        )

    if intent == "faq":  # 17개 브랜드 이용 관련 질문 → DB에서 비슷한 FAQ를 찾아 근거로 답변
        related = db.find_related_faqs(user_msg, limit=5)
        if related:
            context = "\n\n".join(
                f"[{i}] 질문: {r['question']}\n답변: {r['answer']}\n(출처: {r['source']})"
                for i, r in enumerate(related, 1)
            )
        else:
            context = "(관련 FAQ를 찾지 못했음)"
        prompt = (
            "너는 현대·기아·BMW·벤츠 등 17개 브랜드 FAQ 안내 챗봇이다. 아래 [참고 FAQ]에 관련 내용이 있으면 "
            "그것을 우선 근거로 답하고, 없으면 일반적인 자동차 지식으로 최대한 도움이 되게 답하되 "
            "답변 끝에 '※ 공식 FAQ에는 없는 내용이라 참고용으로만 봐주세요.' 를 붙여라. "
            "정확한 수치(가격·기간·전화번호 등)는 근거 없으면 추측하지 말고 확인 방법을 안내해라.\n\n"
            f"[참고 FAQ]\n{context}\n\n[사용자 질문]\n{user_msg}"
        )
        return ask_gemini(prompt)

    # intent 가 "general"(그 외 일반 대화)이면 그냥 AI에게 자유롭게 답변을 맡긴다
    return ask_gemini(f"{CHATBOT_SYSTEM_NOTE}\n\n최근 대화:\n{history_text}\n\n사용자: {user_msg}")


def render_chatbot_menu():
    """AI 챗봇 화면 전체를 그린다: 대화 기록 표시 → 입력창 → 답변 생성 → 대화 초기화 버튼."""
    st.header("AI 챗봇")
    st.caption("차량 추천, 17개 브랜드 FAQ, 그 외 자동차 관련 궁금증까지 편하게 물어보세요.")

    # session_state["chat_msgs"] 에 지금까지의 대화 목록을 저장해둔다.
    # 처음 들어오면 이 목록이 없으므로, 인삿말 1개로 시작한다.
    if "chat_msgs" not in st.session_state:
        st.session_state["chat_msgs"] = [
            {"role": "assistant",
             "content": "안녕하세요! 차량 추천이나 17개 브랜드 FAQ, 그 외 궁금한 점을 편하게 물어보세요"}
        ]

    # 지금까지 저장된 대화를 화면에 순서대로 그린다 (새로고침될 때마다 이 for문이 다시 실행됨)
    for m in st.session_state["chat_msgs"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    user_msg = st.chat_input("메시지를 입력하세요 (예: 서울 사는데 연간 만km 타는 전기차 추천해줘)")
    if user_msg:  # 사용자가 메시지를 입력하고 엔터를 눌렀을 때만 아래 코드 실행
        st.session_state["chat_msgs"].append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.markdown(user_msg)
        with st.chat_message("assistant"):
            with st.spinner("생각하는 중..."):  # AI 응답을 기다리는 동안 로딩 표시
                reply = chatbot_answer(user_msg)
            st.markdown(reply)
        st.session_state["chat_msgs"].append({"role": "assistant", "content": reply})

    if len(st.session_state["chat_msgs"]) > 1:
        if st.button("대화 초기화"):
            st.session_state["chat_msgs"] = []
            st.rerun()
