"""Recommendation selection/form UI and result visualizations."""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st

from ..ai import ask_gemini
from ..config import *
from ..ui_assets import _home_card
from ..faq import _faq_source_for_brand
from .chat import _reco_chat_dialog
from .data import *
from .core import (
    _mini_score_ring_html,
    build_reco_reason,
    build_recommend_summary,
    reco_score_breakdown,
    recommend_cars,
)
def render_recommend_select():
    """추천 시스템 기본 화면: 아직 사이드바에서 추천받기/통계확인 중 아무것도 안 골랐을 때 보여주는
    카드 2장짜리 화면. 사이드바에는 더 이상 "선택 화면"이라는 라디오 항목이 없지만,
    "자동차 추천 시스템" 버튼을 누르면(=아직 하위 항목을 안 골랐으면) 이 화면이 대신 뜬다."""
    hero = (
        '<div class="home-hero"><h1>사용자 특성별 자동차 추천 시스템</h1>'
        "<p>실제 DB 데이터(차량 스펙·지역별 유가·전기차 보조금·인프라 현황) 기준으로 추천해드려요.</p></div>"
    )
    cards = ""
    for key, info in RECO_VIEW_INFO.items():
        cards += _home_card(f"?menu=recommend&amp;view={info['query']}", info["kind"],
                            info["tag"], info["title"], info["desc"], info["cta"],
                            icon_html=info.get("icon", ""))
    st.markdown(HOME_CSS + hero + '<div class="home-grid">' + cards + "</div>", unsafe_allow_html=True)


def render_recommend_menu():
    """사이드바 "자동차 추천 시스템" 메뉴의 진입점.
    사이드바 하위 라디오(추천받기 / 통계확인)에서 아직 아무것도 안 골랐으면 선택 화면을,
    골랐으면 해당 화면을 보여준다."""
    view = st.session_state.get("reco_view")
    if view not in RECO_VIEW_INFO:
        render_recommend_select()
        return
    info = RECO_VIEW_INFO[view]
    st.header(f"사용자 특성별 자동차 추천 시스템 — {info['title']}")
    if view == "form":
        render_recommend_form()      # ── (추천받기) 사용자가 조건을 입력하고 추천받는 화면
    else:
        render_recommend_stats()     # ── (통계 확인) 조회 조건을 골라서 통계만 보는 화면


