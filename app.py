import streamlit as st
import time
from google import genai
from google.genai.errors import APIError
from openai import OpenAI

# 페이지 기본 설정 (브라우저 탭 이름)
st.set_page_config(page_title="AI 사서의 도서 추천소", page_icon="📚")

# 웹사이트 메인 타이틀
st.title("📚 AI 사서의 도서 추천소")
st.write("원하시는 장르, 작가, 키워드를 알려주시면 AI 사서가 당신만을 위한 맞춤형 책을 실시간으로 분석하여 추천해 드립니다!")

st.divider()

# Streamlit Secrets에서 안전하게 API 키 가져오기
try:
    gemini_api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("⚠️ Gemini API 키가 설정되지 않았습니다. Streamlit Cloud의 Settings > Secrets에 'GEMINI_API_KEY'를 등록해 주세요.")
    st.stop()

# 완전 무료 백업용 Groq API 키 불러오기
groq_api_key = st.secrets.get("GROQ_API_KEY", None)

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
    if st.button("✨ AI 사서에게 맞춤 책 추천받기"):
        status_container = st.empty()
        status_container.info("🔄 AI 도서관 서버에 연결하는 중입니다... (답변 생성 **약 3~5초 소요** 예상)")
        
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
                    status_container.info("✍️ AI 사서가 맞춤 도서를 정성껏 고르는 중입니다... (약 3~5초 소요)")
                else:
                    status_container.warning(f"🔄 서킷 브레이커 작동: 구글 백업 회선({model_name})으로 우회 접속 중입니다...")

                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                
                status_container.empty()
                st.success("🎉 AI 사서의 맞춤 도서 추천 결과가 도착했습니다!")
                st.markdown(response.text)
                success = True
                break  # 성공 시 탈출

            except APIError as e:
                error_msg = str(e)
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    break
                time.sleep(1)
                continue
            except Exception:
                time.sleep(1)
                continue

        # ------------------------------------------------------------------
        # [4~5차] Groq 멀티 모델 순차 시도 (Fallback)
        # ------------------------------------------------------------------
        groq_models = ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant']
        
        if not success and groq_api_key:
            groq_client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=groq_api_key
            )
            
            for g_model in groq_models:
                try:
                    status_container.warning(f"🔄 구글 서버 트래픽 초과: **Groq 백업 회선({g_model})**으로 우회 접속합니다...")
                    
                    groq_response = groq_client.chat.completions.create(
                        model=g_model,
                        messages=[
                            {"role": "system", "content": "당신은 전문 도서 추천가이자 사서입니다."},
                            {"role": "user", "content": prompt}
                        ]
                    )
                    
                    status_container.empty()
                    st.success(f"🎉 AI 사서의 맞춤 도서 추천 결과가 도착했습니다! (Groq {g_model} 회선)")
                    st.markdown(groq_response.choices[0].message.content)
                    success = True
                    break  # 성공 시 탈출

                except Exception as e:
                    time.sleep(1)
                    continue

        # 모든 회선이 최종 실패했을 경우
        if not success:
            status_container.empty()
            st.error("❌ 현재 모든 AI 도서관 서가가 매우 혼잡합니다. 1~2분 뒤에 버튼을 다시 눌러주세요.")
