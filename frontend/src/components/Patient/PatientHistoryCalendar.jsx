import React, { useState } from 'react';
import { Calendar, Clock, Activity } from 'lucide-react';
import {
  formatCheckinDateTimeVN,
  getCheckinDateKeyVN,
  getRecentDaysVN,
  getSortedHistoryAsc,
} from '../../utils/patientDate';

function Sparkline({ values = [], color = '#2568d4', height = 28, width = 120 }) {
  if (!values || values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * width;
      const y = height - ((v - min) / range) * (height - 6) - 3;
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <svg width={width} height={height} className="overflow-visible inline-block">
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
      {values.map((v, i) => {
        const x = (i / (values.length - 1)) * width;
        const y = height - ((v - min) / range) * (height - 6) - 3;
        return <circle key={i} cx={x} cy={y} r="3" fill={color} />;
      })}
    </svg>
  );
}

function RiskBadge({ zone }) {
  const normalized = String(zone || '').toUpperCase();
  const config = {
    GREEN: { label: 'Ổn định', bg: 'bg-emerald-50', text: 'text-emerald-800', border: 'border-emerald-200', dot: 'bg-emerald-500' },
    YELLOW: { label: 'Cảnh báo', bg: 'bg-amber-50', text: 'text-amber-800', border: 'border-amber-200', dot: 'bg-amber-500' },
    RED: { label: 'Nguy cấp', bg: 'bg-rose-50', text: 'text-rose-800', border: 'border-rose-200', dot: 'bg-rose-500' },
  };

  const c = config[normalized] || { label: 'Chưa đo', bg: 'bg-slate-50', text: 'text-slate-600', border: 'border-slate-200', dot: 'bg-slate-400' };

  return (
    <span className={`text-xs font-bold ${c.text} ${c.bg} px-2.5 py-0.5 rounded-full border ${c.border} inline-flex items-center gap-1.5`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  );
}

export default function PatientHistoryCalendar({ history = [], hideTrendSummary = false }) {
  const [selectedDay, setSelectedDay] = useState(null);

  const sortedAsc = getSortedHistoryAsc(history);
  const sortedDesc = [...sortedAsc].reverse();

  // Map ngày (Asia/Ho_Chi_Minh) -> bản ghi mới nhất trong ngày
  const logMap = {};
  sortedAsc.forEach((item) => {
    const key = getCheckinDateKeyVN(item);
    if (key) {
      logMap[key] = item;
    }
  });

  // Tạo danh sách 14 ngày gần nhất theo Asia/Ho_Chi_Minh
  const days = getRecentDaysVN(14).map((day) => ({
    ...day,
    log: logMap[day.dateStr] || null,
  }));

  // Lấy các giá trị PEF theo đúng thứ tự thời gian (tăng dần) cho Sparkline
  const pefTrendValues = sortedAsc
    .filter((h) => h && h.pef_value)
    .map((h) => Number(h.pef_value))
    .slice(-7);

  return (
    <div className="space-y-5">
      {/* 1. Header Card with Sparkline (skipped when PatientHistoryView renders the full chart) */}
      {!hideTrendSummary && (
        <section aria-label="Tóm tắt xu hướng hô hấp" className="bg-white rounded-[14px] border border-[#e2e8f0] p-5 sm:p-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-[10px] bg-[#eff6ff] text-[#2568d4] border border-[#dbeafe] shrink-0">
                <Calendar className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base sm:text-lg font-semibold text-[#172b3a] tracking-tight">
                  Nhật Ký & Xu Hướng Kiểm Soát Hen (14 Ngày)
                </h2>
                <p className="text-[13px] text-[#475569] font-normal leading-relaxed">
                  Màu sắc phản ánh mức độ đáp ứng theo phác đồ GINA 2023
                </p>
              </div>
            </div>

            {/* Sparkline box */}
            {pefTrendValues.length >= 2 && (
              <div className="p-3 bg-[#f8fafc] rounded-[10px] border border-[#e2e8f0] flex items-center gap-3 shrink-0">
                <div>
                  <span className="text-xs font-medium text-[#475569] uppercase block">
                    Xu hướng PEF 7 ngày
                  </span>
                  <span className="text-xs sm:text-[13px] font-semibold text-[#172b3a]">
                    {pefTrendValues[pefTrendValues.length - 1]} L/phút gần nhất
                  </span>
                </div>
                <Sparkline values={pefTrendValues} />
              </div>
            )}
          </div>

          {/* Legend */}
          <div className="flex flex-wrap items-center gap-4 pt-4 mt-4 border-t border-[#e2e8f0] text-xs font-medium text-[#475569]">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Vùng Xanh (Ổn định)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> Vùng Vàng (Cảnh báo)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500" /> Vùng Đỏ (Cấp cứu)
            </span>
            <span className="flex items-center gap-1.5 text-[#475569]">
              <span className="w-2.5 h-2.5 rounded-full bg-slate-300" /> Chưa check-in
            </span>
          </div>
        </section>
      )}

      {/* 2. 14-Days Interactive Grid */}
      <section aria-label="Lưới 14 ngày gần nhất" className="bg-white rounded-[14px] border border-[#e2e8f0] p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <h3 className="text-xs font-semibold text-[#475569] uppercase tracking-wider m-0">
            Lưới Theo Dõi 14 Ngày
          </h3>
          {hideTrendSummary && (
            <div className="flex flex-wrap items-center gap-3 text-xs font-medium text-[#475569]">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Xanh
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> Vàng
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500" /> Đỏ
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-slate-300" /> Trống
              </span>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-7 gap-2.5">
          {days.map((item) => {
            const hasLog = !!item.log;
            const zone = (item.log?.action_zone || '').toUpperCase();
            const isSelected = selectedDay?.dateStr === item.dateStr;

            let dotColor = 'bg-slate-300';
            let borderZone = 'border-[#e2e8f0] hover:border-[#cbd5e1] bg-white';
            if (zone === 'GREEN') { dotColor = 'bg-emerald-500'; borderZone = 'border-emerald-200 bg-[#f0fdf4]/70'; }
            else if (zone === 'YELLOW') { dotColor = 'bg-amber-500'; borderZone = 'border-amber-200 bg-amber-50/50'; }
            else if (zone === 'RED') { dotColor = 'bg-rose-500'; borderZone = 'border-rose-200 bg-rose-50/50'; }

            return (
              <button
                key={item.dateStr}
                type="button"
                onClick={() => setSelectedDay(item)}
                className={`p-3 rounded-[10px] border text-center transition-colors cursor-pointer flex flex-col items-center justify-between min-h-[84px] ${borderZone} ${
                  isSelected ? 'ring-2 ring-[#2568d4]' : ''
                }`}
              >
                <div className="flex items-center justify-between w-full text-xs font-medium text-[#475569]">
                  <span>{item.weekday}</span>
                  <span className={`w-2 h-2 rounded-full ${dotColor}`} />
                </div>

                <div className="my-1">
                  <span className="text-xs font-semibold text-[#172b3a] block">{item.dayLabel}</span>
                  {hasLog && item.log.pef_value ? (
                    <span className="text-xs font-semibold text-[#2568d4]">{item.log.pef_value} L/p</span>
                  ) : (
                    <span className="text-xs text-[#64748b] font-normal">--</span>
                  )}
                </div>

                <span className="text-xs text-[#475569] font-normal">
                  {hasLog ? 'Đã đo' : 'Trống'}
                </span>
              </button>
            );
          })}
        </div>

        {/* Selected Day Detail Popover */}
        {selectedDay && (
          <div className="mt-4 p-4 rounded-[10px] bg-[#f8fafc] border border-[#e2e8f0] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="text-xs font-semibold text-[#475569] uppercase">
                Chi tiết ngày {selectedDay.dayLabel} ({selectedDay.weekday})
              </div>
              {selectedDay.log ? (
                <div className="mt-1 space-y-1 text-xs text-[#475569] font-normal">
                  <p>Lưu lượng đỉnh (PEF): <strong className="font-semibold text-[#172b3a]">{selectedDay.log.pef_value || 'Chưa đo'} L/phút</strong></p>
                  <p>SpO₂: <strong className="font-semibold text-[#172b3a]">{selectedDay.log.spo2_value ? `${selectedDay.log.spo2_value}%` : 'Không có máy đo'}</strong></p>
                  <p>Số nhát xịt cắt cơn: <strong className="font-semibold text-[#172b3a]">{selectedDay.log.reliever_puffs || 0} nhát</strong></p>
                </div>
              ) : (
                <p className="text-xs text-[#64748b] italic mt-1">Không có dữ liệu check-in trong ngày này.</p>
              )}
            </div>

            {selectedDay.log?.action_zone && (
              <RiskBadge zone={selectedDay.log.action_zone} />
            )}
          </div>
        )}
      </section>

      {/* 3. Detailed Check-in History List */}
      <section aria-label="Bảng danh sách check-in" className="bg-white rounded-[14px] border border-[#e2e8f0] p-5 sm:p-6 space-y-4">
        <h3 className="text-xs font-semibold text-[#475569] uppercase tracking-wider">
          Lịch Sử Đánh Giá Chi Tiết ({history.length} bản ghi)
        </h3>

        {history.length === 0 ? (
          <div className="text-center py-8 text-[#475569] space-y-2">
            <Clock className="w-8 h-8 mx-auto text-[#64748b]" />
            <p className="text-sm font-semibold text-[#172b3a]">Chưa có lịch sử check-in</p>
            <p className="text-xs sm:text-[13px] text-[#475569]">Hãy thực hiện check-in hôm nay để theo dõi diễn biến sức khỏe.</p>
          </div>
        ) : (
          <div className="divide-y divide-[#e2e8f0] border-t border-b border-[#e2e8f0]">
            {sortedDesc.map((item, idx) => (
              <div
                key={item.id || `${getCheckinDateKeyVN(item)}-${idx}`}
                className="py-3 px-2.5 sm:px-3 bg-white hover:bg-[#f8fafc] flex items-center justify-between gap-3 flex-wrap transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-[#eff6ff] border border-[#dbeafe] text-[#2568d4] shrink-0">
                    <Activity className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="text-xs sm:text-sm font-semibold text-[#172b3a] block">
                      {formatCheckinDateTimeVN(item)}
                    </span>
                    <span className="text-xs sm:text-[13px] text-[#475569] font-normal">
                      PEF: <strong className="font-semibold text-[#172b3a]">{item.pef_value || '--'} L/phút</strong>
                      {item.spo2_value ? ` • SpO₂: ${item.spo2_value}%` : ''}
                      {item.reliever_puffs ? ` • Cắt cơn: ${item.reliever_puffs} nhát` : ''}
                    </span>
                  </div>
                </div>

                <RiskBadge zone={item.action_zone} />
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