def render_recommend_form():
    """[추천 받기] 화면: 나이/지역/예산 등 입력 → 추천 계산 → 상위 차량 카드로 결과 표시."""
    st.caption(
        "지역·출퇴근 거리·가격대·국산차/수입차·선호 차량 크기를 "
        "바탕으로 연료비·구매부담·전기차 인프라를 종합해 실제 데이터 기준으로 추천합니다."
    )

    # 채팅창을 화면에 바로 펼쳐두는 대신, 버튼을 누르면 팝업(모달)으로 열리게 한다
    # (실제 클릭 이벤트를 받아야 하는 진짜 st.button이라 HTML 아이콘은 못 넣고,
    #  대신 스트림릿이 기본 제공하는 아이콘(Material Symbols)을 버튼 안에 직접 넣는다)
    unread = len(st.session_state.get("reco_chat_msgs", []))
    chat_label = "AI 상담사에게 물어보기" + (f" ({unread}개 대화 중)" if unread > 1 else "")
    if st.button(chat_label, key="open_reco_chat", type="primary",
                 icon=":material/android:", use_container_width=True):
        _reco_chat_dialog()
    st.divider()

    # ---- 즐겨찾기한 차량 (세션 동안 유지) ----------------------------------------------
    st.session_state.setdefault("favorites", {})
    favorites = st.session_state["favorites"]
    with st.expander(f"즐겨찾기한 차량 ({len(favorites)}건)", expanded=False):
        if not favorites:
            st.caption("추천 카드에서 '☆ 즐겨찾기' 버튼을 누르면 여기에 저장됩니다.")
        else:
            fav_df = pd.DataFrame([
                {
                    "브랜드": r["브랜드"], "모델명": r["모델명"], "세그먼트": r["세그먼트"], "연료": r["연료"],
                    "연간 연료비(원)": r["annual_fuel_cost"], "실구매가(원)": r["effective_price"],
                    "종합점수": r["종합점수"],
                }
                for r in favorites.values()
            ])
            st.dataframe(fav_df, hide_index=True)
            st.download_button(
                "즐겨찾기 CSV로 다운로드", data=fav_df.to_csv(index=False).encode("utf-8-sig"),
                file_name="즐겨찾기_차량.csv", mime="text/csv", key="download_fav_csv",
            )
            if st.button("즐겨찾기 전체 비우기", key="clear_favorites"):
                st.session_state["favorites"] = {}
                st.rerun()

    st.subheader("내 정보 입력")
    # st.columns(2) 로 화면을 가로 2칸으로 나눠서 입력창을 나란히 배치한다
    c1, c2 = st.columns(2)
    region = c1.selectbox("거주 지역", REGIONS)
    commute_km = c2.number_input("편도 출퇴근 거리 (km)", min_value=0, max_value=100, value=10, step=1)

    origin_pref = st.selectbox("국산차 / 수입차", ORIGIN_CHOICES)

    pc1, pc2 = st.columns(2)
    price_min = pc1.number_input("최소 가격대 (만원)", min_value=0, max_value=100_000, value=2000, step=100)
    price_max = pc2.number_input("최대 가격대 (만원)", min_value=0, max_value=100_000, value=5000, step=100)
    if price_min > price_max:
        price_min, price_max = price_max, price_min  # 사용자가 반대로 입력해도 자동으로 바로잡음
    price_min, price_max = price_min * 10_000, price_max * 10_000

    size_pref = st.multiselect("선호 차량 크기", CAR_SEGMENTS, placeholder="선택 안 함 (전체)")
    fuel_pref = st.multiselect(
        "선호 연료 (비워두면 전체 연료 대상)", FUEL_CHOICES, placeholder="선택 안 함 (전체)",
    )

    # 우선순위(가중치)는 연료비:가격:인프라 = 40:40:20 으로 고정 (사용자가 직접 조정하지 않음)
    w_fuel, w_price, w_infra = 40, 40, 20

    # 편도 출퇴근 거리를 왕복·연간(약 260 근무일) 기준 연간 주행거리로 환산 (샘플 가정)
    annual_km = max(commute_km * 2 * 260, 1000)

    if st.button("차량 추천받기", type="primary"):  # 버튼을 누른 순간에만 아래 계산을 실행
        result = recommend_cars(
            annual_km, region, price_min, price_max, fuel_pref, origin_pref, size_pref,
            w_fuel, w_price, w_infra,
        )
        profile = (
            f"{region} 거주 · 편도 출퇴근 {commute_km}km(연간 약 {annual_km:,}km) · "
            f"가격대 {price_min:,}~{price_max:,}원 · {origin_pref} · "
            f"선호크기 {', '.join(size_pref) if size_pref else '전체'} · "
            f"선호연료 {', '.join(fuel_pref) if fuel_pref else '전체'} · "
            f"중요도(연료비:가격:인프라)={w_fuel}:{w_price}:{w_infra}"
        )
        st.session_state["reco_result"] = result   # 다음에 화면이 다시 그려져도 결과가 안 사라지게 저장
        st.session_state["reco_profile"] = profile
        st.session_state["reco_weights"] = (w_fuel, w_price, w_infra)  # 추천 이유 문구가 그때의 가중치를 그대로 쓰도록 같이 저장

    # 버튼을 누른 적이 있으면(session_state 에 결과가 있으면) 그 결과를 계속 화면에 보여준다
    result = st.session_state.get("reco_result")
    if result is not None and not result.empty:
        profile = st.session_state.get("reco_profile", "")
        st.caption(f"조건: {profile}")
        st.divider()

        # 차량 하나를 여러 탭/랭킹에서도 같은 차로 알아볼 수 있게 만드는 고유 id
        # (즐겨찾기·비교선택 모두 이 id를 기준으로 저장한다)
        def _car_id(row) -> str:
            return f"{row['브랜드']}|{row['모델명']}|{row['세그먼트']}|{row['연료']}"

        st.session_state.setdefault("favorites", {})     # car_id -> 저장 당시 row(dict)
        st.session_state.setdefault("compare_selected", {})  # car_id -> 저장 당시 row(dict), 비교용 (최대 3대)

        def _render_reco_card(col, rank, row, key_ns: str, show_actions: bool = False):
            badge = "1위" if rank == 0 else f"{rank+1}위"
            car_id = _car_id(row)
            with col:
                with st.container(border=True):
                    st.markdown(f"**{badge} · {row['브랜드']} {row['모델명']}** ({row['세그먼트']} · {row['연료']})")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("연간 예상 연료비", f"{row['annual_fuel_cost']:,.0f}원")
                    m2.metric("실구매가", f"{row['effective_price']:,.0f}원")
                    m3.metric("종합점수", f"{row['종합점수']:.1f}점")

                    # 연료비/가격/인프라/종합 점수(0~100)를 작은 원형 게이지 4개로 보여준다 (종합점수를 맨 앞에)
                    g1, g2, g3, g4 = st.columns(4)
                    for gcol, glabel, gvalue, gcolor in (
                        (g1, "종합", row["종합점수"], "#8a7fd6"),
                        (g2, "연료비", row["연료비점수"], "#f06a6a"),
                        (g3, "가격", row["가격점수"], "#4fc3c3"),
                        (g4, "인프라", row["인프라점수"], "#f5a95f"),
                    ):
                        with gcol:
                            st.markdown(_mini_score_ring_html(gvalue, gcolor, glabel), unsafe_allow_html=True)

                    used_w_fuel, used_w_price, used_w_infra = st.session_state.get(
                        "reco_weights", (w_fuel, w_price, w_infra)
                    )
                    bd = reco_score_breakdown(row, used_w_fuel, used_w_price, used_w_infra)
                    st.caption(
                        f"연료비 {bd['fuel']:.1f}점 + 가격 {bd['price']:.1f}점 + "
                        f"인프라 {bd['infra']:.1f}점 = 종합점수 {bd['total']:.1f}점"
                    )
                    st.caption("추천 이유: " + build_reco_reason(row, used_w_fuel, used_w_price, used_w_infra, result))

                    # ---- 즐겨찾기 + 비교선택 (모든 탭 카드에 공통으로 표시) ----
                    a1, a2 = st.columns(2)
                    is_fav = car_id in st.session_state["favorites"]
                    fav_label = "★ 즐겨찾기 해제" if is_fav else "☆ 즐겨찾기"
                    if a1.button(fav_label, key=f"fav_{key_ns}_{rank}_{car_id}", use_container_width=True):
                        if is_fav:
                            st.session_state["favorites"].pop(car_id, None)
                        else:
                            st.session_state["favorites"][car_id] = row.to_dict()
                        st.rerun()

                    # 비교선택 버튼은 "종합점수 순위" 탭에서만 보여준다.
                    # (같은 차가 탭마다 중복 렌더링되므로, 위젯 key 충돌을 피하고 헷갈리지 않게 하나의 탭에서ㄴ만 고르게 함)
                    if show_actions:
                        is_cmp = car_id in st.session_state["compare_selected"]
                        cmp_label = "비교 해제" if is_cmp else "비교에 추가"
                        cmp_disabled = (not is_cmp) and len(st.session_state["compare_selected"]) >= 3
                        if a2.button(cmp_label, key=f"cmp_{key_ns}_{rank}_{car_id}",
                                     use_container_width=True, disabled=cmp_disabled):
                            if is_cmp:
                                st.session_state["compare_selected"].pop(car_id, None)
                            else:
                                st.session_state["compare_selected"][car_id] = row.to_dict()
                            st.rerun()
                        if cmp_disabled:
                            a2.caption("최대 3대까지 비교 가능해요")
                    else:
                        a2.caption("비교선택은 '종합점수 순위' 탭에서")

                    # ---- 🏢 같은 브랜드 FAQ 보기 + 🧮 이 차량으로 월납입금계산하기 ----
                    b1, b2 = st.columns(2)
                    faq_source = _faq_source_for_brand(row["브랜드"])
                    if faq_source:
                        if b1.button(f"{row['브랜드']} FAQ 보기", key=f"faq_{key_ns}_{rank}_{car_id}",
                                     use_container_width=True):
                            st.session_state["faq_brand"] = faq_source
                            st.session_state["menu"] = FAQ_MENU
                            st.rerun()
                    else:
                        b1.caption("FAQ 미제공 브랜드")

                    if b2.button("이 차량으로 월납입금 계산하기", key=f"calc_{key_ns}_{rank}_{car_id}",
                                 use_container_width=True):
                        st.session_state["calc_car_price"] = int(round(row["출고가"] / 10_000))
                        st.session_state["menu"] = CALC_MENU
                        st.rerun()

        def _render_reco_grid(df_sorted: "pd.DataFrame", key_ns: str, show_actions: bool = False):
            """순위를 1·2 / 3·4 / 5·6 ... 처럼 2열로 배열해서 보여준다 (상위 10대까지)."""
            top_rows = list(df_sorted.head(10).reset_index(drop=True).iterrows())
            for pair_start in range(0, len(top_rows), 2):
                pair = top_rows[pair_start:pair_start + 2]
                cols = st.columns(2)
                for col, (rank, row) in zip(cols, pair):
                    _render_reco_card(col, rank, row, key_ns, show_actions)

        def _render_reco_chart(df_sorted: "pd.DataFrame", chart_key: str):
            """df_sorted 순서 그대로(상위 10대) 점수 구성 누적 막대그래프를 그린다."""
            used_w_fuel, used_w_price, used_w_infra = st.session_state.get(
                "reco_weights", (w_fuel, w_price, w_infra)
            )
            chart_rows = []
            chart_order = []  # x축 순서를 순위대로 고정 (동명 차량이 있어도 막대가 안 겹치게)
            for rank, (_, row) in enumerate(df_sorted.head(10).iterrows(), start=1):
                bd = reco_score_breakdown(row, used_w_fuel, used_w_price, used_w_infra)
                label = f"{rank}위 {row['브랜드']} {row['모델명']}"
                chart_order.append(label)
                chart_rows.append({"차량": label, "항목": "연료비", "점수": bd["fuel"], "표시값": f"{bd['fuel']:.1f}점"})
                chart_rows.append({"차량": label, "항목": "가격", "점수": bd["price"], "표시값": f"{bd['price']:.1f}점"})
                chart_rows.append({"차량": label, "항목": "인프라", "점수": bd["infra"], "표시값": f"{bd['infra']:.1f}점"})
            chart_df = pd.DataFrame(chart_rows)
            fig = px.bar(
                chart_df, x="차량", y="점수", color="항목", barmode="stack", text="표시값",
                category_orders={"차량": chart_order},
            )
            fig.update_traces(textposition="inside")
            fig.update_layout(
                height=420, margin=dict(l=10, r=10, t=20, b=10), bargap=0.4,
                yaxis_title="종합점수까지 누적된 점수", xaxis_title=None,
            )
            st.plotly_chart(fig, use_container_width=True, key=chart_key)

        # 어떤 점수 기준으로 순위를 볼지 탭으로 나눠서 보여준다 (종합점수 순위가 맨 앞)
        # 탭을 바꾸면 카드 순서뿐 아니라 아래 "점수 구성 그래프"도 그 탭 기준 순서로 같이 바뀐다.
        tab_total, tab_fuel, tab_price = st.tabs(
            ["종합점수 순위", "연료비점수 순위", "가격점수 순위"]
        )
        with tab_total:
            _render_reco_grid(result, "total", show_actions=True)  # result 는 이미 종합점수 내림차순으로 정렬돼 있음
            st.divider()
            st.subheader("점수 구성 그래프 (상위 10대)")
            _render_reco_chart(result, "reco_chart_total")
        with tab_fuel:
            fuel_sorted = result.sort_values("연료비점수", ascending=False)
            _render_reco_grid(fuel_sorted, "fuel", show_actions=False)
            st.divider()
            st.subheader("점수 구성 그래프 (상위 10대)")
            _render_reco_chart(fuel_sorted, "reco_chart_fuel")
        with tab_price:
            price_sorted = result.sort_values("가격점수", ascending=False)
            _render_reco_grid(price_sorted, "price", show_actions=False)
            st.divider()
            st.subheader("점수 구성 그래프 (상위 10대)")
            _render_reco_chart(price_sorted, "reco_chart_price")

        with st.expander("전체 후보 비교표"):
            show_cols = ["브랜드", "모델명", "세그먼트", "연료", "annual_fuel_cost",
                         "effective_price", "infra_score", "종합점수"]
            show = result[show_cols].rename(columns={
                "annual_fuel_cost": "연간 연료비(원)", "effective_price": "실구매가(원)",
                "infra_score": "인프라점수",
            })
            st.dataframe(show, hide_index=True)
            st.download_button(
                "⬇️ 추천 결과 CSV로 다운로드", data=show.to_csv(index=False).encode("utf-8-sig"),
                file_name="차량추천결과.csv", mime="text/csv", key="download_reco_csv",
            )

        st.divider()
        st.subheader("AI 추천 이유 설명")
        if st.button("제미나이에게 추천 이유 물어보기"):
            summary = build_recommend_summary(profile, result)
            prompt = (
                "아래는 자동차 추천 시스템이 실제 데이터로 계산한 상위 후보 목록이다. "
                "1위 차량이 왜 이 사용자에게 적합한지, 2~3위와 비교해서 4~5문장으로 친절하게 설명해줘. "
                "숫자에 근거해서만 설명해줘.\n\n"
                f"{summary}"
            )
            with st.spinner("AI 답변 생성 중..."):
                st.session_state["reco_ai_text"] = ask_gemini(prompt)
        if "reco_ai_text" in st.session_state:
            st.info(st.session_state["reco_ai_text"])

        # ---- 차량 비교 (레이더 차트 + 표) ----------------------------------------------
        st.divider()
        st.subheader("차량 비교")
        compare_map = st.session_state.get("compare_selected", {})
        if len(compare_map) < 2:
            st.caption("위 '종합점수 순위' 탭의 카드에서 차량 2~3대의 '비교에 추가' 버튼을 누르면 여기에 비교 결과가 나타납니다.")
        else:
            compare_rows = list(compare_map.values())[:3]  # 최대 3대까지만 비교
            if len(compare_map) > 3:
                st.caption("※ 최대 3대까지 비교합니다. 먼저 선택한 3대만 표시돼요.")

            # 레이더(스파이더) 차트: 연료비/가격/인프라/종합 점수를 축으로 선형(채우기 없이)으로 겹쳐 그린다
            # 가시성 좋은 고대비 색상(색약 배려 팔레트, Okabe-Ito 기반)만 사용
            RADAR_COLORS = ["#E69F00", "#0072B2", "#009E73"]  # 주황 / 파랑 / 초록
            categories = ["연료비점수", "가격점수", "인프라점수", "종합점수"]
            fig = go.Figure()
            for i, r in enumerate(compare_rows):
                values = [r["연료비점수"], r["가격점수"], r["인프라점수"], r["종합점수"]]
                color = RADAR_COLORS[i % len(RADAR_COLORS)]
                fig.add_trace(go.Scatterpolar(
                    r=values + values[:1], theta=categories + categories[:1],
                    fill="none", mode="lines+markers",
                    line=dict(color=color, width=3), marker=dict(color=color, size=7),
                    name=f"{r['브랜드']} {r['모델명']}",
                ))
            fig.update_layout(
                polar=dict(
                    bgcolor="rgba(0,0,0,0)",
                    radialaxis=dict(visible=True, range=[0, 100], gridcolor="rgba(150,150,150,0.35)"),
                    angularaxis=dict(gridcolor="rgba(150,150,150,0.35)"),
                ),
                height=420, margin=dict(l=30, r=30, t=30, b=30), showlegend=True,
            )
            st.plotly_chart(fig, use_container_width=True, key="compare_radar")

            # 나란히 비교하는 표
            cmp_df = pd.DataFrame([
                {
                    "차량": f"{r['브랜드']} {r['모델명']}", "세그먼트": r["세그먼트"], "연료": r["연료"],
                    "연간 연료비(원)": r["annual_fuel_cost"], "실구매가(원)": r["effective_price"],
                    "연료비점수": r["연료비점수"], "가격점수": r["가격점수"],
                    "인프라점수": r["인프라점수"], "종합점수": r["종합점수"],
                }
                for r in compare_rows
            ])
            st.dataframe(cmp_df, hide_index=True)

            if st.button("비교 선택 초기화", key="clear_compare"):
                st.session_state["compare_selected"] = {}
                st.rerun()
    elif result is not None:
        st.info("조건에 맞는 차량이 없습니다. 예산이나 연료 선호도를 조정해 보세요.")

    st.divider()
    with st.expander("이 화면이 사용하는 실제 데이터 출처"):
        st.markdown(
            f"- **차량 연비/출고가** — DB `car_info` 테이블 ({len(SAMPLE_CARS)}종)\n"
            "- **연료비점수 / 인프라점수 / 실구매가점수** — DB 뷰 `view_car_recommend` "
            "(차량×지역별로 이미 계산되어 있는 점수를 그대로 가져와 씀)\n"
            "- **시도별 주유소 평균가격 / 전기차 보조금 / 등록현황 / 충전소 현황** — "
            "`view_car_recommend` 뷰가 내부적으로 `sido_oil_price` / `electric_car_subsidies` / "
            "`electric_vehicles` / `ev_chargers` 테이블을 조인해서 계산함"
        )

