import React from 'react';
import { ShieldCheck, AlertTriangle, AlertOctagon, Clock, PhoneCall, Bot, CheckCircle2 } from 'lucide-react';
import { ACTION_ZONE_ALERT_COPY } from './actionZoneCopy';

export default function PatientActionZoneCard({
  zone = 'green',
  screenerResult,
  countdownSeconds = 1200,
  safetyConfirmed = false,
  onConfirmSafety,
  onOpenChatWithAlert
}) {
  const formatTime = (secs) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const isGreen = zone === 'green';
  const isYellow = zone === 'yellow';
  const isRed = zone === 'red';

  return (
    <section aria-label="Khối vùng hành động và khuyến nghị an toàn" className="bg-white rounded-[14px] border border-[#e2e8f0] p-5 sm:p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#e2e8f0] pb-3">
        <div className="flex items-center gap-3">
          <div className={`p-2.5 rounded-[10px] border shrink-0 ${
            isRed
              ? 'bg-rose-50 text-rose-700 border-rose-200'
              : isYellow
              ? 'bg-amber-50 text-amber-700 border-amber-200'
              : 'bg-emerald-50 text-emerald-700 border-emerald-200'
          }`}>
            {isRed ? <AlertOctagon className="w-5 h-5" /> : isYellow ? <AlertTriangle className="w-5 h-5" /> : <ShieldCheck className="w-5 h-5" />}
          </div>
          <div>
            <h3 className="font-semibold text-[#172b3a] text-base sm:text-lg flex items-center gap-2 flex-wrap">
              3. Đánh Giá Phân Tầng An Toàn
              <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${
                isRed
                  ? 'bg-rose-100 text-rose-900 border-rose-300'
                  : isYellow
                  ? 'bg-amber-100 text-amber-900 border-amber-300'
                  : 'bg-emerald-100 text-emerald-900 border-emerald-300'
              }`}>
                {isRed ? 'VÙNG ĐỎ' : isYellow ? 'VÙNG VÀNG' : 'VÙNG XANH'}
              </span>
            </h3>
            <p className="text-[13px] sm:text-sm text-[#475569] font-normal leading-[1.55]">
              Phác đồ hành động theo dõi xử trí hen ngoại trú
            </p>
          </div>
        </div>
      </div>

      {/* GREEN ZONE */}
      {isGreen && (
        <div className="p-4 rounded-[10px] border border-emerald-200 bg-[#f0fdf4] text-emerald-950 space-y-2">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-700 shrink-0" />
            <h4 className="text-sm font-bold uppercase text-emerald-900 tracking-wide">
              Kiểm soát tốt — Tiếp tục duy trì
            </h4>
          </div>
          <p className="text-[13px] sm:text-sm text-emerald-900 font-normal leading-[1.6]">
            Các chỉ số PEF, SpO₂ và triệu chứng của bạn đều nằm trong vùng an toàn. Tiếp tục hít/xịt thuốc kiểm soát đúng giờ, giữ ấm cổ ngực và tránh khói bụi, dị nguyên.
          </p>
        </div>
      )}

      {/* YELLOW ZONE */}
      {isYellow && (
        <div className="space-y-3">
          <div className="p-4 rounded-[10px] border border-amber-400 bg-amber-50 text-amber-950 space-y-2">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-700 shrink-0" />
              <h4 className="text-sm font-bold uppercase text-amber-900 tracking-wide">
                {ACTION_ZONE_ALERT_COPY.yellow.heading}
              </h4>
            </div>
            <p className="text-xs sm:text-sm text-amber-900 leading-relaxed font-normal">
              {ACTION_ZONE_ALERT_COPY.yellow.subtitle} Hãy xịt ngay thuốc cắt cơn theo phác đồ, ngồi nghỉ ngơi nơi thoáng khí và theo dõi nhịp thở.
            </p>
          </div>

          {/* 20-Minute Safety Timer */}
          <div className="p-4 rounded-[10px] border border-amber-300 bg-amber-50/70 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs sm:text-sm font-semibold text-amber-950">
                <Clock className="w-4 h-4 text-amber-800 animate-pulse" />
                Bộ đếm giờ an toàn 20 phút: {formatTime(countdownSeconds)}
              </div>
              <p className="text-xs sm:text-[13px] text-amber-900 font-normal leading-relaxed">
                Dùng thuốc cắt cơn, nghỉ ngơi 20 phút. Nếu nhịp thở dịu, bấm xác nhận để không kích hoạt báo động tới điều dưỡng.
              </p>
            </div>

            <button
              type="button"
              onClick={onConfirmSafety}
              disabled={safetyConfirmed}
              className={`min-h-[40px] px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold transition-colors flex items-center justify-center gap-2 shrink-0 cursor-pointer ${
                safetyConfirmed
                  ? 'bg-emerald-700 text-white'
                  : 'bg-amber-800 hover:bg-amber-900 text-white'
              }`}
            >
              <CheckCircle2 className="w-4 h-4" />
              {safetyConfirmed ? '✓ Đã xác nhận an toàn' : 'Xác nhận an toàn sau 20p'}
            </button>
          </div>
        </div>
      )}

      {/* RED ZONE */}
      {isRed && (
        <div className="p-4 sm:p-5 rounded-[10px] border-2 border-rose-500 bg-rose-50 text-rose-950 space-y-4">
          <div className="flex items-center gap-2">
            <AlertOctagon className="w-6 h-6 text-rose-700 shrink-0" />
            <div>
              <h4 className="text-sm sm:text-base font-bold uppercase text-rose-950 tracking-wide">
                {ACTION_ZONE_ALERT_COPY.red.heading}
              </h4>
              <p className="text-xs text-rose-800 font-medium">
                {ACTION_ZONE_ALERT_COPY.red.subtitle}
              </p>
            </div>
          </div>

          <div className="text-xs sm:text-sm text-rose-900 space-y-1.5 font-normal bg-white p-3 rounded-lg border border-rose-200">
            <p>1. <strong>Dùng thuốc cắt cơn khẩn cấp:</strong> Xịt ngay 2–4 nhát thuốc cắt cơn qua buồng đệm.</p>
            <p>2. <strong>Tư thế:</strong> Ngồi thẳng lưng, hơi cúi người ra trước, tuyệt đối không nằm ngửa.</p>
            <p>3. <strong>Hỗ trợ y tế:</strong> Gọi ngay người nhà hoặc bấm nút cấp cứu bên dưới.</p>
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-1">
            <a
              href="tel:115"
              className="min-h-[42px] px-5 py-2 rounded-lg bg-rose-700 hover:bg-rose-800 text-white font-semibold text-sm flex items-center gap-2 transition-colors"
            >
              <PhoneCall className="w-4 h-4" />
              {ACTION_ZONE_ALERT_COPY.red.emergencyCta}
            </a>

            {onOpenChatWithAlert && (
              <button
                type="button"
                onClick={onOpenChatWithAlert}
                className="min-h-[42px] px-4 py-2 rounded-lg bg-white border border-rose-300 text-rose-900 hover:bg-rose-100/60 font-semibold text-xs sm:text-sm flex items-center gap-2 transition-colors cursor-pointer"
              >
                <Bot className="w-4 h-4 text-rose-700" />
                {ACTION_ZONE_ALERT_COPY.red.hopiCta}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Screener reasons / notes if available */}
      {screenerResult?.matched_reasons?.length > 0 && (
        <div className="text-xs sm:text-[13px] text-[#475569] font-normal pt-2 border-t border-[#e2e8f0] leading-relaxed">
          <strong className="font-semibold text-[#172b3a]">Căn cứ lâm sàng:</strong> {screenerResult.matched_reasons.join('; ')}
        </div>
      )}
    </section>
  );
}
