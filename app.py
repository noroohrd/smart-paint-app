import streamlit as st
from google import genai
from google.genai.errors import APIError
from PIL import Image
import os
import io
import re
import pandas as pd

# ----------------------------------------------------
# 0. 이미지 최적화 리사이즈 및 정규식 레시피 파서
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

def parse_recipe_to_df(recipe_text):
    """
    텍스트 레시피에서 Q-코드와 중량을 추출하여 DataFrame으로 변환합니다.
    예: "Q-7000 80g, Q-8200 10g" -> DataFrame 생성
    """
    pattern = r"(Q-\d+)\s*([\d\.]+)\s*g?"
    matches = re.findall(pattern, recipe_text, re.IGNORECASE)
    if matches:
        codes = [m[0].upper() for m in matches]
        weights = [float(m[1]) for m in matches]
        return pd.DataFrame({
            "안료 코드 (Q-Code)": codes,
            "1차 배합 중량 (g)": weights
        })
    else:
        return pd.DataFrame({
            "안료 코드 (Q-Code)": ["Q-7000", "Q-8200", "Q-5450"],
            "1차 배합 중량 (g)": [80.0, 10.0, 5.0]
        })

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def find_logo_file():
    possible_names = ["waterq_logo.png", "waterq_logo.PNG", "waterq_logo.jpg", "logo.png"]
    for fname in possible_names:
        full_path = os.path.join(BASE_DIR, fname)
        if os.path.exists(full_path):
            return full_path
    return None

# ----------------------------------------------------
# 1. 페이지 설정 및 세션 상태(Session State) 관리
# ----------------------------------------------------
st.set_page_config(
    page_title="NOROO Auto Refinishes | Water-Q AI Smart Color System",
    page_icon="🎨",
    layout="wide"
)

# 조색 워크플로우 진행 단계 상태 초기화
if "current_stage" not in st.session_state:
    st.session_state.current_stage = 1
if "target_img_bytes" not in st.session_state:
    st.session_state.target_img_bytes = None
if "target_img_name" not in st.session_state:
    st.session_state.target_img_name = None

if "prev_sample_bytes" not in st.session_state:
    st.session_state.prev_sample_bytes = None
if "temp_sample_bytes" not in st.session_state:
    st.session_state.temp_sample_bytes = None

if "recipe_table_df" not in st.session_state:
    st.session_state.recipe_table_df = pd.DataFrame({
        "안료 코드 (Q-Code)": ["Q-7000", "Q-8200", "Q-5450"],
        "1차 배합 중량 (g)": [80.0, 10.0, 5.0]
    })

if "ai_result_text" not in st.session_state:
    st.session_state.ai_result_text = ""
if "show_next_btn" not in st.session_state:
    st.session_state.show_next_btn = False