def _ranked_bar(series: "pd.Series", value_label: str, color_scale: str = "Blues"):
    """지역/모델별 값을 정렬된 막대그래프로 (색상=값 크기).
    통계 탭의 여러 항목(주유소가격/보조금 등)이 공통으로 이 함수를 재사용한다."""
    df = series.reset_index()
    df.columns = ["구분", value_label]
    fig = px.bar(
        df, x="구분", y=value_label, color=value_label,
        color_continuous_scale=color_scale, text_auto=".2s",
    )
    fig.update_layout(showlegend=False, coloraxis_showscale=False, height=380,
                       margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)


def _region_bubble_map(series: "pd.Series", value_label: str, color_scale: str = "Blues"):
    """지역별 값을 버블(원 크기·색)로 지도 위에 표시 (근사 좌표 기반)."""
    rows = [
        {"지역": r, value_label: v, "lat": REGION_COORDS[r][0], "lon": REGION_COORDS[r][1]}
        for r, v in series.items() if r in REGION_COORDS
    ]
    if not rows:
        return
    mdf = pd.DataFrame(rows)
    if hasattr(px, "scatter_map"):
        # plotly >= 5.24: 신규 MapLibre 기반 API (scatter_mapbox 대체)
        fig = px.scatter_map(
            mdf, lat="lat", lon="lon", size=value_label, color=value_label,
            color_continuous_scale=color_scale, size_max=38, zoom=5.2,
            center={"lat": 36.3, "lon": 127.8}, hover_name="지역",
            map_style="open-street-map", height=400,
        )
    else:
        # plotly 구버전 호환
        fig = px.scatter_mapbox(
            mdf, lat="lat", lon="lon", size=value_label, color=value_label,
            color_continuous_scale=color_scale, size_max=38, zoom=5.2,
            center={"lat": 36.3, "lon": 127.8}, hover_name="지역",
            mapbox_style="open-street-map", height=400,
        )
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("※ 지도는 시도청 소재지 기준 근사 좌표이며, 원의 크기·색이 클수록 값이 큽니다.")


