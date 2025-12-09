import streamlit as st
import pandas as pd
import time
import plotly.express as px
from openai import OpenAI

# [설정] 페이지 기본 세팅
st.set_page_config(page_title="Deep Agora: 숙의 매트릭스", layout="wide", page_icon="⚖️")

# --- [스타일] CSS (Professional Dark) ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3 { color: #E0E0E0 !important; font-family: 'Pretendard'; }
    .stMarkdown, p, div, li { color: #B0B8C4; font-weight: 400 !important; }
    
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

# --- 0. 초기 데이터 (정교화된 예시) ---
if "matrix_df" not in st.session_state:
    data = {
        "keyword": ["기술적 실효성", "청소년 보호 의무", "프라이버시권", "플랫폼의 책임", "리터러시 교육"],
        "summary": [
            "VPN 등 우회 기술이 보편화된 환경에서 물리적 차단은 한계가 있다는 지적",
            "국가는 유해 환경으로부터 청소년을 보호할 헌법적 의무가 있다는 원칙론",
            "연령 인증을 위한 과도한 개인정보 수집은 감시 사회를 초래한다는 우려",
            "알고리즘 중독을 방치하여 수익을 낸 빅테크 기업에 징벌적 책임을 물어야 함",
            "강제적 차단보다는 스스로 제어할 수 있는 미디어 리터러시 교육이 본질적 해법"
        ],
        "count": [45, 30, 15, 25, 10],  # Y축: 관심도
        "consensus": [0.2, 0.9, 0.3, 0.8, 0.6], # X축: 합의 수준 (수단 vs 가치)
        "type": ["쟁점", "합의", "쟁점", "합의", "숙의필요"] 
    }
    st.session_state.matrix_df = pd.DataFrame(data)

# --- [핵심 로직] GPT 프롬프트 (정치 필터 + 합의 기준 강화) ---
def analyze_opinion(user_text):
    client = OpenAI(api_key=api_key)
    
    # 기존 키워드 리스트 (중복 방지용)
    existing_keywords = ", ".join(st.session_state.matrix_df['keyword'].unique())

    system_prompt = f"""
    You are a 'Policy Analyst' for a public debate on "Australia's SNS Ban for under-16s".
    
    [Step 1: Noise & Politics Filter] (CRITICAL)
    * IF input is purely "Yoon Out", "Free Lee", or unrelated nonsense -> OUTPUT: "REJECT"
    * IF input mentions politicians (Lee Myung-bak, Yoon, Moon) as sarcasm/metaphor:
      -> IGNORE the name. EXTRACT the underlying policy argument.
      -> Example: "It's not Lee Myung-bak era, why censor?" -> Argument: "Opposition to excessive state censorship". (NOT 'Praise for Lee').

    [Step 2: Analysis & Scoring]
    1. Keyword: Extract the core value (Korean Noun, max 10 chars).
       * FORBIDDEN WORDS: 'SNS', '호주', '정치', '기업', '정부' (Too generic).
       * Use specific terms: '기술적 실효성', '표현의 자유', '디지털 중독', '플랫폼 책임'.
    2. Summary: One formal Korean sentence summarizing the argument.
    3. Consensus Score (0.0 ~ 1.0):
       * High (0.8~1.0): Abstract Values/Goals everyone agrees on (e.g., "Kids should be safe", "Addiction is bad").
       * Low (0.0~0.4): Specific Methods/Regulations that cause conflict (e.g., "Ban it", "Don't ban it", "VPN works").
       * Mid (0.5~0.7): Alternative proposals (e.g., "Education").

    [Step 3: Output Format]
    Keyword|Summary|Consensus_Score
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text}],
            temperature=0.1
        )
        result = response.choices[0].message.content
        
        if "REJECT" in result:
            return "REJECT"
            
        parts = result.split("|")
        return {
            "keyword": parts[0].strip(),
            "summary": parts[1].strip(),
            "consensus": float(parts[2].strip())
        }
    except:
        return None

# ================= UI 시작 =================

st.title("⚖️ Deep Agora: 숙의 매트릭스")
st.caption("우리의 논의는 어디쯤 와있을까요? 갈등하는 '수단'과 합의된 '가치'를 구분해 봅니다.")

# 뉴스 브리핑 (심플하게)
with st.expander("📢 [이슈 브리핑] 호주 16세 미만 SNS 차단 법안", expanded=False):
    st.markdown("호주 정부가 청소년 SNS 계정 보유를 금지합니다. 쟁점은 '국가의 보호 의무' vs '자율권 및 실효성'입니다.")

col_main, col_side = st.columns([3, 2])

# --- [메인 시각화] 4분면 매트릭스 ---
with col_main:
    st.markdown("### 🗺️ 공론 지형도 (Debate Landscape)")
    
    df = st.session_state.matrix_df
    
    # Scatter Plot 설정
    fig = px.scatter(
        df, 
        x="consensus", 
        y="count", 
        size="count", 
        color="type",
        text="keyword", # 점 위에 키워드 표시
        hover_name="summary",
        range_x=[-0.1, 1.2], # 여백 확보
        range_y=[0, df['count'].max() + 20],
        color_discrete_map={"쟁점": "#FF5252", "합의": "#00E676", "숙의필요": "#FFD740"},
        size_max=60
    )
    
    # 4분면 배경 디자인
    fig.update_layout(
        plot_bgcolor="#161B22",
        paper_bgcolor="#0E1117",
        font=dict(color="#E0E0E0", family="Pretendard", size=14),
        xaxis=dict(title="◀ 논쟁 중 (수단) --------- 합의됨 (가치) ▶", showgrid=True, gridcolor="#30363D", zeroline=False),
        yaxis=dict(title="참여 강도 (관심도) ▲", showgrid=True, gridcolor="#30363D", zeroline=False),
        showlegend=False,
        shapes=[
            # 중앙 기준선
            dict(type="line", x0=0.5, y0=0, x1=0.5, y1=df['count'].max()+20, line=dict(color="grey", width=1, dash="dot")),
        ]
    )
    
    fig.update_traces(textposition='top center', textfont=dict(size=14, weight='bold'))
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.info("""
    **💡 차트 해석 가이드**
    * **왼쪽 (논쟁 구간):** "어떻게 할 것인가?" (차단 vs 허용) - *치열하게 토론해야 할 영역*
    * **오른쪽 (합의 구간):** "무엇을 지킬 것인가?" (청소년 보호, 기업 책임) - *우리가 공유하는 대원칙*
    * **위쪽:** 지금 가장 뜨거운 주제 🔥
    """)

# --- [사이드바] 의견 입력 및 리스트 ---
with col_side:
    # 2. 의견 입력
    st.markdown("### 🗳️ 의견 보태기")
    with st.container(border=True):
        user_input = st.text_area("이 사안의 핵심은 무엇인가요?", height=80, placeholder="비유나 비난보다는 본질적인 이유를 적어주세요.")
        if st.button("매트릭스에 점 찍기 📍", use_container_width=True, type="primary"):
            if user_input:
                with st.spinner("AI가 정치적 소음을 걷어내고 좌표를 분석 중입니다..."):
                    res = analyze_opinion(user_input)
                    
                    if res == "REJECT":
                        st.error("🚫 주제와 무관하거나 정치적 구호에 가까운 내용은 반영되지 않습니다.")
                    elif res:
                        # 기존에 같은 키워드가 있으면 카운트만 증가 (간이 로직)
                        if res['keyword'] in st.session_state.matrix_df['keyword'].values:
                            idx = st.session_state.matrix_df.index[st.session_state.matrix_df['keyword'] == res['keyword']].tolist()[0]
                            st.session_state.matrix_df.at[idx, 'count'] += 5 # 가중치
                            st.success(f"'{res['keyword']}' 이슈가 더 뜨거워졌습니다! 🔥")
                        else:
                            # 신규 추가
                            new_row = {
                                "keyword": res['keyword'],
                                "summary": res['summary'],
                                "count": 10, 
                                "consensus": res['consensus'],
                                "type": "쟁점" if res['consensus'] < 0.6 else "합의"
                            }
                            st.session_state.matrix_df = pd.concat([pd.DataFrame([new_row]), st.session_state.matrix_df], ignore_index=True)
                            st.success(f"새로운 관점 '{res['keyword']}'이 매트릭스에 등장했습니다! 📍")
                        
                        time.sleep(1)
                        st.rerun()

    # 3. 우선순위 리스트
    st.markdown("### 📋 우선순위 안건")
    
    tab1, tab2 = st.tabs(["🔥 치열한 쟁점", "✅ 합의된 가치"])
    
    with tab1:
        st.caption("찬반이 팽팽하여 더 깊은 숙의가 필요한 주제들입니다.")
        issues = df[df['consensus'] < 0.6].sort_values(by='count', ascending=False)
        for _, row in issues.iterrows():
            with st.container(border=True):
                st.markdown(f"**{row['keyword']}**")
                st.caption(f"{row['summary']}")
            
    with tab2:
        st.caption("대다수가 동의하는, 정책 실행의 기반이 되는 가치들입니다.")
        agreements = df[df['consensus'] >= 0.6].sort_values(by='count', ascending=False)
        for _, row in agreements.iterrows():
            with st.container(border=True):
                st.markdown(f"**{row['keyword']}**")
                st.caption(f"{row['summary']}")
