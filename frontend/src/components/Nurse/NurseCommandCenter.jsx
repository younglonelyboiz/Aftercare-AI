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
import {
  getNurseOverview,
  getCarePlan,
  updateCarePlan,
  getCheckinHistory,
  getActiveAlertTickets,
  acknowledgeAlertTicket,
  resolveAlertTicket,
  triggerNonResponseScan
} from '../../services/api';
import LiveAlertBanner from './LiveAlertBanner';
import TicketResolveModal from './TicketResolveModal';
import NotificationToast from '../Common/NotificationToast';
import { medicalAudioAlert } from '../../utils/audioAlert';

// Danh mục nhãn cảnh báo sinh từ Chatbot (W07-T5.1)
const CHATBOT_ALERT_TYPES = new Set([
  'CHAT_RED_FLAG_DETECTION',
  'CHAT_YELLOW_ZONE_ALERT',
  'MEDICATION_NONADHERENCE_INTENT',
  'MENTAL_HEALTH_CONCERN',
  'SYSTEM_DEGRADED_PATIENT_UNSERVED',
]);

export function isChatbotTicket(ticket) {
  if (!ticket) return false;
  return (
    ticket.source_channel === 'CHATBOT' ||
    ticket.clinical_data?.source === 'CHAT' ||
    CHATBOT_ALERT_TYPES.has(ticket.alert_type)
  );
}

