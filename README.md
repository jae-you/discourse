# 🌿 Deep Agora: AI-Mediated Opinion Garden
> "승패가 아닌 숙의를, 소음이 아닌 신호를."

**Deep Agora**는 극단적인 대립으로 치닫는 온라인 공론장을 AI 중재 기술을 통해 **'숙의의 정원(Opinion Garden)'**으로 재구성하는 실험적 프로젝트입니다.

## 🎯 Project Goal
이 프로젝트는 기존 소셜 미디어의 '전쟁터(Battleground)' 모델을 지양합니다. 대신 AI 에이전트가 다음과 같은 역할을 수행하여 건강한 토론 생태계를 조성합니다:
1.  **Reception-side Mediation:** 발화자의 표현을 검열하는 대신, 수신자가 듣는 메시지를 순화하여 감정적 반발을 낮춥니다.
2.  **Semantic Clustering:** 단순 찬반(51:49) 구도가 아닌, '핵심 쟁점' 단위로 의견을 묶어 시각화합니다.
3.  **Civility Ranking:** '좋아요' 수가 아닌, 논리적 완결성과 협력적 태도(Civility)를 기준으로 상위 노출합니다.

## 🛠️ Features (Demo)
이 데모는 Python Streamlit으로 구현된 목업(Mock-up)입니다.

- **Topic Gardening:** 거대 언어 모델(LLM)이 수천 개의 댓글을 분석해 도출한 3가지 핵심 어젠다를 카드 형태로 보여줍니다.
- **Civility Filter:** 사용자가 직접 공론장의 '품격 농도'를 조절할 수 있는 슬라이더 UI를 제공합니다.
- **Common Ground Report:** 서로 다른 진영이 합의한 공통의 가치(Consensus)를 별도로 추출해 보여줍니다.

## 🚀 How to Run
```bash
# 1. 저장소 클론
git clone [YOUR_REPO_URL]

# 2. 필수 라이브러리 설치
pip install -r requirements.txt

# 3. 앱 실행
streamlit run app.py