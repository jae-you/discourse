import streamlit as st
import pandas as pd
import random
import time
from openai import OpenAI

# [설정] 페이지 기본 세팅
st.set_page_config(page_title="Deep Agora: 숙의의 정원", layout="wide", page_icon="🌿")

# --- [보안 1] 간단한 비밀번호 기능 (선택 사항) ---
# 외부인이 아무나 들어와서 API를 남용하지 못하게 막습니다.
def check_password():
    """로그인 성공 여부를 반환합니다."""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    st.markdown("### 🔒 접속 권한 확인")
    password = st.text_input("비밀번호를 입력하세요", type="password")
    
    # [설정] 원하는 비밀번호를 'snu1234' 부분에 바꾸세요
    if password == "snu1234":
        st.session_state.password_correct = True
        st.rerun()
    elif password:
        st.error("비밀번호가 틀렸습니다.")
    
    return False

# 비밀번호가 틀리면 여기서 멈춤 (앱 내용 안 보여줌)
if not check_password():
    st.stop()

# --- [보안 2] API 키 로드 (Secrets 우선 사용) ---
# 로컬에서는 secrets.toml을, 배포 서버에서는 Cloud Secrets를 자동으로 가져옵니다.
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("⚠️ API 키가 설정되지 않았습니다. 관리자에게 문의하세요.")
    st.stop()

# --- 0. 초기 데이터 및 상태 설정 ---
if "comments_df" not in st.session_state:
    data = {
        "original_text": [
            "꼰대들이 뭘 알아? VPN 쓰면 됨.", 
            "애들 망치는 틱톡 금지 찬성!", 
            "기술적으로 막는 건 불가능함. 교육이 중요하지.", 
            "알고리즘 중독 심각함. 기업 책임 물어야 함.", 
            "개인정보 털어가면서 나이 확인한다고? 미쳤네.", 
            "부모가 관리해야지 왜 국가가 나서?", 
            "청소년도 시민인데 기본권 침해임."
        ],
        "refined_text": [
            "우회 기술이 보편화된 상황에서 강제적 차단은 실효성이 낮다는 기술적 우려가 있습니다.",
            "청소년 보호를 위해 플랫폼의 유해한 영향력을 규제할 필요성에 깊이 공감합니다.",
            "기술적 차단보다는 미디어 리터러시 교육이 근본적인 해결책이 될 수 있습니다.",
            "알고리즘의 중독성 문제는 심각하며, 이에 대한 기업의 사회적 책임을 강화해야 합니다.",
            "연령 인증 과정에서 발생할 수 있는 과도한 개인정보 수집과 프라이버시 침해를 우려합니다.",
            "국가의 일괄적 규제보다는 가정 내에서의 지도와 자율성이 우선시되어야 한다고 생각합니다.",
            "청소년의 디지털 정보 접근권과 자기결정권 또한 중요한 가치로 고려되어야 합니다."
        ],
        "topic_cluster": [
            "실효성 및 기술", "보호 및 규제 필요성", "실효성 및 기술", "보호 및 규제 필요성", "프라이버시/기본권", "프라이버시/기본권", "프라이버시/기본권"
        ],
        "civility_score": [0.2, 0.3, 0.85, 0.9, 0.4, 0.75, 0.8],
        "representative_score": [0.5, 0.6, 0.95, 0.92, 0.7, 0.88, 0.85]
    }
    st.session_state.comments_df = pd.DataFrame(data)

