import streamlit as st
from google import genai
from google.genai.errors import APIError
from PIL import Image
import os
import io
import pandas as pd

# ----------------------------------------------------
# 0. 이미지 최적화 리사이즈 및 절대 경로 로고 탐색
# ----------------------------------------------------
def load_and_resize(image_file_or_bytes, max_size=(800, 800)):
    """
    고화질 이미지를 비율을 유지하면서 최대 800x800 해상도로 축소합니다.
    """
    if isinstance(image_file_or_bytes, bytes):
        img = Image.open(io.BytesIO(image_file_or_bytes))
    else:
        img = Image.open(image_file_or_bytes)
        
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.thumbnail(max_size)
    return img

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def find_logo_file():
    possible_names = ["waterq_logo.png", "waterq_logo.PNG", "waterq_logo.jpg", "logo.png"]
    for fname in possible_names:
        full_path = os.path.join(BASE_DIR, fname)
        if os.path.exists(full_path):
            return full_path
    return None

# ----------------------------------------------------
# 1. 페이지 기본 설정 및 세션 상태(Session State) 초기화
# ----------------------------------------------------
st.set_page_config(
    page_title="NOROO Auto Refinishes | Water-Q AI Smart Color System",
    page_icon="🎨",
    layout="wide"
)

# 세션 데이터 유지 (목표 사진, 1차 시편 사진, 1차 배합 레시피 저장)
if "target_img_bytes" not in st.session_state:
    st.session_state["target_img_bytes"] = None
if "target_img_name" not in st.session_state:
    st.session_state["target_img_name"] = None

if "sample_1_bytes" not in st.session_state:
    st.session_state["sample_1_bytes"] = None
if "sample_1_name" not in st.session_state:
    st.session_state["sample_1_name"] = None

# 기본 1차 레시피 데이터 예시 (표 형태 연동용)
if "recipe_table_df" not in st.session_state:
    st.session_state["recipe_table_df"] = pd.DataFrame({
        "안료 코드 (Q-Code)": ["Q-7800", "Q-8200", "Q-5450", "Q-9500"],
        "1차 배합 중량 (g)": [80.0, 10.0, 5.0, 5.0]
    })

# Custom CSS Inject
st.markdown("""<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
    }

    .noroo-header-box {
        background: linear-gradient(135deg, #091936 0%, #003375 50%, #005BB5 100%);
        padding: 22px 28px;
        border-radius: 16px;
        color: #FFFFFF;
        box-shadow: 0 8px 24px rgba(0, 51, 117, 0.18);
    }

    .noroo-brand-name {
        font-size: 13px;
        font-weight: 700;
        color: #82B1FF;
        letter-spacing: 2px;
        text-transform: uppercase;
    }

    .noroo-main-title {
        font-size: 23px;
        font-weight: 800;
        color: #FFFFFF;
        margin: 4px 0 0 0;
        letter-spacing: -0.5px;
        word-break: keep-all;
    }

    .comparison-card {
        background-color: #F8FAFC;
        border: 2px solid #005BB5;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 20px;
    }

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

    [data-testid="stSidebar"] {
        background-color: #F8FAFC;
        border-right: 1px solid #E2E8F0;
    }
</style>""", unsafe_allow_html=True)

# 메인 헤더 레이아웃
col_header_left, col_header_right = st.columns([3.5, 1.2], vertical_alignment="center")

with col_header_left:
    st.markdown("""<div class="noroo-header-box">
        <span class="noroo-brand-name">NOROO AUTO REFINISHES</span>
        <h1 class="noroo-main-title">AI 스마트 조색 & 도장 결함 진단 솔루션</h1>
    </div>""", unsafe_allow_html=True)

with col_header_right:
    logo_path = find_logo_file()
    if logo_path:
        st.image(logo_path, use_container_width=True)
    else:
        st.warning("⚠️ `waterq_logo.png` 로고 파일 필요")

st.markdown("---")

