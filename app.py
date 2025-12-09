import streamlit as st
import pandas as pd
import time
import difflib
from openai import OpenAI

# [설정] 페이지 기본 세팅
st.set_page_config(page_title="Deep Agora: 인사이트 클러스터", layout="wide", page_icon="🧠")

# --- [기능 1] 비밀번호 접속 제한 (가장 먼저 실행) ---
def check_password():
    """로그인 성공 여부를 반환합니다."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    # 로그인 화면 디자인
    st.markdown("<br><br><br>", unsafe_allow_html=True) # 상단 여백
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("🔒 Deep Agora")
        st.markdown("시민과 AI가 함께 만드는 숙의의 공간에 오신 것을 환영합니다.")
        
        password = st.text_input("입장 코드 (Access Code)", type="password")
        
        if st.button("입장하기", use_container_width=True, type="primary"):
            if password == "snu1234":
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("코드가 일치하지 않습니다. 다시 확인해주세요.")
                
    return False

# 비밀번호 통과 못하면 여기서 코드 실행 중단 (아래 내용은 안 보임)
if not check_password():
    st.stop()

# =========================================================
# 여기부터 메인 앱 로직 시작
# =========================================================

# --- [스타일] CSS (Dark & Clean) ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3, h4 { color: #E0E0E0 !important; font-family: 'Pretendard'; }
    .stMarkdown, p, div, li { color: #B0B8C4; font-weight: 400 !important; }
    
    /* 클러스터 카드 스타일 */
    .cluster-card {
        background-color: #1F2937;
        padding: 18px;
        border-radius: 8px;
        margin-bottom: 12px;
        border-left: 4px solid #374151;
        transition: transform 0.2s;
    }
    .cluster-card:hover {
        transform: scale(1.01);
    }
    
    /* 리포트 카드 */
    .report-box {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- [보안] API 키 로드 ---
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("⚠️ API 키가 설정되지 않았습니다. 관리자에게 문의하세요.")
    st.stop()

# --- 0. 초기 데이터 (클러스터 구조) ---
if "clusters" not in st.session_state:
    st.session_state.clusters = [
        {"id": 1, "keyword": "기업의 책임", "stance": "대안 제시", "text": "단순 차단보다는 알고리즘을 개선하여 기업이 안전한 환경을 조성해야 합니다.", "count": 12},
        {"id": 2, "keyword": "기술적 한계", "stance": "실효성 의문", "text": "VPN 우회 기술이 보편화된 상황에서 물리적 차단은 실효성이 낮다는 지적입니다.", "count": 25},
        {"id": 3, "keyword": "국가 보호 의무", "stance": "원칙적 찬성", "text": "유해 환경으로부터 청소년을 보호하는 것은 국가의 당연한 헌법적 책무입니다.", "count": 18}
    ]

# --- [로직 1] 의견 분석기 (Contextual Gatekeeper) ---
def analyze_opinion(user_text):
    client = OpenAI(api_key=api_key)
    
    system_prompt = """
    You are a 'Contextual Civic Editor'. 
    The topic is "Australia's SNS Ban for under-16s".

    [Rule 1: Implicit Context Assumption]
    * Users often omit the subject. If the input is about "Market", "Freedom", "Regulation", "Blocking", "Education" -> ASSUME it refers to this SNS topic.
    * Example: "Stopping what we use is market infringement" -> ACCEPT (Interpret as: Stopping SNS usage is market infringement).
    * REJECT ONLY IF: Pure political slogans ("Yoon Out"), Random noise (Food, Sports).

    [Rule 2: Extraction]
    * Keyword: Core noun (e.g. '시장 자율성', '기본권', '기술적 한계'). NO 'SNS', 'Ban'.
    * Stance: Choose [찬성 / 반대 / 실효성 지적 / 대안 제시 / 우려].
    * Refined Text: Rewrite into a polite, formal Korean sentence.

    Output: Keyword|Stance|Refined_Text  (OR "REJECT")
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text}],
            temperature=0.1
        )
        result = response.choices[0].message.content.strip().replace("Output:", "").replace("ACCEPT", "")
        
        if "REJECT" in result:
            return None
            
        parts = result.split("|")
        if len(parts) >= 3:
            return {"keyword": parts[0].strip(), "stance": parts[1].strip(), "refined": parts[2].strip()}
        return None
    except:
        return None

# --- [로직 2] 클러스터 매칭 (Deduplication) ---
def match_and_merge(new_opinion):
    best_match_idx = -1
    best_similarity = 0.0
    
    for idx, cluster in enumerate(st.session_state.clusters):
        sim = difflib.SequenceMatcher(None, new_opinion['refined'], cluster['text']).ratio()
        if new_opinion['keyword'] == cluster['keyword']: sim += 0.2
        
        if sim > best_similarity:
            best_similarity = sim
            best_match_idx = idx
            
    if best_similarity >= 0.65:
        return best_match_idx
    else:
        return None