def render_recommend_stats():
    """[통계 확인] 화면: 볼 통계 종류를 고르면 그 아래에 해당 통계만 보여주는 화면.
    흐름: ① 볼 통계 종류 선택(버튼) → ② 선택한 종류에 맞는 지표·그래프·표를 그리고 → ③ AI 해설 버튼.
    (예전에는 여기에 "조회 조건"(지역/연료/국산·수입 멀티셀렉트) 이 있었는데 삭제함 —
     이제 아래 각 통계는 항상 "전체" 기준으로 보여준다.)"""
    regions_sel = REGIONS
    fuels_sel = FUEL_CHOICES
    origin_sel = ORIGIN_CHOICES[1:]  # ["국산차", "수입차"] — "전체" 통계에선 이 둘을 다 합쳐서 본다

    # 통계 종류 버튼: 여러 개 중 하나를 누르면 그 항목만 선택된 상태(primary)로 표시되고,
    # 아래 if/elif 중 해당 블록만 실행되어 그 통계에 맞는 지표·그래프·표가 그려진다.
    st.write("**통계 종류 선택**")
    st.session_state.setdefault("stats_analysis_pick", STATS_ANALYSIS_OPTIONS[0])
    BTN_PER_ROW = 5
    for row_start in range(0, len(STATS_ANALYSIS_OPTIONS), BTN_PER_ROW):
        row_opts = STATS_ANALYSIS_OPTIONS[row_start:row_start + BTN_PER_ROW]
        cols = st.columns(BTN_PER_ROW)
        for col, opt in zip(cols, row_opts):
            is_sel = st.session_state["stats_analysis_pick"] == opt
            if col.button(opt, key=f"stat_btn_{opt}", use_container_width=True,
                          type="primary" if is_sel else "secondary"):
                st.session_state["stats_analysis_pick"] = opt
                st.rerun()
    analysis = st.session_state["stats_analysis_pick"]
    st.markdown(f"#### {analysis}")

    ai_block = ""  # 맨 아래 "AI 해설" 버튼에 넘겨줄 데이터 텍스트 (각 분기에서 채워짐)

    if analysis == STATS_ANALYSIS_GAS:  # ---- 지역별 주유소 평균가격 ----
        price_view = st.radio("연료 종류", list(GAS_PRICE_BASE.keys()), horizontal=True, key="stats_fuel_pick")
        price_series = pd.Series(
            {r: gas_price(price_view, r) for r in regions_sel}, name=f"{price_view}(원/L)"
        ).sort_values(ascending=False)
        m1, m2 = st.columns(2)
        m1.metric("선택 지역 평균가격", f"{price_series.mean():,.0f}원")
        m2.metric("최고-최저 지역 차이", f"{price_series.max() - price_series.min():,.0f}원")
        c1, c2 = st.columns([3, 2])
        with c1:
            _ranked_bar(price_series, f"{price_view}(원/L)", color_scale="OrRd")
        with c2:
            _region_bubble_map(price_series, f"{price_view}(원/L)", color_scale="OrRd")
        st.dataframe(price_series.reset_index().rename(columns={"index": "지역"}), hide_index=True)
        ai_block = f"[선택 지역 {price_view} 가격]\n{price_series.to_csv()}"

    elif analysis == STATS_ANALYSIS_SUBSIDY:  # ---- 전기차 보조금 ----
        subsidy_series = pd.Series(
            {r: EV_SUBSIDY.get(r, 0) for r in regions_sel}, name="보조금(원)"
        ).sort_values(ascending=False)
        m1, m2 = st.columns(2)
        m1.metric("선택 지역 평균 보조금", f"{subsidy_series.mean():,.0f}원")
        m2.metric("최고 지역", f"{subsidy_series.idxmax()} ({subsidy_series.max():,.0f}원)")
        c1, c2 = st.columns([3, 2])
        with c1:
            _ranked_bar(subsidy_series, "보조금(원)", color_scale="Greens")
        with c2:
            _region_bubble_map(subsidy_series, "보조금(원)", color_scale="Greens")
        st.dataframe(subsidy_series.reset_index().rename(columns={"index": "지역"}), hide_index=True)
        ai_block = f"[선택 지역 전기차 보조금]\n{subsidy_series.to_csv()}"

    elif analysis == STATS_ANALYSIS_EV_RAW:  # ---- 전기차 등록·충전소 현황(원본 수치) ----
        ev_df = pd.DataFrame({
            "전기차 등록대수": [EV_REGISTRATION[r] for r in regions_sel],
            "충전기 수": [EV_CHARGERS[r] for r in regions_sel],
        }, index=regions_sel).sort_values("전기차 등록대수", ascending=False)
        m1, m2 = st.columns(2)
        m1.metric("선택 지역 전기차 등록대수 합", f"{ev_df['전기차 등록대수'].sum():,}대")
        m2.metric("선택 지역 충전기 수 합", f"{ev_df['충전기 수'].sum():,}기")
        c1, c2 = st.columns(2)
        with c1:
            _ranked_bar(ev_df["전기차 등록대수"], "전기차 등록대수", color_scale="Blues")
        with c2:
            _ranked_bar(ev_df["충전기 수"], "충전기 수", color_scale="Greens")
        st.dataframe(ev_df.reset_index(names="지역"), hide_index=True)
        ai_block = f"[선택 지역 전기차 등록대수/충전기수]\n{ev_df.to_csv()}"

    elif analysis == STATS_ANALYSIS_FUEL_EFF:  # ---- 연료별 평균 연비/전비 비교 ----
        spec_df = pd.DataFrame(SAMPLE_CARS)
        view = spec_df[spec_df["국산차"].isin(origin_sel)].copy()
        eff_rows = []
        for fuel in FUEL_CHOICES:
            sub = view[view["연료"] == fuel]
            if sub.empty:
                continue
            if fuel == "전기":
                eff_rows.append({"연료": fuel, "평균 효율": round(sub["전비"].mean(), 2), "단위": "km/kWh"})
            else:
                eff_rows.append({"연료": fuel, "평균 효율": round(sub["연비"].mean(), 2), "단위": "km/L"})
        eff_df = pd.DataFrame(eff_rows)
        if not eff_df.empty:
            m1, m2 = st.columns(2)
            best = eff_df.loc[eff_df["평균 효율"].idxmax()]
            m1.metric("비교 연료 수", f"{len(eff_df)}종")
            m2.metric("효율 1위 연료", f"{best['연료']} ({best['평균 효율']} {best['단위']})")
            fig = px.bar(
                eff_df, x="연료", y="평균 효율", color="단위", text="평균 효율",
                color_discrete_sequence=["#4fc3c3", "#f5a95f"],
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(eff_df, hide_index=True)
        ai_block = f"[연료별 평균 연비(km/L)·전비(km/kWh)]\n{eff_df.to_csv(index=False)}"

    elif analysis == STATS_ANALYSIS_ORIGIN_PRICE:  # ---- 국산차 vs 수입차 가격대 ----
        spec_df = pd.DataFrame(SAMPLE_CARS)
        view = spec_df[spec_df["연료"].isin(fuels_sel)].copy()
        dom = view[view["국산차"] == "국산차"]["출고가"]
        imp = view[view["국산차"] == "수입차"]["출고가"]
        m1, m2 = st.columns(2)
        m1.metric("국산차 평균 출고가", f"{dom.mean():,.0f}원" if not dom.empty else "-")
        m2.metric("수입차 평균 출고가", f"{imp.mean():,.0f}원" if not imp.empty else "-")
        if not view.empty:
            fig = px.box(
                view, x="국산차", y="출고가", color="국산차",
                color_discrete_sequence=["#4fc3c3", "#f06a6a"], title="국산차 vs 수입차 출고가 분포",
            )
            fig.update_layout(height=380, margin=dict(l=10, r=10, t=40, b=10), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        origin_stat = view.groupby("국산차")["출고가"].agg(["mean", "median", "min", "max", "count"]).rename(
            columns={"mean": "평균", "median": "중앙값", "min": "최저", "max": "최고", "count": "대수"}
        )
        st.dataframe(origin_stat.reset_index(), hide_index=True)
        ai_block = f"[국산차/수입차 출고가 비교]\n{origin_stat.to_csv()}"

    st.divider()
    ai_key = "recommend_stats_ai"
    if st.button("제미나이로 이 통계 해설받기", key="recommend_stats_ai_btn"):  # 누를 때만 AI 호출(비용 절약)
        prompt = (
            "아래는 자동차 추천 시스템의 '자동차 통계 확인' 화면에서 사용자가 고른 통계 종류에 "
            "맞춰 나온 실제 통계다(전체 지역·전체 연료·국산+수입 기준). "
            "숫자에 근거해서만 3~4문장으로 눈에 띄는 특징을 짚어줘.\n\n"
            + ai_block
        )
        with st.spinner("AI 답변 생성 중..."):
            st.session_state[ai_key] = ask_gemini(prompt)
    if ai_key in st.session_state:
        st.info(st.session_state[ai_key])
