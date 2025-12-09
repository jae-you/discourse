import streamlit as st
import pandas as pd
import time
import plotly.express as px
from openai import OpenAI

# [설정] 페이지 기본 세팅
st.set_page_config(page_title="Deep Agora: 갈등과 다리", layout="wide", page_icon="🌉")

# --- [스타일] CSS (Dark & Professional) ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3 { color: #E0E0E0 !important; font-family: 'Pretendard'; }
    .stMarkdown, p, div, li { color: #B0B8C4; font-weight: 400 !important; }
    
    /* 브릿지 카드 스타일 */
    .bridge-card {
        background: linear-gradient(90deg, #1E2329 0%, #2D333B 50%, #1E2329 100%);
        border: 2px solid #4CAF50;
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 0 15px rgba(76, 175, 80, 0.3);
    }
    .bridge-title { color: #4CAF50; font-weight: bold; font-size: 1.2em; }
    .bridge-text { color: white; font-size: 1.1em; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# --- [보안] API 키 로드 ---
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("⚠️ API 키가 설정되지 않았습니다.")
    st.stop()

# --- 0. 초기 데이터 (데이터 마이그레이션 로직 추가 ⭐) ---
# 기존 세션에 데이터가 있어도, 구버전(polarity 컬럼 없음)이면 강제 리셋합니다.
should_reset = False
if "matrix_df" not in st.session_state:
    should_reset = True
else:
    # 컬럼 검사: 'polarity'가 없으면 구버전 데이터임 -> 리셋 필요
    if "polarity" not in st.session_state.matrix_df.columns:
        should_reset = True

if should_reset:
    data = {
        "keyword": ["기술적 실효성", "국가의 보호책무", "프라이버시", "플랫폼의 책임", "리터러시 교육"],
        "summary": [
            "VPN 우회 등 기술적 한계로 인해 차단 정책은 실효성이 없다는 비판",
            "국가는 유해 환경으로부터 청소년을 보호할 헌법적 의무를 져야 함",
            "과도한 인증은 감시 사회를 초래하며 개인의 프라이버시를 침해함",
            "중독 알고리즘으로 수익을 낸 플랫폼 기업에 강력한 책임을 물어야 함",
            "강제 차단보다는 스스로 제어할 수 있는 디지털 리터러시 교육이 중요함"
        ],
        "count": [45, 30, 20, 25, 40],  # 관심도
        "polarity": [-0.8, 0.9, -0.7, 0.6, 0.1], # -1(반대) ~ +1(찬성)
        "side": ["반대(자율)", "찬성(규제)", "반대(자율)", "찬성(규제)", "공통(대안)"] 
    }
    st.session_state.matrix_df = pd.DataFrame(data)

# --- [핵심 로직] GPT 프롬프트 (입장 분석) ---
def analyze_opinion(user_text):
    client = OpenAI(api_key=api_key)
    existing_keywords = ", ".join(st.session_state.matrix_df['keyword'].unique())

    system_prompt = f"""
    You are a 'Policy Analyst'. Analyze the input regarding "Australia's SNS Ban".
    
    [Step 1: Political Noise Filter]
    * IF input is purely political slogans (e.g. "Yoon Out") -> OUTPUT: "REJECT"
    * IF input uses politicians as metaphors -> IGNORE names, EXTRACT policy argument.

    [Step 2: Analysis]
    1. Keyword: Core value (Korean Noun, max 10 chars). NO generic words (SNS, Govt).
    2. Summary: One formal Korean sentence.
    3. Polarity Score (-1.0 to 1.0):
       * -1.0 ~ -0.5: Strongly Against Ban (Freedom, Tech limits, Privacy).
       * 0.5 ~ 1.0: Strongly Support Ban (Protection, Addiction, State Duty).
       * -0.4 ~ 0.4: Neutral / Alternative / Bridge (Education, Corporate Responsibility).

    Format: Keyword|Summary|Polarity_Score
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
            "polarity": float(parts[2].strip())
        }
    except:
        return None

# --- [로직] 브릿지 발견 알고리즘 ---
def find_bridges(df):
    # Polarity 절대값이 0.4 미만이고(중도/대안), 관심도가 높은 것
    bridges = df[
        (df['polarity'].abs() < 0.4) & 
        (df['count'] > 10)
    ].sort_values(by='count', ascending=False)
    return bridges

# ================= UI 시작 =================

st.title("🌉 Deep Agora: 갈등과 다리")
st.caption("우리는 어디서 갈라지고, 어디서 만나는가? 양극단의 주장 속에서 '연결고리'를 찾습니다.")

# 1. 브릿지 리포트
bridges = find_bridges(st.session_state.matrix_df)

if not bridges.empty:
    top_bridge = bridges.iloc[0]
    st.markdown(f"""
    <div class="bridge-card">
        <span class="bridge-title">🤝 우리가 발견한 합의의 다리</span>
        <div class="bridge-text">
            서로 다른 입장이지만, <b>'{top_bridge['keyword']}'</b>의 중요성에는 모두가 공감하고 있습니다.<br>
            <span style="font-size:0.8em; color:#B0B8C4;">"{top_bridge['summary']}"</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

col_main, col_side = st.columns([3, 1.5])

# --- [메인 시각화] 갈등 지형도 ---
with col_main:
    st.markdown("### 🗺️ 갈등 지형도 (Polarity Map)")
    
    df = st.session_state.matrix_df
    
    # 색상 지정
    df['color'] = df['polarity'].apply(lambda x: '#FF5252' if x < -0.3 else ('#448AFF' if x > 0.3 else '#69F0AE'))
    
    fig = px.scatter(
        df, 
        x="polarity", 
        y="count", 
        size="count", 
        text="keyword",
        hover_name="summary",
        range_x=[-1.2, 1.2],
        range_y=[0, df['count'].max() + 20],
        size_max=60
    )
    
    fig.update_traces(marker=dict(color=df['color']), textposition='top center', textfont=dict(size=14, weight='bold'))
    
    fig.update_layout(
        plot_bgcolor="#161B22",
        paper_bgcolor="#0E1117",
        font=dict(color="#E0E0E0", family="Pretendard", size=14),
        xaxis=dict(title="◀ 반대 (자율/기술) --------- 중립/대안 --------- 찬성 (규제/보호) ▶", showgrid=True, gridcolor="#30363D", zeroline=True, zerolinecolor="white"),
        yaxis=dict(title="논의 강도 (관심도) ▲", showgrid=True, gridcolor="#30363D"),
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

# --- [사이드바] 의견 입력 ---
with col_side:
    st.markdown("### 🗣️ 당신의 입장은?")
    with st.container(border=True):
        user_input = st.text_area("의견을 남겨주세요", height=100, placeholder="예: 무조건 막는 건 반대지만, 기업이 책임지는 건 찬성합니다.")
        
        if st.button("지도에 점 찍기 📍", use_container_width=True, type="primary"):
            if user_input:
                with st.spinner("AI가 당신의 입장을 분석하여 지도에 배치합니다..."):
                    res = analyze_opinion(user_input)
                    
                    if res == "REJECT":
                        st.error("🚫 주제와 무관한 내용은 반영되지 않습니다.")
                    elif res:
                        if res['keyword'] in st.session_state.matrix_df['keyword'].values:
                            idx = st.session_state.matrix_df.index[st.session_state.matrix_df['keyword'] == res['keyword']].tolist()[0]
                            st.session_state.matrix_df.at[idx, 'count'] += 5
                            old_pol = st.session_state.matrix_df.at[idx, 'polarity']
                            st.session_state.matrix_df.at[idx, 'polarity'] = (old_pol + res['polarity']) / 2
                            st.success(f"'{res['keyword']}' 이슈가 더 커지고 위치가 조정되었습니다!")
                        else:
                            new_row = {
                                "keyword": res['keyword'],
                                "summary": res['summary'],
                                "count": 10, 
                                "polarity": res['polarity'],
                                "side": "중립"
                            }
                            st.session_state.matrix_df = pd.concat([pd.DataFrame([new_row]), st.session_state.matrix_df], ignore_index=True)
                            st.success(f"새로운 관점 '{res['keyword']}'이 지도에 등장했습니다!")
                        
                        time.sleep(1)
                        st.rerun()

    st.markdown("### 📋 분석 리포트")
    tab1, tab2 = st.tabs(["🔥 치열한 쟁점", "🌉 합의의 다리"])
    
    with tab1:
        conflicts = df[df['polarity'].abs() > 0.4].sort_values(by='count', ascending=False)
        for _, row in conflicts.iterrows():
            icon = "🛡️" if row['polarity'] > 0 else "🚫"
            st.markdown(f"**{icon} {row['keyword']}**")
            
    with tab2:
        bridges_list = find_bridges(df)
        if not bridges_list.empty:
            for _, row in bridges_list.iterrows():
                st.markdown(f"**🤝 {row['keyword']}**")
                st.caption(f"{row['summary']}")
        else:
            st.info("아직 뚜렷한 합의점이 보이지 않습니다.")
