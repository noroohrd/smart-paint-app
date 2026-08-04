import streamlit as st
from google import genai
from google.genai.errors import APIError
from PIL import Image

# ----------------------------------------------------
# 0. 이미지 최적화 리사이즈 함수
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
    page_title="노루페인트 워터큐(Water-Q) AI 스마트 도장/조색 시스템",
    page_icon="🎨",
    layout="wide"
)

st.title("🎨 노루페인트 워터큐(Water-Q) AI 스마트 조색 & 결함 진단 솔루션")
st.caption("Water-Q 칼라뱅크 시스템 전용 AI 미세 조색(Fine-Tuning) 및 현장 도장 결함 진단 리포트")

# ----------------------------------------------------
# 2. 사이드바 - API 키 및 설정 (Secrets 자동 연동)
# ----------------------------------------------------
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("🔒 API 키가 연동되었습니다.")
    else:
        api_key = st.text_input("Gemini API Key 입력", type="password")
    
    st.markdown("---")
    st.markdown("### 📘 워터큐(Water-Q) 시스템 핵심 수칙")
    st.markdown("""
    * **Q-7000(표준백색)**: 배합 내 **10% 이상 사용 금지** (초과 시 고농도 백색 **Q-7800 / Q-7900** 사용)
    * **Q-3550(옥사이드 황색)**: 메탈릭 색상 조색 시 **사용 엄금** (솔리드 전용)
    * **정면/측면(Face/Flop)**: 입자감(Q-9260~9890) 및 간섭펄(Q-0130~0770) 각도별 색차 정밀 계산
    """)

if not api_key:
    st.info("👈 왼쪽 사이드바에 Gemini API 키를 입력하면 시스템이 활성화됩니다.")
    st.stop()

# Gemini 클라이언트 초기화
client = genai.Client(api_key=api_key)

# ----------------------------------------------------
# 3. 메인 탭 구성
# ----------------------------------------------------
tab_tuning, tab_defect = st.tabs(["🎨 Water-Q AI 미세 조색 (Fine-Tuning)", "🔍 도장 결함 진단"])


