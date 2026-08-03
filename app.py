import streamlit as st
from google import genai
from google.genai.errors import APIError
from PIL import Image

# ----------------------------------------------------
# 0. 이미지 최적화 리사이즈 함수 (API 토큰 절감 핵심)
# ----------------------------------------------------
def load_and_resize(image_file, max_size=(800, 800)):
    """
    고화질 이미지를 비율을 유지하면서 최대 800x800 해상도로 축소합니다.
    """
    img = Image.open(image_file)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.thumbnail(max_size)
    return img

# ----------------------------------------------------
# 1. 페이지 기본 설정
# ----------------------------------------------------
st.set_page_config(
    page_title="자동차 도장 스마트 AI 통합 솔루션",
    page_icon="🚗",
    layout="wide"
)

st.title("🚗 자동차 도장 스마트 AI 통합 솔루션")
st.caption("AI 기반 도장 결함 원인 진단 및 미세 조색(Fine-Tuning) 레시피 산출 시스템")

# ----------------------------------------------------
# 2. 사이드바 - API 키 및 설정 (Secrets 자동 연동)
# ----------------------------------------------------
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    
    # Streamlit Secrets에 등록된 키가 있으면 자동 연동, 없으면 화면에서 입력받음
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("🔒 API 키가 안전하게 자동 연결되었습니다.")
    else:
        api_key = st.text_input("Gemini API Key 입력", type="password")
    
    st.markdown("---")
    st.markdown("### 💡 주요 기능 안내")
    st.markdown("""
    * **🔍 도장 결함 진단**: 오렌지필, 핀홀, 흘러내림(Run) 등 결함 이미지 분석 및 재작업 공정 제시
    * **🎨 AI 조색 Fine-Tuning**: 시편 사진 비교 및 $L^*a*b^*$ 데이터를 기반으로 0.01g 단위 미세 보정량 산출
    """)

# API 키가 없으면 하단 모듈 비활성화
if not api_key:
    st.info("👈 왼쪽 사이드바에 Gemini API 키를 입력하면 시스템이 활성화됩니다.")
    st.stop()

# Gemini 클라이언트 초기화
client = genai.Client(api_key=api_key)

# ----------------------------------------------------
# 3. 메인 탭 구성
# ----------------------------------------------------
tab_defect, tab_tuning = st.tabs(["🔍 도장 결함 진단", "🎨 AI 조색 Fine-Tuning"])


# ====================================================
# TAB 1: 도장 결함 진단 모듈
# ====================================================
with tab_defect:
    st.header("🔍 도장 결함 원인 분석 및 재작업 가이드")
    st.write("결함이 발생한 도장면 사진을 업로드하고 현장 특이사항을 입력해 주세요.")

    col1, col2 = st.columns([1, 1])

    with col1:
        defect_img_file = st.file_uploader("결함 부위 사진 업로드", type=["jpg", "png", "jpeg"], key="defect_img")
        if defect_img_file:
            st.image(Image.open(defect_img_file), caption="업로드된 결함 이미지", use_container_width=True)

    with col2:
        defect_context = st.text_area(
            "작업 환경 및 현장 증상 요약",
            placeholder="예: 클리어 코트 도포 후 건조 과정에서 오렌지필 현상 심화. 건조 온도 60도, 스프레이 압력 2.0bar 사용함."
        )

    if st.button("🚨 결함 진단 실행", type="primary", use_container_width=True):
        if defect_img_file:
            with st.spinner("AI가 결함 형태와 작업 환경을 분석 중입니다..."):
                try:
                    # 이미지 경량화 적용
                    img = load_and_resize(defect_img_file)
                    
                    defect_prompt = f"""
                    당신은 자동차 도장 및 표면처리 최고 전문가입니다.
                    전달된 결함 부위 이미지를 분석하고, 제공된 작업 환경 정보를 참고하여 종합 진단 리포트를 작성해 주세요.
                    작업 환경 정보: {defect_context}

                    아래 항목으로 나누어 명확하게 답변해 주세요:
                    1. **진단된 결함명**: (예: 오렌지필 / 핀홀 / 흘러내림 / 백화 현상 등)
                    2. **추정 원인**: (신너 휘발 속도, 토출량, 노즐 거리에 따른 원인 분석)
                    3. **즉각적인 재작업 솔루션**: (샌딩 방안, 재도장 공정)
                    4. **향후 예방 대책**: (스프레이 건 세팅 및 환경 설정 권장 값)
                    """

                    response = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[img, defect_prompt]
                    )
                    st.success("결함 진단 완료!")
                    st.markdown(response.text)

                except APIError as e:
                    st.error(f"오류가 발생했습니다: {e}")
        else:
            st.warning("결함 부위 사진을 업로드해 주세요.")


