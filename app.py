import streamlit as st
import pandas as pd
import time
import difflib
from openai import OpenAI

# [설정] 페이지 기본 세팅
st.set_page_config(page_title="Deep Agora: 인사이트 클러스터", layout="wide", page_icon="🧠")

# --- [스타일] CSS (Dark & Clean) ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3, h4 { color: #E0E0E0 !important; font-family: 'Pretendard'; }
    .stMarkdown, p, div, li { color: #B0B8C4; font-weight: 400 !important; }
    
    /* 클러스터 카드 스타일 */
    .cluster-card {
        background-color: #1F2937;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
        border-left: 4px solid #374151;
    }
    .cluster-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; }
    .cluster-tag { font-size: 0.8em; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .cluster-count { font-size: 0.9em; color: #9CA3AF; }
</style>
""", unsafe_allow_html=True)

# --- [보안] API 키 로드 ---
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("⚠️ API 키가 설정되지 않았습니다.")
    st.stop()

# --- 0. 초기 데이터 (클러스터 구조) ---
if "clusters" not in st.session_state:
    # 초기 클러스터 (이미 형성된 여론 그룹)
    st.session_state.clusters = [
        {"id": 1, "keyword": "기업의 책임", "stance": "대안 제시", "text": "단순 차단보다는 알고리즘을 개선하여 기업이 안전한 환경을 조성해야 합니다.", "count": 12},
        {"id": 2, "keyword": "기술적 한계", "stance": "실효성 의문", "text": "VPN 우회 기술이 보편화된 상황에서 물리적 차단은 실효성이 낮다는 지적입니다.", "count": 25},
        {"id": 3, "keyword": "국가 보호 의무", "stance": "원칙적 찬성", "text": "유해 환경으로부터 청소년을 보호하는 것은 국가의 당연한 헌법적 책무입니다.", "count": 18}
    ]

# --- [로직 1] 의견 분석기 (문맥 추론 강화) ---
def analyze_opinion(user_text):
    client = OpenAI(api_key=api_key)
    
    system_prompt = """
    You are a 'Contextual Civic Editor'. 
    The topic is "Australia's SNS Ban for under-16s".

    [Rule 1: Implicit Context Assumption] (CRITICAL)
    * Users often omit the subject. If the input is about "Market", "Freedom", "Regulation", "Blocking", "Education" -> ASSUME it refers to this SNS topic.
    * Example: "Stopping what we use is market infringement" -> ACCEPT (Interpret as: Stopping SNS usage is market infringement).
    * REJECT ONLY IF: Pure political slogans ("Yoon Out"), Random noise (Food, Sports) that CANNOT be linked to the topic.

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

# --- [로직 2] 클러스터 매칭 (도배 방지 & 합치기) ---
def match_and_merge(new_opinion):
    # 기존 클러스터들과 비교
    best_match_idx = -1
    best_similarity = 0.0
    
    for idx, cluster in enumerate(st.session_state.clusters):
        # 문장 유사도 비교 (SequenceMatcher)
        # 실제 서비스에선 Embedding Cosine Similarity 권장
        sim = difflib.SequenceMatcher(None, new_opinion['refined'], cluster['text']).ratio()
        
        # 키워드나 스탠스가 같으면 가산점
        if new_opinion['keyword'] == cluster['keyword']: sim += 0.2
        
        if sim > best_similarity:
            best_similarity = sim
            best_match_idx = idx
            
    # 유사도가 0.65 이상이면 "같은 의견"으로 간주하고 병합
    if best_similarity >= 0.65:
        return best_match_idx # 병합할 인덱스 반환
    else:
        return None # 새로운 의견임

# --- [로직 3] 인사이트 리포트 (변화 감지) ---
def generate_insight_report():
    # 클러스터 데이터를 요약해서 GPT에게 던져줌
    # "가장 큰 그룹"과 "새로 등장한 소수 그룹"을 구분해서 분석 요청
    
    clusters = sorted(st.session_state.clusters, key=lambda x: x['count'], reverse=True)
    summary_text = "\n".join([f"- [{c['keyword']}/{c['stance']}] {c['text']} (지지자: {c['count']}명)" for c in clusters])
    
    client = OpenAI(api_key=api_key)
    system_prompt = """
    You are a 'Public Discourse Analyst'. Write a brief 'Insight Report' based on the opinion clusters.
    
    [Focus]
    1. Main Stream: What is the dominant opinion? (Based on count)
    2. Conflict Point: Where is the sharpest disagreement?
    3. Blind Spot: Is there any unique minority opinion that needs attention?
    
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

# 1. 뉴스 브리핑
with st.expander("📢 [이슈] 호주 16세 미만 SNS 원천 차단", expanded=False):
    st.markdown("호주 정부의 청소년 SNS 금지 법안. '국가의 보호' vs '시장/개인의 자율' 충돌.")

col_main, col_side = st.columns([2, 1])

# --- [메인] 인사이트 리포트 ---
with col_main:
    st.markdown("### 📊 현재의 숙의 흐름 (Live Insight)")
    
    # 리포트 생성 (버튼 또는 자동)
    if st.button("🔄 리포트 갱신 (AI 분석)", type="secondary", use_container_width=True):
        with st.spinner("전체 의견 지형을 분석 중입니다..."):
            report = generate_insight_report()
            st.session_state.insight_report = report
            
    if "insight_report" in st.session_state:
        st.info(st.session_state.insight_report)
    else:
        st.info("아직 분석된 리포트가 없습니다. 갱신 버튼을 눌러보세요.")

    st.markdown("---")
    st.markdown("### 🧩 형성된 의견 그룹 (Clusters)")
    
    # 클러스터 보여주기 (지지자 많은 순)
    sorted_clusters = sorted(st.session_state.clusters, key=lambda x: x['count'], reverse=True)
    
    for cluster in sorted_clusters:
        # 색상 로직
        border_color = "#3B82F6" # 기본 블루
        if "반대" in cluster['stance'] or "지적" in cluster['stance']: border_color = "#EF4444" # 레드
        elif "대안" in cluster['stance']: border_color = "#10B981" # 그린
        
        st.markdown(f"""
        <div style="background-color: #1F2937; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid {border_color};">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div>
                    <span style="color: {border_color}; font-weight: bold; font-size: 1em;">#{cluster['keyword']}</span>
                    <span style="background-color: #374151; color: #D1D5DB; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; margin-left: 8px;">{cluster['stance']}</span>
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
        user_input = st.text_area("당신의 생각은?", height=100, placeholder="예: 이미 쓰고 있는 걸 못 쓰게 하는 건 시장 침해 아닌가요?")
        
        if st.button("의견 제출", type="primary", use_container_width=True):
            if user_input:
                with st.spinner("AI가 의견을 분석하고 분류 중입니다..."):
                    # 1. 분석 (Gatekeeper)
                    res = analyze_opinion(user_input)
                    
                    if res is None:
                        st.error("🚫 주제와 무관하거나 의미 없는 내용은 반영되지 않습니다.")
                    else:
                        # 2. 클러스터 매칭 (Deduplication)
                        match_idx = match_and_merge(res)
                        
                        if match_idx is not None:
                            # 기존 의견에 병합 (Count 증가)
                            st.session_state.clusters[match_idx]['count'] += 1
                            keyword = st.session_state.clusters[match_idx]['keyword']
                            st.success(f"비슷한 의견인 '{keyword}' 그룹에 공감을 더했습니다! (+1)")
                        else:
                            # 새로운 클러스터 생성
                            new_cluster = {
                                "id": len(st.session_state.clusters) + 1,
                                "keyword": res['keyword'],
                                "stance": res['stance'],
                                "text": res['refined'],
                                "count": 1
                            }
                            st.session_state.clusters.append(new_cluster)
                            st.success(f"새로운 관점 '{res['keyword']}'이(가) 등록되었습니다!")
                            # 새 관점이 생기면 리포트를 갱신하도록 유도할 수도 있음
                        
                        time.sleep(1.5)
                        st.rerun()
