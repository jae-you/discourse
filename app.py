import streamlit as st
import pandas as pd
import time
from openai import OpenAI

# [설정] 페이지 기본 세팅
st.set_page_config(page_title="Deep Agora: 숙의 리포트", layout="wide", page_icon="📝")

# --- [스타일] CSS (Dark & Report Style) ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3, h4 { color: #E0E0E0 !important; font-family: 'Pretendard'; }
    .stMarkdown, p, div, li { color: #B0B8C4; font-weight: 400 !important; }
    
    /* 리포트 카드 스타일 */
    .report-card {
        background-color: #1F2937;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #3B82F6;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .report-title { font-size: 1.1em; font-weight: bold; color: #60A5FA; margin-bottom: 8px; }
    .report-content { font-size: 1.0em; color: #E5E7EB; line-height: 1.6; }
    
    /* 입력창 */
    .stTextInput > div > div > input {
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
if "opinions_df" not in st.session_state:
    data = {
        "original": [],
        "refined": [],
        "keyword": [],
        "stance": [] # 찬성/반대/회의적/대안제시 등
    }
    st.session_state.opinions_df = pd.DataFrame(data)
    
    # 초기 샘플 데이터 (다양한 뉘앙스)
    sample_data = [
        {"original": "애들은 보호해야지 당연한거 아님?", "refined": "청소년을 유해 환경으로부터 보호하는 것은 국가의 당연한 책무입니다.", "keyword": "국가 책임", "stance": "원칙적 찬성"},
        {"original": "VPN 쓰면 그만인데 뭔 소용 ㅋㅋ", "refined": "VPN 등 우회 기술이 보편화된 상황에서 차단 정책은 실효성이 없다는 현실적 지적입니다.", "keyword": "기술적 실효성", "stance": "현실적 반론"},
        {"original": "교육으로 해결한다고? 그거 다 환상이야 정신차려", "refined": "미디어 교육만으로는 급변하는 중독 문제를 해결하기에 역부족이라는 강력한 우려가 있습니다.", "keyword": "교육의 한계", "stance": "대안 비판"},
        {"original": "기업들이 알고리즘 장난질 치는게 문제임", "refined": "중독성 강한 알고리즘을 방치한 플랫폼 기업에 대한 규제와 책임 강화가 선행되어야 합니다.", "keyword": "기업 책임", "stance": "구조적 원인 지적"}
    ]
    st.session_state.opinions_df = pd.DataFrame(sample_data)

# --- [핵심 1] 개별 의견 분석기 (Gatekeeper & Refiner) ---
def analyze_opinion(user_text):
    client = OpenAI(api_key=api_key)
    
    system_prompt = """
    You are a 'Civic Editor'. analyze the user's input regarding "Australia's SNS Ban".

    [Step 1: Relevance Check - Wide & Deep]
    * ACCEPT:
      - Direct mentions (SNS, Ban, Australia).
      - Technical skepticism (VPN, Bypass, DNS, "It won't work").
      - Cynical/Realist views (e.g., "Education is fantasy", "Kids will find a way").
      - Abstract principles (State control, Freedom, Market logic).
    * REJECT ONLY IF:
      - Pure domestic political slogan ("Yoon Out", "Lee Out") with NO policy link.
      - Completely unrelated (Sports, Food).

    [Step 2: Refinement & Extraction]
    * Task: Rewrite the core argument into a declarative Korean sentence.
    * NOTE: If the user is cynical (e.g., "Education is a joke"), Preserve the sharp critique in a formal way (e.g., "Education effectiveness is questionable"). DO NOT water it down to "neutral".
    * Stance: Label the stance (e.g., 찬성, 반대, 실효성 의문, 기업책임 강조, 대안 비판).

    Output Format: REJECT OR Keyword|Stance|Refined_Text
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text}],
            temperature=0.1
        )
        result = response.choices[0].message.content
        
        if "REJECT" in result:
            return None
            
        keyword, stance, refined = result.split("|", 2)
        return {
            "keyword": keyword.strip(),
            "stance": stance.strip(),
            "refined": refined.strip()
        }
    except:
        return None

# --- [핵심 2] 종합 리포트 생성기 (The Insight Generator) ---
def generate_insight_report(df):
    client = OpenAI(api_key=api_key)
    
    # 최근 의견들을 텍스트로 변환해서 프롬프트에 넣음
    all_opinions = "\n".join([f"- [{row['keyword']}/{row['stance']}] {row['refined']}" for _, row in df.iterrows()])
    
    system_prompt = """
    You are a 'Public Opinion Analyst'. Read the collected opinions and generate a structued 'Civic Report'.
    
    [Report Structure]
    1. 🌉 합의의 흐름 (Consensus Flow): What is the common ground? (e.g., "Everyone agrees kids need protection, but...")
    2. ⚡ 핵심 쟁점과 반론 (Key Conflicts): What are the sharpest counterarguments? (Highlight technical doubts like VPN, or skepticism about education).
    3. 💡 우리가 놓친 질문 (Remaining Questions): What perspective needs more thought?
    
    * Style: Insightful, objective, and high-quality Korean.
    * Length: Concise (3-4 sentences per section).
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # 리포트는 분석이 필요하니 mini나 4o 사용
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Here are the citizens' opinions:\n{all_opinions}"}
            ],
            temperature=0.5
        )
        return response.choices[0].message.content
    except:
        return "리포트 생성 중 오류가 발생했습니다."

# ================= UI 시작 =================

st.title("📝 Deep Agora: 숙의 리포트")
st.caption("파편화된 댓글이 아니라, 정리된 하나의 흐름으로 봅니다.")

# 1. 뉴스 브리핑
with st.expander("📢 [이슈 브리핑] 호주 16세 미만 SNS 원천 차단", expanded=False):
    st.markdown("""
    호주 정부가 청소년 정신건강 보호를 위해 16세 미만의 SNS 계정 보유를 금지하는 법안을 추진합니다.
    **핵심 논점:** 국가의 강제적 개입이 정당한가? vs 기술적으로 실효성이 있는가? vs 기업의 책임은?
    [🔗 기사 원문 보기](https://www.yna.co.kr/view/AKR20251209006700084?input=1195m)
    """)

st.divider()

# 2. 의견 입력 (Action)
col_input, col_btn = st.columns([4, 1])
with col_input:
    user_input = st.text_input("당신의 생각은?", placeholder="예: 교육만으로는 안 돼. 이건 마약이랑 같아서 강제력이 필요해.")
with col_btn:
    submit = st.button("의견 보태기 ✍️", type="primary", use_container_width=True)

if submit and user_input:
    with st.spinner("의견을 분석하여 리포트에 반영 중입니다..."):
        res = analyze_opinion(user_input)
        if res:
            new_row = {
                "original": user_input,
                "refined": res['refined'],
                "keyword": res['keyword'],
                "stance": res['stance']
            }
            st.session_state.opinions_df = pd.concat([pd.DataFrame([new_row]), st.session_state.opinions_df], ignore_index=True)
            st.success("의견이 성공적으로 반영되었습니다!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("⚠️ 주제와 무관하거나, 단순한 정치적 비방은 반영되지 않습니다.")

# 3. 실시간 숙의 리포트 (Insight Report) - 여기가 핵심!
st.subheader("📊 실시간 숙의 리포트")

if not st.session_state.opinions_df.empty:
    # 데이터가 변경될 때마다 리포트를 다시 쓸 수도 있지만, 비용 절약을 위해 버튼으로 하거나 
    # 여기서는 매번 렌더링 시 생성 (데이터가 적을 땐 괜찮음. 많아지면 캐싱 필요)
    
    # 비용 최적화를 위해 session_state에 리포트 저장해두고, 데이터 개수가 바뀔 때만 갱신하는 로직 추천
    if "last_count" not in st.session_state:
        st.session_state.last_count = 0
        
    current_count = len(st.session_state.opinions_df)
    
    if current_count > st.session_state.last_count:
        with st.spinner("새로운 의견을 포함하여 리포트를 갱신하고 있습니다..."):
            report_text = generate_insight_report(st.session_state.opinions_df)
            st.session_state.report_text = report_text
            st.session_state.last_count = current_count
    
    # 리포트 파싱 및 출력
    if "report_text" in st.session_state:
        report = st.session_state.report_text
        
        # GPT가 마크다운으로 줄 테니 그대로 출력하거나, 예쁘게 파싱
        st.markdown(f"""
        <div class="report-card">
            <div class="report-content">{report}</div>
        </div>
        """, unsafe_allow_html=True)

    # 4. 개별 의견 타임라인 (증거 자료)
    with st.expander("📜 분석에 사용된 시민들의 의견 원문 보기"):
        for idx, row in st.session_state.opinions_df.iloc[::-1].iterrows(): # 최신순
            st.markdown(f"**[{row['keyword']}]** {row['refined']} <span style='color:grey; font-size:0.8em'>({row['stance']})</span>", unsafe_allow_html=True)

else:
    st.info("아직 수집된 의견이 없습니다. 첫 번째 의견을 남겨주세요!")
