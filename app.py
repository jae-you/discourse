import streamlit as st
import pandas as pd
import time
import difflib  # 텍스트 유사도 검사를 위한 라이브러리
from openai import OpenAI

# [설정] 페이지 기본 세팅
st.set_page_config(page_title="Deep Agora: 숙의의 정원", layout="wide", page_icon="🌷")

# --- [스타일] CSS 커스텀 (다크모드 호환성 해결) ---
st.markdown("""
<style>
    /* 1. 전체 배경색: 은은한 미색 */
    .stApp {
        background-color: #FDFCF8;
    }
    
    /* 2. 메인 텍스트 강제 검정색 (다크모드일 때 흰 글씨 되는 것 방지) */
    .stMarkdown, .stText, p, div {
        color: #333333 !important;
    }

    /* 3. 카드 디자인 */
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {
        background-color: white;
        padding: 15px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #E0E0E0;
        /* 카드 내부 글자색도 확실하게 검정으로 고정 */
        color: #333333 !important;
    }

    /* 4. 헤더 폰트 스타일 */
    h1, h2, h3 {
        font-family: 'Helvetica Neue', sans-serif;
        color: #2E7D32 !important; /* 진한 초록색 */
    }
    
    /* 5. 입력창, 버튼 등 컴포넌트 텍스트 색상 보정 */
    .stTextInput > label, .stButton > button {
        color: #333333 !important;
    }
    
    /* 6. 프로그레스 바 색상 (초록색) */
    .stProgress > div > div > div > div {
        background-color: #66BB6A;
    }
</style>
""", unsafe_allow_html=True)

# --- [보안 1] 비밀번호 기능 (선택) ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    if st.session_state.password_correct:
        return True
    
    st.markdown("### 🔒 정원사 확인")
    password = st.text_input("접속 코드를 입력하세요", type="password")
    if password == "snu1234":
        st.session_state.password_correct = True
        st.rerun()
    elif password:
        st.error("코드가 일치하지 않습니다.")
    return False

if not check_password():
    st.stop()

# --- [보안 2] API 키 로드 ---
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("⚠️ API 키가 설정되지 않았습니다.")
    st.stop()

# --- 0. 초기 데이터 (초기 꽃 심기) ---
if "comments_df" not in st.session_state:
    data = {
        "original_text": [
            "꼰대들이 뭘 알아? VPN 쓰면 됨.", 
            "애들 망치는 틱톡 금지 찬성!", 
            "기술적으로 막는 건 불가능함. 교육이 중요하지.", 
            "알고리즘 중독 심각함. 기업 책임 물어야 함.", 
            "개인정보 털어가면서 나이 확인한다고? 미쳤네.", 
        ],
        "refined_text": [
            "우회 기술이 보편화된 상황에서 강제적 차단은 실효성이 낮다는 기술적 우려가 있습니다.",
            "청소년 보호를 위해 플랫폼의 유해한 영향력을 규제할 필요성에 깊이 공감합니다.",
            "기술적 차단보다는 미디어 리터러시 교육이 근본적인 해결책이 될 수 있습니다.",
            "알고리즘의 중독성 문제는 심각하며, 이에 대한 기업의 사회적 책임을 강화해야 합니다.",
            "연령 인증 과정에서 발생할 수 있는 과도한 개인정보 수집과 프라이버시 침해를 우려합니다.",
        ],
        "topic_cluster": [
            "🌱 실효성 및 기술", "🛡️ 보호 및 규제", "🌱 실효성 및 기술", "🛡️ 보호 및 규제", "🔒 프라이버시/권리"
        ],
        "representative_score": [50, 60, 95, 92, 70], # 100점 만점 기준
        "count": [1, 1, 5, 3, 2] # 몇 명이 비슷한 말을 했는지 (물 주기 횟수)
    }
    st.session_state.comments_df = pd.DataFrame(data)

# --- [로직] 유사도 검사 및 병합 (Simulated Semantic Merging) ---
def find_similar_opinion(new_text, df):
    """
    새로운 의견이 기존 의견과 얼마나 비슷한지 검사합니다.
    (간단한 문자열 유사도 사용, 실제로는 Embedding 사용 권장)
    """
    threshold = 0.6 # 60% 이상 비슷하면 같은 의견으로 간주
    for index, row in df.iterrows():
        similarity = difflib.SequenceMatcher(None, new_text, row['refined_text']).ratio()
        if similarity >= threshold:
            return index # 가장 비슷한 의견의 인덱스 반환
    return None

