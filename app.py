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
# 1. 스마트폰 기종 데이터베이스 (2015년 ~ 현재)
# ----------------------------------------------------
PHONE_MODELS = {
    "애플 (iPhone)": [
        "iPhone 17 / 17 Pro / 17 Pro Max (2025/2026)",
        "iPhone 16 / 16 Plus / 16 Pro / 16 Pro Max (2024)",
        "iPhone 15 / 15 Plus / 15 Pro / 15 Pro Max (2023)",
        "iPhone 14 / 14 Plus / 14 Pro / 14 Pro Max (2022)",
        "iPhone 13 / 13 mini / 13 Pro / 13 Pro Max (2021)",
        "iPhone 12 / 12 mini / 12 Pro / 12 Pro Max (2020)",
        "iPhone 11 / 11 Pro / 11 Pro Max애플(iPhone)과 삼성(Galaxy)의 2015년 출시작부터 현재 모델까지 손쉽게 선택할 수 있는 **2단계 연동 드롭다운(제조사/년도 → 기종 선택)** 구조와 예시 코드를 정리해 드립니다.

웹 페이지나 앱 UI에 바로 적용할 수 있도록 **HTML/JavaScript** 예시 코드와 **JSON 데이터 구조** 형태로 구현했습니다.

---

## 1. 스마트폰 선택 드롭다운 UI 예시 (HTML/JS)

아래 코드를 복사해서 `.html` 파일로 저장 후 브라우저에서 열면 바로 작동하는 드롭다운 메뉴를 확인할 수 있습니다.

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>스마트폰 기종 선택</title>
  <style>
    .select-container {
      display: flex;
      gap: 12px;
      margin-top: 20px;
    }
    select {
      padding: 10px 14px;
      font-size: 15px;
      border: 1px solid #ccc;
      border-radius: 8px;
    }
  </style>
</head>
<body>

  <h2>📱 스마트폰 기종을 선택하세요</h2>

  <div class="select-container">
    <!-- 1단계: 제조사 선택 -->
    <select id="brandSelect" onchange="updateModels()">
      <option value="">제조사 선택</option>
      <option value="apple">애플 (Apple)</option>
      <option value="samsung">삼성 (Samsung)</option>
    </select>

    <!-- 2단계: 상세 모델 선택 -->
    <select id="modelSelect" disabled>
      <option value="">제조사를 먼저 선택해주세요</option>
    </select>
  </div>

  <script>
    // 2015년 ~ 현재(2026년) 주요 기종 데이터베이스
    const phoneData = {
      apple: [
        { year: 2026, models: ["iPhone SE (4세대)", "iPhone 17 Pro Max", "iPhone 17 Pro", "iPhone 17 Plus", "iPhone 17"] },
        { year: 2024, models: ["iPhone 16 Pro Max", "iPhone 16 Pro", "iPhone 16 Plus", "iPhone 16"] },
        { year: 2023, models: ["iPhone 15 Pro Max", "iPhone 15 Pro", "iPhone 15 Plus", "iPhone 15"] },
        { year: 2022, models: ["iPhone 14 Pro Max", "iPhone 14 Pro", "iPhone 14 Plus", "iPhone 14", "iPhone SE (3세대)"] },
        { year: 2021, models: ["iPhone 13 Pro Max", "iPhone 13 Pro", "iPhone 13", "iPhone 13 mini"] },
        { year: 2020, models: ["iPhone 12 Pro Max", "iPhone 12 Pro", "iPhone 12", "iPhone 12 mini", "iPhone SE (2세대)"] },
        { year: 2019, models: ["iPhone 11 Pro Max", "iPhone 11 Pro", "iPhone 11"] },
        { year: 2018, models: ["iPhone XS Max", "iPhone XS", "iPhone XR"] },
        { year: 2017, models: ["iPhone X", "iPhone 8 Plus", "iPhone 8"] },
        { year: 2016, models: ["iPhone 7 Plus", "iPhone 7", "iPhone SE (1세대)"] },
        { year: 2015, models: ["iPhone 6s Plus", "iPhone 6s"] }
      ],
      samsung: [
        { year: 2026, models: ["Galaxy S26 Ultra", "Galaxy S26+", "Galaxy S26"] },
        { year: 2025, models: ["Galaxy Z Fold7", "Galaxy Z Flip7", "Galaxy S25 Ultra", "Galaxy S25+", "Galaxy S25"] },
        { year: 2024, models: ["Galaxy Z Fold6", "Galaxy Z Flip6", "Galaxy S24 Ultra", "Galaxy S24+", "Galaxy S24", "Galaxy A35/A55"] },
        { year: 2023, models: ["Galaxy Z Fold5", "Galaxy Z Flip5", "Galaxy S23 Ultra", "Galaxy S23+", "Galaxy S23"] },
        { year: 2022, models: ["Galaxy Z Fold4", "Galaxy Z Flip4", "Galaxy S22 Ultra", "Galaxy S22+", "Galaxy S22"] },
        { year: 2021, models: ["Galaxy Z Fold3", "Galaxy Z Flip3", "Galaxy S21 Ultra", "Galaxy S21+", "Galaxy S21"] },
        { year: 2020, models: ["Galaxy Note 20 Ultra", "Galaxy Note 20", "Galaxy Z Fold2", "Galaxy Z Flip", "Galaxy S20 시리즈"] },
        { year: 2019, models: ["Galaxy Fold", "Galaxy Note 10/10+", "Galaxy S10/S10+/S10e"] },
        { year: 2018, models: ["Galaxy Note 9", "Galaxy S9/S9+"] },
        { year: 2017, models: ["Galaxy Note 8", "Galaxy S8/S8+"] },
        { year: 2016, models: ["Galaxy S7/S7 Edge", "Galaxy Note 7"] },
        { year: 2015, models: ["Galaxy S6/S6 Edge", "Galaxy Note 5"] }
      ]
    };

    function updateModels() {
      const brandSelect = document.getElementById("brandSelect");
      const modelSelect = document.getElementById("modelSelect");
      const selectedBrand = brandSelect.value;

      // 초기화
      modelSelect.innerHTML = "";

      if (!selectedBrand) {
        modelSelect.disabled = true;
        modelSelect.innerHTML = '<option value="">제조사를 먼저 선택해주세요</option>';
        return;
      }

      modelSelect.disabled = false;
      
      const defaultOption = document.createElement("option");
      defaultOption.value = "";
      defaultOption.textContent = "상세 모델을 선택하세요";
      modelSelect.appendChild(defaultOption);

      // 선택한 제조사의 연도별 모델 추가
      phoneData[selectedBrand].forEach(group => {
        const optgroup = document.createElement("optgroup");
        optgroup.label = `--- ${group.year}년 출시 ---`;

        group.models.forEach(model => {
          const option = document.createElement("option");
          option.value = model;
          option.textContent = model;
          
          // 사용자가 가지고 있는 아이폰 14 자동 기본 강조 예시
          if (model === "iPhone 14") {
            option.textContent += " (현재 사용중인 기종)";
          }

          optgroup.appendChild(option);
        });

        modelSelect.appendChild(optgroup);
      });
    }
  </script>

</body>
</html>