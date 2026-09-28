import streamlit as st
from ai_service import ask_gemini, classify_chat_intent
from db.faq import find_related_faqs

CHATBOT_SYSTEM_NOTE = (
    "너는 '자동차 추천 시스템 및 기업FAQ 조회' 사이트의 AI 챗봇이다. "
    "차량 추천이나 FAQ 관련 질문에 친절하게 답해줘."
)

def _recent_chat_text(n: int = 6) -> str:
    msgs = st.session_state.get("chat_msgs", [])[-n:]
    return "\n".join(f"{m['role']}: {m['content'][:200]}" for m in msgs)

def chatbot_answer(user_msg: str, regions: list, recommend_fn) -> str:
    history_text = _recent_chat_text()
    route = classify_chat_intent(user_msg, history_text, regions)
    intent = route.get("intent", "general")

    if intent == "recommend":
        annual_km = route.get("annual_km") or 12000
        region = route.get("region") if route.get("region") in regions else "서울"
        budget = (route.get("budget_manwon") or 3000) * 10_000
        fuel_pref = route.get("fuel_pref") or []

        df = recommend_fn(annual_km, region, 0, budget, fuel_pref, "전체", [], 40, 40, 20)
        if df.empty:
            return "조건에 맞는 차량을 찾지 못했어요. 예산이나 선호 연료를 다르게 말씀해 주시겠어요?"

        profile = f"연간 {annual_km:,}km · {region} 거주 · 예산 {budget:,}원"
        table = ["| 순위 | 차량 | 연료 | 연간 연료비 | 실구매가 | 종합점수 |", "|---|---|---|---|---|---|"]
        for i, row in df.head(3).iterrows():
            table.append(
                f"| {i+1} | {row['브랜드']} {row['모델명']} | {row['연료']} | "
                f"{row['annual_fuel_cost']:,.0f}원 | {row['effective_price']:,.0f}원 | {row['종합점수']:.1f}점 |"
            )
        explanation = ask_gemini(f"추천 결과 이유 설명해줘:\n{df.head(3).to_string()}")
        return f"**조건: {profile}**\n\n" + "\n".join(table) + f"\n\n{explanation}"

    if intent == "faq":
        related = find_related_faqs(user_msg, limit=5)
        context = "\n\n".join(f"[{i}] 질문: {r['question']}\n답변: {r['answer']}" for i, r in enumerate(related, 1)) if related else "(관련 FAQ 없음)"
        return ask_gemini(f"참고 FAQ:\n{context}\n\n질문: {user_msg}")

    return ask_gemini(f"{CHATBOT_SYSTEM_NOTE}\n\n최근 대화:\n{history_text}\n\n사용자: {user_msg}")

def render_chatbot_menu(regions: list, recommend_fn):
    st.header("AI 챗봇")
    st.caption("차량 추천, 17개 브랜드 FAQ, 기타 자동차 관련 질문을 물어보세요.")

    if "chat_msgs" not in st.session_state:
        st.session_state["chat_msgs"] = [
            {"role": "assistant", "content": "안녕하세요! 궁금한 점을 편하게 물어보세요."}
        ]

    for m in st.session_state["chat_msgs"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    user_msg = st.chat_input("메시지를 입력하세요")
    if user_msg:
        st.session_state["chat_msgs"].append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.markdown(user_msg)
        with st.chat_message("assistant"):
            with st.spinner("생각하는 중..."):
                reply = chatbot_answer(user_msg, regions, recommend_fn)
            st.markdown(reply)
        st.session_state["chat_msgs"].append({"role": "assistant", "content": reply})