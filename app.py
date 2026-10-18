import streamlit as st
import time
from google import genai
from google.genai.errors import APIError
from openai import OpenAI  # OpenAI 연동을 위한 라이브러리

# 페이지 기본 설정
st.set_page_config(page_title="Gemini AI 맞춤 도서 추천", page_icon="📚")

st.title("📚 Gemini AI 실시간 맞춤 도서 추천 서비스")
st.write("원하시는 장르, 작가, 키워드를 알려주시면 Gemini가 당신만을 위한 책을 실시간으로 분석하여 추천해 드립니다!")

st.divider()

# Streamlit Secrets에서 안전하게 API 키 가져오기
try:
    gemini_api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("⚠️ Gemini API 키가 설정되지 않았습니다. Streamlit Cloud의 Settings > Secrets에 'GEMINI_API_KEY'를 등록해 주세요.")
    st.stop()

# OpenAI API 키는 선택적으로 불러오기 (없어도 1~3차 구글 모델은 정상 작동)
openai_api_key = st.secrets.get("OPENAI_API_KEY", None)

# 1. 장르 선택
genre = st.selectbox(
    "1. 어떤 장르의 책을 원하시나요?",
    ["선택해 주세요", "인문/철학", "문학/소설", "과학/IT", "자기계발", "에세이/시", "자율 입력"]
)

# 2. 세부 질문들
if genre != "선택해 주세요":
    
    col1, col2 = st.columns(2)
    
    with col1:
        author = st.text_input(
            "2. 좋아하는 작가나 유사한 스타일의 작가가 있나요? (선택)",
            placeholder="예: 유발 하라리, 히가시노 게이고, 김영하"
        )
        
    with col2:
        keywords = st.text_input(
            "3. 어떤 느낌/주제의 책인가요? (선택)",
            placeholder="예: 따뜻한 위로, 반전이 있는, 입문자용, 우주와 인류"
        )
        
    situation = st.text_area(
        "4. 지금 어떤 상황이거나 고민이 있으신가요? (선택)",
        placeholder="예: 최근 번아웃이 와서 마음을 정돈하고 싶어요 / 새로운 프로그래밍 언어를 배우는 중이에요"
    )

    st.divider()

    # 3. 추천받기 버튼
    if st.button("✨ Gemini AI에게 맞춤 책 추천받기"):
        status_container = st.empty()
        status_container.info("🔄 AI 서버에 연결하는 중입니다... (답변 생성 **약 3~5초 소요** 예상)")
        
        prompt = f"""
        당신은 전문 도서 추천가이자 사서입니다. 사용자의 요청 사항에 맞춰 가장 적절한 책 3권을 추천해 주세요.

        [사용자 요청 정보]
        - 희망 장르: {genre}
        - 선호 작가/스타일: {author if author else '없음'}
        - 핵심 키워드/느낌: {keywords if keywords else '없음'}
        - 현재 상황/고민: {situation if situation else '없음'}

        [응답 형식]
        각 책마다 다음 항목을 포함해서 깔끔하고 보기 쉽게 작성해 주세요:
        1. **책 제목** (저자 / 출판사)
        2. **한 줄 요약**
        3. **이 책을 추천하는 이유** (사용자의 상황/취향과 연결해서 설명)
        4. **함께 읽으면 좋은 포인트**
        """

        success = False
        
        # ------------------------------------------------------------------
        # [1~3차] Gemini 모델들 순차 시도 (Fallback)
        # ------------------------------------------------------------------
        gemini_models = ['gemini-3.8-flash', 'gemini-2.5-flash', 'gemini-1.5-flash']
        client = genai.Client(api_key=gemini_api_key)

        for model_name in gemini_models:
            try:
                if model_name == gemini_models[0]:
                    status_container.info("✍️ Gemini AI가 맞춤 도서를 정성껏 작성 중입니다... (약 3~5초 소요)")
                else:
                    status_container.warning(f"🔄 서킷 브레이커 작동: 구글 백업 모델({model_name})로 우회 접속 중입니다...")

                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                
                status_container.empty()
                st.success("🎉 AI 맞춤 도서 추천 결과가 도착했습니다!")
                st.markdown(response.text)
                success = True
                break  # 성공 시 탈출

            except APIError as e:
                error_msg = str(e)
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    # 토큰 초과는 구글 계정 한도이므로 바로 4차(OpenAI)로 넘어가거나 중단
                    break
                time.sleep(1)
                continue
            except Exception:
                time.sleep(1)
                continue

        # ------------------------------------------------------------------
        # [4차] 구글 모델들이 모두 실패했을 때 -> OpenAI (gpt-4o-mini)로 최종 우회!
        # ------------------------------------------------------------------
        if not success and openai_api_key:
            try:
                status_container.warning("🔄 구글 서버 트래픽 초과: **OpenAI (GPT-4o-mini)** 백업 회선으로 최종 우회 접속합니다...")
                
                openai_client = OpenAI(api_key=openai_api_key)
                openai_response = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "당신은 전문 도서 추천가이자 사서입니다."},
                        {"role": "user", "content": prompt}
                    ]
                )
                
                status_container.empty()
                st.success("🎉 AI 맞춤 도서 추천 결과가 도착했습니다! (OpenAI 백업 회선)")
                st.markdown(openai_response.choices[0].message.content)
                success = True

            except Exception as e:
                pass

        # 모든 회선(1~4차)이 최종 실패했을 경우
        if not success:
            status_container.empty()
            st.error("❌ 현재 구글 및 OpenAI 모든 AI 서버 회선이 매우 혼잡합니다. 1~2분 뒤에 버튼을 다시 눌러주세요.")