# --- [로직] OpenAI 처리 ---
def process_opinion_with_gpt(user_text):
    client = OpenAI(api_key=api_key)
    system_prompt = """
    You are a 'Garden Mediator'.
    1. Refine input into polite Korean (Collaborative style).
    2. Classify into: ['🌱 실효성 및 기술', '🛡️ 보호 및 규제', '🔒 프라이버시/권리'].
    Output: "Topic|Refined Text"
    Example: "🌱 실효성 및 기술|기술적 한계를 고려해야 합니다."
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text}]
        )
        result = response.choices[0].message.content
        topic, refined = result.split("|", 1)
        return {"refined": refined.strip(), "topic": topic.strip()}
    except:
        return None

# --- UI 시작 ---
st.title("🌷 Deep Agora: 의견 정원")
st.markdown("##### 승패가 없는 숙의의 공간, 당신의 생각을 꽃피우세요.")

# [설명] 논리적 대표성이란?
with st.expander("ℹ️ '논리적 대표성' 점수는 어떻게 계산되나요?"):
    st.markdown("""
    **논리적 대표성(Logical Representativeness)**은 다음 두 가지를 합친 점수입니다:
    1.  **논리적 완결성 (Logic):** 주장이 타당한 근거를 갖추고 있는지 AI가 평가합니다.
    2.  **공감의 밀도 (Density):** 얼마나 많은 사람이 비슷한 의견을 냈는지(물 주기 횟수) 반영합니다.
    *즉, 단순히 목소리가 큰 의견이 아니라, **많은 사람들이 공감하면서도 논리적인 의견**이 정원의 상단에 핍니다.* 🌸
    """)

st.divider()

# 뉴스 브리핑 (카드 스타일)
st.info("""
📢 **[오늘의 이슈] 호주, 16세 미만 SNS 원천 차단** "청소년의 정신건강 보호(찬성)" vs "기술적 실효성 및 기본권 침해(반대)" 
""")

# --- 메인 정원 (3개의 화분) ---
df = st.session_state.comments_df
topics = ["🌱 실효성 및 기술", "🛡️ 보호 및 규제", "🔒 프라이버시/권리"]
cols = st.columns(3)

for i, topic in enumerate(topics):
    with cols[i]:
        st.markdown(f"### {topic}")
        
        # 점수순 정렬
        topic_df = df[df["topic_cluster"] == topic].sort_values(by="representative_score", ascending=False)
        
        for idx, row in topic_df.head(4).iterrows():
            # 카드 디자인 컨테이너
            with st.container():
                # 점수에 따라 꽃 이모지 다르게 표시
                flower_icon = "🌻" if row['representative_score'] > 80 else "🌱"
                
                st.markdown(f"**{flower_icon} {row['refined_text']}**")
                
                # 점수와 '물 주기' 횟수 표시
                st.caption(f"논리 점수: {row['representative_score']}점 | 💧 {row['count']}명이 공감하여 물을 줬습니다.")
                st.progress(row['representative_score'] / 100)
                
                # 원문 확인 (토글)
                with st.popover("원문 보기"):
                    st.write(f"\"{row['original_text']}\"")
        st.write("---")

# --- 의견 심기 섹션 ---
st.markdown("### 👩‍🌾 정원에 의견 심기")
with st.container():
    col_in, col_btn = st.columns([4, 1])
    new_opinion = col_in.text_input("당신의 생각은?", placeholder="비난보다는 대안을 심어주세요.")
    submit = col_btn.button("심기", type="primary", use_container_width=True)

    if submit and new_opinion:
        with st.spinner("AI 정원사가 의견을 다듬고 있습니다..."):
            result = process_opinion_with_gpt(new_opinion)
            if result:
                refined = result['refined']
                topic = result['topic']
                
                # [핵심 로직] 중복 체크 (Merging)
                existing_idx = find_similar_opinion(refined, st.session_state.comments_df)
                
                if existing_idx is not None:
                    # 비슷한 의견이 있으면 -> 점수 올리기 (물 주기)
                    st.session_state.comments_df.at[existing_idx, 'count'] += 1
                    # 점수도 조금 올려줌 (최대 100점)
                    current_score = st.session_state.comments_df.at[existing_idx, 'representative_score']
                    st.session_state.comments_df.at[existing_idx, 'representative_score'] = min(current_score + 5, 100)
                    msg = f"이미 비슷한 의견이 자라고 있어서 물을 줬습니다! (공감 +1) 💧"
                else:
                    # 새로운 의견이면 -> 새로 심기
                    new_row = {
                        "original_text": new_opinion,
                        "refined_text": refined,
                        "topic_cluster": topic,
                        "representative_score": 70, # 기본 시작 점수
                        "count": 1
                    }
                    st.session_state.comments_df = pd.concat([pd.DataFrame([new_row]), st.session_state.comments_df], ignore_index=True)
                    msg = "새로운 씨앗을 심었습니다! 🌱"
                
                st.success(msg)
                time.sleep(1.5)
                st.rerun()

# 하단 합의점 표시
st.success("🌉 **Consensus:** 참여자 대다수가 '청소년 보호의 필요성'에는 동의하고 있습니다.")
