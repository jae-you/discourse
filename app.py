import streamlit as st
import pandas as pd
import time
import plotly.express as px
import plotly.graph_objects as go
from openai import OpenAI

# [설정] 페이지 기본 세팅
st.set_page_config(page_title="Deep Agora: 숙의 매트릭스", layout="wide", page_icon="⚖️")

# --- [스타일] CSS 커스텀 (Professional Dark Theme) ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3 { color: #E0E0E0 !important; font-family: 'Pretendard'; }
    .stMarkdown, p, div { color: #B0B8C4; }
    
    /* 매트릭스 설명 카드 */
    .info-card {
        background-color: #1F2937;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #374151;
        margin-bottom: 10px;
    }
    
    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; white-space: pre-wrap; background-color: #1F2937; border-radius: 5px; color: white;
    }
    .stTabs [aria-selected="true"] { background-color: #3B82F6; }
</style>
""", unsafe_allow_html=True)

# --- [보안] API 키 로드 ---
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("⚠️ API 키가 설정되지 않았습니다.")
    st.stop()

# --- 0. 초기 데이터 (매트릭스 좌표용 데이터 포함) ---
if "matrix_df" not in st.session_state:
    data = {
        "keyword": ["기술적 실효성", "청소년 보호", "프라이버시", "기업 책임", "교육적 대안"],
        "summary": [
            "VPN 등 우회 기술로 인해 차단은 무용지물이라는 기술적 회의론",
            "국가가 나서서라도 중독으로부터 청소년을 보호해야 한다는 당위론",
            "연령 인증 과정에서 발생하는 개인정보 유출 및 감시 사회 우려",
            "알고리즘 중독을 방치한 플랫폼 기업에 징벌적 책임을 물어야 함",
            "강제적 차단보다는 미디어 리터러시 교육이 근본적 해법임"
        ],
        "count": [45, 30, 15, 25, 10],  # Y축: 참여도(관심도)
        "consensus": [0.2, 0.8, 0.4, 0.9, 0.6], # X축: 합의 수준 (0=갈등, 1=합의)
        "type": ["쟁점", "합의", "쟁점", "합의", "숙의필요"] # 카테고리
    }
    st.session_state.matrix_df = pd.DataFrame(data)

# --- [로직] GPT 프롬프트 (좌표 분석 추가) ---
def analyze_opinion(user_text):
    client = OpenAI(api_key=api_key)
    
    system_prompt = """
    You are a 'Policy Analyst'.
    Analyze the user's input regarding "Australia's SNS Ban".
    
    Output Format: Keyword|Summary|Consensus_Score(0.0-1.0)|Is_New_Topic(True/False)
    
    Rules:
    1. Keyword: Core value (Korean Noun).
    2. Summary: One formal Korean sentence.
    3. Consensus_Score: Estimate how controversial this opinion is based on general public sentiment.
       - 0.0 ~ 0.3: Highly controversial / Minority view
       - 0.7 ~ 1.0: Generally agreed / Common sense (e.g. "Addiction is bad")
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text}],
            temperature=0.1
        )
        result = response.choices[0].message.content
        parts = result.split("|")
        return {
            "keyword": parts[0],
            "summary": parts[1],
            "consensus": float(parts[2]),
            "is_new": parts[3]
        }
    except:
        return None

# ================= UI 시작 =================

st.title("⚖️ Deep Agora: 숙의 매트릭스")
st.caption("단순한 나열이 아닙니다. 우리가 '어디에 집중해야 하는지'를 보여줍니다.")

# 1. 뉴스 브리핑 (간략화)
with st.expander("📢 [이슈 브리핑] 호주 16세 미만 SNS 차단 법안", expanded=False):
    st.markdown("호주 정부가 청소년 SNS 계정 보유를 금지합니다. 쟁점은 '국가의 보호 의무' vs '자율권 및 실효성'입니다.")

col_main, col_side = st.columns([3, 2])

