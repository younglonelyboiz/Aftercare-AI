import React from 'react';
import { Pill, Wind, Clock, Check } from 'lucide-react';

export default function MedicationReminderBanner({ reminders = [], onAcknowledge, onSnooze, onMeasure }) {
  if (!reminders || reminders.length === 0) return null;

  return (
    <div className="medication-reminder-container">
      {reminders.map((rem) => {
        const isOverdue = rem.status === 'OVERDUE' || Boolean(rem.is_overdue);
        const isMed = rem.reminder_type === 'MEDICATION';

        return (
          <div 
            key={rem.id} 
            className={`reminder-alert-card ${isOverdue ? 'overdue' : 'pending'}`}
          >
            <div className="reminder-icon-box">
              {isMed ? (
                <Pill size={24} color={isOverdue ? '#9a3412' : '#1d4ed8'} />
              ) : (
                <Wind size={24} color={isOverdue ? '#9a3412' : '#1d4ed8'} />
              )}
            </div>
            
            <div className="reminder-body">
              <div className="reminder-header-row">
                <span className={`reminder-badge ${isOverdue ? 'overdue' : 'pending'}`}>
                  {isOverdue ? 'Đã quá hạn' : 'Đến giờ nhắc'}
                </span>
                <span className="reminder-time" style={{ display: 'inline-flex', alignItems: 'center', gap: 4, whiteSpace: 'nowrap' }}>
                  <Clock size={13} aria-hidden="true" />
                  <span>Giờ hẹn: {String(rem.scheduled_time || '').slice(0, 5)}</span>
                </span>
              </div>
              <h4 className="reminder-title">{rem.title}</h4>
              <p className="reminder-message">{rem.message_content}</p>
            </div>

            <div className="reminder-actions">
              <button 
                type="button"
                className="btn-ack" 
                onClick={() => !isMed && onMeasure ? onMeasure() : onAcknowledge(rem.id)}
                title="Xác nhận đã dùng thuốc hoặc đã đo"
              >
                <Check size={14} aria-hidden="true" />
                <span>{!isMed && onMeasure ? 'Nhập chỉ số' : 'Đã thực hiện'}</span>
              </button>
              <button 
                type="button"
                className="btn-snooze" 
                onClick={() => onSnooze(rem.id)}
                title="Nhắc lại sau 15 phút nữa"
              >
                <Clock size={14} aria-hidden="true" />
                <span>Nhắc sau 15p</span>
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
