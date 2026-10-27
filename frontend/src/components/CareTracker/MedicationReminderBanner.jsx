import React, { useState } from 'react';

export default function MedicationReminderBanner({ reminders = [], onAcknowledge, onSnooze }) {
  if (!reminders || reminders.length === 0) return null;

  return (
    <div className="medication-reminder-container">
      {reminders.map((rem) => {
        const isOverdue = rem.status === 'OVERDUE';
        const isMed = rem.reminder_type === 'MEDICATION';

        return (
          <div 
            key={rem.id} 
            className={`reminder-alert-card ${isOverdue ? 'overdue' : 'pending'}`}
          >
            <div className="reminder-icon-box">
              {isMed ? '💊' : '🫁'}
            </div>
            
            <div className="reminder-body">
              <div className="reminder-header-row">
                <span className="reminder-badge">
                  {isOverdue ? '⚠️ ĐÃ QUÁ HẠN' : '⏰ ĐẾN GIỜ NHẮC'}
                </span>
                <span className="reminder-time">
                  Giờ hẹn: {rem.scheduled_time.slice(0, 5)}
                </span>
              </div>
              <h4 className="reminder-title">{rem.title}</h4>
              <p className="reminder-message">{rem.message_content}</p>
            </div>

            <div className="reminder-actions">
              <button 
                className="btn-ack" 
                onClick={() => onAcknowledge(rem.id)}
                title="Xác nhận đã dùng thuốc hoặc đã đo"
              >
                ✓ Đã thực hiện
              </button>
              <button 
                className="btn-snooze" 
                onClick={() => onSnooze(rem.id)}
                title="Nhắc lại sau 15 phút nữa"
              >
                ⏱️ Nhắc sau 15p
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