export default function NurseCommandCenter({ patients = [], selectedPatientId, onSelectPatientId }) {
  const [patientsOverview, setPatientsOverview] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedPid, setSelectedPid] = useState(selectedPatientId || 'BN-2026-ASTHMA-02');
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [bestPefInput, setBestPefInput] = useState(280);
  const [notesInput, setNotesInput] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [patientHistory, setPatientHistory] = useState([]);

  // REAL-TIME ESCALATION & ALERT TICKETS STATES (W06)
  const [tickets, setTickets] = useState([]);
  const [isMuted, setIsMuted] = useState(false);
  const [resolvingTicket, setResolvingTicket] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [isScanning, setIsScanning] = useState(false);

  // NOTIFICATION TOAST UI (Thay thế hoàn toàn window.alert mặc định)
  const [toast, setToast] = useState({ show: false, type: 'info', title: '', message: '', stats: null });
  const showToast = (config) => {
    setToast({ show: true, stats: null, duration: 3000, ...config });
  };
  const closeToast = () => {
    setToast((prev) => ({ ...prev, show: false }));
  };



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

  // 1. Tải danh sách vé cảnh báo từ Server
  const fetchTickets = async () => {
    try {
      const activeTickets = await getActiveAlertTickets();
      setTickets(activeTickets || []);
      // Nếu có vé P0_CRITICAL trạng thái OPEN thì phát còi báo động
      const hasOpenP0 = activeTickets && activeTickets.some(t => t.priority === 'P0_CRITICAL' && t.status === 'OPEN');
      if (hasOpenP0 && !isMuted) {
        medicalAudioAlert.startP0Siren();
      } else {
        medicalAudioAlert.stop();
      }
    } catch (err) {
      console.warn('Lỗi tải danh sách vé cảnh báo:', err);
    }
  };

  // 2. Thiết lập kết nối WebSocket thời gian thực (W06 Escalation Hub)
  useEffect(() => {
    fetchTickets();

    const apiBase = new URL(import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1');
    apiBase.protocol = apiBase.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${apiBase.href.replace(/\/$/, '')}/escalations/ws/nurse-alerts`;
    let ws = null;
    let pingInterval = null;

    try {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setWsConnected(true);
        // Gửi ping định kỳ 25s để giữ kết nối
        pingInterval = setInterval(() => {
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, 25000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.event === 'NEW_ALERT_TICKET') {
            const newTicket = data.ticket;
            setTickets(prev => {
              const filtered = prev.filter(t => t.id !== newTicket.id);
              return [newTicket, ...filtered];
            });

            // Kích hoạt âm thanh theo mức độ ưu tiên
            if (newTicket.priority === 'P0_CRITICAL') {
              if (!isMuted) medicalAudioAlert.startP0Siren();
            } else {
              medicalAudioAlert.playWarningBeep();
            }

            // Làm mới danh sách bệnh nhân
            fetchOverview();
          } else if (data.event === 'TICKET_ACKNOWLEDGED') {
            const ackTicket = data.ticket;
            setTickets(prev => prev.map(t => t.id === ackTicket.id ? ackTicket : t));
            medicalAudioAlert.stop();
          } else if (data.event === 'TICKET_RESOLVED') {
            const resTicket = data.ticket;
            setTickets(prev => prev.filter(t => t.id !== resTicket.id));
            medicalAudioAlert.stop();
            fetchOverview();
          } else if (data.event === 'PATIENT_CONFIRMED_SAFE') {
            fetchTickets();
            fetchOverview();
          }
        } catch (e) {
          // Tin dạng text pong
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        if (pingInterval) clearInterval(pingInterval);
      };

      ws.onerror = () => {
        setWsConnected(false);
      };
    } catch (err) {
      console.warn('Lỗi khởi tạo WebSocket:', err);
    }

    return () => {
      medicalAudioAlert.stop();
      if (pingInterval) clearInterval(pingInterval);
      if (ws) ws.close();
    };
  }, [isMuted]);

  // Handlers thao tác vé
  const handleAcknowledgeTicket = async (ticketId) => {
    try {
      await acknowledgeAlertTicket(ticketId, 'Điều dưỡng trực ban');
      medicalAudioAlert.stop();
      fetchTickets();
      showToast({
        type: 'info',
        title: 'Đã Tiếp Nhận Ca',
        message: 'Đã ngắt còi báo động. Vui lòng liên hệ hỗ trợ bệnh nhân.'
      });
    } catch (err) {
      showToast({ type: 'error', title: 'Lỗi Tiếp Nhận', message: err.message });
    }
  };

  const handleResolveTicket = async (ticketId, nurseName, notes) => {
    try {
      await resolveAlertTicket(ticketId, nurseName, notes);
      medicalAudioAlert.stop();
      fetchTickets();
      fetchOverview();
      showToast({
        type: 'success',
        title: 'Đã Đóng Ca Can Thiệp Thành Công',
        message: 'Biên bản xử lý lâm sàng đã được lưu vào hệ thống kiểm toán y tế.'
      });
    } catch (err) {
      showToast({ type: 'error', title: 'Lỗi Xử Lý Ca', message: err.message });
    }
  };

  const handleToggleMute = () => {
    const nextMuted = medicalAudioAlert.toggleMute();
    setIsMuted(nextMuted);
    showToast({
      type: nextMuted ? 'warning' : 'info',
      title: nextMuted ? 'Đã Tắt Chuông Báo Động' : 'Đã Bật Chuông Báo Động',
      message: nextMuted ? 'Âm thanh cảnh báo sẽ tạm thời không phát.' : 'Hệ thống sẽ phát còi khi có ca P0 nguy cấp.'
    });
  };

  const handleManualScan = async () => {
    setIsScanning(true);
    try {
      const res = await triggerNonResponseScan();
      const s = res.scan_results;
      showToast({
        type: 'success',
        title: 'Hoàn Tất Quét Tự Động Non-Response',
        message: `Đã kiểm tra toàn bộ ${s.scanned_patients || 3} bệnh nhân đang theo dõi ngoại trú.`,
        stats: s,
        duration: 3000
      });
      fetchTickets();
      fetchOverview();
    } catch (err) {
      showToast({ type: 'error', title: 'Lỗi Quét Tự Động', message: err.message });
    } finally {
      setIsScanning(false);
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
      showToast({
        type: 'success',
        title: 'Cập Nhật Thành Công',
        message: 'Đã lưu phác đồ chăm sóc và ngưỡng PEF mới cho bệnh nhân.'
      });
      fetchOverview();
    } catch (err) {
      showToast({ type: 'error', title: 'Lỗi Cập Nhật Phác Đồ', message: err.message });
    } finally {
      setIsSaving(false);
    }
  };

  const selectedPatientName = patientNameMap[selectedPid] || selectedPid;

  return (
    <div className="nurse-command-center">
      {/* 0. Toast Notification UI chuyên nghiệp thay thế window.alert */}
      <NotificationToast toast={toast} onClose={closeToast} />

      {/* 0. Live Escalation Alert Banner (W06 Real-Time Siren & Flash) */}
      <LiveAlertBanner
        tickets={tickets}
        onAcknowledge={handleAcknowledgeTicket}
        onOpenResolve={(t) => setResolvingTicket(t)}
        isMuted={isMuted}
        onToggleMute={handleToggleMute}
      />

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
            Phân loại mức độ ưu tiên theo chuẩn GINA & Tự động phát hiện ca nguy kịch tức thời (Escalation Engine W06)
          </p>
        </div>


        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className="btn-refresh"
            onClick={handleManualScan}
            disabled={isScanning}
            title="Quét ngay các ca bỏ quên check-in 24h hoặc quá 20m Vùng Vàng"
            style={{ backgroundColor: '#f8fafc', color: '#0369a1', borderColor: '#bae6fd' }}
          >
            <Clock size={14} className={isScanning ? 'spin' : ''} style={{ marginRight: 6, verticalAlign: 'middle' }} />
            {isScanning ? 'Đang quét...' : 'Quét Non-Response'}
          </button>

          <button className="btn-refresh" onClick={fetchOverview} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin' : ''} style={{ marginRight: 6, verticalAlign: 'middle' }} />
            Làm mới dữ liệu
          </button>
        </div>
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
              const patientTickets = tickets.filter((t) => t.patient_id === item.patient_id && t.status !== 'RESOLVED');
              const chatTicket = patientTickets.find((t) => isChatbotTicket(t));

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

                  {chatTicket && (
                    <div
                      className="chatbot-alert-badge"
                      style={{
                        marginTop: 8,
                        padding: '6px 8px',
                        borderRadius: 6,
                        backgroundColor: chatTicket.priority === 'P0_CRITICAL' ? '#fef2f2' : '#fffbeb',
                        border: chatTicket.priority === 'P0_CRITICAL' ? '1px solid #fecaca' : '1px solid #fde68a',
                        fontSize: '0.74rem',
                        color: chatTicket.priority === 'P0_CRITICAL' ? '#991b1b' : '#92400e',
                        fontWeight: 600,
                      }}
                    >
                      <span>Nguồn: Chatbot ({chatTicket.priority})</span> — <span>{chatTicket.trigger_reason}</span>
                    </div>
                  )}

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

      {/* MODAL BIÊN BẢN GIẢI QUYẾT VÉ CẢNH BÁO LÂM SÀNG */}
      {resolvingTicket && (
        <TicketResolveModal
          ticket={resolvingTicket}
          onClose={() => setResolvingTicket(null)}
          onResolve={handleResolveTicket}
        />
      )}
    </div>
  );
}
