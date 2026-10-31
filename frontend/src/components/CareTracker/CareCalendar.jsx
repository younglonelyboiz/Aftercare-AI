import React, { useState } from 'react';
import { Calendar } from 'lucide-react';

export default function CareCalendar({ history = [], onSelectDate }) {
  const [selectedDay, setSelectedDay] = useState(null);

  // Tạo map ngày -> log
  const logMap = {};
  history.forEach(item => {
    logMap[item.date] = item;
  });

  // Tạo danh sách 14 ngày gần nhất (sử dụng local date để tránh lệch múi giờ)
  const days = [];
  for (let i = 13; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const dateStr = `${year}-${month}-${day}`;
    const dayLabel = `${d.getDate()}/${d.getMonth() + 1}`;
    const weekday = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'][d.getDay()];
    days.push({
      dateStr,
      dayLabel,
      weekday,
      log: logMap[dateStr] || null
    });
  }

  const handleDayClick = (dayItem) => {
    setSelectedDay(dayItem);
    if (onSelectDate) onSelectDate(dayItem);
  };

  return (
    <div className="care-calendar-card">
      <div className="calendar-header">
        <div>
          <h3 className="section-title">
            <Calendar size={18} color="var(--primary)" style={{ marginRight: 6, verticalAlign: 'middle' }} />
            Nhật Ký & Lịch Theo Dõi Hen (14 Ngày)
          </h3>
          <p className="section-desc">Màu sắc thể hiện mức độ kiểm soát cơn hen theo chuẩn GINA</p>
        </div>
        <div className="calendar-legend">
          <span className="legend-item"><span className="dot dot-green"></span> Kiểm soát tốt</span>
          <span className="legend-item"><span className="dot dot-yellow"></span> Cảnh báo</span>
          <span className="legend-item"><span className="dot dot-red"></span> Cơn cấp</span>
          <span className="legend-item"><span className="dot dot-empty"></span> Chưa check-in</span>
        </div>
      </div>

      <div className="calendar-grid">
        {days.map((item, idx) => {
          const zone = item.log?.action_zone?.toLowerCase() || 'empty';
          const isSelected = selectedDay?.dateStr === item.dateStr;

          return (
            <div 
              key={idx}
              className={`calendar-day-cell zone-${zone} ${isSelected ? 'selected' : ''}`}
              onClick={() => handleDayClick(item)}
            >
              <div className="day-weekday">{item.weekday}</div>
              <div className="day-number">{item.dayLabel}</div>
              <div className="day-status-indicator">
                <span className={`status-circle status-${zone}`}></span>
              </div>
              {item.log && (
                <div className="day-pef-tag">
                  {item.log.pef_value} L/m
                </div>
              )}
            </div>
          );
        })}
      </div>

      {selectedDay && (
        <div className="day-detail-panel">
          <div className="detail-header">
            <h4>Chi tiết ngày {selectedDay.dayLabel} ({selectedDay.weekday})</h4>
            <button className="btn-close-detail" onClick={() => setSelectedDay(null)}>✕</button>
          </div>
          {selectedDay.log ? (
            <div className="detail-body">
              <div className="detail-stat-row">
                <div className="stat-box">
                  <span className="stat-label">Chỉ số PEF</span>
                  <strong className="stat-val">{selectedDay.log.pef_value} L/phút ({selectedDay.log.pef_percent}%)</strong>
                </div>
                <div className="stat-box">
                  <span className="stat-label">Oxy SpO2</span>
                  <strong className="stat-val">{selectedDay.log.spo2_value || 98}%</strong>
                </div>
                <div className="stat-box">
                  <span className="stat-label">Vùng kiểm soát</span>
                  <strong className={`stat-val zone-text-${selectedDay.log.action_zone.toLowerCase()}`}>
                    {selectedDay.log.action_zone === 'GREEN' && 'VÙNG XANH (An toàn)'}
                    {selectedDay.log.action_zone === 'YELLOW' && 'VÙNG VÀNG (Cảnh báo)'}
                    {selectedDay.log.action_zone === 'RED' && 'VÙNG ĐỎ (Nguy kịch)'}
                  </strong>
                </div>
              </div>
              {selectedDay.log.notes && (
                <p className="detail-note">📝 <strong>Ghi chú bệnh nhân:</strong> {selectedDay.log.notes}</p>
              )}
              {selectedDay.log.reliever_puffs > 0 && (
                <p className="detail-reliever">💨 <strong>Số nhát cắt cơn đã dùng:</strong> {selectedDay.log.reliever_puffs} nhát Ventolin</p>
              )}
            </div>
          ) : (
            <p className="empty-day-text">Chưa có nhật ký check-in nào được ghi nhận cho ngày này.</p>
          )}
        </div>
      )}
    </div>
  );
}
