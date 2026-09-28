import streamlit as st

def render_calc_menu():
    st.header("🧮 자동차 월 납입금 계산기")
    st.caption("차량 가격, 선수금, 할부 금리 및 기간에 따른 월 납입금과 원리금 상환 일정을 계산합니다.")

    col1, col2 = st.columns(2)

    with col1:
        car_price_manwon = st.number_input("차량 가격 (만원)", min_value=100, max_value=30000, value=3500, step=100)
        advance_pay_manwon = st.number_input("선수금/보증금 (만원)", min_value=0, max_value=car_price_manwon, value=500, step=50)
        interest_rate = st.number_input("연 할부 금리 (%)", min_value=0.0, max_value=20.0, value=4.5, step=0.1)
        months = st.selectbox("할부 기간 (개월)", options=[12, 24, 36, 48, 60, 72], index=3)

    # 원리금균등상환 계산 공식
    loan_principal = (car_price_manwon - advance_pay_manwon) * 10_000  # 원
    monthly_rate = (interest_rate / 100) / 12

    if loan_principal <= 0:
        monthly_payment = 0
        total_interest = 0
        total_payment = 0
    elif monthly_rate == 0:
        monthly_payment = loan_principal / months
        total_interest = 0
        total_payment = loan_principal
    else:
        monthly_payment = loan_principal * (monthly_rate * (1 + monthly_rate)**months) / (((1 + monthly_rate)**months) - 1)
        total_payment = monthly_payment * months
        total_interest = total_payment - loan_principal

    with col2:
        st.subheader("📌 계산 결과 요약")
        st.metric("월 예상 납입금", f"{monthly_payment:,.0f} 원")
        st.write("---")
        st.write(f"- **대출 원금 (차량가 - 선수금):** {loan_principal:,.0f} 원")
        st.write(f"- **총 이자 비용:** {total_interest:,.0f} 원")
        st.write(f"- **총 납입 금액 (원금 + 이자):** {total_payment:,.0f} 원")

    if loan_principal > 0:
        st.divider()
        st.subheader("📅 월별 상환 스케줄 (상위 12개월)")
        
        schedule = []
        balance = loan_principal
        for m in range(1, months + 1):
            interest_m = balance * monthly_rate
            principal_m = monthly_payment - interest_m
            balance -= principal_m
            if m <= 12 or m == months:
                schedule.append({
                    "회차": f"{m}회차",
                    "납입금": f"{monthly_payment:,.0f}원",
                    "원금": f"{principal_m:,.0f}원",
                    "이자": f"{interest_m:,.0f}원",
                    "대출 잔액": f"{max(balance, 0):,.0f}원"
                })
        
        st.table(schedule)