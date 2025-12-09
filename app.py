import streamlit as st
import pandas as pd
import random
import time
from openai import OpenAI

# [설정] 페이지 기본 세팅
st.set_page_config(page_title="Deep Agora: 숙의의 정원", layout="wide", page_icon="🌿")

# --- 0. 초기 데이터 및 상태 설정 (Session State) ---
# 새로고침해도 데이터가 날아가지 않도록 session_state에 저장합니다.
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

# --- 1. OpenAI 연동 함수 (논문의 Collaborative Prompt 적용) ---
def process_opinion_with_gpt(api_key, user_text):
    """
    GPT를 사용하여 1) 패러프레이징(협력적 스타일) 2) 주제 분류를 수행합니다.
    """
    if not api_key:
        # 키가 없을 경우 시뮬레이션 모드 동작
        time.sleep(1)
        return {
            "refined": f"(시뮬레이션) {user_text} - 라는 의견을 협력적으로 다듬었습니다.",
            "topic": random.choice(["실효성 및 기술", "보호 및 규제 필요성", "프라이버시/기본권"]),
            "score": random.uniform(0.7, 0.95)
        }

    client = OpenAI(api_key=api_key)
    
    # 논문 Appendix A의 Collaborative Prompt + 주제 분류 요청
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
            model="gpt-4o-mini", # 또는 gpt-3.5-turbo
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ]
        )
        result = response.choices[0].message.content
        topic, refined = result.split("|", 1)
        return {"refined": refined.strip(), "topic": topic.strip(), "score": 0.95} # New inputs get high visibility initially
    except Exception as e:
        st.error(f"OpenAI Error: {e}")
        return None

# --- 2. UI: 헤더 및 뉴스 브리핑 (Context Injection) ---
st.title("🌿 Deep Agora: 의견 정원")

# [중요] 뉴스 브리핑 섹션 (사용자가 맥락을 파악하도록 함)
with st.container(border=True):
    col_news_l, col_news_r = st.columns([1, 4])
    with col_news_l:
        st.image("https://img.icons8.com/fluency/96/news.png", width=80)
    with col_news_r:
        st.subheader("📢 [이슈] 호주, 16세 미만 SNS 사용 원천 차단 추진")
        st.markdown("""
        **핵심 내용:** 호주 정부가 세계 최초로 16세 미만 청소년의 소셜미디어(SNS) 계정 보유를 금지하는 법안을 시행합니다. 
        기업은 연령 확인 의무를 지며 위반 시 거액의 벌금을 물게 됩니다.
        
        **논의 쟁점:**
        * 🛡️ **찬성:** "청소년 정신건강 보호 및 중독 방지"
        * 🚫 **반대:** "실효성 부족(VPN 우회), 프라이버시 침해, 청소년 소통 권리 박탈"
        """)

st.divider()

# --- 3. 사이드바 및 필터 ---
with st.sidebar:
    st.header("⚙️ 설정 & 필터")
    
    # OpenAI API Key 입력 (비밀번호 타입)
    api_key = st.text_input("OpenAI API Key", type="password", help="키를 입력하면 실제 AI가 동작합니다. 없으면 시뮬레이션 모드로 작동합니다.")
    
    st.divider()
    st.caption("정원 가꾸기")
    min_quality = st.slider("품격 필터 (욕설/비난 제외)", 0.0, 1.0, 0.4)
    st.info("💡 '품격 필터'를 높이면 감정적인 소음은 사라지고 논리적인 신호만 남습니다.")

# --- 4. 메인 화면: 의견 정원 (DataFrame 기반 렌더링) ---
df = st.session_state.comments_df # Session State에서 데이터 로드

col1, col2, col3 = st.columns(3)
topics = ["실효성 및 기술", "보호 및 규제 필요성", "프라이버시/기본권"] # 고정된 3개 주제 화분
cols = [col1, col2, col3]

for i, topic in enumerate(topics):
    with cols[i]:
        st.subheader(f"📌 {topic}")
        
        # 필터링 및 정렬
        topic_df = df[
            (df["topic_cluster"] == topic) & 
            (df["civility_score"] >= min_quality)
        ].sort_values(by="representative_score", ascending=False)
        
        for idx, row in topic_df.head(4).iterrows(): # 상위 4개까지만 표시
            with st.container(border=True):
                # AI 정제 텍스트 강조
                st.markdown(f"**🗣️ {row['refined_text']}**")
                st.progress(row['representative_score'], text="논리적 대표성")
                
                # 원문 보기 (투명성)
                with st.expander("원문 확인"):
                    st.caption(f"Original: {row['original_text']}")

# --- 5. 의견 심기 (Action Section) ---
st.divider()
st.markdown("### 🌱 정원에 당신의 의견 심기")

with st.container(border=True):
    col_input, col_btn = st.columns([5, 1])
    
    with col_input:
        new_opinion = st.text_input("의견을 입력하세요", placeholder="예: 무조건 막는다고 해결될까요? 교육이 더 중요하다고 봅니다.")
    
    with col_btn:
        st.write("") # 줄맞춤용
        st.write("") 
        submit_btn = st.button("심기", use_container_width=True, type="primary")

    if submit_btn and new_opinion:
        with st.spinner("AI가 당신의 의견을 다듬어 정원에 심고 있습니다..."):
            # 1. GPT 호출 (또는 시뮬레이션)
            processed_data = process_opinion_with_gpt(api_key, new_opinion)
            
            if processed_data:
                # 2. DataFrame에 새 행 추가
                new_row = {
                    "original_text": new_opinion,
                    "refined_text": processed_data["refined"],
                    "topic_cluster": processed_data["topic"], # AI가 분류한 주제로 자동 배정
                    "civility_score": 1.0, # 방금 심은 의견은 우선 필터 통과하도록 설정
                    "representative_score": processed_data["score"]
                }
                
                # Session State 업데이트
                st.session_state.comments_df = pd.concat(
                    [pd.DataFrame([new_row]), st.session_state.comments_df], 
                    ignore_index=True
                )
                
                st.success("의견이 성공적으로 반영되었습니다! 위쪽 정원에서 확인해보세요.")
                time.sleep(1.5)
                st.rerun() # 화면 새로고침하여 즉시 반영

# --- 6. 하단: 공통의 기반 ---
st.markdown("---")
st.subheader("🌉 Consensus (합의된 기반)")
st.info("현재까지 참여자의 **88%**가 '청소년 보호의 대원칙'과 '실효성 있는 기술적 대안 마련'의 필요성에 동의했습니다.")
