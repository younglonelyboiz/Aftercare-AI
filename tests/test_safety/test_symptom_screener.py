import pytest
from backend.app.clinical_agents.screener.symptom_screener import SymptomScreenerEngine
from backend.app.schemas.screener import ScreenerInput, ScreenerRuleConfig

@pytest.fixture
def screener():
    return SymptomScreenerEngine()

@pytest.fixture
def sample_profile():
    return {
        "patient_info": {
            "patient_id": "BN001",
            "full_name": "Nguyễn Văn An"
        },
        "clinical_status": {
            "personal_best_pef": 500
        },
        "current_medications": {
            "reliever_med": "Ventolin Inhaler 100mcg"
        },
        "action_plan_rules": {
            "yellow_zone": "Xịt 2 nhát Ventolin, nghỉ ngơi 20 phút.",
            "red_zone": "Xịt ngay 4 nhát Ventolin, ngồi thẳng thở chúm môi và gọi 115."
        },
        "follow_up": {
            "hospital": "Bệnh viện Phổi Trung Ương"
        }
    }

# ==============================================================================
# 1. KIỂM THỬ CHỈ SỐ SINH HIỆU (VITAL SIGNS BOUNDARIES)
# ==============================================================================
def test_pef_boundary_red_zone(screener, sample_profile):
    """PEF < 60% của 500 = 300 -> PEF = 290 phải kích hoạt RED_ZONE."""
    data = ScreenerInput(patient_id="BN001", pef_value=290)
    result = screener.evaluate(data, profile=sample_profile)
    assert result.risk_level == "RED_ZONE"
    assert "pef_critical" in result.matched_flags
    assert result.escalate_to_staff is True

def test_pef_boundary_yellow_zone(screener, sample_profile):
    """PEF = 350 (70% mức chuẩn) -> YELLOW_ZONE."""
    data = ScreenerInput(patient_id="BN001", pef_value=350)
    result = screener.evaluate(data, profile=sample_profile)
    assert result.risk_level == "YELLOW_ZONE"
    assert "pef_warning" in result.matched_flags
    assert result.escalate_to_staff is True

def test_spo2_critical_red_zone(screener, sample_profile):
    """SpO2 = 91% (< 92%) -> Bắt buộc RED_ZONE."""
    data = ScreenerInput(patient_id="BN001", spo2=91)
    result = screener.evaluate(data, profile=sample_profile)
    assert result.risk_level == "RED_ZONE"
    assert "spo2_critical" in result.matched_flags
    assert result.escalate_to_staff is True

def test_spo2_warning_yellow_zone(screener, sample_profile):
    """SpO2 = 94% (92 - 94%) -> YELLOW_ZONE."""
    data = ScreenerInput(patient_id="BN001", spo2=94)
    result = screener.evaluate(data, profile=sample_profile)
    assert result.risk_level == "YELLOW_ZONE"
    assert "spo2_warning" in result.matched_flags

def test_all_normal_vitals(screener, sample_profile):
    """PEF = 450 (90%), SpO2 = 98% -> NORMAL."""
    data = ScreenerInput(patient_id="BN001", pef_value=450, spo2=98)
    result = screener.evaluate(data, profile=sample_profile)
    assert result.risk_level == "NORMAL"
    assert result.escalate_to_staff is False
    assert len(result.matched_flags) == 0

# ==============================================================================
# 2. KIỂM THỬ XỊT THUỐC KHÔNG ĐỠ (RELIEVER REFRACTORY)
# ==============================================================================
def test_reliever_refractory_patterns(screener, sample_profile):
    """Bệnh nhân báo đã xịt thuốc nhưng không bớt -> RED_ZONE."""
    queries = [
        "Tôi đã xịt 2 nhát ventolin mà vẫn không đỡ khó thở",
        "vừa hít thuốc cắt cơn nhưng càng khó thở hơn",
        "xịt mấy lần rồi mà vẫn nghẹt thở"
    ]
    for q in queries:
        data = ScreenerInput(patient_id="BN001", free_text=q)
        res = screener.evaluate(data, profile=sample_profile)
        assert res.risk_level == "RED_ZONE", f"Thất bại với câu: {q}"
        assert res.escalate_to_staff is True

# ==============================================================================
# 3. KIỂM THỬ TIẾNG VIỆT, TỪ LÓNG & VIẾT TẮT (LINGUISTIC VARIATIONS)
# ==============================================================================
def test_vietnamese_teencode_and_no_accents(screener, sample_profile):
    """Kiểm tra nhận diện viết tắt: 'k tho dc', 'cap cuu', 'tim moi'."""
    queries = [
        "k tho dc nua roi giup toi voi",
        "me man bat tinh goi khong biet",
        "tim tai het ca moi"
    ]
    for q in queries:
        data = ScreenerInput(patient_id="BN001", free_text=q)
        res = screener.evaluate(data, profile=sample_profile)
        assert res.risk_level == "RED_ZONE", f"Thất bại với câu: {q}"

# ==============================================================================
# 4. KIỂM THỬ NGUYÊN TẮC ZERO-DIAGNOSIS (KHÔNG CHẨN ĐOÁN BỆNH HỌC)
# ==============================================================================
def test_zero_diagnosis_assertion(screener, sample_profile):
    """Đảm bảo không bao giờ chứa từ ngữ chẩn đoán bệnh học trong chỉ dẫn và lý do."""
    forbidden_terms = [
        "chẩn đoán", "bạn bị viêm phổi", "bạn mắc hen ác tính", 
        "kết luận bệnh", "chúng tôi chẩn đoán", "bệnh nhân mắc"
    ]
    test_inputs = [
        ScreenerInput(patient_id="BN001", free_text="tức ngực và ho liên tục"),
        ScreenerInput(patient_id="BN001", pef_value=250),
        ScreenerInput(patient_id="BN001", free_text="mê man lả đi")
    ]
    for item in test_inputs:
        res = screener.evaluate(item, profile=sample_profile)
        combined_text = (res.action_instructions + " " + " ".join(res.matched_reasons)).lower()
        for term in forbidden_terms:
            assert term not in combined_text, f"Vi phạm nguyên tắc không chẩn đoán: tìm thấy '{term}'"
        assert res.disclaimer is not None
        assert "tuyệt đối không thay thế chẩn đoán" in res.disclaimer

# ==============================================================================
# 5. KIỂM THỬ CẤU HÌNH ĐỘNG GHI ĐÈ (CONFIG OVERRIDE)
# ==============================================================================
def test_custom_rule_config_override(screener, sample_profile):
    """Bác sĩ nâng ngưỡng SpO2 đỏ lên 94% -> SpO2 = 93% phải nhảy vào RED_ZONE."""
    custom_cfg = ScreenerRuleConfig(
        personal_best_pef=500,
        red_spo2_threshold=94
    )
    data = ScreenerInput(patient_id="BN001", spo2=93, config_override=custom_cfg)
    res = screener.evaluate(data, profile=sample_profile)
    assert res.risk_level == "RED_ZONE"
    assert "spo2_critical" in res.matched_flags
