
import pandas as pd
import streamlit as st
import plotly.express as px

# ★ 1. 화면 설정: 가로 공간을 넓게 사용
st.set_page_config(
    page_title="철도 데이터 분석 대시보드",
    page_icon="🚉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ★ 2. 데이터 읽기
df = pd.read_csv("analysis_result.csv")
df["측정시각"] = pd.to_datetime(df["측정시각"])
df["목표시각"] = pd.to_datetime(df["목표시각"])

if df.empty:
    st.warning("분석 자료가 없습니다.")
    st.stop()

# ★ 3. 사이드바: 조회 조건
with st.sidebar:
    st.header("조회 조건")

    equipment = st.selectbox(
        "설비 선택",
        df["설비ID"].dropna().unique()
    )

    equipment_data = df[df["설비ID"] == equipment].copy()

    first_date = equipment_data["측정시각"].min().date()
    last_date = equipment_data["측정시각"].max().date()

    st.caption(f"자료 기간: {first_date} ~ {last_date}")

    start = st.date_input(
        "시작일",
        value=first_date,
        min_value=first_date,
        max_value=last_date,
        key=f"start_{equipment}"
    )

    end = st.date_input(
        "종료일",
        value=last_date,
        min_value=first_date,
        max_value=last_date,
        key=f"end_{equipment}"
    )

    st.caption("조건을 변경하면 분석 결과가 자동으로 갱신됩니다.")

# ★ 4. 제목과 조회 자료
st.title("🚉 철도 데이터 분석 대시보드")
st.caption("교육용 가상 자료입니다. AI 확인후보는 고장 확정이 아닙니다.")

if start > end:
    st.warning("시작일은 종료일보다 빠르거나 같아야 합니다.")
    st.stop()

view = equipment_data[
    (equipment_data["측정시각"].dt.date >= start)
    & (equipment_data["측정시각"].dt.date <= end)
].sort_values("측정시각")

st.caption(f"선택 설비: {equipment}  |  조회 기간: {start} ~ {end}")

if view.empty:
    st.warning("조회 결과가 없습니다. 날짜를 다시 선택하세요.")
    st.stop()

# ★ 5. 공통 분석 결과
candidates = view[view["AI결과"] == "확인후보"]
candidate_rate = len(candidates) / len(view) * 100

pred = view.dropna(
    subset=["목표시각", "다음온도_C", "AI예측온도_C"]
).sort_values("목표시각")

mae = (pred["다음온도_C"] - pred["AI예측온도_C"]).abs().mean()
mae_text = f"{mae:.2f} ℃" if len(pred) > 0 else "비교 자료 없음"

# ★ 6. 상단 요약: 중요한 수치를 먼저 표시
col1, col2, col3, col4 = st.columns(4)

col1.metric("조회 건수", f"{len(view):,}건")
col2.metric("AI 확인후보", f"{len(candidates):,}건")
col3.metric("확인후보 비율", f"{candidate_rate:.1f}%")
col4.metric("온도 예측 MAE", mae_text)

# ★ 7. 분석 탭
tab1, tab2, tab3 = st.tabs([
    "AI 점검 후보",
    "다음 1시간 온도 예측",
    "업무 검토 및 저장"
])

# ──────────────────────────
# 탭 1: AI 점검 후보
# ──────────────────────────
with tab1:
    if len(candidates) > 0:
        st.warning(
            f"선택한 기간에 AI 확인후보가 {len(candidates):,}건 있습니다. "
            "센서 상태와 운전 조건을 확인하세요."
        )
    else:
        st.info(
            "선택한 기간에 AI 확인후보가 없습니다. "
            "이 결과만으로 설비의 정상 여부를 확정할 수는 없습니다."
        )

    # 그래프는 넓게, 판정 요약은 좁게 배치
    chart_area, summary_area = st.columns([3, 1])

    with chart_area:
        fig = px.line(
            view,
            x="측정시각",
            y="온도_C",
            title="온도 추이와 AI 확인후보",
            labels={"측정시각": "측정 시각", "온도_C": "온도 (℃)"}
        )

        fig.add_scatter(
            x=candidates["측정시각"],
            y=candidates["온도_C"],
            mode="markers",
            name="확인후보",
            marker=dict(color="red", size=10)
        )

        fig.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=50, b=20)
        )

        st.plotly_chart(fig, use_container_width=True)

    with summary_area:
        st.subheader("AI 판정별 건수")

        counts = (
            view["AI결과"]
            .fillna("결과 없음")
            .value_counts()
            .rename_axis("AI결과")
            .reset_index(name="건수")
        )

        st.dataframe(
            counts,
            hide_index=True,
            use_container_width=True
        )

        st.caption("확인후보 비율 = 확인후보 건수 ÷ 조회 건수 × 100")

    st.subheader("확인후보 상세")

    if not candidates.empty:
        st.dataframe(
            candidates.sort_values("측정시각", ascending=False),
            height=250,
            hide_index=True,
            use_container_width=True
        )

        st.download_button(
            "점검 후보 CSV 내려받기",
            candidates.to_csv(index=False).encode("utf-8-sig"),
            "inspection_candidates.csv",
            mime="text/csv"
        )
    else:
        st.caption("표시할 확인후보가 없습니다.")

