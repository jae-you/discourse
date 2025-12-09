import streamlit as st
import pandas as pd
import time
import difflib
from openai import OpenAI

# [설정] 페이지 기본 세팅
st.set_page_config(page_title="Deep Agora: 숙의의 숲", layout="wide", page_icon="🌲")

# --- [스타일] CSS 커스텀 (Dark Forest Theme) ---
st.markdown("""
<style>
    /* 1. 전체 배경: 깊은 숲속 색상 */
    .stApp { background-color: #0E1117; }
    
    /* 2. 텍스트: 눈이 편한 밝은 회색, 볼드체 제거 */
    .stMarkdown, .stText, p, div, span, label, li {
        color: #C1C7D0 !important;
        font-weight: 400 !important;
    }
    
    /* 3. 헤더: 숲의 생명력 (네온 민트) */
    h1, h2, h3, h4 {
        font-family: 'Helvetica Neue', sans-serif;
        color: #69F0AE !important;
        font-weight: 500 !important;
    }

    /* 4. 카드 디자인: 나무 껍질 같은 다크 브라운/그레이 */
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {
        background-color: #1E2329;
        padding: 18px;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.4);
        border-left: 4px solid #69F0AE; /* 왼쪽 포인트 라인 */
    }

    /* 5. 입력창 강조 */
    .stTextInput > div > div > input {
        color: #FFFFFF !important;
        background-color: #2D333B !important;
        border: 1px solid #444C56;
    }

    /* 6. 물방울 뱃지 스타일 */
    .water-badge {
        background-color: #2196F3;
        color: white;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.8em;
        margin-left: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- [보안] API 키 로드 ---
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("⚠️ API 키가 설정되지 않았습니다.")
    st.stop()

# --- 0. 초기 데이터 (동적 키워드 구조) ---
if "forest_df" not in st.session_state:
    data = {
        "original_text": [
            "꼰대들이 뭘 알아? VPN 쓰면 됨.", 
            "애들 망치는 틱톡 금지 찬성!", 
            "기술적으로 막는 건 불가능함.", 
            "알고리즘 중독 심각함.", 
            "개인정보 털어가면서 나이 확인한다고?", 
        ],
        "refined_text": [
            "우회 기술이 보편화된 상황에서 강제적 차단은 실효성이 낮다는 기술적 우려가 있습니다.",
            "청소년 보호를 위해 플랫폼의 유해한 영향력을 규제할 필요성에 깊이 공감합니다.",
            "기술적 차단보다는 미디어 리터러시 교육이 근본적인 해결책이 될 수 있습니다.",
            "알고리즘의 중독성 문제는 심각하며, 기업의 사회적 책임을 강화해야 합니다.",
            "연령 인증 과정에서 발생할 수 있는 과도한 개인정보 수집과 프라이버시 침해를 우려합니다.",
        ],
        "keyword": [ # 고정 카테고리가 아니라, AI가 추출한 핵심 가치
            "기술적 실효성", "청소년 보호", "기술적 실효성", "기업의 책임", "프라이버시"
        ],
        "count": [1, 1, 3, 2, 2] # 공감 수 (물 주기)
    }
    st.session_state.forest_df = pd.DataFrame(data)

# --- [로직] 유사도 병합 (Smart Merging) ---
def merge_similar_opinion(new_text, df):
    """
    새로운 의견이 기존 의견과 65% 이상 유사하면 병합(Merge)합니다.
    """
    threshold = 0.65 
    best_match_idx = None
    best_match_score = 0
    
    for index, row in df.iterrows():
        similarity = difflib.SequenceMatcher(None, new_text, row['refined_text']).ratio()
        if similarity > best_match_score:
            best_match_score = similarity
            best_match_idx = index
            
    if best_match_score >= threshold:
        return best_match_idx
    return None

# --- [로직] GPT 프롬프트 (Keyword Extraction) ---
def process_opinion_with_gpt(user_text):
    client = OpenAI(api_key=api_key)
    
    # 기존 키워드 리스트를 힌트로 줌 (파편화 방지)
    existing_keywords = ", ".join(st.session_state.forest_df['keyword'].unique())
    
    system_prompt = f"""
    You are a 'Civic Editor'. 
    Task 1: REWRITE user's input into a formal, constructive Korean statement (Declarative tone).
    Task 2: EXTRACT the single most important 'Value Keyword' (max 3 words). 
    
    * Context: Debate on banning SNS for under-16s in Australia.
    * Existing Keywords (Try to reuse if applicable): [{existing_keywords}]
    
    Format: Keyword|Refined Text
    
    Examples:
    Input: "VPN 쓰면 그만인데 바보짓임" -> Output: 기술적 실효성|우회 기술이 존재하는 상황에서 단순 차단은 효과가 제한적이라는 지적입니다.
    Input: "애들 다 망치는 틱톡 없애라" -> Output: 청소년 보호|유해 플랫폼으로부터 청소년을 보호하기 위한 강력한 조치가 필요합니다.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            temperature=0.3
        )
        result = response.choices[0].message.content
        if "|" in result:
            keyword, refined = result.split("|", 1)
            return {"refined": refined.strip(), "keyword": keyword.strip()}
        else:
            return None
    except:
        return None

