import streamlit as st
import pandas as pd
import time
import difflib
import plotly.express as px  # 시각화 라이브러리 추가
from openai import OpenAI

# [설정] 페이지 기본 세팅
st.set_page_config(page_title="Deep Agora: 가치의 숲", layout="wide", page_icon="🌲")

# --- [스타일] CSS 커스텀 (Dark & Neon) ---
st.markdown("""
<style>
    /* 전체 배경: 깊은 밤 숲속 */
    .stApp { background-color: #0E1117; }
    
    /* 텍스트 가독성 */
    .stMarkdown, .stText, p, div, span, label, li {
        color: #C1C7D0 !important;
        font-family: 'Pretendard', sans-serif;
    }
    
    /* 헤더 포인트 컬러 */
    h1, h2, h3 { color: #69F0AE !important; }

    /* 뉴스 카드 스타일 */
    .news-card {
        background-color: #161B22;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #2196F3;
        margin-bottom: 20px;
    }
    
    /* 입력창 스타일 */
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        background-color: #21262D !important;
        color: white !important;
        border: 1px solid #30363D;
    }
</style>
""", unsafe_allow_html=True)

# --- [보안] API 키 로드 ---
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("⚠️ API 키가 설정되지 않았습니다.")
    st.stop()

# --- 0. 초기 데이터 ---
if "forest_df" not in st.session_state:
    data = {
        "refined_text": [
            "우회 기술이 보편화되어 차단은 실효성이 낮다는 우려가 있습니다.",
            "청소년 보호를 위한 규제 필요성에 공감합니다.",
            "미디어 리터러시 교육이 근본적 해결책입니다.",
            "알고리즘 중독에 대한 기업 책임을 강화해야 합니다.",
            "과도한 개인정보 수집과 프라이버시 침해 우려가 있습니다.",
        ],
        "keyword": [
            "기술적 실효성", "청소년 보호", "대안적 교육", "기업의 책임", "프라이버시"
        ],
        "count": [5, 8, 3, 4, 6] # 초기 데이터 (나무의 크기)
    }
    st.session_state.forest_df = pd.DataFrame(data)

# --- [로직] GPT 프롬프트 ---
def process_opinion_with_gpt(user_text):
    client = OpenAI(api_key=api_key)
    existing_keywords = ", ".join(st.session_state.forest_df['keyword'].unique())
    
    system_prompt = f"""
    You are a 'Civic Editor'.
    1. REWRITE input into a formal, declarative Korean statement (No "I think", No aggression).
    2. EXTRACT the single most important 'Value Keyword' (Noun form, max 3 words).
    
    * Context: Australia's SNS ban for under-16s.
    * Existing Keywords: [{existing_keywords}]
    
    Format: Keyword|Refined Text
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text}],
            temperature=0.3
        )
        result = response.choices[0].message.content
        keyword, refined = result.split("|", 1)
        return {"refined": refined.strip(), "keyword": keyword.strip()}
    except:
        return None

# --- [로직] 유사도 병합 ---
def merge_opinion(refined_text, keyword, df):
    # 1. 같은 키워드 내에서 유사한 문장이 있는지 확인
    subset = df[df['keyword'] == keyword]
    for idx, row in subset.iterrows():
        similarity = difflib.SequenceMatcher(None, refined_text, row['refined_text']).ratio()
        if similarity >= 0.7: # 70% 이상 유사하면
            return idx, True # 병합 대상 인덱스 반환
            
    # 2. 문장은 안 비슷해도 키워드가 같으면, 키워드 그룹의 카운트를 위해 로직 분리 필요없음 (시각화에서 처리)
    return None, False

# ================= UI 시작 =================

st.title("🌲 Deep Agora: 가치의 숲")

# 1. 뉴스 브리핑 (카드 형태 + 링크)
st.markdown("""
<div class="news-card">
    <h4>📢 [이슈] 호주, 16세 미만 SNS 원천 차단 법안</h4>
    <p style="color: #8B949E;">호주 정부가 청소년 정신건강 보호를 위해 SNS 계정 보유를 금지합니다.<br>
    쟁점: <b>국가의 보호 의무</b> vs <b>기술적 실효성 및 기본권</b></p>
