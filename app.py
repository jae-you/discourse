import streamlit as st
import pandas as pd
import time
import difflib
import plotly.express as px
from openai import OpenAI

# [설정] 페이지 기본 세팅
st.set_page_config(page_title="Deep Agora: 가치의 숲", layout="wide", page_icon="🌲")

# --- [스타일] CSS 커스텀 (Dark Forest Theme) ---
st.markdown("""
<style>
    /* 전체 배경 */
    .stApp { background-color: #0E1117; }
    
    /* 텍스트 가독성 */
    .stMarkdown, .stText, p, div, span, label, li {
        color: #C1C7D0 !important;
        font-family: 'Pretendard', sans-serif;
        font-weight: 400 !important;
    }
    
    /* 헤더 포인트 */
    h1, h2, h3 { color: #69F0AE !important; }

    /* 뉴스 카드 */
    .news-card {
        background-color: #161B22;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #2196F3;
        margin-bottom: 20px;
        color: #C9D1D9;
    }
    
    /* 입력창 커스텀 */
    .stTextInput > div > div > input {
        background-color: #21262D !important;
        color: white !important;
        border: 1px solid #30363D;
    }
    
    /* 슬라이더 스타일 */
    .stSlider > div > div > div > div {
        background-color: #69F0AE;
    }
</style>
""", unsafe_allow_html=True)

# --- [보안] API 키 로드 ---
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("⚠️ API 키가 설정되지 않았습니다.")
    st.stop()

# --- 0. 초기 데이터 (데이터 마이그레이션 포함) ---
should_reset = False
if "forest_df" not in st.session_state:
    should_reset = True
else:
    if "full_text" not in st.session_state.forest_df.columns:
        should_reset = True

if should_reset:
    data = {
        "refined_text": [
            "우회 기술 보편화로 실효성 우려",
            "청소년 보호를 위한 국가 규제 필요",
            "미디어 리터러시 교육이 근본 대안",
            "알고리즘 중독 기업 책임 강화",
            "연령 인증 시 개인정보 침해 우려",
        ],
        "full_text": [ 
            "우회 기술이 보편화된 상황에서 단순 차단은 실효성이 낮다는 기술적 우려가 있습니다.",
            "청소년의 정신건강 보호를 위해 국가 차원의 규제가 필요하다는 점에 공감합니다.",
            "기술적 차단보다는 미디어 리터러시 교육이 근본적인 해결책이 될 수 있습니다.",
            "중독성 강한 알고리즘을 방치한 기업의 사회적 책임을 강화해야 합니다.",
            "연령 인증을 위해 신분증 등을 요구하는 것은 과도한 개인정보 수집입니다."
        ],
        "keyword": [
            "기술적 실효성", "청소년 보호", "대안적 교육", "기업의 책임", "프라이버시"
        ],
        "count": [15, 12, 8, 6, 10]
    }
    st.session_state.forest_df = pd.DataFrame(data)

# --- [수정된 핵심 로직] GPT 프롬프트 (Topic Guard 개선) ---
def process_opinion_with_gpt(user_text, purity_level):
    client = OpenAI(api_key=api_key)
    existing_keywords = ", ".join(st.session_state.forest_df['keyword'].unique())
    
    if purity_level >= 80:
        tone_instruction = "Extremely formal, diplomatic, and soft tone."
    elif purity_level >= 40:
        tone_instruction = "Polite, objective, and declarative tone."
    else:
        tone_instruction = "Direct and assertive tone. Remove only curse words."

    # [프롬프트 수정 포인트]
    # 1. Relevance Check에 'VPN', 'Bypass', 'Education' 등 구체적 키워드 명시
    # 2. "Casual tone is OK"라고 명시하여 말투 때문에 거절하지 않도록 함
    system_prompt = f"""
    You are a 'Civic Editor' acting as a Gatekeeper.
    
    [Step 1: Relevance Check]
    Check if the user input is logically related to: 
    - "Australia's SNS ban for under-16s"
    - "Social Media Regulation / Teenager Protection"
    - "Technical Feasibility (e.g., VPN, Bypass, Verification errors)"
    - "Digital Rights / Privacy"
    
    * CRITICAL: Even if the user uses slang, informal language, or short sentences (e.g., "VPN 쓰면 됨", "이게 말이 되냐"), IF the meaning is relevant, proceed to Step 2.
    * REJECT ONLY IF: The input is about South Korean domestic politics (President Yoon, impeachment), Sports, Food, or meaningless gibberish.
      -> In that case, OUTPUT ONLY: "REJECT"
    
    [Step 2: Processing]
    1. REWRITE input into Korean ({tone_instruction}).
    2. EXTRACT 'Value Keyword' (Noun, max 3 words).
    3. Create 'Short Label' (max 20 chars).
    
    Format: Keyword|Short Label|Full Refined Text
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text}],
            temperature=0.3
        )
        result = response.choices[0].message.content
        
        if "REJECT" in result:
            return "REJECT"
            
        keyword, short_label, full_text = result.split("|", 2)
        return {
            "keyword": keyword.strip(),
            "short_label": short_label.strip(),
            "full_text": full_text.strip()
        }
    except:
        return None

# --- [로직] 유사도 병합 ---
def merge_opinion(new_full_text, keyword, df):
    subset = df[df['keyword'] == keyword]
    for idx, row in subset.iterrows():
        similarity = difflib.SequenceMatcher(None, new_full_text, row['full_text']).ratio()
        if similarity >= 0.7: 
            return idx, True 
    return None, False

# ================= UI 시작 =================

st.title("🌲 Deep Agora: 가치의 숲")

# 1. 뉴스 브리핑
st.markdown("""
<div class="news-card">
    <h4>📢 [이슈] 호주, 16세 미만 SNS 원천 차단 법안</h4>
    <p>호주 정부가 청소년 정신건강 보호를 위해 SNS 계정 보유를 금지합니다.<br>
    쟁점: <b>국가의 보호 의무</b> vs <b>기술적 실효성 및 기본권</b></p>