# ----------------------------------------------------
# 2. 사이드바 - API 키 및 스마트폰/시스템 설정
# ----------------------------------------------------
with st.sidebar:
    st.header("⚙️ 시스템 및 기기 설정")
    
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("🔒 API 키가 연동되었습니다.")
    else:
        api_key = st.text_input("Gemini API Key 입력", type="password")
    
    st.markdown("---")
    
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
    * **2차 레시피 표 자동연동**: 2차 조색 선택 시 1차 레시피 업로드 제거 및 표 형태 자동 대조
    * **시편 정밀 확대 비교**: 1차 vs 2차 시편 이미지 확대 비교
    * **카메라 왜곡 보정**: 선택 기종 특유의 HDR/색감 왜곡을 역추정하여 실제 육안 기준 색차 분석
    * **Q-7000(표준백색)**: 배합 내 **10% 이상 사용 금지** (초과 시 고농도 백색 **Q-7800 / Q-7900** 교체)
    """)

if not api_key:
    st.info("👈 왼쪽 사이드바에 Gemini API 키를 입력하면 시스템이 활성화됩니다.")
    st.stop()

client = genai.Client(api_key=api_key)

# ----------------------------------------------------
# 3. 메인 탭 구성
# ----------------------------------------------------
tab_tuning, tab_defect = st.tabs(["🎨 Water-Q AI 미세 조색 (Fine-Tuning)", "🔍 도장 결함 진단"])

# ====================================================
# TAB 1: Water-Q AI 스마트 미세 조색 모듈
# ====================================================
with tab_tuning:
    st.subheader("🎯 현재 진행할 조색 단계를 선택하세요:")
    
    stage_choice = st.radio(
        "조색 단계 선택",
        ["1차 조색 (최초 조색)", "2차 조색 (1차 시편 오차 반영 2차 보정)", "3차 이상 N차 조색 (N-1차 오차 반영 N차 보정)"],
        horizontal=True,
        key="stage_choice_radio"
    )
    
    st.markdown("---")

    # 단계별 플래그 및 문자열 세팅
    is_stage_1 = stage_choice.startswith("1차")
    is_stage_2 = stage_choice.startswith("2차")
    
    if is_stage_1:
        stage_code = "1차"
        prev_stage_code = "기본"
        sample_header_text = "2. 1차 도장 시편 사진 (Sample)"
        sample_uploader_text = "1차 도장 시편 사진 업로드"
        btn_text = "🚀 1차 Water-Q 미세 조색 실행"
    elif is_stage_2:
        stage_code = "2차"
        prev_stage_code = "1차"
        sample_header_text = "2. 2차 도장 시편 사진 (Sample)"
        sample_uploader_text = "2차 도장 시편 사진 업로드"
        btn_text = "🚀 2차 Water-Q 미세 조색 실행 (1차 vs 2차 대조표 생성)"
    else:
        stage_code = "N차"
        prev_stage_code = "이전(N-1차)"
        sample_header_text = f"2. {stage_code} 도장 시편 사진 (Sample)"
        sample_uploader_text = f"{stage_code} 도장 시편 사진 업로드"
        btn_text = f"🚀 {stage_code} Water-Q 미세 조색 실행 ({prev_stage_code} vs {stage_code} 대조표 생성)"

    col_t1, col_t2 = st.columns(2)
    
    # 1. 목표 차체 사진 (1차 등록 후 세션 유지)
    with col_t1:
        st.write("1. 목표 차체/판넬 사진 (Target)")
        uploaded_target = st.file_uploader(
            "목표 차체 사진 업로드 (자동 유지됨)",
            type=["jpg", "png", "jpeg"],
            key="target_file_uploader"
        )
        
        if uploaded_target is not None:
            st.session_state["target_img_bytes"] = uploaded_target.getvalue()
            st.session_state["target_img_name"] = uploaded_target.name

        if st.session_state["target_img_bytes"] is not None:
            target_pil_img = load_and_resize(st.session_state["target_img_bytes"])
            st.image(
                target_pil_img,
                caption=f"목표 색상 (Target) [자동 유지] - [{selected_camera}]",
                use_container_width=True
            )
        else:
            st.info("💡 목표 차체 사진을 업로드해 주세요. 2차/N차 단계에서도 자동으로 유지됩니다.")

    # 2. 단계별 시편 사진 업로드 (1차 사진 지워지고 2차/N차 신규 업로드)
    with col_t2:
        st.write(sample_header_text)
        current_img_file = st.file_uploader(
            sample_uploader_text,
            type=["jpg", "png", "jpeg"],
            key=f"sample_uploader_{stage_code}"
        )
        
        # 1차 조색일 때 1차 시편 세션 저장
        if is_stage_1 and current_img_file is not None:
            st.session_state["sample_1_bytes"] = current_img_file.getvalue()
            st.session_state["sample_1_name"] = current_img_file.name
            
        if current_img_file:
            st.image(
                Image.open(current_img_file),
                caption=f"{stage_code} 신규 도장 시편 사진 (Sample) - [{selected_camera}]",
                use_container_width=True
            )

    # ★ 2차 이상 조색 시: 1차 시편 vs 2차 시편 확대 비교 영역 표시 ★
    if not is_stage_1 and st.session_state["sample_1_bytes"] is not None and current_img_file is not None:
        st.markdown("---")
        st.markdown("""<div class="comparison-card">
            <h4 style="margin-top:0; color:#003375;">🔍 1차 시편 vs 2차 시편 정밀 확대 비교 (Visual Magnification)</h4>
            <p style="font-size:13px; color:#4A5568;">1차 시편 대비 2차 시편의 명도, 색조, 입자감 변화를 크게 대조하여 확인할 수 있습니다.</p>
        </div>""", unsafe_allow_html=True)
        
        c_comp1, c_comp2 = st.columns(2)
        with c_comp1:
            st.write("🔻 **1차 도장 시편 (이전)**")
            st.image(load_and_resize(st.session_state["sample_1_bytes"]), use_container_width=True)
        with c_comp2:
            st.write("🔻 **2차 도장 시편 (현재 신규)**")
            st.image(Image.open(current_img_file), use_container_width=True)

    st.markdown("---")
    
    col_r1, col_r2 = st.columns([1.2, 0.8])

    # 3. 배합 레시피 영역 (1차만 업로드 / 2차부터는 표 형태로 자동 정리)
    with col_r1:
        if is_stage_1:
            st.subheader("3. 1차 기본 배합 레시피 정보")
            recipe_input_type = st.radio(
                "배합표 입력 방식을 선택하세요:",
                ["📸 배합표 사진 업로드 (추천)", "✍️ 텍스트 직접 입력"],
                horizontal=True,
                key="recipe_type_1차"
            )

            recipe_img_file = None
            recipe_text = ""

            if "사진 업로드" in recipe_input_type:
                recipe_img_file = st.file_uploader(
                    "1차 배합표 / 조색기 화면 사진 업로드",
                    type=["jpg", "png", "jpeg"],
                    key="recipe_img_1차"
                )
                if recipe_img_file:
                    st.image(Image.open(recipe_img_file), caption="업로드된 배합표 이미지", width=350)
            else:
                recipe_text = st.text_area(
                    "1차 배합 레시피 직접 작성",
                    value="Q-7000 80g, Q-8200 10g, Q-5450 5g, Q-9500 5g",
                    placeholder="예: Q-7000 100g, Q-5450 12g, Q-8200 1.5g...",
                    key="recipe_text_1차"
                )
        else:
            # 2차/N차 조색 모드: 사진 업로드 제거 및 1차 배합 표(Table) 자동 출력
            st.subheader(f"3. {prev_stage_code} 확정 배합 레시피 (표 형태로 자동 연동)")
            st.info("💡 2차 이상 조색 시에는 배합표 사진 업로드가 생략되며, 1차 배합 데이터가 표(Table)로 정리되어 반영됩니다.")
            
            # 1차 배합 표 편집/확인
            edited_df = st.data_editor(
                st.session_state["recipe_table_df"],
                use_container_width=True,
                num_rows="dynamic",
                key=f"editor_{stage_code}"
            )
            st.session_state["recipe_table_df"] = edited_df

    with col_r2:
        st.subheader(f"4. {stage_code} 목표 조색 중량 및 측색 수치")
        
        target_total_weight = st.number_input(
            f"🎯 {stage_code} 새로 배합할 총 중량 (g)",
            min_value=10.0,
            max_value=10000.0,
            value=100.0,
            step=10.0,
            key=f"weight_{stage_code}",
            help="새로 조색할 전체 도료 중량을 입력하시면 AI가 해당 중량에 완벽히 들어맞는 신규 배합표를 산출합니다."
        )

        lab_data = st.text_input(
            "측색기 $L^*a*b^*$ 수치 (선택 사항)",
            placeholder="예: [목표] L*: 45.2, a*: 12.3 / [시편] L*: 43.8, a*: 13.5",
            key=f"lab_{stage_code}"
        )

    st.markdown("---")

    if st.button(btn_text, type="primary", use_container_width=True):
        if st.session_state["target_img_bytes"] is None:
            st.warning("⚠️ 목표 차체/판넬 사진(Target)을 1. 영역에 업로드해 주세요.")
        elif current_img_file is None:
            st.warning(f"⚠️ {stage_code} 도장 시편 사진(Sample)을 2. 영역에 업로드해 주세요.")
        elif is_stage_1 and (not recipe_img_file and not recipe_text.strip()):
            st.warning("⚠️ 1차 배합표 사진을 업로드하거나 텍스트를 입력해 주세요.")
        else:
            with st.spinner(f"AI가 [{stage_code} 조색] 모드로 {prev_stage_code} 배합표와 {stage_code} 시편 오차를 분석하여 신규 배합 대조표를 생성 중입니다..."):
                try:
                    img_target = load_and_resize(st.session_state["target_img_bytes"])
                    img_current = load_and_resize(current_img_file)

                    contents_payload = [img_target, img_current]

                    if is_stage_1:
                        if recipe_img_file:
                            img_recipe = load_and_resize(recipe_img_file)
                            contents_payload.append(img_recipe)
                            recipe_prompt_part = "- 1차 사용 배합 레시피: [첨부된 세 번째 이미지(배합표 사진)에서 안료명과 중량을 OCR 및 시각 분석하여 파악할 것]"
                        else:
                            recipe_prompt_part = f"- 1차 사용 배합 레시피: {recipe_text}"
                    else:
                        # 2차/N차 모드: DataFrame 표 형태 텍스트로 전달
                        table_str = st.session_state["recipe_table_df"].to_string(index=False)
                        recipe_prompt_part = f"- {prev_stage_code} 확정 배합표 (표 연동):\n{table_str}"

                    waterq_system_prompt = f"""
                    당신은 노루페인트 '워터큐(Water-Q) 칼라뱅크 시스템' 최고의 기술 조색 전문가입니다.
                    첫 번째 이미지('목표 색상')와 두 번째 이미지('{stage_code} 도장 시편')를 비교 분석하여, **새로 조색할 {stage_code} 신규 전체 배합 레시피(100% 비율)**를 제안해 주세요.

                    [진행 단계 및 입력 데이터]
                    - **현재 조색 진행 단계**: {stage_code} 조색
                    {recipe_prompt_part}
                    - **{stage_code} 새로 배합할 목표 총 중량**: {target_total_weight}g
                    - **촬영 기기 정보**: {selected_camera}
                    - 측색기 수치 정보: {lab_data if lab_data else '없음 (이미지 시각 분석 기반)'}

                    [★ {stage_code} 신규 재배합 및 시각적 대조표 지침 ★]
                    1. 기존 배합에 덧붓는 방식이 아닙니다. {prev_stage_code} 레시피로 도장한 시편과 목표 색상의 차이(명도, 색상, 채도, 입자감, Flop 감도)를 정밀 분석하여 **새 용기에 새로 조색할 목표 총 중량({target_total_weight}g) 기준의 신규 전체 배합표**를 산출하세요.
                    2. **시각적 대조표 필수 작성**: {prev_stage_code} 배합 중량과 {stage_code} 신규 배합 중량을 대조하여 각 안료의 가감 변화량(+g / -g)과 처방 역할을 표(Table)로 명확히 보여주세요.
                    3. {prev_stage_code} 배합에서 부족했던 색조 및 입자감은 비율을 높이고, 오차를 유발한 안료는 감량하거나 제외(0g) 처리하세요. 필요 시 워터큐 DB 중 최적 안료를 신규 투입하세요.
                    4. 백색 규정(Q-7000 10% 이내 사용, 초과 시 Q-7800/7900 사용) 및 메탈릭 조색 시 Q-3550 금지 수칙을 철저히 준수하세요.

                    [작성 양식]
                    1. **실제 육안(Human Eye) 기준 색상 및 {stage_code} 오차 정밀 분석**: ({selected_camera} 특성 보정 후 명도, 색상, 입자감, Flop 차이 분석)
                    2. **{stage_code} 배합 변경 처방 이유**: ({prev_stage_code} 배합 대비 안료 비율 수정 이유 및 신규 추가/제외 안료 설명)
                    3. **📊 Water-Q AI {prev_stage_code} vs {stage_code} 신규 배합 대조표 (목표 총량 {target_total_weight}g 기준)**:
                       - 반드시 아래 마크다운 표 형식으로 작성하세요.
                       
                       | 안료 코드 (Q-Code) | {prev_stage_code} 배합 중량 (g) | {stage_code} 신규 배합 중량 (g) | 가감 차이 (g) | 처방 역할 및 상태 |
                       | :--- | :--- | :--- | :--- | :--- |
                       | 예: Q-7000 | 80.00 | 0.00 | -80.00 | ❌ 제외 (백색 규정 위반) |
                       | 예: Q-7800 | 0.00 | 15.00 | +15.00 | ✨ 신규 추가 (고농도 백색) |
                       | 예: Q-5450 | 5.00 | 5.80 | +0.80 | 🔺 비율 보강 (청색 강화) |
                       | **합계 (Total)** | **{prev_stage_code} 총량** | **{target_total_weight}g** | **-** | **{stage_code} 100% 신규 완벽 배합** |

                    4. **🎯 예상 $\Delta E$ (색차) 및 육안 평가**: 
                       - 이번 {stage_code} 레시피로 재도장 시 예상되는 **델타 E ($\Delta E$) 수치** 표기 (예: "예상 $\Delta E$: 0.35 (매우 우수)")
                    5. **교반 및 도장 주의사항**: (희석 비율, 노즐 거리, 건조 수칙)
                    """

                    contents_payload.append(waterq_system_prompt)

                    response = client.models.generate_content(
                        model="gemini-3.5-flash",
                        contents=contents_payload
                    )

                    st.success(f"🎉 [{stage_code} 조색] 신규 배합 레시피 및 대조표 산출 완료!")
                    st.markdown(response.text)

                except APIError as e:
                    st.error(f"API 오류가 발생했습니다: {e}")

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
                    2. **추정 원인**: (샌딩, 토출량, 노즐 거리에 따른 원인 분석)
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