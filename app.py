import streamlit as st
import time
from google import genai
from google.genai.errors import APIError

# 페이지 기본 설정
st.set_page_config(page_title="Gemini AI 맞춤 도서 추천", page_icon="📚")

st.title("📚 Gemini AI 실시간 맞춤 도서 추천 서비스")
st.write("원하시는 장르, 작가, 키워드를 알려주시면 Gemini가 당신만을 위한 책을 실시간으로 분석하여 추천해 드립니다!")

st.divider()

# Streamlit Secrets에서 안전하게 API 키 가져오기
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("⚠️ API 키가 설정되지 않았습니다. Streamlit Cloud의 Settings > Secrets에 'GEMINI_API_KEY'를 등록해 주세요.")
    st.stop()

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
        # 실시간 상태를 보여주기 위한 영역 생성
        status_container = st.empty()
        status_container.info("🔄 Gemini AI 서버에 연결하는 중입니다... (답변 생성 **약 3~5초 소요** 예상)")
        
        client = genai.Client(api_key=api_key)
        
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

        # 503 과부하 대비 스마트 자동 재시도 설정 (최대 5번까지 트라이)
        max_retries = 5
        success = False

        for attempt in range(max_retries):
            try:
                # 연결 성공 후 생성 중 메시지 출력
                status_container.info("✍️ Gemini AI가 맞춤 도서를 정성껏 작성 중입니다... (약 3~5초 소요)")
                
                # 최신 요구 모델인 gemini-3.8-flash 사용
                response = client.models.generate_content(
                    model='gemini-3.8-flash',
                    contents=prompt,
                )
                
                # 성공 시 상태 박스 비우고 결과 출력
                status_container.empty()
                st.success("🎉 Gemini AI 맞춤 도서 추천 결과가 도착했습니다!")
                st.markdown(response.text)
                success = True
                break

            except APIError as e:
                error_msg = str(e)
                
                # 429 토큰 / 할당량 초과 처리
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    status_container.empty()
                    st.error("⏳ 오늘 준비된 AI 무료 질문 토큰(할당량)을 모두 사용했거나 단시간 요청이 몰렸습니다. 잠시 후 다시 시도해 주세요!")
                    break
                
                # 503 서버 과부하인 경우: 대기 시간을 카운트하며 재시도
                elif "503" in error_msg or "UNAVAILABLE" in error_msg:
                    if attempt < max_retries - 1:
                        wait_sec = (attempt + 1) * 2  # 2초, 4초, 6초... 대기 시간 점진적 증가
                        status_container.warning(
                            f"⚠️ 구글 AI 서버에 일시적인 과부하가 발생했습니다 (시도 {attempt+1}/{max_retries}).\n"
                            f"서버 안정화를 위해 **약 {wait_sec}초 후** 자동으로 다시 시도합니다..."
                        )
                        time.sleep(wait_sec)
                        continue
                    else:
                        status_container.empty()
                        st.error("❌ 서버 과부하가 지속되어 연결에 실패했습니다. 1~2분 뒤에 버튼을 다시 눌러주세요.")
                        break
                
                # 기타 API 에러
                else:
                    status_container.empty()
                    st.error(f"API 오류가 발생했습니다: {e}")
                    break
                    
            except Exception as e:
                status_container.empty()
                st.error(f"오류가 발생했습니다: {e}")
                break
