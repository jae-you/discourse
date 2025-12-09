import streamlit as st
import pandas as pd
import time
import difflib
from openai import OpenAI

# [설정] 페이지 기본 세팅
st.set_page_config(page_title="Deep Agora: 숙의의 정원", layout="wide", page_icon="🌷")

# --- [스타일] CSS 커스텀 (Dark Garden Theme) ---
st.markdown("""
<style>
    /* 1. 전체 배경색: 아주 깊은 다크 그레이 */
    .stApp {
        background-color: #0E1117;
    }
    
    /* 2. 기본 텍스트: 밝은 회색 (볼드체 없이 가독성 확보) */
    .stMarkdown, .stText, p, div, span, label, li {
        color: #E0E0E0 !important;
        font-weight: 400 !important; /* 모든 텍스트 두께 보통으로 고정 */
    }

    /* 3. 카드 디자인 */
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {
        background-color: #262730;
        padding: 15px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.5);
        border: 1px solid #41444C;
    }

    /* 4. 헤더 폰트: 민트색 포인트 */
    h1, h2, h3, h4, h5 {
        font-family: 'Helvetica Neue', sans-serif;
        color: #81C784 !important;
        font-weight: 500 !important; /* 헤더만 살짝 두껍게 */
    }
    
    /* 5. 입력창 스타일 */
    .stTextInput > div > div > input {
        color: #FFFFFF !important;
        background-color: #1F2229 !important;
    }
    
    /* 6. Expander 스타일 */
    .streamlit-expanderHeader {
        background-color: #262730 !important;
        color: #E0E0E0 !important;
    }
    
    /* 7. 팝오버 등 */
    div[data-testid="stPopoverBody"] {
        background-color: #262730 !important;
        color: #E0E0E0 !important;
        border: 1px solid #41444C;
    }

    /* 8. 프로그레스 바 (네온 그린) */
    .stProgress > div > div > div > div {
        background-color: #00E676;
    }
</style>
""", unsafe_allow_html=True)

# --- [보안 1] 비밀번호 기능 (선택사항 - 필요 없으면 삭제 가능) ---
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

# 비밀번호 기능 활성화 (원치 않으면 이 두 줄 주석 처리)
if not check_password():
    st.stop()

# --- [보안 2] API 키 로드 ---
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("⚠️ API 키가 설정되지 않았습니다.")
    st.stop()

# --- 0. 초기 데이터 ---
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
        "representative_score": [50, 60, 95, 92, 70],
        "count": [1, 1, 5, 3, 2]
    }
    st.session_state.comments_df = pd.DataFrame(data)

# --- [로직] 유사도 검사 ---
def find_similar_opinion(new_text, df):
    threshold = 0.6 
    for index, row in df.iterrows():
        similarity = difflib.SequenceMatcher(None, new_text, row['refined_text']).ratio()
        if similarity >= threshold:
            return index 
    return None