# ====================================================
# TAB 1: Water-Q AI 스마트 미세 조색 모듈
# ====================================================
with tab_tuning:
    st.header("🎨 워터큐(Water-Q) 전용 AI Fine-Tuning 조색")
    st.write("목표 색상과 1차 시편, 현재 배합표, 그리고 원하시는 조색 총량을 입력해 주세요.")

    # 1. 사진 2장 업로드 (목표 / 1차 시편)
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        target_img_file = st.file_uploader("1. 목표 차체/판넬 사진 (Target)", type=["jpg", "png", "jpeg"], key="target_img")
        if target_img_file:
            st.image(Image.open(target_img_file), caption="목표 색상 (Target)", use_container_width=True)

    with col_t2:
        current_img_file = st.file_uploader("2. 1차 도장된 시편 사진 (Sample)", type=["jpg", "png", "jpeg"], key="current_img")
        if current_img_file:
            st.image(Image.open(current_img_file), caption="1차 시편 (Sample)", use_container_width=True)

    st.markdown("---")
    
    # 2. 배합 정보 입력 및 목표 총량 설정
    col_r1, col_r2 = st.columns([1.2, 0.8])

    with col_r1:
        st.subheader("3. 현재 1차 배합 레시피 정보")
        recipe_input_type = st.radio(
            "배합표 입력 방식을 선택하세요:",
            ["📸 배합표 사진 업로드 (추천)", "✍️ 텍스트 직접 입력"],
            horizontal=True
        )

        recipe_img_file = None
        recipe_text = ""

        if "사진 업로드" in recipe_input_type:
            recipe_img_file = st.file_uploader("1차 배합표 / 조색기 화면 / 손글씨 레시피 사진 업로드", type=["jpg", "png", "jpeg"], key="recipe_img")
            if recipe_img_file:
                st.image(Image.open(recipe_img_file), caption="업로드된 배합표 이미지", width=350)
        else:
            recipe_text = st.text_area(
                "1차 배합 레시피 직접 작성",
                value="Q-7000 80g, Q-8200 10g, Q-5450 5g, Q-9500 5g",
                placeholder="예: Q-7000 100g, Q-5450 12g, Q-8200 1.5g..."
            )

    with col_r2:
        st.subheader("4. 조색 중량 및 측색 데이터")
        
        # ★ 원하는 조색 총 중량 설정 기능 ★
        target_total_weight = st.number_input(
            "🎯 목표 조색 총 중량 (g)",
            min_value=10.0,
            max_value=10000.0,
            value=100.0,
            step=10.0,
            help="원하시는 총 도료 조색 중량을 입력하시면 AI가 해당 중량에 맞춰 배합량을 정밀 계산합니다."
        )

        lab_data = st.text_input(
            "측색기 $L^*a*b^*$ 수치 (선택 사항)",
            placeholder="예: [목표] L*: 45.2, a*: 12.3 / [시편] L*: 43.8, a*: 13.5"
        )

    st.markdown("---")

    if st.button("🚀 Water-Q AI 미세 조색 실행", type="primary", use_container_width=True):
        if target_img_file and current_img_file:
            if not recipe_img_file and not recipe_text.strip():
                st.warning("⚠️ 1차 배합표 사진을 업로드하거나 텍스트를 입력해 주세요.")
            else:
                with st.spinner(f"AI가 목표 중량({target_total_weight}g)에 맞춰 워터큐 보정 레시피 표를 생성 중입니다..."):
                    try:
                        # 이미지 리사이즈
                        img_target = load_and_resize(target_img_file)
                        img_current = load_and_resize(current_img_file)

                        contents_payload = [img_target, img_current]

                        if recipe_img_file:
                            img_recipe = load_and_resize(recipe_img_file)
                            contents_payload.append(img_recipe)
                            recipe_prompt_part = "- 1차 배합 레시피: [첨부된 세 번째 이미지(배합표 사진)에서 안료명과 중량을 OCR 및 시각 분석하여 파악할 것]"
                        else:
                            recipe_prompt_part = f"- 1차 배합 레시피: {recipe_text}"

                        waterq_system_prompt = f"""
                        당신은 노루페인트 '워터큐(Water-Q) 칼라뱅크 시스템' 최고의 기술 조색 전문가입니다.
                        첫 번째 이미지('목표 색상')와 두 번째 이미지('1차 도장 시편')를 비교 분석하여 보정 레시피를 제안해 주세요.

                        [입력 데이터 및 조건]
                        {recipe_prompt_part}
                        - **목표 조색 총 중량**: {target_total_weight}g (반드시 이 총 중량 비율 기준으로 가감량을 계산할 것)
                        - 측색기 수치 정보: {lab_data if lab_data else '없음 (이미지 시각 분석 기반)'}

                        [★ 워터큐(Water-Q) 공식 칼라가이드 필수 규정 ★]
                        1. **백색 제약 조건**: Q-7000(표준 백색)은 전체 배합 내 10% 이상 사용 금지. 백색 투입량이 10% 초과하여 밝기(L*)를 크게 올릴 경우 반드시 고농도 고은폐 백색인 **Q-7800** 또는 **Q-7900**을 사용하도록 안내할 것.
                        2. **메탈릭 제약 조건**: 메탈릭/펄 색상 조색 시 **Q-3550(옥사이드 황색)**은 절대로 투입하지 말 것 (솔리드 전용).
                        3. **정면/측면(Face/Flop) 및 입자감 계산**:
                           - 실버 메탈릭: 미세입자(Q-9260~9360, 정면 어둡고 측면 밝음) / 대입자·스파클(Q-9660~9890, 정면 고휘도) 구분 반영.
                           - 청색계: Q-5300/5350(녹미 강함), Q-5600/5800(적미 청색)
                           - 펄/마이카: Q-0130~0770 간섭색 및 바탕색 조화 계산.

                        [작성 양식]
                        1. **색상 차이 및 정면/측면(Face/Flop) 정밀 분석**: (명도, 색상, 채도, 입자감 차이)
                        2. **보정 방향성 요약**: (어떤 원색/메탈릭/펄을 보강해야 하는지 핵심 정리)
                        3. **📊 Water-Q 미세 조색 비교표 (목표 총량 {target_total_weight}g 기준)**:
                           - 기존 배합과 추가 투입량, 최종 배합 중량을 한눈에 비교할 수 있도록 **반드시 아래 마크다운 표 형식으로 작성**해 주세요.
                           
                           | 안료 코드 (Q-Code) | 1차 배합 중량 (g) | 추가 투입량 (g) | 최종 보정 중량 (g) | 비고 및 보정 역할 |
                           | :--- | :--- | :--- | :--- | :--- |
                           | 예: Q-7800 | 0.00 | +0.15 | 0.15 | 고농도 백색 / 명도 상승 |
                           | 예: Q-5450 | 5.00 | +0.03 | 5.03 | 청색 보강 |
                           | **합계 (Total)** | **{target_total_weight}g 전후** | **+0.xxg** | **{target_total_weight}g** | **목표 총량 달성** |

                        4. **교반 및 현장 도장 주의사항**: (희석 비율, 스프레이 노즐 및 건조 시 주의점)
                        """

                        contents_payload.append(waterq_system_prompt)

                        # 최신 Gemini 3.5 Flash 구동
                        response = client.models.generate_content(
                            model="gemini-3.5-flash",
                            contents=contents_payload
                        )

                        st.success(f"🎉 목표 중량 {target_total_weight}g 기준 Water-Q 보정 레시피 표 산출 완료!")
                        st.markdown(response.text)

                    except APIError as e:
                        st.error(f"API 오류가 발생했습니다: {e}")
        else:
            st.warning("⚠️ 목표 색상 사진과 1차 시편 사진을 모두 업로드해 주세요.")


# ====================================================
# TAB 2: 도장 결함 진단 모듈
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
                        model="gemini-3.5-flash",
                        contents=[img, defect_prompt]
                    )
                    st.success("결함 진단 완료!")
                    st.markdown(response.text)

                except APIError as e:
                    st.error(f"오류가 발생했습니다: {e}")
        else:
            st.warning("결함 부위 사진을 업로드해 주세요.")