# --- [메인 시각화] 4분면 매트릭스 ---
with col_main:
    st.markdown("### 🗺️ 공론 지형도 (Debate Landscape)")
    
    df = st.session_state.matrix_df
    
    # Scatter Plot 그리기
    fig = px.scatter(
        df, 
        x="consensus", 
        y="count", 
        size="count", 
        color="type",
        text="keyword",
        hover_name="summary",
        range_x=[0, 1.1],
        range_y=[0, df['count'].max() + 20],
        color_discrete_map={"쟁점": "#FF5252", "합의": "#00E676", "숙의필요": "#FFD740"}
    )
    
    # 4분면 배경 및 축 설정
    fig.update_layout(
        plot_bgcolor="#161B22",
        paper_bgcolor="#0E1117",
        font=dict(color="#E0E0E0"),
        xaxis=dict(title="합의 수준 (오른쪽일수록 합의됨)", showgrid=True, gridcolor="#30363D"),
        yaxis=dict(title="참여 강도 (위쪽일수록 뜨거움)", showgrid=True, gridcolor="#30363D"),
        shapes=[
            # 4분면 구분선
            dict(type="line", x0=0.5, y0=0, x1=0.5, y1=df['count'].max()+20, line=dict(color="grey", dash="dot")),
            dict(type="line", x0=0, y0=20, x1=1.1, y1=20, line=dict(color="grey", dash="dot"))
        ]
    )
    
    # 텍스트 위치 조정
    fig.update_traces(textposition='top center')
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.info("""
    **💡 차트 읽는 법:**
    - **좌상단 (🔥 치열한 쟁점):** 참여는 많은데 합의가 안 된 곳. **우리가 가장 먼저 토론해야 할 주제**입니다.
    - **우상단 (✅ 사회적 합의):** 참여도 많고 동의도 얻은 곳. 정책으로 바로 실행 가능합니다.
    """)

# --- [사이드바] 의견 입력 및 리스트 ---
with col_side:
    # 2. 의견 입력
    st.markdown("### 🗳️ 의견 보태기")
    with st.container(border=True):
        user_input = st.text_area("이 사안의 핵심은 무엇인가요?", height=80)
        if st.button("매트릭스에 점 찍기 📍", use_container_width=True, type="primary"):
            if user_input:
                with st.spinner("좌표를 계산 중입니다..."):
                    res = analyze_opinion(user_input)
                    if res:
                        # 데이터 업데이트 로직 (간소화)
                        # 실제로는 키워드가 같으면 병합해야 함
                        new_row = {
                            "keyword": res['keyword'],
                            "summary": res['summary'],
                            "count": 10, # 초기값
                            "consensus": res['consensus'],
                            "type": "쟁점" if res['consensus'] < 0.5 else "합의"
                        }
                        st.session_state.matrix_df = pd.concat([pd.DataFrame([new_row]), st.session_state.matrix_df], ignore_index=True)
                        st.rerun()

    # 3. 우선순위 리스트 (Priority List)
    st.markdown("### 📋 우선순위별 안건")
    
    # 탭으로 구분하여 보여줌
    tab1, tab2 = st.tabs(["🔥 쟁점 (토론필요)", "✅ 합의 (실행가능)"])
    
    with tab1:
        # 합의 점수가 낮은 순(0.0~0.5) & 카운트 높은 순
        issues = df[df['consensus'] <= 0.5].sort_values(by='count', ascending=False)
        for _, row in issues.iterrows():
            st.warning(f"**{row['keyword']}** (관심도 {row['count']})\n\n{row['summary']}")
            
    with tab2:
        # 합의 점수가 높은 순(0.6~1.0)
        agreements = df[df['consensus'] > 0.5].sort_values(by='count', ascending=False)
        for _, row in agreements.iterrows():
            st.success(f"**{row['keyword']}** (관심도 {row['count']})\n\n{row['summary']}")