# ──────────────────────────
# 탭 2: 다음 1시간 온도 예측
# ──────────────────────────
with tab2:
    st.caption(
        "선택 기간의 측정 자료에 연결된 다음 1시간 예측을 비교합니다. "
        "목표시각은 조회 종료일 이후일 수 있습니다."
    )

    if pred.empty:
        st.info("실제 온도와 예측 온도를 비교할 자료가 없습니다.")
    else:
        st.write(
            f"비교 자료: **{len(pred):,}건**  |  "
            f"평균 절대 오차(MAE): **{mae_text}**"
        )

        fig2 = px.line(
            pred,
            x="목표시각",
            y=["다음온도_C", "AI예측온도_C"],
            title="실제 온도와 AI 예측 온도",
            labels={
                "목표시각": "예측 대상 시각",
                "value": "온도 (℃)",
                "variable": "구분"
            },
            color_discrete_map={
                "다음온도_C": "#2563EB",
                "AI예측온도_C": "#F97316"
            }
        )

        fig2.update_layout(
            height=380,
            legend_title_text="",
            margin=dict(l=20, r=20, t=50, b=20)
        )

        st.plotly_chart(fig2, use_container_width=True)
        st.caption(
            "MAE는 실제 온도와 예측 온도의 차이를 절댓값으로 바꾼 뒤 "
            "평균한 값입니다. 작을수록 예측 오차가 작습니다."
        )

        with st.expander("예측 비교 상세 자료 보기"):
            st.dataframe(
                pred[
                    ["측정시각", "목표시각", "다음온도_C", "AI예측온도_C"]
                ],
                height=250,
                hide_index=True,
                use_container_width=True
            )

# ──────────────────────────
# 탭 3: 업무 검토 및 저장
# ──────────────────────────
with tab3:
    memo_area, report_area = st.columns(2)

    with memo_area:
        st.subheader("업무 메모")

        note = st.text_area(
            "확인할 사항 및 조치 제안",
            value="센서 상태와 운전 조건을 확인한 후 담당자 검토가 필요합니다.",
            height=220,
            key=f"note_{equipment}_{start}_{end}"
        )

        st.caption(
            "메모는 설비·조회 기간별로 구분합니다. "
            "보관할 내용은 보고서 TXT로 내려받으세요."
        )

    report = f"""[철도 설비 분석 보고서]

설비: {equipment}
조회 기간: {start} ~ {end}
조회 건수: {len(view):,}건
AI 확인후보: {len(candidates):,}건
확인후보 비율: {candidate_rate:.1f}%
온도 예측 MAE: {mae_text}
예측 비교 자료: {len(pred):,}건

[업무 메모]
{note}

※ 교육용 가상 자료이며, 확인후보는 고장 확정이 아닙니다."""

    with report_area:
        st.subheader("보고서 미리보기")
        st.text(report)

    st.download_button(
        "보고서 TXT 내려받기",
        report.encode("utf-8-sig"),
        "dashboard_report.txt",
        mime="text/plain"
    )

# ★ 8. 원본 조회 자료: 필요할 때만 펼쳐 보기
with st.expander(f"전체 조회 자료 보기 · {len(view):,}건"):
    st.dataframe(
        view,
        height=300,
        hide_index=True,
        use_container_width=True
    )

    st.download_button(
        "조회 결과 CSV 내려받기",
        view.to_csv(index=False).encode("utf-8-sig"),
        "dashboard_result.csv",
        mime="text/csv"
    )
