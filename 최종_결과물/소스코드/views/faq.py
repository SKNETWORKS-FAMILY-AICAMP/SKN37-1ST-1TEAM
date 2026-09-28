import streamlit as st
from db.faq import FAQ_BRAND_TABLES, get_categories, get_faqs
from ai_service import ask_gemini

def render_faq_menu():
    st.header("🏢 17개 브랜드 기업 FAQ 조회")
    st.caption("원하시는 자동차 브랜드의 주요 FAQ 검색 및 카테고리별 질문을 확인하세요.")

    col1, col2, col3 = st.columns([2, 2, 3])
    
    with col1:
        brand_list = ["전체"] + list(FAQ_BRAND_TABLES.keys())
        selected_brand = st.selectbox("브랜드 선택", options=brand_list, index=0)
        source = None if selected_brand == "전체" else selected_brand

    with col2:
        categories = ["전체"] + get_categories(source=source)
        selected_cat = st.selectbox("카테고리 선택", options=categories, index=0)

    with col3:
        search_kw = st.text_input("검색어 입력 (질문 또는 답변 키워드)", value="")

    # 데이터 조회
    faqs = get_faqs(keyword=search_kw, category=selected_cat, source=source)

    st.write(f"총 **{len(faqs):,}** 건의 FAQ가 검색되었습니다.")
    st.divider()

    if not faqs:
        st.info("검색 조건에 일치하는 FAQ가 없습니다.")
        return

    # FAQ 목록 (st.expander 활용)
    for idx, faq in enumerate(faqs[:50], 1):  # 최대 50개까지 표시
        title = f"[{faq['source']}] [{faq['category'] or '일반'}] {faq['question']}"
        with st.expander(f"{idx}. {title}"):
            st.markdown(f"**답변:**\n{faq['answer']}")
            
            # FAQ 내용에 대해 AI 질문 연동
            if st.button(f"🤖 이 내용 AI에게 더 구체적으로 물어보기", key=f"faq_ai_btn_{idx}"):
                with st.spinner("AI 분석 중..."):
                    prompt = f"다음 자동차 관련 FAQ 내용에 대해 사용자가 더 이해하기 쉽게 추가 설명을 제공해줘.\n\n질문: {faq['question']}\n답변: {faq['answer']}"
                    reply = ask_gemini(prompt)
                    st.success("AI 추가 설명:")
                    st.write(reply)

    if len(faqs) > 50:
        st.caption("🔍 검색 결과가 50개를 초과하여 상위 50개만 표시합니다. 키워드를 정밀하게 입력해주세요.")