# --- [로직 3] 인사이트 리포트 생성 ---
def generate_insight_report():
    clusters = sorted(st.session_state.clusters, key=lambda x: x['count'], reverse=True)
    summary_text = "\n".join([f"- [{c['keyword']}/{c['stance']}] {c['text']} (지지자: {c['count']}명)" for c in clusters])
    
    client = OpenAI(api_key=api_key)
    system_prompt = """
    You are a 'Public Discourse Analyst'. Write a brief 'Insight Report' based on the opinion clusters.
    
    [Focus]
    1. Main Stream: What is the dominant opinion?
    2. Conflict Point: Where is the sharpest disagreement?
    3. Blind Spot: Is there any unique minority opinion?
    
    * Language: Korean. Concise and Insightful.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Here are the opinion clusters:\n{summary_text}"}
            ],
            temperature=0.5
        )
        return response.choices[0].message.content
    except:
        return "분석 중..."

# ================= UI 시작 =================

st.title("🧠 Deep Agora: 인사이트 클러스터")
st.caption("비슷한 의견은 뭉치고, 새로운 통찰은 드러납니다. 도배는 의미가 없습니다.")

# 1. 뉴스 브리핑 (기사 링크 추가됨 ⭐)
with st.expander("📢 [이슈 브리핑] 호주 16세 미만 SNS 원천 차단", expanded=False):
    st.markdown("""
    **호주 정부가 청소년 정신건강 보호를 위해 16세 미만 SNS 계정 보유 금지 법안을 추진합니다.**
    
    * **주요 내용:** 페이스북, 틱톡, 인스타그램 등 대상. 위반 시 기업에 거액 벌금.
    * **핵심 쟁점:** "국가의 적극적 보호 의무" vs "기술적 실효성(VPN) 및 기본권 침해"
    """)
    # [기능 2] 원문 기사 링크 버튼
    st.link_button("🔗 연합뉴스 기사 원문 보기", "https://www.yna.co.kr/view/AKR20251209006700084?input=1195m")

col_main, col_side = st.columns([2, 1])

# --- [메인] 인사이트 리포트 & 클러스터 ---
with col_main:
    st.markdown("### 📊 현재의 숙의 흐름 (Live Insight)")
    
    # 리포트 갱신 버튼
    if st.button("🔄 리포트 갱신 (AI 분석)", type="secondary", use_container_width=True):
        with st.spinner("전체 의견 지형을 분석 중입니다..."):
            report = generate_insight_report()
            st.session_state.insight_report = report
            
    # 리포트 표시 영역
    if "insight_report" in st.session_state:
        st.markdown(f"<div class='report-box'>{st.session_state.insight_report}</div>", unsafe_allow_html=True)
    else:
        st.info("아직 분석된 리포트가 없습니다. 갱신 버튼을 눌러보세요.")

    st.markdown("---")
    st.markdown("### 🧩 형성된 의견 그룹 (Clusters)")
    
    # 클러스터 표시 (지지자 많은 순)
    sorted_clusters = sorted(st.session_state.clusters, key=lambda x: x['count'], reverse=True)
    
    for cluster in sorted_clusters:
        # 색상 로직
        border_color = "#3B82F6" # 기본 블루
        if "반대" in cluster['stance'] or "지적" in cluster['stance'] or "의문" in cluster['stance']: border_color = "#EF4444" # 레드
        elif "대안" in cluster['stance'] or "책임" in cluster['stance']: border_color = "#10B981" # 그린
        
        st.markdown(f"""
        <div class="cluster-card" style="border-left-color: {border_color};">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div>
                    <span style="color: {border_color}; font-weight: bold; font-size: 1.1em;">#{cluster['keyword']}</span>
                    <span style="background-color: #374151; color: #D1D5DB; padding: 2px 8px; border-radius: 4px; font-size: 0.85em; margin-left: 8px;">{cluster['stance']}</span>
                </div>
                <div style="font-weight: bold; color: #E5E7EB;">
                    👥 {cluster['count']}명 공감
                </div>
            </div>
            <div style="color: #D1D5DB; font-size: 1em; line-height: 1.5;">
                {cluster['text']}
            </div>
        </div>
        """, unsafe_allow_html=True)

# --- [사이드바] 의견 입력 ---
with col_side:
    st.markdown("### 💬 의견 보태기")
    with st.container(border=True):
        user_input = st.text_area("당신의 생각은?", height=150, placeholder="예: 이미 쓰고 있는 걸 못 쓰게 하는 건 시장 침해 아닌가요?")
        
        if st.button("의견 제출", type="primary", use_container_width=True):
            if user_input:
                with st.spinner("AI가 의견을 분석하고 분류 중입니다..."):
                    res = analyze_opinion(user_input)
                    
                    if res is None:
                        st.error("🚫 주제와 무관하거나 의미 없는 내용은 반영되지 않습니다.")
                    else:
                        match_idx = match_and_merge(res)
                        
                        if match_idx is not None:
                            st.session_state.clusters[match_idx]['count'] += 1
                            keyword = st.session_state.clusters[match_idx]['keyword']
                            st.success(f"비슷한 의견인 '{keyword}' 그룹에 공감을 더했습니다! (+1)")
                        else:
                            new_cluster = {
                                "id": len(st.session_state.clusters) + 1,
                                "keyword": res['keyword'],
                                "stance": res['stance'],
                                "text": res['refined'],
                                "count": 1
                            }
                            st.session_state.clusters.append(new_cluster)
                            st.success(f"새로운 관점 '{res['keyword']}'이(가) 등록되었습니다!")
                        
                        time.sleep(1.5)
                        st.rerun()