# --- 1. OpenAI 연동 함수 ---
def process_opinion_with_gpt(user_text):
    client = OpenAI(api_key=api_key)
    
    # 논문 기반 '협력적(Collaborative)' 스타일 프롬프트
    system_prompt = """
    You are a 'Mediation Machine' specializing in the COLLABORATING style.
    Your task:
    1. Refine the user's input into Korean. Maintain assertiveness but use cooperative phrasing.
    2. Classify the input into one of these 3 topics: ['실효성 및 기술', '보호 및 규제 필요성', '프라이버시/기본권'].
    
    Output format must be exactly: "Topic|Refined Text"
    Example: "실효성 및 기술|기술적 한계에 대해 함께 고민해봐야 합니다."
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ]
        )
        result = response.choices[0].message.content
        topic, refined = result.split("|", 1)
        return {"refined": refined.strip(), "topic": topic.strip(), "score": 0.95}
    except Exception as e:
        st.error(f"AI 처리 중 오류가 발생했습니다: {e}")
        return None

# --- 2. UI: 헤더 및 뉴스 브리핑 (Context Injection) ---
st.title("🌿 Deep Agora: 의견 정원")

# [중요] 뉴스 브리핑 섹션 (사용자가 맥락을 파악하도록 함)
with st.container(border=True):
    col_news_l, col_news_r = st.columns([1, 5])
    with col_news_l:
        st.write("📢 **[이슈 브리핑]**")
    with col_news_r:
        st.subheader("호주, 16세 미만 SNS 사용 원천 차단 추진")
        st.markdown("""
        **핵심 내용:** 호주 정부가 16세 미만 청소년의 소셜미디어 계정 보유를 금지하는 법안을 시행합니다. 
        기업은 연령 확인 의무를 지며 위반 시 거액의 벌금을 뭅니다.
        
        **주요 쟁점:**
        * 🛡️ **찬성:** "청소년 정신건강 보호 및 중독 방지"
        * 🚫 **반대:** "실효성 부족(우회 가능), 프라이버시 침해, 소통 권리 박탈"
        """)

st.divider()

# --- 3. 사이드바 (필터만 남김) ---
with st.sidebar:
    st.header("⚙️ 정원 가꾸기")
    st.caption("✅ 공용 AI 엔진이 가동 중입니다.") # 사용자 안심 멘트
    
    min_quality = st.slider("품격 필터 (욕설/비난 제외)", 0.0, 1.0, 0.4)
    st.info("💡 '품격 필터'를 높이면 감정적인 소음은 사라지고 논리적인 신호만 남습니다.")

# --- 4. 메인 화면: 의견 정원 ---
df = st.session_state.comments_df

col1, col2, col3 = st.columns(3)
topics = ["실효성 및 기술", "보호 및 규제 필요성", "프라이버시/기본권"]
cols = [col1, col2, col3]

for i, topic in enumerate(topics):
    with cols[i]:
        st.subheader(f"📌 {topic}")
        
        topic_df = df[
            (df["topic_cluster"] == topic) & 
            (df["civility_score"] >= min_quality)
        ].sort_values(by="representative_score", ascending=False)
        
        for idx, row in topic_df.head(4).iterrows():
            with st.container(border=True):
                st.markdown(f"**🗣️ {row['refined_text']}**")
                st.progress(row['representative_score'], text="논리적 대표성")
                
                with st.expander("원문 확인"):
                    st.caption(f"Original: {row['original_text']}")

# --- 5. 의견 심기 ---
st.divider()
st.markdown("### 🌱 정원에 당신의 의견 심기")

with st.container(border=True):
    col_input, col_btn = st.columns([5, 1])
    
    with col_input:
        new_opinion = st.text_input("의견을 입력하세요", placeholder="예: 무조건 막는다고 해결될까요? 교육이 더 중요하다고 봅니다.")
    
    with col_btn:
        st.write("")
        st.write("")
        submit_btn = st.button("심기", use_container_width=True, type="primary")

    if submit_btn and new_opinion:
        with st.spinner("AI가 당신의 의견을 다듬어 정원에 심고 있습니다..."):
            processed_data = process_opinion_with_gpt(new_opinion)
            
            if processed_data:
                new_row = {
                    "original_text": new_opinion,
                    "refined_text": processed_data["refined"],
                    "topic_cluster": processed_data["topic"],
                    "civility_score": 1.0,
                    "representative_score": processed_data["score"]
                }
                
                st.session_state.comments_df = pd.concat(
                    [pd.DataFrame([new_row]), st.session_state.comments_df], 
                    ignore_index=True
                )
                
                st.success("의견이 반영되었습니다!")
                time.sleep(1)
                st.rerun()

# --- 6. 하단: 공통의 기반 ---
st.markdown("---")
st.subheader("🌉 Consensus (합의된 기반)")
st.info("현재까지 참여자의 **88%**가 '청소년 보호의 대원칙'과 '실효성 있는 기술적 대안 마련'의 필요성에 동의했습니다.")