</div>
""", unsafe_allow_html=True)
st.link_button("🔗 관련 기사 원문 보기 (연합뉴스)", "https://www.yna.co.kr/view/AKR20251209006700084?input=1195m")

st.divider()

# 2. 의견 심기
st.markdown("#### 👩‍🌾 당신의 의견을 심어주세요")
col_input, col_opt = st.columns([3, 1])

with col_input:
    user_input = st.text_input("생각 입력", label_visibility="collapsed", placeholder="예: 무조건 막는 건 답이 아닙니다. 교육이 먼저죠.")

with col_opt:
    purity = st.slider("정제 강도", 0, 100, 70, help="낮을수록 직설적, 높을수록 완곡하게 표현됩니다.")
    submit = st.button("숲에 심기 🌱", type="primary", use_container_width=True)

if submit and user_input:
    with st.spinner("AI가 의견을 검토하고 있습니다..."):
        res = process_opinion_with_gpt(user_input, purity)
        
        # [수정] 결과 처리 로직 분기
        if res == "REJECT":
            st.error("🚫 주제와 무관한 의견(국내 정치, 비방, 잡담 등)은 정원에 심을 수 없습니다.")
        elif res:
            idx, merged = merge_opinion(res['full_text'], res['keyword'], st.session_state.forest_df)
            
            if merged:
                st.session_state.forest_df.at[idx, 'count'] += 1
                msg = f"'{res['keyword']}' 나무가 더 크게 자랐습니다! (공감 +1) 💧"
            else:
                new_row = {
                    "refined_text": res['short_label'],
                    "full_text": res['full_text'],
                    "keyword": res['keyword'],
                    "count": 1
                }
                st.session_state.forest_df = pd.concat([pd.DataFrame([new_row]), st.session_state.forest_df], ignore_index=True)
                msg = f"새로운 묘목 '{res['keyword']}'을 심었습니다! 🌲"
            
            st.success(msg)
            time.sleep(1.0)
            st.rerun()
        else:
            st.error("오류가 발생했습니다. 다시 시도해주세요.")

st.divider()

# 3. 가치의 숲 시각화
st.subheader("🌳 가치의 지도 (Value Map)")

if not st.session_state.forest_df.empty:
    df = st.session_state.forest_df
    
    fig = px.treemap(
        df, 
        path=[px.Constant("Deep Agora"), 'keyword', 'refined_text'],
        values='count',
        color='keyword',
        color_discrete_sequence=px.colors.qualitative.Set3,
        custom_data=['full_text', 'count']
    )
    
    fig.update_layout(
        margin=dict(t=0, l=0, r=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Pretendard", color='#E0E0E0'),
        uniformtext=dict(minsize=14, mode='hide')
    )
    
    fig.update_traces(
        root_color="#1E2329",
        textinfo="label+value",
        hovertemplate='<b>%{label}</b><br><br>📝 전체 의견:<br>%{customdata[0]}<br><br>💧 공감: %{customdata[1]}<extra></extra>',
        marker=dict(cornerradius=5)
    )
    
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📜 의견 목록 자세히 보기"):
        st.dataframe(
            df[['keyword', 'full_text', 'count']].sort_values(by='count', ascending=False),
            column_config={
                "keyword": "핵심 가치",
                "full_text": "전체 의견",
                "count": st.column_config.NumberColumn("공감", format="💧 %d")
            },
            hide_index=True,
            use_container_width=True
        )
else:
    st.info("아직 숲이 비어있습니다. 의견을 심어주세요!")
