import React, { useState, useEffect } from 'react';
import {
  Activity,
  RefreshCw,
  TrendingUp,
  Settings,
  Save,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  User,
  Pill,
  FileText,
  ChevronRight,
  ShieldCheck
} from 'lucide-react';
import { getNurseOverview, getCarePlan, updateCarePlan, getCheckinHistory } from '../../services/api';

export default function NurseCommandCenter({ patients = [], selectedPatientId, onSelectPatientId }) {
  const [patientsOverview, setPatientsOverview] = useState([
    {
      patient_id: "BN-2026-ASTHMA-02",
      personal_best_pef: 280,
      baseline_spo2: 95,
      doctor_notes: "Bệnh nhân có tiền sử cấp cứu ICU năm ngoái, nhạy cảm với thời tiết lạnh và mạt bụi nhà.",
      adherence_rate_7d: 85,
      priority_score: 30,
      has_overdue_reminders: true,
      latest_checkin: {
        time: "2026-10-22T19:28:56.213794+00:00",
        pef_value: 250,
        pef_percent: 89.3,
        spo2_value: 95,
        action_zone: "GREEN",
        reliever_puffs: 0
      }
    },
    {
      patient_id: "BN-2026-ASTHMA-01",
      personal_best_pef: 520,
      baseline_spo2: 98,
      doctor_notes: "Bệnh nhân trẻ tuổi, tuân thủ tốt. Hạn chế tiếp xúc phấn hoa và khói bụi.",
      adherence_rate_7d: 92,
      priority_score: 0,
      has_overdue_reminders: false,
      latest_checkin: {
        time: "2026-10-22T20:28:56.214072+00:00",
        pef_value: 503,
        pef_percent: 96.7,
        spo2_value: 98,
        action_zone: "GREEN",
        reliever_puffs: 0
      }
    },
    {
      patient_id: "BN-2026-ASTHMA-03",
      personal_best_pef: 400,
      baseline_spo2: 97,
      doctor_notes: "Có trào ngược dạ dày thực quản (GERD), uống Esomeprazole trước ăn sáng, không ăn sát giờ ngủ.",
      adherence_rate_7d: 70,
      priority_score: 0,
      has_overdue_reminders: false,
      latest_checkin: null
    }
  ]);
  const [loading, setLoading] = useState(false);
  const [selectedPid, setSelectedPid] = useState(selectedPatientId || 'BN-2026-ASTHMA-02');
  const [selectedPlan, setSelectedPlan] = useState({
    id: "plan-BN-2026-ASTHMA-02",
    patient_id: "BN-2026-ASTHMA-02",
    personal_best_pef: 280,
    baseline_spo2: 95,
    doctor_notes: "Bệnh nhân có tiền sử cấp cứu ICU năm ngoái, nhạy cảm với thời tiết lạnh và mạt bụi nhà.",
    items: [
      {
        id: "item-1",
        item_type: "CONTROLLER_MED",
        title: "Xịt Symbicort 160/4.5mcg",
        dosage: "2 nhát/lần",
        instructions: "Hít sâu qua buồng đệm, nín thở 10s, súc miệng nước ấm sạch",
        schedule_times: ["08:00", "20:00"],
        is_active: true
      },
      {
        id: "item-2",
        item_type: "PEF_MEASURE",
        title: "Đo lưu lượng đỉnh (PEF) 2 lần/ngày",
        dosage: "Thổi 3 lần",
        instructions: "Đo vào lúc 07:30 sáng và 19:30 tối trước khi xịt thuốc",
        schedule_times: ["07:30", "19:30"],
        is_active: true
      }
    ]
  });
  const [patientHistory, setPatientHistory] = useState([
    { date: "2026-10-16", pef_value: 210, action_zone: "YELLOW" },
    { date: "2026-10-17", pef_value: 220, action_zone: "YELLOW" },
    { date: "2026-10-18", pef_value: 265, action_zone: "GREEN" },
    { date: "2026-10-19", pef_value: 270, action_zone: "GREEN" },
    { date: "2026-10-20", pef_value: 160, action_zone: "RED" },
    { date: "2026-10-21", pef_value: 215, action_zone: "YELLOW" },
    { date: "2026-10-22", pef_value: 250, action_zone: "GREEN" }
  ]);

  // Form edit care plan
  const [bestPefInput, setBestPefInput] = useState(280);
  const [notesInput, setNotesInput] = useState("Bệnh nhân có tiền sử cấp cứu ICU năm ngoái, nhạy cảm với thời tiết lạnh và mạt bụi nhà.");
  const [isSaving, setIsSaving] = useState(false);

  // Map tên bệnh nhân theo ID
  const patientNameMap = React.useMemo(() => {
    const map = {
      'BN-2026-ASTHMA-01': 'Nguyễn Văn An (28t)',
      'BN-2026-ASTHMA-02': 'Trần Thị Mai (61t)',
      'BN-2026-ASTHMA-03': 'Lê Hoàng Long (45t)'
    };
    if (patients && patients.length > 0) {
      patients.forEach(p => {
        map[p.patient_id] = `${p.full_name} (${p.age}t)`;
      });
    }
    return map;
  }, [patients]);

  const handleSelectPatient = async (pid) => {
    setSelectedPid(pid);
    if (onSelectPatientId) {
      onSelectPatientId(pid);
    }
    try {
      const plan = await getCarePlan(pid);
      setSelectedPlan(plan);
      setBestPefInput(plan.personal_best_pef || 500);
      setNotesInput(plan.doctor_notes || '');

      const hist = await getCheckinHistory(pid, 14);
      setPatientHistory(hist || []);
    } catch (err) {
      console.error('Lỗi tải chi tiết bệnh nhân:', err);
    }
  };

  const fetchOverview = async () => {
    try {
      setLoading(true);
      const data = await getNurseOverview();
      setPatientsOverview(data || []);

      const targetId = selectedPid || (data && data.length > 0 ? data[0].patient_id : 'BN-2026-ASTHMA-02');
      handleSelectPatient(targetId);
    } catch (err) {
      console.error('Lỗi tải tổng quan điều dưỡng:', err);
      // Fallback nếu API có độ trễ
      handleSelectPatient(selectedPid || 'BN-2026-ASTHMA-02');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, []);

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

  const selectedPatientName = patientNameMap[selectedPid] || selectedPid;

  return (
    <div className="nurse-command-center">
      {/* 1. Header & Triage Stats */}
      <div className="nurse-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <span
              style={{
                width: 32,
                height: 32,
                borderRadius: '8px',
                backgroundColor: 'var(--primary-subtle)',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--primary)'
              }}
            >
              <Activity size={18} />
            </span>
            <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600, color: '#0f172a' }}>
              Trung Tâm Điều Dưỡng Giám Sát Sau Xuất Viện (Asthma Care)
            </h2>
          </div>
          <p style={{ margin: 0, fontSize: '0.85rem', color: '#64748b' }}>
            Phân loại mức độ ưu tiên theo chuẩn GINA & Theo dõi độ tuân thủ dùng thuốc kiểm soát hằng ngày
          </p>
        </div>

        <button className="btn-refresh" onClick={fetchOverview} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spin' : ''} style={{ marginRight: 6, verticalAlign: 'middle' }} />
          Làm mới dữ liệu
        </button>
      </div>

      <div className="nurse-layout-grid">
        {/* CỘT TRÁI: DANH SÁCH BỆNH NHÂN THEO ĐỘ ƯU TIÊN */}
        <div className="nurse-patient-list-card">
          <div className="card-header" style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: '#0f172a' }}>
                Danh Sách Bệnh Nhân ({patientsOverview.length})
              </h3>
              <span
                style={{
                  fontSize: '0.72rem',
                  fontWeight: 500,
                  backgroundColor: '#f1f5f9',
                  color: '#475569',
                  padding: '2px 8px',
                  borderRadius: 4
                }}
              >
                Ưu tiên Triage
              </span>
            </div>
            <span className="sort-hint">Sắp xếp tự động: Cấp cứu ➔ Cảnh báo ➔ Ổn định</span>
          </div>

          <div className="patient-cards-scroll">
            {patientsOverview.map((item) => {
              const zone = item.latest_checkin?.action_zone || 'UNKNOWN';
              const isSelected = selectedPid === item.patient_id;
              const nameDisplay = patientNameMap[item.patient_id] || item.patient_id;

              return (
                <div
                  key={item.patient_id}
                  className={`nurse-p-card zone-border-${zone.toLowerCase()} ${isSelected ? 'active' : ''}`}
                  onClick={() => handleSelectPatient(item.patient_id)}
                >
                  <div className="p-card-top">
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.92rem', color: '#0f172a' }}>
                        {nameDisplay}
                      </div>
                      <span className="p-card-id" style={{ fontSize: '0.76rem', color: '#64748b' }}>
                        {item.patient_id}
                      </span>
                    </div>

                    <span className={`zone-chip zone-${zone.toLowerCase()}`}>
                      <span className={`status-circle status-${zone.toLowerCase()}`} style={{ marginRight: 4 }}></span>
                      {zone === 'RED' && 'Cấp cứu'}
                      {zone === 'YELLOW' && 'Cảnh báo'}
                      {zone === 'GREEN' && 'Ổn định'}
                      {zone === 'UNKNOWN' && 'Chưa đo'}
                    </span>
                  </div>

                  <div className="p-card-stats">
                    <div className="stat-col">
                      <span className="lbl">PEF gần nhất</span>
                      <strong className="val">
                        {item.latest_checkin?.pef_value ? `${item.latest_checkin.pef_value} L/m` : '---'}
                      </strong>
                      <small className="sub">Chuẩn: {item.personal_best_pef}</small>
                    </div>

                    <div className="stat-col">
                      <span className="lbl">SpO2</span>
                      <strong className="val" style={{ color: (item.latest_checkin?.spo2_value && item.latest_checkin.spo2_value < 92) ? '#dc2626' : 'inherit' }}>
                        {item.latest_checkin?.spo2_value ? `${item.latest_checkin.spo2_value}%` : '---'}
                      </strong>
                      <small className="sub">{item.latest_checkin?.spo2_value ? (item.latest_checkin.spo2_value < 92 ? 'Thiếu oxy' : 'Bình thường') : 'Chưa đo'}</small>
                    </div>

                    <div className="stat-col">
                      <span className="lbl">Tuân thủ 7 ngày</span>
                      <strong className="val text-primary">{item.adherence_rate_7d}%</strong>
                      <div className="adherence-bar-bg">
                        <div className="adherence-bar-fill" style={{ width: `${item.adherence_rate_7d}%` }}></div>
                      </div>
                    </div>
                  </div>

                  {item.has_overdue_reminders && (
                    <div
                      style={{
                        marginTop: 10,
                        paddingTop: 8,
                        borderTop: '1px dashed #fcd34d',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        fontSize: '0.74rem',
                        color: '#b45309',
                        fontWeight: 500
                      }}
                    >
                      <Clock size={12} /> Có lịch xịt thuốc / đo PEF chưa xác nhận
                    </div>
                  )}
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
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.2rem', color: '#0f172a', fontWeight: 600 }}>
                    Hồ Sơ Giám Sát: <span style={{ color: '#0284c7' }}>{selectedPatientName}</span>
                  </h3>
                  <span style={{ fontSize: '0.8rem', color: '#64748b' }}>
                    Mã hồ sơ: <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: '#334155' }}>{selectedPid}</span> • Phác đồ theo chuẩn GINA 2024
                  </span>
                </div>
                <span className="tag-best">
                  Personal Best PEF: <strong>{selectedPlan.personal_best_pef} L/phút</strong>
                </span>
              </div>

              {/* Biểu đồ xu hướng PEF 14 ngày */}
              <div className="trend-box">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <h4 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.92rem', color: '#1e293b' }}>
                    <TrendingUp size={16} color="var(--primary)" />
                    Biến Thiên Lưu Lượng Đỉnh PEF (14 Ngày Gần Nhất)
                  </h4>
                  <div style={{ display: 'flex', gap: 12, fontSize: '0.72rem', color: '#64748b' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#10b981' }}></span> &ge; 80% (Xanh)
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#f59e0b' }}></span> 60-80% (Vàng)
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#ef4444' }}></span> &lt; 60% (Đỏ)
                    </span>
                  </div>
                </div>

                {patientHistory && patientHistory.length > 0 ? (
                  <div className="trend-bars-container">
                    {patientHistory.map((h, i) => {
                      const ratio = Math.min(100, Math.round((h.pef_value / (selectedPlan.personal_best_pef || 500)) * 100));
                      return (
                        <div key={i} className="trend-bar-wrapper" title={`${h.date}: ${h.pef_value} L/min (${ratio}% chuẩn)`}>
                          <div className="trend-bar-val">{h.pef_value}</div>
                          <div
                            className={`trend-bar-fill bar-zone-${(h.action_zone || 'green').toLowerCase()}`}
                            style={{ height: `${ratio}%` }}
                          ></div>
                          <div className="trend-bar-date">{h.date ? h.date.slice(5) : ''}</div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div style={{ padding: '30px 20px', textAlign: 'center', color: '#94a3b8', fontSize: '0.85rem' }}>
                    Bệnh nhân chưa có dữ liệu đo PEF trong 14 ngày qua.
                  </div>
                )}
              </div>

              {/* Form thiết lập Care Plan */}
              <form onSubmit={handleSaveCarePlan} className="care-plan-edit-form">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                  <span
                    style={{
                      width: 28,
                      height: 28,
                      borderRadius: '6px',
                      backgroundColor: 'var(--primary-subtle)',
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'var(--primary)'
                    }}
                  >
                    <Settings size={15} />
                  </span>
                  <h4 style={{ margin: 0, fontSize: '0.98rem', fontWeight: 600, color: '#0f172a' }}>
                    Hiệu Chỉnh Ngưỡng Cá Nhân Hóa & Dặn Dò Lâm Sàng
                  </h4>
                </div>

                <div className="form-row" style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 14 }}>
                  <div className="form-group">
                    <label style={{ fontSize: '0.86rem', fontWeight: 600, color: '#334155', marginBottom: 4, display: 'block' }}>
                      Lưu lượng đỉnh cá nhân tốt nhất (Personal Best PEF - L/phút):
                    </label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <input
                        type="number"
                        value={bestPefInput}
                        onChange={(e) => setBestPefInput(e.target.value)}
                        required
                        style={{
                          width: 140,
                          padding: '8px 12px',
                          border: '1px solid #cbd5e1',
                          borderRadius: 6,
                          fontSize: '1rem',
                          fontWeight: 600,
                          textAlign: 'center'
                        }}
                      />
                      <span style={{ fontSize: '0.85rem', color: '#64748b' }}>L/phút</span>
                      <span
                        style={{
                          fontSize: '0.78rem',
                          backgroundColor: '#f0fdf4',
                          border: '1px solid #bbf7d0',
                          color: '#166534',
                          padding: '4px 10px',
                          borderRadius: 4
                        }}
                      >
                        Vùng Xanh (&ge; 80%): &ge; {Math.round(bestPefInput * 0.8)} L/m
                      </span>
                      <span
                        style={{
                          fontSize: '0.78rem',
                          backgroundColor: '#fef2f2',
                          border: '1px solid #fecaca',
                          color: '#991b1b',
                          padding: '4px 10px',
                          borderRadius: 4
                        }}
                      >
                        Vùng Đỏ (&lt; 60%): &lt; {Math.round(bestPefInput * 0.6)} L/m
                      </span>
                    </div>
                  </div>
                </div>

                <div className="form-group" style={{ marginTop: 14 }}>
                  <label style={{ fontSize: '0.86rem', fontWeight: 600, color: '#334155', marginBottom: 4, display: 'block' }}>
                    Ghi chú & Dặn dò điều dưỡng chuyên biệt cho ca này:
                  </label>
                  <textarea
                    rows={3}
                    value={notesInput}
                    onChange={(e) => setNotesInput(e.target.value)}
                    placeholder="VD: Lưu ý bệnh nhân nhạy cảm với thời tiết lạnh, cần xịt dự phòng trước khi ra ngoài..."
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      border: '1px solid #cbd5e1',
                      borderRadius: 6,
                      fontFamily: 'inherit',
                      fontSize: '0.86rem',
                      lineHeight: 1.5,
                      resize: 'vertical'
                    }}
                  />
                </div>

                <div className="current-meds-summary">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                    <Pill size={15} color="var(--primary)" />
                    <h5 style={{ margin: 0, fontSize: '0.88rem', fontWeight: 600, color: '#1e293b' }}>
                      Danh Mục Thuốc & Lịch Đo Đang Phân Bổ:
                    </h5>
                  </div>
                  <ul style={{ margin: 0, paddingLeft: 20 }}>
                    {selectedPlan.items && selectedPlan.items.length > 0 ? (
                      selectedPlan.items.map((it, idx) => (
                        <li key={idx} style={{ marginBottom: 6, fontSize: '0.85rem', color: '#334155' }}>
                          <strong>{it.title}</strong>: {it.dosage} ({it.schedule_times?.join(', ') || 'Định kỳ'}) — <span style={{ color: '#64748b' }}>{it.instructions}</span>
                        </li>
                      ))
                    ) : (
                      <li style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Chưa có phác đồ thuốc cụ thể.</li>
                    )}
                  </ul>
                </div>

                <button type="submit" className="btn-save-plan" disabled={isSaving}>
                  <Save size={15} style={{ marginRight: 6, verticalAlign: 'middle' }} />
                  {isSaving ? 'Đang lưu cập nhật...' : 'Lưu Phác Đồ Chăm Sóc Mới'}
                </button>
              </form>
            </div>
          ) : (
            <div style={{ padding: '60px 20px', textAlign: 'center', color: '#64748b' }}>
              <User size={36} color="#cbd5e1" style={{ marginBottom: 12 }} />
              <p className="select-prompt">Vui lòng chọn một bệnh nhân từ danh sách để xem chi tiết.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
