import React, { useState, useEffect } from 'react';
import { 
  AlertOctagon, 
  AlertTriangle, 
  Bell, 
  Volume2, 
  VolumeX, 
  Clock, 
  PhoneCall, 
  CheckCircle,
  FileEdit
} from 'lucide-react';

export default function LiveAlertBanner({
  tickets = [],
  onAcknowledge,
  onOpenResolve,
  isMuted,
  onToggleMute
}) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // Lọc vé ưu tiên cao nhất
  const p0Ticket = tickets.find(t => t.priority === 'P0_CRITICAL' && t.status === 'OPEN');
  const p1Ticket = !p0Ticket ? tickets.find(t => t.priority === 'P1_HIGH' && t.status === 'OPEN') : null;
  const currentTicket = p0Ticket || p1Ticket || tickets.find(t => t.status === 'OPEN');

  useEffect(() => {
    if (!currentTicket) {
      setElapsedSeconds(0);
      return;
    }

    const createdTime = new Date(currentTicket.created_at).getTime();
    const updateElapsed = () => {
      const now = Date.now();
      setElapsedSeconds(Math.max(0, Math.floor((now - createdTime) / 1000)));
    };

    updateElapsed();
    const interval = setInterval(updateElapsed, 1000);
    return () => clearInterval(interval);
  }, [currentTicket]);

  if (!currentTicket) return null;

  const isP0 = currentTicket.priority === 'P0_CRITICAL';
  const isChatbotSource =
    currentTicket.source_channel === 'CHATBOT' ||
    currentTicket.clinical_data?.source === 'CHAT' ||
    [
      'CHAT_RED_FLAG_DETECTION',
      'CHAT_YELLOW_ZONE_ALERT',
      'MEDICATION_NONADHERENCE_INTENT',
      'MENTAL_HEALTH_CONCERN',
      'SYSTEM_DEGRADED_PATIENT_UNSERVED',
    ].includes(currentTicket.alert_type);

  const formatTime = (secs) => {
    const mins = Math.floor(secs / 60);
    const s = secs % 60;
    return `${mins > 0 ? `${mins}m ` : ''}${s}s`;
  };

  return (
    <div className={`live-escalation-banner ${isP0 ? 'banner-p0-critical' : 'banner-p1-high'}`}>
      <div className="banner-left-content">
        <div className="alert-icon-pulse">
          {isP0 ? <AlertOctagon size={26} className="shake-animation" /> : <AlertTriangle size={24} />}
        </div>
        <div>
          <div className="banner-headline">
            <strong>{isP0 ? '🚨 BÁO ĐỘNG ĐỎ CẤP CỨU P0:' : '⚠️ CẢNH BÁO LEO THANG P1:'}</strong>{' '}
            <span>{currentTicket.patient_name || currentTicket.patient_id}</span>
            {isChatbotSource && (
              <span
                className="source-chatbot-badge"
                style={{
                  marginLeft: 8,
                  padding: '2px 8px',
                  borderRadius: 999,
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  backgroundColor: '#ffffff',
                  color: isP0 ? '#b91c1c' : '#92400e',
                }}
              >
                Nguồn: Chatbot
              </span>
            )}
            <span className="latency-tag">
              Độ trễ: {currentTicket.escalation_latency_ms || '<50'}ms
            </span>
          </div>
          <div className="banner-subtext">
            <span>{currentTicket.trigger_reason}</span>
            <span className="elapsed-counter">
              <Clock size={13} style={{ verticalAlign: 'middle', marginRight: 4 }} />
              Đã trôi qua: <strong>{formatTime(elapsedSeconds)}</strong>
            </span>
          </div>
        </div>
      </div>

      <div className="banner-actions">
        <button
          className="btn-banner-mute"
          onClick={onToggleMute}
          title={isMuted ? 'Bật chuông' : 'Tắt chuông tạm thời'}
        >
          {isMuted ? <VolumeX size={16} /> : <Volume2 size={16} />}
          <span>{isMuted ? 'Đã tắt tiếng' : 'Tắt tiếng'}</span>
        </button>

        <button
          className="btn-banner-ack"
          onClick={() => onAcknowledge(currentTicket.id)}
          title="Tiếp nhận ca & ngắt chuông báo động"
        >
          <Bell size={15} style={{ marginRight: 6, verticalAlign: 'middle' }} />
          Tiếp Nhận Ca
        </button>

        <button
          className="btn-banner-resolve"
          onClick={() => onOpenResolve(currentTicket)}
          title="Xử lý & Nhập biên bản can thiệp"
        >
          <FileEdit size={15} style={{ marginRight: 6, verticalAlign: 'middle' }} />
          Xử Lý & Ký Biên Bản
        </button>
      </div>
    </div>
  );
}

