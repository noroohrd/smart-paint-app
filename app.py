import streamlit as st
from google import genai
from google.genai.errors import APIError
from PIL import Image
import base64
import os

# ----------------------------------------------------
# 0. 이미지 최적화 및 Base64 변환 함수
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

def get_image_base64(image_path):
    """
    로컬 파일의 이미지를 읽어 Base64 인코딩 문자열로 반환합니다.
    """
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    return None

# ----------------------------------------------------
# 1. 페이지 기본 설정 및 노루페인트 커스텀 테마 Inject
# ----------------------------------------------------
st.set_page_config(
    page_title="NOROO Auto Refinishes | Water-Q AI Smart Color System",
    page_icon="🎨",
    layout="wide"
)

# 현재 스크립트 실행 경로 기준 로고 파일 탐색
current_dir = os.path.dirname(os.path.abspath(__file__))
logo_b64 = None

for logo_filename in ["waterq_logo.png", "waterq_logo.jpg", "waterq_logo.jpeg", "logo.png"]:
    target_path = os.path.join(current_dir, logo_filename)
    logo_b64 = get_image_base64(target_path)
    if not logo_b64:
        logo_b64 = get_image_base64(logo_filename) # 상대 경로 재시도
    if logo_b64:
        break

# 로고 HTML 구성 (들여쓰기 공백 제거로 코드블록 버그 방지)
if logo_b64:
    logo_header_html = f'<div class="waterq-badge"><img src="data:image/png;base64,{logo_b64}" class="waterq-logo-img" alt="WATER-Q Logo" /></div>'
else:
    logo_header_html = '<div class="waterq-badge-text"><div class="waterq-logo-text">WATER-Q</div><div class="waterq-sub-text">COLOR BANK SYSTEM</div></div>'

# 노루페인트 자동차보수용 도료(autorefinishes.co.kr) 웹사이트 컨셉 Custom CSS
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
    }

    /* 상단 노루페인트 헤더 배너 */
    .noroo-header-container {
        background: linear-gradient(135deg, #091936 0%, #003375 50%, #005BB5 100%);
        padding: 20px 28px;
        border-radius: 16px;
        color: #FFFFFF;
        margin-bottom: 25px;
        box-shadow: 0 8px 24px rgba(0, 51, 117, 0.18);
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        word-break: keep-all;
    }

    .noroo-title-group {
        display: flex;
        flex-direction: column;
    }

    .noroo-brand-name {
        font-size: 13px;
        font-weight: 700;
        color: #82B1FF;
        letter-spacing: 2px;
        text-transform: uppercase;
    }

    .noroo-main-title {
        font-size: 22px;
        font-weight: 800;
        color: #FFFFFF;
        margin: 4px 0 0 0;
        letter-spacing: -0.5px;
        word-break: keep-all;
    }

    /* Water-Q 로고 뱃지 (이미지용 화이트 카드) */
    .waterq-badge {
        background: #FFFFFF;
        padding: 8px 16px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }

    .waterq-logo-img {
        max-height: 48px;
        width: auto;
        object-fit: contain;
    }

    /* 로고 미감지 시 백업 텍스트 뱃지 */
    .waterq-badge-text {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.25);
        backdrop-filter: blur(12px);
        padding: 8px 16px;
        border-radius: 12px;
        text-align: center;
        flex-shrink: 0;
    }

    .waterq-logo-text {
        font-size: 18px;
        font-weight: 900;
        color: #00D2FF;
        letter-spacing: 2px;
        font-style: italic;
    }

    .waterq-sub-text {
        font-size: 9px;
        color: #E0E0E0;
        letter-spacing: 1px;
    }

    /* Streamlit Tab 스타일링 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: #F0F4F8;
        padding: 6px;
        border-radius: 12px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 700;
        color: #4A5568;
    }

    .stTabs [aria-selected="true"] {
        background-color: #003375 !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 12px rgba(0, 51, 117, 0.2);
    }

    /* 버튼 커스텀 */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #003375 0%, #005BB5 100%);
        color: white;
        border: none;
        padding: 14px 28px;
        font-size: 17px;
        font-weight: 700;
        border-radius: 10px;
        box-shadow: 0 4px 14px rgba(0, 51, 117, 0.25);
        transition: all 0.2s ease;
    }

    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #002252 0%, #00448A 100%);
        box-shadow: 0 6px 18px rgba(0, 51, 117, 0.35);
        transform: translateY(-1px);
    }

    /* 사이드바 스타일링 */
    [data-testid="stSidebar"] {
        background-color: #F8FAFC;
        border-right: 1px solid #E2E8F0;
    }
