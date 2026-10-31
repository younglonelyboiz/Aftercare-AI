import React, { useState, useEffect } from 'react';
import { ClipboardCheck, CheckCircle2 } from 'lucide-react';
import ActionZoneBanner from './ActionZoneBanner';
import { evaluateScreener } from '../services/api';

export default function DailyCheckInForm({
  patientId,
  personalBestPef,
  actionPlan,
  pef,
  setPef,
  spo2,
  setSpo2,
  symptoms,
  setSymptoms,
  medsTaken,
  setMedsTaken,
  currentZone,
  onOpenChatWithAlert,
  onSubmitCheckin
}) {
  const pefRatio = personalBestPef > 0 ? Math.round((pef / personalBestPef) * 100) : 100;
  const [screenerResult, setScreenerResult] = useState({
    risk_level: "NORMAL",
    matched_flags: [],
    matched_reasons: ["Các chỉ số sinh hiệu và triệu chứng ghi nhận đều trong giới hạn an toàn bình thường."],
    action_instructions: "✅ TÌNH TRẠNG HIỆN TẠI ỔN ĐỊNH: Các chỉ số và triệu chứng của Nguyễn Văn An đều nằm trong vùng an toàn (Vùng Xanh).\n\n• Tiếp tục duy trì xịt thuốc kiểm soát định kỳ đúng liều lượng.\n• Giữ ấm đường thở, uống đủ nước ấm và theo dõi chỉ số PEF hàng ngày.",
    disclaimer: "Lưu ý y tế: Kết quả sàng lọc chỉ nhằm đánh giá mức độ khẩn cấp và hướng dẫn xử trí ban đầu, tuyệt đối không thay thế chẩn đoán của bác sĩ chuyên khoa."
  });

  // Tự động gọi evaluateScreener ngay khi mount và khi bệnh nhân thay đổi chỉ số
  useEffect(() => {
    let isMounted = true;
    const fetchScreener = async () => {
      try {
        const selectedList = [];
        if (symptoms.nightWaking) selectedList.push('night_waking');
        if (symptoms.relieverUsed) selectedList.push('reliever_frequent');
        if (symptoms.activityLimited) selectedList.push('activity_limited');
        if (symptoms.dangerSign) selectedList.push('severe_dyspnea');

        const result = await evaluateScreener({
          patient_id: patientId || 'BN-2026-ASTHMA-01',
          pef_value: pef,
          spo2: spo2,
          reliever_puffs: symptoms.relieverUsed ? 2 : 0,
          selected_symptoms: selectedList
        });
        if (isMounted) {
          setScreenerResult(result);
        }
      } catch (err) {
        console.error('Không thể đánh giá sàng lọc:', err);
      }
    };

    fetchScreener();
    return () => {
      isMounted = false;
    };
  }, [patientId, pef, spo2, symptoms]);

  const toggleSymptom = (key) => {
    setSymptoms((prev) => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  return (
    <div className="card-panel">
      <div className="card-header-row">
        <div className="card-title">
          <ClipboardCheck size={20} color="var(--primary)" />
          Check-in Sức Khỏe Hằng Ngày
        </div>
        <button
          onClick={onSubmitCheckin}
          style={{
            padding: '6px 14px',
            backgroundColor: 'var(--primary)',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: 600,
            fontSize: '0.84rem'
          }}
        >
          Lưu đánh giá hôm nay
        </button>
      </div>

      {/* Action Zone Feedback Banner */}
      <ActionZoneBanner
        zone={currentZone}
        actionPlan={actionPlan}
        screenerResult={screenerResult}
        onOpenChatWithAlert={onOpenChatWithAlert}
      />


      {/* 1. PEF Input */}
      <div className="input-section">
        <div className="section-label-row">
          <label className="section-label">1. Lưu lượng đỉnh (PEF đo sáng nay):</label>
          <div className="pef-number-group">
            <input
              type="number"
              className="pef-input"
              value={pef}
              min="100"
              max="800"
              onChange={(e) => setPef(Number(e.target.value))}
            />
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>L/phút</span>
            <span className={`pef-percent-badge ${currentZone}`}>
              {pefRatio}% mức chuẩn
            </span>
          </div>
        </div>
        <input
          type="range"
          className="pef-slider"
          min="100"
          max={Math.max(800, personalBestPef * 1.2)}
          value={pef}
          onChange={(e) => setPef(Number(e.target.value))}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          <span>100 L/phút</span>
          <span>Chuẩn cá nhân: {personalBestPef} L/phút</span>
          <span>800 L/phút</span>
        </div>
      </div>

      {/* 2. SpO2 Input */}
      <div className="input-section">
        <div className="section-label-row">
          <label className="section-label">2. Nồng độ oxy trong máu (SpO2):</label>
          <div className="spo2-row">
            <input
              type="number"
              className="spo2-input"
              value={spo2}
              min="70"
              max="100"
              onChange={(e) => setSpo2(Number(e.target.value))}
            />
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>%</span>
            <span style={{ fontSize: '0.8rem', color: spo2 < 92 ? '#dc2626' : (spo2 < 95 ? '#d97706' : '#059669'), fontWeight: 600 }}>
              {spo2 >= 95 ? 'Bình thường' : (spo2 >= 92 ? 'Cảnh báo giảm nhẹ' : 'Nguy hiểm (Thiếu oxy)')}
            </span>
          </div>
        </div>
      </div>

      {/* 3. Symptoms Checklist in past 24h */}
      <div className="input-section">
        <label className="section-label">3. Triệu chứng trong 24 giờ qua:</label>
        <div className="symptoms-checklist">
          <label className={`checkbox-item ${symptoms.nightWaking ? 'checked' : ''}`}>
            <input
              type="checkbox"
              className="checkbox-box"
              checked={symptoms.nightWaking}
              onChange={() => toggleSymptom('nightWaking')}
            />
            <span className="checkbox-text">
              Thức giấc ban đêm hoặc sáng sớm vì ho, khò khè hoặc khó thở
            </span>
          </label>

          <label className={`checkbox-item ${symptoms.relieverUsed ? 'checked' : ''}`}>
            <input
              type="checkbox"
              className="checkbox-box"
              checked={symptoms.relieverUsed}
              onChange={() => toggleSymptom('relieverUsed')}
            />
            <span className="checkbox-text">
              Phải dùng thuốc cắt cơn từ 2 lần trở lên trong ngày
            </span>
          </label>

          <label className={`checkbox-item ${symptoms.activityLimited ? 'checked' : ''}`}>
            <input
              type="checkbox"
              className="checkbox-box"
              checked={symptoms.activityLimited}
              onChange={() => toggleSymptom('activityLimited')}
            />
            <span className="checkbox-text">
              Bị hạn chế sinh hoạt/đi lại nhẹ nhàng vì cảm thấy hụt hơi
            </span>
          </label>

          <label className={`checkbox-item danger ${symptoms.dangerSign ? 'checked' : ''}`}>
            <input
              type="checkbox"
              className="checkbox-box"
              checked={symptoms.dangerSign}
              onChange={() => toggleSymptom('dangerSign')}
            />
            <span className="checkbox-text" style={{ fontWeight: 600, color: symptoms.dangerSign ? '#991b1b' : 'inherit' }}>
              Dấu hiệu nguy cấp: thở không nổi, nói không ra hơi, rút lõm ngực
            </span>
          </label>
        </div>
      </div>

      {/* 4. Medication Adherence */}
      <div className="adherence-row">
        <span className="adherence-label">
          4. Tuân thủ: Đã hít/xịt thuốc duy trì đúng liều sáng nay
        </span>
        <button
          onClick={() => setMedsTaken(!medsTaken)}
          style={{
            padding: '6px 14px',
            backgroundColor: medsTaken ? '#059669' : '#e2e8f0',
            color: medsTaken ? 'white' : '#475569',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: 600,
            fontSize: '0.84rem',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6
          }}
        >
          <CheckCircle2 size={16} /> {medsTaken ? 'Đã dùng thuốc' : 'Chưa dùng'}
        </button>
      </div>
    </div>
  );
}