# ====================================================
# TAB 2: AI 조색 Fine-Tuning 모듈
# ====================================================
with tab_tuning:
    st.header("🎨 AI 자동차 스마트 조색 & Fine-Tuning")
    st.write("목표 차체 사진과 1차 시편 사진을 비교하여 추가 투입 안료 양을 미세 계산합니다.")

    # 사진 2장 업로드
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        target_img_file = st.file_uploader("1. 목표 차체/판넬 사진", type=["jpg", "png", "jpeg"], key="target_img")
        if target_img_file:
            st.image(Image.open(target_img_file), caption="목표 색상", use_container_width=True)

    with col_t2:
        current_img_file = st.file_uploader("2. 1차 도장된 시편 사진", type=["jpg", "png", "jpeg"], key="current_img")
        if current_img_file:
            st.image(Image.open(current_img_file), caption="1차 시편", use_container_width=True)

    st.markdown("---")
    
    # 배합 정보 및 LAB 수치 입력
    col_r1, col_r2 = st.columns([1, 1])
    with col_r1:
        current_recipe = st.text_area(
            "3. 현재 1차 배합 레시피 (필수)",
            value="바탕안료A 100g, 시너 50g, 흑색 0.5g, 조색제B 1.2g"
        )

    with col_r2:
        lab_data = st.text_area(
            "4. 분광측색기 L*a*b* 수치 (선택 사항)",
            placeholder="예:\n[목표] L*: 45.2, a*: 12.3, b*: -5.1\n[시편] L*: 43.8, a*: 13.5, b*: -4.2"
        )

    if st.button("🚀 AI Fine-Tuning 실행", type="primary", use_container_width=True):
        if target_img_file and current_img_file:
            with st.spinner("두 시편의 색차 및 안료 비중을 분석 중입니다..."):
                try:
                    # 사진 2장 모두 최적화 리사이즈 적용
                    img_target = load_and_resize(target_img_file)
                    img_current = load_and_resize(current_img_file)

                    tuning_prompt = f"""
                    당신은 최고의 자동차 조색 및 안료 처방 전문가입니다.
                    전달된 첫 번째 이미지는 '목표 색상'이고, 두 번째 이미지는 '1차 도장 시편'입니다.

                    [입력 데이터]
                    - 현재 배합 레시피: {current_recipe}
                    - 분광측색기 수치 정보: {lab_data if lab_data else '없음 (이미지 시각 분석 기반)'}

                    두 이미지와 데이터를 종합 분석하여 아래 항목에 맞게 미세 보정 레시피를 제안해 주세요:
                    1. **색상/명도/채도 차이 분석**: (Lab 수치가 제공되었다면 Delta E 분석 포함)
                    2. **보정 방향성**: (명도, 색상조절 방향)
                    3. **추가 투입 안료 레시피 (0.01g 단위)**: (예: 흰색 안료 +0.08g, 청색 안료 +0.02g 등 정확한 수치 제시)
                    4. **최종 교반 및 도장 주의사항**:
                    """

                    response = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[img_target, img_current, tuning_prompt]
                    )

                    st.success("보정 레시피 산출 완료!")
                    st.markdown(response.text)

                except APIError as e:
                    st.error(f"오류가 발생했습니다: {e}")
        else:
            st.warning("목표 색상 사진과 1차 시편 사진을 모두 업로드해 주세요.")