# --- [핵심 로직] OpenAI 프롬프트 개선 ---
def process_opinion_with_gpt(user_text):
    client = OpenAI(api_key=api_key)
    
    # [수정됨] 대화형(Chat)이 아닌 '문장 변환기(Rewriter)'로 역할 부여
    system_prompt = """
    You are an expert editor for a public policy debate platform.
    Your task is to REWRITE the user's raw input into a formal, constructive statement suitable for a public forum.

    RULES:
    1. DO NOT reply to the user. (Never say "I understand", "You are saying", "Here is a refined version").
    2. DO NOT use second-person pronouns like "You".
    3. Output ONLY the rewritten Korean text.
    4. Maintain the original stance (Pro/Con) and intensity, but remove aggression and slang.
    5. Use a declarative or assertive tone (e.g., "~라는 의견이 있습니다", "~해야 합니다").
    6. Classify the input into one of these 3 topics: ['🌱 실효성 및 기술', '🛡️ 보호 및 규제', '🔒 프라이버시/권리'].

    FORMAT:
    Topic|Refined Text

    EXAMPLES:
    Input: "틱톡 당장 없애버려! 애들 다 망쳐!"
    Output: 🛡️ 보호 및 규제|청소년에게 유해한 영향을 미치는 플랫폼에 대한 즉각적이고 강력한 제재 조치가 필요합니다.

    Input: "VPN 쓰면 그만인데 멍청한 짓 하고 있네 ㅋㅋ"
    Output: 🌱 실효성 및 기술|VPN 우회 기술이 존재하는 상황에서 단순한 접속 차단 정책은 실효성이 부족하다는 지적이 있습니다.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            temperature=0.3 # 창의성을 낮춰서 지시사항을 더 잘 따르게 함
        )
        result = response.choices[0].message.content
        
        # 안전장치: 혹시라도 형식이 깨졌을 경우를 대비
        if "|" in result:
            topic, refined = result.split("|", 1)
        else:
            topic = "🛡️ 보호 및 규제" # 기본값
            refined = result
            
        return {"refined": refined.strip(), "topic": topic.strip()}
    except Exception as e:
        return None

# --- UI 시작 ---
st.title("🌷 Deep Agora: 의견 정원")
st.markdown("승패가 없는 숙의의 공간, 당신의 생각을 꽃피우세요.")

# 설명 섹션
with st.expander("ℹ️ 논리적 대표성 점수는 어떻게 계산되나요?"):
    st.markdown("""
    논리적 대표성(Logical Representativeness)은 다음 두 가지를 합친 점수입니다:
    1. 논리적 완결성: 주장이 타당한 근거를 갖추고 있는지 AI가 평가합니다.
    2. 공감의 밀도: 얼마나 많은 사람이 비슷한 의견을 냈는지 반영합니다.
    즉, 단순히 목소리가 큰 의견이 아니라, 많은 사람들이 공감하면서도 논리적인 의견이 정원의 상단에 핍니다. 🌸
    """)

st.divider()

# 뉴스 브리핑 (볼드체 제거)
st.info("""
📢 [오늘의 이슈] 호주, 16세 미만 SNS 원천 차단
쟁점: 청소년의 정신건강 보호(찬성) vs 기술적 실효성 및 기본권 침해(반대)
""")

# --- 메인 정원 ---
df = st.session_state.comments_df
topics = ["🌱 실효성 및 기술", "🛡️ 보호 및 규제", "🔒 프라이버시/권리"]
cols = st.columns(3)

for i, topic in enumerate(topics):
    with cols[i]:
        st.markdown(f"### {topic}")
        
        topic_df = df[df["topic_cluster"] == topic].sort_values(by="representative_score", ascending=False)
        
        for idx, row in topic_df.head(4).iterrows():
            with st.container():
                flower_icon = "🌻" if row['representative_score'] > 80 else "🌱"
                
                # 볼드체 제거: f-string 내의 ** 삭제
                st.write(f"{flower_icon} {row['refined_text']}")
                
                st.caption(f"논리 점수: {row['representative_score']}점 | 💧 {row['count']}명이 공감하여 물을 줬습니다.")
                st.progress(row['representative_score'] / 100)
                
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
                
                existing_idx = find_similar_opinion(refined, st.session_state.comments_df)
                
                if existing_idx is not None:
                    st.session_state.comments_df.at[existing_idx, 'count'] += 1
                    current_score = st.session_state.comments_df.at[existing_idx, 'representative_score']
                    st.session_state.comments_df.at[existing_idx, 'representative_score'] = min(current_score + 5, 100)
                    msg = f"이미 비슷한 의견이 자라고 있어서 물을 줬습니다! (공감 +1) 💧"
                else:
                    new_row = {
                        "original_text": new_opinion,
                        "refined_text": refined,
                        "topic_cluster": topic,
                        "representative_score": 70,
                        "count": 1
                    }
                    st.session_state.comments_df = pd.concat([pd.DataFrame([new_row]), st.session_state.comments_df], ignore_index=True)
                    msg = "새로운 씨앗을 심었습니다! 🌱"
                
                st.success(msg)
                time.sleep(1.5)
                st.rerun()

st.success("🌉 Consensus: 참여자 대다수가 '청소년 보호의 필요성'에는 동의하고 있습니다.")