</div>
""", unsafe_allow_html=True)

# 링크 버튼 (새 탭에서 열기)
st.link_button("🔗 관련 기사 원문 보기 (연합뉴스)", "https://www.yna.co.kr/view/AKR20251209006700084?input=1195m")

st.divider()

# 2. 의견 심기 (Action)
col_input, col_btn = st.columns([4, 1])
with col_input:
    user_input = st.text_input("이 사안에서 가장 중요한 가치는 무엇인가요?", placeholder="예: 무조건 막는 건 답이 아닙니다. 교육이 먼저죠.")
with col_btn:
    submit = st.button("숲에 심기 🌱", type="primary", use_container_width=True)

if submit and user_input:
    with st.spinner("AI가 의견을 분석하여 가치의 숲을 키우고 있습니다..."):
        res = process_opinion_with_gpt(user_input)
        if res:
            # 병합 로직
            idx, merged = merge_opinion(res['refined'], res['keyword'], st.session_state.forest_df)
            
            if merged:
                # 문장까지 비슷하면 해당 문장의 카운트 증가
                st.session_state.forest_df.at[idx, 'count'] += 1
                msg = f"'{res['keyword']}' 나무에 물을 주었습니다! 💧"
            else:
                # 새로운 문장이면 추가 (키워드 카운트는 시각화 때 합산됨)
                new_row = {"refined_text": res['refined'], "keyword": res['keyword'], "count": 1}
                st.session_state.forest_df = pd.concat([pd.DataFrame([new_row]), st.session_state.forest_df], ignore_index=True)
                msg = f"새로운 묘목 '{res['keyword']}'을 심었습니다! 🌲"
            
            st.success(msg)
            time.sleep(1.5)
            st.rerun()

st.divider()

# 3. 가치의 숲 시각화 (Treemap) - 여기가 핵심! 🌳
st.subheader("🌳 가치의 지도 (Value Map)")
st.caption("참여자들이 중요하게 생각하는 가치일수록 영역이 넓어집니다.")

if not st.session_state.forest_df.empty:
    df = st.session_state.forest_df
    
    # 시각화를 위해 데이터 가공 (키워드별 합산)
    # path: 계층 구조 (전체 -> 키워드 -> 개별의견)
    # values: 영역 크기 (공감 수)
    fig = px.treemap(
        df, 
        path=[px.Constant("Deep Agora"), 'keyword', 'refined_text'], 
        values='count',
        color='keyword', # 키워드별로 색상 구분
        color_discrete_sequence=px.colors.qualitative.Pastel, # 파스텔톤 컬러
        hover_data=['refined_text']
    )
    
    # 차트 디자인 커스텀 (다크모드 대응)
    fig.update_layout(
        margin=dict(t=0, l=0, r=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)', # 투명 배경
        font=dict(color='#E0E0E0', size=16)
    )
    fig.update_traces(
        root_color="rgba(0,0,0,0)",
        textinfo="label+value", # 라벨과 물방울 수 표시
        hovertemplate='<b>%{label}</b><br>공감(물방울): %{value}개<extra></extra>'
    )
    
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("아직 심어진 나무가 없습니다. 첫 번째 의견을 심어주세요!")

# 4. 세부 목록 (숨김 처리)
with st.expander("📜 의견 전체 목록 보기 (최신순)"):
    st.dataframe(
        st.session_state.forest_df[['keyword', 'refined_text', 'count']].sort_values(by='count', ascending=False),
        column_config={
            "keyword": "핵심 가치",
            "refined_text": "정제된 의견",
            "count": st.column_config.NumberColumn("공감(물)", format="💧 %d")
        },
        hide_index=True,
        use_container_width=True
    )
