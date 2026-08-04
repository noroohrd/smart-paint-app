import streamlit as st
from google import genai
from google.genai.errors import APIError
from PIL import Image
import os
import io
import re
import json
import pandas as pd

# ----------------------------------------------------
# 0. 이미지 최적화 및 3분할 가로 결합 함수
# ----------------------------------------------------
def load_and_resize(image_file_or_bytes, max_size=(1200, 1200)):
    if isinstance(image_file_or_bytes, bytes):
        img = Image.open(io.BytesIO(image_file_or_bytes))
    else:
        img = Image.open(image_file_or_bytes)
        
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.thumbnail(max_size)
    return img

def crop_center(img, crop_ratio=0.5):
    w, h = img.size
    cw, ch = int(w * crop_ratio), int(h * crop_ratio)
    left = (w - cw) // 2
    top = (h - ch) // 2
    return img.crop((left, top, left + cw, top + ch))

def create_3way_split_view(bytes_prev, bytes_target, bytes_curr, crop_ratio=0.5):
    img_prev = load_and_resize(bytes_prev)
    img_target = load_and_resize(bytes_target)
    img_curr = load_and_resize(bytes_curr)
    
    crop1 = crop_center(img_prev, crop_ratio)
    crop_t = crop_center(img_target, crop_ratio)
    crop2 = crop_center(img_curr, crop_ratio)
    
    h = min(crop1.height, crop_t.height, crop2.height)
    w1 = int(crop1.width * (h / crop1.height))
    wt = int(crop_t.width * (h / crop_t.height))
    w2 = int(crop2.width * (h / crop2.height))
    
    c1_resized = crop1.resize((w1, h))
    ct_resized = crop_t.resize((wt, h))
    c2_resized = crop2.resize((w2, h))
    
    merged_img = Image.new("RGB", (w1 + wt + w2, h))
    merged_img.paste(c1_resized, (0, 0))
    merged_img.paste(ct_resized, (w1, 0))
    merged_img.paste(c2_resized, (w1 + wt, 0))
    
    return merged_img

def extract_recipe_df_from_ai_text(text):
    if not text:
        return None
    try:
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if not json_match:
            json_match = re.search(r"(\{[\s\S]*?\"Q-\d+\"[\s\S]*?\})", text)
            
        if json_match:
            data = json.loads(json_match.group(1))
            codes = [k.upper().strip() for k in data.keys()]
            weights = [float(v) for v in data.values()]
            if codes:
                return pd.DataFrame({"안료 코드 (Q-Code)": codes, "1차 배합 중량 (g)": weights})
    except Exception:
        pass

    pattern = r"(Q-\d{3,4})\s*[:\=\|\s]+([\d\.]+)\s*g?"
    matches = re.findall(pattern, text, re.IGNORECASE)
    if matches:
        codes = []
        weights = []
        seen = set()
        for m in matches:
            code = m[0].upper()
            try:
                weight = float(m[1])
                if code not in seen and weight >= 0:
                    codes.append(code)
                    weights.append(weight)
                    seen.add(code)
            except ValueError:
                continue
        if codes:
            return pd.DataFrame({"안료 코드 (Q-Code)": codes, "1차 배합 중량 (g)": weights})

    return None

def extract_df_from_recipe_image(client, image_bytes):
    try:
        img = load_and_resize(image_bytes)
        prompt = """
        첨부된 도료 배합표/시편 카드 이미지에서 안료 코드(Q-Code)와 해당 중량(g)을 읽어 JSON으로만 출력하세요.
        ```json
        { "Q-9760": 88.0, "Q-9800": 60.31 }
        ```
        """
        res = client.models.generate_content(model="gemini-3.5-flash", contents=[img, prompt])
        return extract_recipe_df_from_ai_text(res.text)
    except Exception as e:
        st.error(f"사진 인식 중 오류가 발생했습니다: {e}")
        return None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def find_logo_file():
    possible_names = ["waterq_logo.png", "waterq_logo.PNG", "waterq_logo.jpg", "logo.png"]
    for fname in possible_names:
        full_path = os.path.join(BASE_DIR, fname)
        if os.path.exists(full_path):
            return full_path
    return None

# ----------------------------------------------------
# 1. 페이지 설정 및 Secrets 자동 API 키 연동
# ----------------------------------------------------
st.set_page_config(
    page_title="NOROO Auto Refinishes | Water-Q AI Smart Color System",
    page_icon="🎨",
    layout="wide"
)