# ================= UI 시작 =================

st.title("🌲 Deep Agora: 숙의의 숲")
st.caption("우리의 의견이 모여 숲을 이룹니다. 승패 대신 가치를 심어주세요.")

# 1. 뉴스 브리핑 (Context)
with st.container():
    st.markdown("#### 📢 [이슈] 호주, 16세 미만 SNS 원천 차단 법안")
    st.markdown("""
    호주 정부가 청소년의 정신건강 보호를 위해 SNS 계정 보유를 금지합니다.
    **핵심 쟁점:** "국가의 적극적 보호 의무" vs "기술적 우회 가능성 및 기본권 침해"
    """)

st.divider()

# 2. 의견 심기 (Action First) - "먼저 내 생각을 정리해보세요"
st.markdown("#### 👩‍🌾 이 사안에 대해 어떻게 생각하시나요?")

col_input, col_opt = st.columns([3, 1])

with col_input:
    user_input = st.text_area("당신의 의견을 심어주세요", height=100, placeholder="비난보다는 이유와 대안을 적어주시면, AI가 품격 있는 문장으로 다듬어 숲에 심습니다.")

with col_opt:
    st.markdown("<br>", unsafe_allow_html=True) # 줄맞춤
    # 순도 슬라이더 (원하는 필터링 강도)
    purity_level = st.slider("AI 정제 강도", 0, 100, 70, help="높을수록 거친 표현이 더 부드럽게 순화됩니다.")
    submit_btn = st.button("숲에 심기 🌱", type="primary", use_container_width=True)

# 로직 처리
if submit_btn and user_input:
    with st.spinner("AI가 문장을 다듬고, 비슷한 의견이 있는지 숲을 살피고 있습니다..."):
        result = process_opinion_with_gpt(user_input)
        
        if result:
            refined_text = result['refined']
            keyword = result['keyword']
            
            # 중복 체크 (Merging)
            merged_idx = merge_similar_opinion(refined_text, st.session_state.forest_df)
            
            if merged_idx is not None:
                # 병합: 카운트만 증가
                st.session_state.forest_df.at[merged_idx, 'count'] += 1
                msg = f"숲에 이미 비슷한 나무가 자라고 있어 물을 주었습니다! (공감 +1) 💧"
            else:
                # 신규 생성
                new_row = {
                    "original_text": user_input,
                    "refined_text": refined_text,
                    "keyword": keyword,
                    "count": 1
                }
                st.session_state.forest_df = pd.concat([pd.DataFrame([new_row]), st.session_state.forest_df], ignore_index=True)
                msg = f"'{keyword}' 구역에 새로운 나무를 심었습니다! 🌲"
            
            st.success(msg)
            time.sleep(1.5)
            st.rerun()
        else:
            st.error("오류가 발생했습니다. 다시 시도해주세요.")

st.divider()

# 3. 숙의의 숲 (Forest View) - "남들의 생각 보기"
st.markdown("#### 🌳 지금 우리 사회가 가꾸고 있는 가치의 숲")

df = st.session_state.forest_df

# [동적 숲 로직] 키워드별로 그룹화하여, 카운트(공감)가 많은 순서대로 표시
keyword_counts = df.groupby("keyword")['count'].sum().sort_values(ascending=False)

# 상위 3개 키워드는 크게 보여줌 (Main Trees)
top_keywords = keyword_counts.index.tolist()

for keyword in top_keywords:
    # 해당 키워드의 의견들만 추출
    keyword_df = df[df['keyword'] == keyword].sort_values(by='count', ascending=False)
    total_votes = keyword_counts[keyword]
    
    # 아코디언 형태로 숲을 표현 (가장 큰 나무가 먼저 보임)
    with st.expander(f"🌲 {keyword} (공감 {total_votes}명)", expanded=True if total_votes > 2 else False):
        for _, row in keyword_df.iterrows():
            col_text, col_badge = st.columns([5, 1])
            with col_text:
                st.write(row['refined_text'])
                # 원문은 아주 작게 토글 없이 툴팁처럼 제공하거나 숨김 (깔끔함 유지)
            with col_badge:
                if row['count'] > 1:
                    st.markdown(f"<span class='water-badge'>💧 {row['count']}</span>", unsafe_allow_html=True)
            st.markdown("---") # 구분선

st.caption("※ 이 숲의 나무들은 참여자들의 의견을 AI가 실시간으로 분류하고 정제하여 자라납니다.")