# 다음 조색 단계로 이동하는 콜백
def go_next_stage():
    st.session_state.current_stage += 1
    st.session_state.show_next_btn = False
    st.session_state.ai_result_text = ""
    if st.session_state.temp_sample_bytes is not None:
        st.session_state.prev_sample_bytes = st.session_state.temp_sample_bytes
        st.session_state.temp_sample_bytes = None

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

    .stage-badge {
        background-color: #003375;
        color: #FFFFFF;
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: 800;
        font-size: 15px;
        display: inline-block;
        margin-bottom: 15px;
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
    st.header("⚙️ 시스템 설정")
    
    if st.button("🔄 작업 초기화 (Reset)", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.markdown("---")

    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("🔒 API 키 연동됨")
    else:
        api_key = st.text_input("Gemini API Key 입력", type="password")
    
    st.markdown("---")
    st.subheader("📱 스마트폰 카메라 보정")
    
    brand = st.selectbox("제조사 선택", ["애플 (Apple)", "삼성 (Samsung)", "기타"])
    phone_model = st.selectbox("기종 선택", ["iPhone 14 / Pro (기본)", "iPhone 15 시리즈", "Galaxy S23/S24", "직접 입력"])
    selected_camera = f"{brand} {phone_model}"

    st.markdown("---")
    st.markdown("### 📘 Water-Q 원스톱 수칙")
    st.markdown("""
    * **원스톱 워크플로우**: 1차 조색 완료 후 하단 버튼 클릭으로 2차/N차 단계로 자동 전환
    * **1차 배합 실시간 이관**: 1차에서 입력한 배합표가 2차 표 데이터로 자동 연동
    * **시편 확대 대조 비교**: 이전 시편과 신규 시편을 1:1 확대 대조
    * **Q-7000 사용 제약**: 배합 내 **10% 이상 사용 금지** (초과 시 Q-7800/Q-7900 교체)
    """)

if not api_key:
    st.info("👈 사이드바에 Gemini API 키를 입력해 주세요.")
    st.stop()

client = genai.Client(api_key=api_key)

# ----------------------------------------------------
# 3. 메인 탭 구성 및 조색 워크플로우
# ----------------------------------------------------
tab_tuning, tab_defect = st.tabs(["🎨 Water-Q AI 미세 조색", "🔍 도장 결함 진단"])

with tab_tuning:
    current_stage = st.session_state.current_stage
    is_stage_1 = (current_stage == 1)
    
    stage_code = f"{current_stage}차"
    prev_stage_code = "1차" if current_stage == 2 else f"{current_stage-1}차"
    
    st.markdown(f'<div class="stage-badge">📍 현재 진행 단계: {stage_code} 조색 프로세스</div>', unsafe_allow_html=True)
    
    col_t1, col_t2 = st.columns(2)
    
    # 1. 목표 차체 사진 (1차 업로드 후 세션 잠금 유지)
    with col_t1:
        st.write("1. 목표 차체/판넬 사진 (Target)")
        if st.session_state.target_img_bytes is None:
            uploaded_target = st.file_uploader("목표 차체 사진 업로드 (자동 유지됨)", type=["jpg", "png", "jpeg"])
            if uploaded_target:
                st.session_state.target_img_bytes = uploaded_target.getvalue()
                st.session_state.target_img_name = uploaded_target.name
                st.rerun()
        else:
            st.image(
                load_and_resize(st.session_state.target_img_bytes),
                caption=f"목표 색상 (Target) [잠금됨: {st.session_state.target_img_name}] - [{selected_camera}]",
                use_container_width=True
            )
            if st.button("🔄 목표 사진 변경하기"):
                st.session_state.target_img_bytes = None
                st.rerun()

    # 2. 단계별 시편 사진 업로드 (2차로 넘어가면 1차 사진 삭제되고 2차 신규 업로드)
    with col_t2:
        st.write(f"2. {stage_code} 도장 시편 사진 (Sample)")
        current_img_file = st.file_uploader(
            f"{stage_code} 도장 시편 사진 업로드",
            type=["jpg", "png", "jpeg"],
            key=f"uploader_stage_{current_stage}"
        )
        if current_img_file:
            st.session_state.temp_sample_bytes = current_img_file.getvalue()
            st.image(
                Image.open(current_img_file),
                caption=f"{stage_code} 신규 도장 시편 (Sample) - [{selected_camera}]",
                use_container_width=True
            )

    # 3. 이전 시편 vs 신규 시편 1:1 확대 대조 비교 (2차 이상 조색 시 표시)
    if not is_stage_1 and st.session_state.prev_sample_bytes and st.session_state.temp_sample_bytes:
        st.markdown("---")
        st.markdown("""<div class="comparison-card">
            <h4 style="margin-top:0; color:#003375;">🔍 이전 시편 vs 신규 시편 정밀 확대 비교 (Visual Magnification)</h4>
            <p style="font-size:13px; color:#4A5568;">이전 시편 대비 신규 시편의 명도, 색조, 입자감 개선 상태를 크게 대조하여 확인하세요.</p>
        </div>""", unsafe_allow_html=True)
        
        c_comp1, c_comp2 = st.columns(2)
        with c_comp1:
            st.write(f"🔻 **{prev_stage_code} 도장 시편 (이전)**")
            st.image(load_and_resize(st.session_state.prev_sample_bytes), use_container_width=True)
        with c_comp2:
            st.write(f"🔻 **{stage_code} 도장 시편 (현재 신규)**")
            st.image(load_and_resize(st.session_state.temp_sample_bytes), use_container_width=True)

    st.markdown("---")
    
    col_r1, col_r2 = st.columns([1.2, 0.8])

    # 4. 배합 레시피 영역 (1차만 작성 / 2차부터는 1차 작성표 자동 연동)
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
                recipe_img_file = st.file_uploader("1차 배합표 / 조색기 화면 사진 업로드", type=["jpg", "png"], key="r_img_1차")
            else:
                recipe_text = st.text_area(
                    "1차 배합 레시피 직접 작성 (입력 시 2차 표로 자동 연동됩니다)",
                    value="Q-7000 80g, Q-8200 10g, Q-5450 5g",
                    placeholder="예: Q-7000 100g, Q-5450 12g...",
                    key="r_text_1차"
                )
                if recipe_text.strip():
                    parsed_df = parse_recipe_to_df(recipe_text)
                    if not parsed_df.empty:
                        st.session_state.recipe_table_df = parsed_df

            st.write("📋 **1차 확정 배합표 (2차 조색에 그대로 연결됩니다):**")
            edited_1st_df = st.data_editor(
                st.session_state.recipe_table_df,
                use_container_width=True,
                num_rows="dynamic",
                key="editor_1차_preview"
            )
            st.session_state.recipe_table_df = edited_1st_df

        else:
            # 2차/N차 조색 모드: 1차에서 완성한 배합표 자동 연동 (사진 업로드 제거됨)
            st.subheader(f"3. {prev_stage_code} 확정 배합 레시피 (자동 연동됨)")
            st.info(f"💡 {prev_stage_code} 조색 시 작성했던 배합 정보가 아래 표(Table)로 100% 연동되었습니다.")
            
            edited_df = st.data_editor(
                st.session_state.recipe_table_df,
                use_container_width=True,
                num_rows="dynamic",
                key=f"editor_{stage_code}"
            )
            st.session_state.recipe_table_df = edited_df

    with col_r2:
        st.subheader(f"4. {stage_code} 목표 조색 중량 및 측색 수치")
        
        target_total_weight = st.number_input(
            f"🎯 {stage_code} 새로 배합할 총 중량 (g)",
            min_value=10.0,
            max_value=10000.0,
            value=100.0,
            step=10.0,
            key=f"weight_{stage_code}",
            help="새로 조색할 전체 도료 중량을 입력하시면 AI가 완벽히 들어맞는 신규 배합표를 산출합니다."
        )

        lab_data = st.text_input(
            "측색기 $L^*a*b^*$ 수치 (선택 사항)",
            placeholder="예: [목표] L*: 45.2, a*: 12.3 / [시편] L*: 43.8, a*: 13.5",
            key=f"lab_{stage_code}"
        )

    st.markdown("---")

    # 5. AI 실행 버튼
    btn_label = f"🚀 {stage_code} Water-Q 미세 조색 실행" if is_stage_1 else f"🚀 {stage_code} Water-Q 미세 조색 실행 ({prev_stage_code} vs {stage_code} 대조표 생성)"

    if st.button(btn_label, type="primary", use_container_width=True):
        if st.session_state.target_img_bytes is None:
            st.warning("⚠️ 목표 차체/판넬 사진(Target)을 1. 영역에 업로드해 주세요.")
        elif st.session_state.temp_sample_bytes is None:
            st.warning(f"⚠️ {stage_code} 도장 시편 사진(Sample)을 2. 영역에 업로드해 주세요.")
        elif is_stage_1 and (not recipe_img_file and not recipe_text.strip()):
            st.warning("⚠️ 1차 배합표 사진을 업로드하거나 텍스트를 입력해 주세요.")
        else:
            with st.spinner(f"AI가 [{stage_code} 조색] 모드로 {prev_stage_code} 배합표와 {stage_code} 시편 오차를 분석하여 신규 대조표를 산출 중입니다..."):
                try:
                    img_target = load_and_resize(st.session_state.target_img_bytes)
                    img_current = load_and_resize(st.session_state.temp_sample_bytes)

                    contents_payload = [img_target, img_current]

                    if is_stage_1:
                        if recipe_img_file:
                            img_recipe = load_and_resize(recipe_img_file)
                            contents_payload.append(img_recipe)
                            recipe_prompt_part = "- 1차 사용 배합 레시피: [첨부된 세 번째 이미지(배합표 사진)에서 안료명과 중량을 OCR 분석할 것]"
                        else:
                            recipe_prompt_part = f"- 1차 사용 배합 레시피: {recipe_text}"
                    else:
                        table_str = st.session_state.recipe_table_df.to_string(index=False)
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

                    st.session_state.ai_result_text = response.text
                    st.session_state.show_next_btn = True

                except APIError as e:
                    st.error(f"API 오류가 발생했습니다: {e}")

    # 6. 결과 출력 및 '다음 단계 진행' 연속성 버튼
    if st.session_state.ai_result_text:
        st.markdown("### 📊 AI 조색 분석 및 대조 리포트")
        st.markdown(st.session_state.ai_result_text)

    if st.session_state.show_next_btn:
        st.markdown("---")
        st.info(f"💡 {stage_code} 도장 후 색상 매칭률이 아직 부족하다면, 하단 버튼을 클릭하여 방금 완료된 배합을 바탕으로 {current_stage + 1}차 조색을 즉시 진행하세요.")
        st.button(
            f"➡️ {current_stage + 1}차 조색으로 계속 진행하기",
            on_click=go_next_stage,
            type="primary",
            use_container_width=True
        )

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