import React, { useState, useEffect } from 'react';
import { getNurseOverview, getCarePlan, updateCarePlan, getCheckinHistory } from '../../services/api';

export default function NurseCommandCenter({ onSelectPatientId }) {
  const [patientsOverview, setPatientsOverview] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedPid, setSelectedPid] = useState(null);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [patientHistory, setPatientHistory] = useState([]);

  // Form edit care plan
  const [bestPefInput, setBestPefInput] = useState(500);
  const [notesInput, setNotesInput] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const fetchOverview = async () => {
    try {
      setLoading(true);
      const data = await getNurseOverview();
      setPatientsOverview(data);
      if (data.length > 0 && !selectedPid) {
        handleSelectPatient(data[0].patient_id);
      }
    } catch (err) {
      console.error('Lỗi tải tổng quan điều dưỡng:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, []);

  const handleSelectPatient = async (pid) => {
    setSelectedPid(pid);
    try {
      const plan = await getCarePlan(pid);
      setSelectedPlan(plan);
      setBestPefInput(plan.personal_best_pef);
      setNotesInput(plan.doctor_notes || '');

      const hist = await getCheckinHistory(pid, 14);
      setPatientHistory(hist);
    } catch (err) {
      console.error('Lỗi tải chi tiết bệnh nhân:', err);
    }
  };

  const handleSaveCarePlan = async (e) => {
    e.preventDefault();
    if (!selectedPlan) return;
    setIsSaving(true);
    try {
      await updateCarePlan({
        patient_id: selectedPid,
        personal_best_pef: parseInt(bestPefInput, 10),
        baseline_spo2: selectedPlan.baseline_spo2 || 95,
        doctor_notes: notesInput,
        items: selectedPlan.items.map(it => ({
          item_type: it.item_type,
          title: it.title,
          dosage: it.dosage,
          instructions: it.instructions,
          schedule_times: it.schedule_times
        }))
      });
      alert('✓ Đã cập nhật thành công Phác đồ chăm sóc cho bệnh nhân!');
      fetchOverview();
    } catch (err) {
      alert('Lỗi cập nhật phác đồ: ' + err.message);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="nurse-command-center">
      {/* 1. Header & Triage Stats */}
      <div className="nurse-header">
        <div>
          <h2>🏥 Trung Tâm Điều Dưỡng Giám Sát Sau Xuất Viện (Asthma Care)</h2>
          <p>Phân loại ưu tiên tự động theo chuẩn GINA & Theo dõi độ tuân thủ dùng thuốc kiểm soát</p>
        </div>
        <button className="btn-refresh" onClick={fetchOverview}>🔄 Làm mới dữ liệu</button>
      </div>

      <div className="nurse-layout-grid">
        {/* CỘT TRÁI: DANH SÁCH BỆNH NHÂN THEO ĐỘ ƯU TIÊN */}
        <div className="nurse-patient-list-card">
          <div className="card-header">
            <h3>Danh Sách Bệnh Nhân Đang Quản Lý ({patientsOverview.length})</h3>
            <span className="sort-hint">Sắp xếp: 🔴 Cấp cứu ➔ 🟡 Cảnh báo ➔ 🟢 An toàn</span>
          </div>

          <div className="patient-cards-scroll">
            {patientsOverview.map((item) => {
              const zone = item.latest_checkin?.action_zone || 'UNKNOWN';
              const isSelected = selectedPid === item.patient_id;

              return (
                <div 
                  key={item.patient_id}
                  className={`nurse-p-card zone-border-${zone.toLowerCase()} ${isSelected ? 'active' : ''}`}
                  onClick={() => handleSelectPatient(item.patient_id)}
                >
                  <div className="p-card-top">
                    <span className="p-card-id">{item.patient_id}</span>
                    <span className={`zone-chip zone-${zone.toLowerCase()}`}>
                      {zone === 'RED' && '🚨 VÙNG ĐỎ CẤP CỨU'}
                      {zone === 'YELLOW' && '⚠️ VÙNG VÀNG'}
                      {zone === 'GREEN' && '🟢 VÙNG XANH'}
                      {zone === 'UNKNOWN' && '⚪ CHƯA CHECKIN'}
                    </span>
                  </div>

                  <div className="p-card-stats">
                    <div className="stat-col">
                      <span className="lbl">PEF gần nhất</span>
                      <strong className="val">
                        {item.latest_checkin?.pef_value ? `${item.latest_checkin.pef_value} L/m` : '---'}
                      </strong>
                      <small className="sub">Mục tiêu: {item.personal_best_pef}</small>
                    </div>

                    <div className="stat-col">
                      <span className="lbl">Tuân thủ 7 ngày</span>
                      <strong className="val text-primary">{item.adherence_rate_7d}%</strong>
                      <div className="adherence-bar-bg">
                        <div className="adherence-bar-fill" style={{ width: `${item.adherence_rate_7d}%` }}></div>
                      </div>
                    </div>

                    <div className="stat-col">
                      <span className="lbl">Thuốc cắt cơn</span>
                      <strong className="val">{item.latest_checkin?.reliever_puffs || 0} nhát</strong>
                      <small className="sub">Ventolin</small>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* CỘT PHẢI: CHI TIẾT LÂM SÀNG & CẤU HÌNH PHÁC ĐỒ */}
        <div className="nurse-detail-panel">
          {selectedPlan ? (
            <div>
              <div className="detail-top-bar">
                <h3>Hồ Sơ Giám Sát: <span className="highlight-id">{selectedPid}</span></h3>
                <span className="tag-best">Best PEF chuẩn: <strong>{selectedPlan.personal_best_pef} L/phút</strong></span>
              </div>

              {/* Biểu đồ xu hướng PEF 14 ngày */}
              <div className="trend-box">
                <h4>📈 Biến Thiên Lưu Lượng Đỉnh PEF (14 Ngày Qua)</h4>
                <div className="trend-bars-container">
                  {patientHistory.map((h, i) => {
                    const ratio = Math.min(100, Math.round((h.pef_value / selectedPlan.personal_best_pef) * 100));
                    return (
                      <div key={i} className="trend-bar-wrapper" title={`${h.date}: ${h.pef_value} L/min (${ratio}%)`}>
                        <div className="trend-bar-val">{h.pef_value}</div>
                        <div 
                          className={`trend-bar-fill bar-zone-${h.action_zone.toLowerCase()}`}
                          style={{ height: `${ratio}%` }}
                        ></div>
                        <div className="trend-bar-date">{h.date.slice(5)}</div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Form thiết lập Care Plan */}
              <form onSubmit={handleSaveCarePlan} className="care-plan-edit-form">
                <h4>⚙️ Cập Nhật Phác Đồ & Ngưỡng Cá Nhân Hóa (GINA)</h4>
                
                <div className="form-row">
                  <div className="form-group">
                    <label>Lưu lượng đỉnh cá nhân tốt nhất (Personal Best PEF - L/phút):</label>
                    <input 
                      type="number" 
                      value={bestPefInput} 
                      onChange={(e) => setBestPefInput(e.target.value)}
                      required 
                    />
                    <small>Ngưỡng 80% (Vùng Xanh): &ge; {Math.round(bestPefInput * 0.8)} L/min | 60% (Vùng Đỏ): &lt; {Math.round(bestPefInput * 0.6)} L/min</small>
                  </div>
                </div>

                <div className="form-group">
                  <label>Ghi chú & Dặn dò lâm sàng của điều dưỡng:</label>
                  <textarea 
                    rows={3} 
                    value={notesInput} 
                    onChange={(e) => setNotesInput(e.target.value)}
                    placeholder="VD: Lưu ý bệnh nhân nhạy cảm với thời tiết lạnh, cần xịt dự phòng trước khi ra ngoài..."
                  />
                </div>

                <div className="current-meds-summary">
                  <h5>Danh Mục Thuốc Đang Giao Trong Phác Đồ:</h5>
                  <ul>
                    {selectedPlan.items.map((it, idx) => (
                      <li key={idx}>
                        <strong>{it.title}</strong>: {it.dosage} ({it.schedule_times.join(', ')}) — <em>{it.instructions}</em>
                      </li>
                    ))}
                  </ul>
                </div>

                <button type="submit" className="btn-save-plan" disabled={isSaving}>
                  {isSaving ? 'Đang lưu...' : '💾 Lưu Phác Đồ Chăm Sóc Mới'}
                </button>
              </form>
            </div>
          ) : (
            <p className="select-prompt">Vui lòng chọn một bệnh nhân từ danh sách để xem chi tiết.</p>
          )}
        </div>
      </div>
    </div>
  );
}