</style>
""", unsafe_allow_html=True)

# 헤더 배너 렌더링
header_container_html = f'<div class="noroo-header-container"><div class="noroo-title-group"><span class="noroo-brand-name">NOROO AUTO REFINISHES</span><h1 class="noroo-main-title">AI 스마트 조색 & 도장 결함 진단 솔루션</h1></div>{logo_header_html}</div>'
st.markdown(header_container_html, unsafe_allow_html=True)

# ----------------------------------------------------
# 2. 사이드바 - API 키 및 스마트폰/시스템 설정
# ----------------------------------------------------
with st.sidebar:
    st.header("⚙️ 시스템 및 기기 설정")
    
    # API 키 연동
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("🔒 API 키가 연동되었습니다.")
    else:
        api_key = st.text_input("Gemini API Key 입력", type="password")
    
    st.markdown("---")
    
    # 스마트폰 제조사 & 기종 선택 (2015년 ~ 현재)
    st.subheader("📱 스마트폰 카메라 보정 설정")
    
    brand = st.selectbox("제조사 선택", ["애플 (Apple)", "삼성 (Samsung)", "기타 / 직접 입력"])
    
    if brand == "애플 (Apple)":
        phone_model = st.selectbox(
            "상세 기종 선택 (2015년~현재)",
            [
                "iPhone 17 / Pro / Pro Max (2025/2026)",
                "iPhone 16 / Plus / Pro / Pro Max (2024)",
                "iPhone 15 / Plus / Pro / Pro Max (2023)",
                "iPhone 14 / Plus / Pro / Pro Max (2022)",
                "iPhone 13 / mini / Pro / Pro Max (2021)",
                "iPhone 12 / mini / Pro / Pro Max (2020)",
                "iPhone 11 / Pro / Pro Max (2019)",
                "iPhone XS / XS Max / XR (2018)",
                "iPhone X / 8 / 8 Plus (2017)",
                "iPhone 7 / 7 Plus / SE (2016)",
                "iPhone 6s / 6s Plus (2015)",
            ],
            index=3
        )
        selected_camera = f"애플 {phone_model}"
    elif brand == "삼성 (Samsung)":
        phone_model = st.selectbox(
            "상세 기종 선택 (2015년~현재)",
            [
                "Galaxy S26 / S26+ / S26 Ultra (2026)",
                "Galaxy S25 / S25+ / S25 Ultra / Z Fold7 / Flip7 (2025)",
                "Galaxy S24 / S24+ / S24 Ultra / Z Fold6 / Flip6 (2024)",
                "Galaxy S23 / S23+ / S23 Ultra / Z Fold5 / Flip5 (2023)",
                "Galaxy S22 / S22+ / S22 Ultra / Z Fold4 / Flip4 (2022)",
                "Galaxy S21 / S21+ / S21 Ultra / Z Fold3 / Flip3 (2021)",
                "Galaxy S20 시리즈 / Note 20 시리즈 / Z Fold2 / Flip (2020)",
                "Galaxy S10 시리즈 / Note 10 시리즈 / Fold (2019)",
                "Galaxy S9 / S9+ / Note 9 (2018)",
                "Galaxy S8 / S8+ / Note 8 (2017)",
                "Galaxy S7 / S7 Edge / Note 7 (2016)",
                "Galaxy S6 / S6 Edge / Note 5 (2015)",
            ]
        )
        selected_camera = f"삼성 {phone_model}"
    else:
        custom_input = st.text_input("기종명 직접 입력", value="기타 스마트폰")
        selected_camera = custom_input

    st.info(f"현재 카메라 보정 기종: **{selected_camera}**")

    st.markdown("---")
    st.markdown("### 📘 Water-Q 시스템 핵심 수칙")
    st.markdown("""
    * **카메라 왜곡 보정**: 선택 기종 특유의 HDR/색감 왜곡을 역추정하여 실제 육안 기준 색차 분석
    * **델타 E ($\Delta E$) 예측**: 도장 완료 시 목표 색상과의 예상 색차율 제공
    * **Q-7000(표준백색)**: 배합 내 **10% 이상 사용 금지** (초과 시 고농도 백색 **Q-7800 / Q-7900** 교체)
    * **신규 안료 추가/제외**: 필요 시 Water-Q DB 기반 **신규 안료 투입 및 불필요 안료 제외**
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
    st.subheader("🎨 워터큐(Water-Q) 전용 AI Fine-Tuning 조색")
    st.write("목표 색상과 1차 시편, 현재 배합표, 원하시는 조색 총량을 입력해 주세요.")

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        target_img_file = st.file_uploader("1. 목표 차체/판넬 사진 (Target)", type=["jpg", "png", "jpeg"], key="target_img")
        if target_img_file:
            st.image(Image.open(target_img_file), caption=f"목표 색상 (Target) - [{selected_camera}]", use_container_width=True)

    with col_t2:
        current_img_file = st.file_uploader("2. 1차 도장된 시편 사진 (Sample)", type=["jpg", "png", "jpeg"], key="current_img")
        if current_img_file:
            st.image(Image.open(current_img_file), caption=f"1차 시편 (Sample) - [{selected_camera}]", use_container_width=True)

    st.markdown("---")
    
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
                with st.spinner(f"AI가 [{selected_camera}] 카메라 특성을 보정하며 목표 중량({target_total_weight}g) 레시피를 계산 중입니다..."):
                    try:
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
                        첫 번째 이미지('목표 색상')와 두 번째 이미지('1차 도장 시편')를 비교 분석하여 최적의 보정 레시피를 제안해 주세요.

                        [입력 데이터 및 조건]
                        {recipe_prompt_part}
                        - **목표 조색 총 중량**: {target_total_weight}g (반드시 이 총 중량 비율 기준으로 최종 배합을 계산할 것)
                        - **촬영 기기 정보**: {selected_camera}
                        - 측색기 수치 정보: {lab_data if lab_data else '없음 (이미지 시각 분석 기반)'}

                        [★ 스마트폰 카메라 왜곡 보정 ({selected_camera}) ★]
                        업로드된 사진들은 **{selected_camera}** 기기로 촬영되었습니다.
                        해당 기기 특유의 이미지 프로세싱(자동 HDR, 명암비 강조, 소프트웨어 색감 보정, Sharpness 및 채도 변화 등)이 적용되어 있을 수 있습니다.
                        이를 감안하여 사진에 보이는 색상 그대로가 아닌, **실제 육안(Human Eye)으로 보았을 때의 색상, 명도, 입자감**을 역추정하여 정확히 분석하세요.

                        [★ 워터큐(Water-Q) 최적 배합 재구성 지침 ★]
                        1. **신규 안료 추가 & 불필요 안료 제외 자유권 부여**:
                           - 기존 1차 배합 안료의 중량 조절만으로 목표 색상 재현이 어려울 경우, 워터큐 안료 DB(Q-0130~Q-9890) 중 가장 적합한 신규 안료를 자유롭게 추가하세요.
                           - 기존 배합 중 색상을 탁하게 만들거나 워터큐 규정에 위반되는 안료는 제외(0g) 또는 차단 조치하세요.
                        2. **백색 제약 조건**: Q-7000(표준 백색)은 전체 배합 내 10% 이상 사용 금지. 백색 투입량이 10% 초과할 경우 반드시 고농도 백색인 **Q-7800** 또는 **Q-7900**을 신규 투입하세요.
                        3. **메탈릭 제약 조건**: 메탈릭/펄 색상 조색 시 **Q-3550(옥사이드 황색)**은 절대로 투입하지 말 것.

                        [작성 양식]
                        1. **실제 육안(Human Eye) 기준 색상 정밀 분석**: ({selected_camera}의 렌즈/HDR 프로세싱 특징을 감안하여 실제 육안에서 보이는 명도, 색상, 입자감 차이를 추정하여 설명)
                        2. **배합 변경 및 신규 안료 처방 이유**: (어떤 안료가 새로 추가되었고 어떤 안료가 제외/감량되었는지 사유 설명)
                        3. **📊 Water-Q AI 최적 재구성 보정표 (목표 총량 {target_total_weight}g 기준)**:
                           - 반드시 아래 마크다운 표 형식으로 작성하세요.
                           
                           | 안료 코드 (Q-Code) | 1차 배합 중량 (g) | AI 가감/처방량 (g) | 최종 레시피 중량 (g) | 상태 / 처방 역할 |
                           | :--- | :--- | :--- | :--- | :--- |
                           | 예: Q-7000 | 80.00 | -80.00 | 0.00 | ❌ 제외 (백색 10% 초과 규정 위반) |
                           | 예: Q-7800 | 0.00 | +15.00 | 15.00 | ✨ 신규 추가 (고농도 백색 / 명도 상승) |
                           | 예: Q-5450 | 5.00 | +0.50 | 5.50 | 🔺 증량 (청색 보강) |
                           | **합계 (Total)** | **기존 총량** | - | **{target_total_weight}g** | **목표 총량 완벽 산출** |

                        4. **🎯 예상 $\Delta E$ (색차) 및 육안 평가**: 
                           - 이 레시피로 재도장 시 목표 색상과의 **예상 델타 E ($\Delta E$) 수치**를 산출해 주세요.
                           - 예시: "예상 $\Delta E$: 0.4 (육안으로 식별이 거의 불가능한 수준)"
                        5. **교반 및 현장 도장 주의사항**: (희석 비율, 건조 시 주의점)
                        """

                        contents_payload.append(waterq_system_prompt)

                        response = client.models.generate_content(
                            model="gemini-3.5-flash",
                            contents=contents_payload
                        )

                        st.success(f"🎉 [{selected_camera}] 보정 적용 및 목표 중량 {target_total_weight}g 기준 레시피 산출 완료!")
                        st.markdown(response.text)

                    except APIError as e:
                        st.error(f"API 오류가 발생했습니다: {e}")
        else:
            st.warning("⚠️ 목표 색상 사진과 1차 시편 사진을 모두 업로드해 주세요.")

# ====================================================
# TAB 2: 도장 결함 진단 모듈
# ====================================================
with tab_defect:
    st.subheader("🔍 도장 결함 원인 분석 및 재작업 가이드")
    st.write("결함이 발생한 도장면 사진을 업로드하고 현장 특이사항을 입력해 주세요.")

    col1, col2 = st.columns([1, 1])

    with col1:
        defect_img_file = st.file_uploader("결함 부위 사진 업로드", type=["jpg", "png", "jpeg"], key="defect_img")
        if defect_img_file:
            st.image(Image.open(defect_img_file), caption=f"업로드된 결함 이미지 ({selected_camera})", use_container_width=True)

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
                    
                    - 촬영 기기: {selected_camera}
                    - 작업 환경 정보: {defect_context}

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