# API 키 세크리트 자동 연결
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    st.error("⚠️ Streamlit Secrets에 GEMINI_API_KEY가 설정되지 않았습니다.")
    st.stop()

client = genai.Client(api_key=api_key)

# 세션 상태 초기화
if "current_stage" not in st.session_state:
    st.session_state.current_stage = 1
if "target_img_bytes" not in st.session_state:
    st.session_state.target_img_bytes = None
if "target_img_name" not in st.session_state:
    st.session_state.target_img_name = "카메라 직촬 Target"

if "prev_sample_bytes" not in st.session_state:
    st.session_state.prev_sample_bytes = None
if "temp_sample_bytes" not in st.session_state:
    st.session_state.temp_sample_bytes = None

if "recipe_table_df" not in st.session_state:
    st.session_state.recipe_table_df = pd.DataFrame({
        "안료 코드 (Q-Code)": ["", "", "", ""],
        "1차 배합 중량 (g)": [0.0, 0.0, 0.0, 0.0]
    })

if "ai_result_text" not in st.session_state:
    st.session_state.ai_result_text = ""
if "show_next_btn" not in st.session_state:
    st.session_state.show_next_btn = False
if "is_passed" not in st.session_state:
    st.session_state.is_passed = False

def go_next_stage():
    st.session_state.current_stage += 1
    st.session_state.show_next_btn = False
    st.session_state.ai_result_text = ""
    st.session_state.is_passed = False
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

    .distance-guide-box {
        background-color: #EBF8FF;
        border-left: 4px solid #3182CE;
        padding: 10px 14px;
        border-radius: 6px;
        font-size: 13px;
        color: #2B6CB0;
        margin-bottom: 12px;
    }

    .comparison-card {
        background-color: #F8FAFC;
        border: 2px solid #005BB5;
        border-radius: 12px;
        padding: 18px;
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

# 메인 헤더
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

st.markdown("---")

# ----------------------------------------------------
# 2. 사이드바 - 기기 설정 전용 (API 키 입력창 제거)
# ----------------------------------------------------
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    
    if st.button("🔄 작업 초기화 (Reset)", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.markdown("---")
    st.subheader("📱 스마트폰 카메라 보정")
    
    brand = st.selectbox("제조사 선택", ["애플 (Apple)", "삼성 (Samsung)", "기타"])
    phone_model = st.selectbox("기종 선택", ["iPhone 14 / Pro (기본)", "iPhone 15 시리즈", "Galaxy S23/S24", "직접 입력"])
    selected_camera = f"{brand} {phone_model}"

    st.markdown("---")
    st.markdown("### 📘 Water-Q 원스톱 수칙")
    st.markdown("""
    * **자동 연동 시스템**: API 키가 시스템에 자동 보안 적용되어 바로 사용 가능합니다.
    * **3분할 대조 (3-Way View)**: [이전 시편] | [🎯 목표 차체] | [신규 시편] 정밀 결합 비교
    * **엄격한 합격 기준 ($\Delta E \le 0.5$)**: 육안 감지 불가능 기준인 **색차 0.5 이하 도달 시 자동 조색 종료**
    * **15cm 정격 촬영 수칙**: 펄/메탈릭 알갱이 질감 분해능 확보를 위한 15cm 수직 촬영
    * **Q-7000 사용 제약**: 배합 내 **10% 이상 사용 금지** (초과 시 Q-7800/Q-7900 교체)
    """)

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
    
    # 1. 목표 차체 사진
    with col_t1:
        st.write("1. 목표 차체/판넬 사진 (Target)")
        st.markdown("""<div class="distance-guide-box">
            <b>📏 촬영 가이드</b>: 차체 표면으로부터 <b>약 15cm 거리</b>에서 수직(90°)으로 촬영해 주세요.
        </div>""", unsafe_allow_html=True)
        
        if st.session_state.target_img_bytes is None:
            t_input_tab1, t_input_tab2 = st.tabs(["📷 앱에서 직접 촬영", "📁 갤러리 파일 선택"])
            
            with t_input_tab1:
                cam_target = st.camera_input("목표 차체 촬영 (거리 15cm)", key="cam_target_input")
                if cam_target:
                    st.session_state.target_img_bytes = cam_target.getvalue()
                    st.session_state.target_img_name = "카메라 직접 촬영"
                    st.rerun()
                    
            with t_input_tab2:
                uploaded_target = st.file_uploader("목표 차체 사진 파일", type=["jpg", "png", "jpeg"], key="file_target_input")
                if uploaded_target:
                    st.session_state.target_img_bytes = uploaded_target.getvalue()
                    st.session_state.target_img_name = uploaded_target.name
                    st.rerun()
        else:
            st.image(
                load_and_resize(st.session_state.target_img_bytes),
                caption=f"목표 색상 (Target) [촬영 완료: {st.session_state.target_img_name}] - [{selected_camera}]",
                use_container_width=True
            )
            if st.button("🔄 목표 사진 다시 찍기"):
                st.session_state.target_img_bytes = None
                st.rerun()

    # 2. 단계별 시편 사진 직접 촬영
    with col_t2:
        st.write(f"2. {stage_code} 도장 시편 사진 (Sample)")
        st.markdown("""<div class="distance-guide-box">
            <b>📏 촬영 가이드</b>: 시편 표면으로부터 <b>약 15cm 거리</b>에서 수직(90°)으로 촬영해 주세요.
        </div>""", unsafe_allow_html=True)
        
        s_input_tab1, s_input_tab2 = st.tabs(["📷 앱에서 직접 촬영", "📁 갤러리 파일 선택"])
        
        with s_input_tab1:
            cam_sample = st.camera_input(f"{stage_code} 시편 촬영 (거리 15cm)", key=f"cam_sample_{current_stage}")
            if cam_sample:
                st.session_state.temp_sample_bytes = cam_sample.getvalue()
                
        with s_input_tab2:
            file_sample = st.file_uploader(f"{stage_code} 시편 파일 선택", type=["jpg", "png", "jpeg"], key=f"file_sample_{current_stage}")
            if file_sample:
                st.session_state.temp_sample_bytes = file_sample.getvalue()

        if st.session_state.temp_sample_bytes:
            st.image(
                Image.open(io.BytesIO(st.session_state.temp_sample_bytes)),
                caption=f"{stage_code} 신규 도장 시편 (Sample) - [{selected_camera}]",
                use_container_width=True
            )

    # 3. 3분할 결합 정밀 확대 대조 (3-Way Split View)
    if not is_stage_1 and st.session_state.prev_sample_bytes and st.session_state.target_img_bytes and st.session_state.temp_sample_bytes:
        st.markdown("---")
        st.markdown("""<div class="comparison-card">
            <h4 style="margin-top:0; color:#003375;">📱 목표 색상 중심 3분할 대형 정밀 대조 (3-Way Split View)</h4>
            <p style="font-size:14px; color:#2D3748; margin-bottom:8px;">
                <b>[좌: {prev_stage_code} 시편]</b> | <b>[중앙: 🎯 목표 차체(Target)]</b> | <b>[우: {stage_code} 신규 시편]</b>
            </p>
            <p style="font-size:12.5px; color:#4A5568;">
                목표 사진을 가운데에 두고 양옆으로 이전 시편과 신규 시편을 접합했습니다. 경계선 부위의 명도, 색감, 펄 입자감이 목표 색상에 얼마나 다가갔는지 크게 비교하세요.
            </p>
        </div>""".format(prev_stage_code=prev_stage_code, stage_code=stage_code), unsafe_allow_html=True)
        
        split_3way_img = create_3way_split_view(
            st.session_state.prev_sample_bytes,
            st.session_state.target_img_bytes,
            st.session_state.temp_sample_bytes,
            crop_ratio=0.5
        )
        
        st.image(
            split_3way_img,
            caption=f"◀️ {prev_stage_code} 시편 (이전) | 🎯 목표 차체 (Target) | {stage_code} 시편 (현재 신규) ▶️",
            use_container_width=True
        )

    st.markdown("---")
    
    col_r1, col_r2 = st.columns([1.2, 0.8])

    # 4. 배합 레시피 영역
    with col_r1:
        if is_stage_1:
            st.subheader("3. 1차 기본 배합 레시피 정보")
            
            r_input_tab1, r_input_tab2 = st.tabs(["📷 카드 촬영 / 업로드 (추천)", "✍️ 텍스트 직접 작성"])
            
            recipe_img_bytes = None
            recipe_text = ""

            with r_input_tab1:
                cam_recipe = st.camera_input("배합표/시편 카드 촬영", key="cam_recipe_1차")
                file_recipe = st.file_uploader("또는 카드 사진 파일 업로드", type=["jpg", "png", "jpeg"], key="file_recipe_1차")
                
                if cam_recipe:
                    recipe_img_bytes = cam_recipe.getvalue()
                elif file_recipe:
                    recipe_img_bytes = file_recipe.getvalue()

                if recipe_img_bytes:
                    st.image(Image.open(io.BytesIO(recipe_img_bytes)), caption="촬영/업로드된 배합표 카드", width=350)
                    
                    if st.button("🔍 카드 사진에서 배합표 읽어와 표에 반영하기", key="btn_ocr_recipe"):
                        with st.spinner("AI가 배합표 카드 사진 속 안료 코드와 0.25L 수치를 정밀 분석하는 중입니다..."):
                            extracted_df = extract_df_from_recipe_image(client, recipe_img_bytes)
                            if extracted_df is not None and not extracted_df.empty:
                                st.session_state.recipe_table_df = extracted_df
                                st.success("🎉 사진 속 안료 수치가 성공적으로 판독되어 아래 표에 자동 입력되었습니다!")
                                st.rerun()
                            else:
                                st.warning("⚠️ 카드에서 안료 수치를 완전히 읽지 못했습니다. 아래 표에 직접 수치를 작성해 주세요.")
            
            with r_input_tab2:
                recipe_text = st.text_area(
                    "1차 배합 레시피 직접 작성",
                    value="",
                    placeholder="예: Q-9760 88g, Q-9800 60.31g, Q-9500 18.76g...",
                    key="r_text_1차"
                )
                if recipe_text.strip():
                    parsed_df = extract_recipe_df_from_ai_text(recipe_text)
                    if parsed_df is not None and not parsed_df.empty:
                        st.session_state.recipe_table_df = parsed_df

            st.write("📋 **1차 확정 배합표 (2차 조색에 그대로 연동됩니다):**")
            edited_1st_df = st.data_editor(
                st.session_state.recipe_table_df,
                use_container_width=True,
                num_rows="dynamic",
                key="editor_1차_preview"
            )
            st.session_state.recipe_table_df = edited_1st_df

        else:
            st.subheader(f"3. {prev_stage_code} 확정 배합 레시피 (1차 실제 입력 데이터 100% 연동)")
            st.info(f"💡 {prev_stage_code} 조색 시 확정했던 실제 배합 중량이 아래 표(Table)로 정확히 연동되었습니다.")
            
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
            st.warning("⚠️ 목표 차체/판넬 사진(Target)을 촬영하거나 업로드해 주세요.")
        elif st.session_state.temp_sample_bytes is None:
            st.warning(f"⚠️ {stage_code} 도장 시편 사진(Sample)을 촬영하거나 업로드해 주세요.")
        elif is_stage_1 and st.session_state.recipe_table_df.empty:
            st.warning("⚠️ 배합표 카드를 촬영 후 [사진에서 배합표 읽어오기] 버튼을 누르거나 텍스트를 입력해 주세요.")
        else:
            with st.spinner(f"AI가 [CIE L*a*b* 색공간 및 Delta E <= 0.5 정밀 알고리즘]을 통해 분석 중입니다..."):
                try:
                    img_target = load_and_resize(st.session_state.target_img_bytes)
                    img_current = load_and_resize(st.session_state.temp_sample_bytes)

                    contents_payload = [img_target, img_current]

                    table_str = st.session_state.recipe_table_df.to_string(index=False)
                    recipe_prompt_part = f"- {prev_stage_code} 확정 배합표:\n{table_str}"

                    waterq_system_prompt = f"""
                    당신은 노루페인트 '워터큐(Water-Q) 칼라뱅크 시스템' 최고의 기술 조색 및 색채학 전문가입니다.
                    첫 번째 이미지('목표 색상')와 두 번째 이미지('{stage_code} 도장 시편')를 CIE L*a*b* 색공간 기준에서 정밀 관찰하세요.

                    [진행 단계 및 입력 데이터]
                    - **현재 조색 진행 단계**: {stage_code} 조색
                    {recipe_prompt_part}
                    - **{stage_code} 새로 배합할 목표 총 중량**: {target_total_weight}g
                    - **촬영 환경 수칙**: 15cm 표준 거리에 따른 펄/메탈릭 입자 분석 적용
                    - **촬영 기기 정보**: {selected_camera}
                    - 측색기 수치 정보: {lab_data if lab_data else '없음 (이미지 CIE L*a*b* 정밀 추정 분석)'}

                    [★ 핵심: 색공간 분석 및 Delta E <= 0.5 판정 규칙 ★]
                    1. **CIE L*a*b* 정밀 색공간 평가**:
                       - 명도 오차 ($\Delta L^*$): 정면/측면 밝기 오차 분석
                       - 적/녹 오차 ($\Delta a^*$): 적미(+) 또는 녹미(-) 오차 파악
                       - 황/청 오차 ($\Delta b^*$): 황미(+) 또는 청미(-) 오차 파악
                       - Flop 감도 오차: 입자 알갱이의 반사 명도차 분석
                    2. **Delta E 판정**:
                       - 두 시편 사진이 동일하거나, 육안으로 구분이 완전히 불가능한 경우 **예상 $\Delta E \le 0.5$** 로 엄격 판정하세요.
                    3. **$\Delta E \le 0.5$ 일 경우**:
                       - 리포트 상단에 **`[판정: 🎉 조색 완벽 합격 (Delta E <= 0.5)]`** 문구를 포함하세요.
                       - 추가 투입/감량 없이 **현재 레시피 유지(0.00g 변동)**로 최종 완벽 합격 처리하세요.
                    4. **$\Delta E > 0.5$ 일 경우**:
                       - 리포트 상단에 **`[판정: 🔺 미세 보정 필요]`** 문구를 포함하고 오차($\Delta L^*, \Delta a^*, \Delta b^*$)를 보정할 신규 배합표를 산출하세요.

                    [작성 양식]
                    1. **CIE L*a*b* 색공간 평가 및 Delta E**:
                       - **추정 색차 ($\Delta E$)**: x.xx
                       - **최종 판정**: [판정: 🎉 조색 완벽 합격 (Delta E <= 0.5)] 또는 [판정: 🔺 미세 보정 필요]
                       - **명도 오차 ($\Delta L^*$)**: (예: +0.2 밝음 / -0.4 어두움)
                       - **색상 오차 ($\Delta a^*, \Delta b^*$)**: (예: 적미 과다 / 황미 부족 등)
                       - **Flop 입자감 오차**: (메탈릭/펄 알갱이 밀도 분석)
                    2. **{stage_code} 배합 변경 처방 이유**: (오차 원인 및 안료 가감 이유 설명)
                    3. **📊 Water-Q AI {prev_stage_code} vs {stage_code} 신규 배합 대조표 (목표 총량 {target_total_weight}g 기준)**:
                       
                       | 안료 코드 (Q-Code) | {prev_stage_code} 배합 중량 (g) | {stage_code} 신규 배합 중량 (g) | 가감 차이 (g) | 처방 역할 및 상태 |
                       | :--- | :--- | :--- | :--- | :--- |
                       | 예: Q-9760 | 88.00 | 88.00 | 0.00 | ➖ 현재 레시피 유지 (합격) |
                       | **합계 (Total)** | **{prev_stage_code} 총량** | **{target_total_weight}g** | **-** | **최종 확정 배합** |

                    4. **교반 및 도장 주의사항**: (희석 비율, 노즐 거리, 건조 수칙)
                    """

                    contents_payload.append(waterq_system_prompt)

                    response = client.models.generate_content(
                        model="gemini-3.5-flash",
                        contents=contents_payload
                    )

                    st.session_state.ai_result_text = response.text
                    
                    if "조색 완벽 합격" in response.text or "Delta E <= 0.5" in response.text:
                        st.session_state.is_passed = True
                        st.session_state.show_next_btn = False
                    else:
                        st.session_state.is_passed = False
                        st.session_state.show_next_btn = True

                    parsed_df = extract_recipe_df_from_ai_text(response.text)
                    if parsed_df is not None and not parsed_df.empty:
                        st.session_state.recipe_table_df = parsed_df

                except APIError as e:
                    st.error(f"API 오류가 발생했습니다: {e}")

    # 6. 결과 출력 및 연속성 버튼 제어
    if st.session_state.ai_result_text:
        st.markdown("### 📊 AI 색공간 분석 및 대조 리포트")
        st.markdown(st.session_state.ai_result_text)

        if st.session_state.is_passed:
            st.balloons()
            st.success("🎉 색차 수치가 기준치($\Delta E \le 0.5$) 이하로 측정되어 조색이 완벽히 합격 처리되었습니다! 더 이상 추가 조색을 진행하지 않고 현재 배합을 최종 확정합니다.")

    if st.session_state.show_next_btn and not st.session_state.is_passed:
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