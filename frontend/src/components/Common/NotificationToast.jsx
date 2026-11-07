import React, { useEffect, useState } from 'react';
import { CheckCircle2, AlertTriangle, Info, X } from 'lucide-react';

export default function NotificationToast({ toast, onClose }) {
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    if (!toast || !toast.show) {
      setIsExiting(false);
      return;
    }

    setIsExiting(false);
    const duration = toast.duration || 3000;

    // Trigger exit slide-out animation 280ms before component unmounts
    const exitTimer = setTimeout(() => {
      setIsExiting(true);
    }, Math.max(duration - 280, 200));

    // Finish close
    const closeTimer = setTimeout(() => {
      onClose();
    }, duration);

    return () => {
      clearTimeout(exitTimer);
      clearTimeout(closeTimer);
    };
  }, [toast, onClose]);

  if (!toast || !toast.show) return null;

  const isSuccess = toast.type === 'success';
  const isError = toast.type === 'error';
  const isWarning = toast.type === 'warning';
  const duration = toast.duration || 3000;

  const handleManualClose = () => {
    setIsExiting(true);
    setTimeout(() => {
      onClose();
    }, 280);
  };

  return (
    <div className="custom-toast-container">
      <div className={`custom-toast-card toast-${toast.type || 'info'} ${isExiting ? 'toast-exiting' : ''}`}>
        <div className="toast-icon-wrap">
          {isSuccess && <CheckCircle2 size={22} className="toast-icon-success" />}
          {isWarning && <AlertTriangle size={22} className="toast-icon-warning" />}
          {isError && <AlertTriangle size={22} className="toast-icon-error" />}
          {!isSuccess && !isWarning && !isError && <Info size={22} className="toast-icon-info" />}
        </div>

        <div className="toast-content-wrap">
          <div className="toast-title">{toast.title}</div>
          {toast.message && <div className="toast-message">{toast.message}</div>}

          {toast.stats && (
            <div className="toast-stats-grid">
              <div className="toast-stat-item">
                <span className="toast-stat-label">Nhắc 20m Vùng Vàng:</span>
                <span className={`toast-stat-val ${toast.stats.yellow_followup_triggered > 0 ? 'text-amber' : ''}`}>
                  {toast.stats.yellow_followup_triggered} ca
                </span>
              </div>
              <div className="toast-stat-item">
                <span className="toast-stat-label">Mất liên lạc 24h:</span>
                <span className={`toast-stat-val ${toast.stats.non_response_24h_triggered > 0 ? 'text-red' : ''}`}>
                  {toast.stats.non_response_24h_triggered} ca
                </span>
              </div>
              <div className="toast-stat-item">
                <span className="toast-stat-label">Quá hạn 12h:</span>
                <span className="toast-stat-val">
                  {toast.stats.non_response_12h_triggered} ca
                </span>
              </div>
            </div>
          )}
        </div>

        <button className="toast-close-btn" onClick={handleManualClose} title="Đóng thông báo">
          <X size={16} />
        </button>

        {/* Thanh đếm ngược thời gian hiển thị 3s */}
        <div
          className="toast-progress-bar"
          style={{ animationDuration: `${duration}ms` }}
        />
      </div>
    </div>
  );
}
