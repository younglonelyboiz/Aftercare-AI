import React from 'react';
import { Wind, HeartPulse, Activity } from 'lucide-react';

export default function PatientVitalsCard({
  pef,
  setPef,
  personalBestPef = 500,
  pefRatio = 100,
  currentZone = 'green',
  spo2,
  setSpo2,
  noSpo2Device = false,
  setNoSpo2Device
}) {
  const zoneBadgeClasses = {
    green: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    yellow: 'bg-amber-50 text-amber-800 border-amber-200',
    red: 'bg-rose-50 text-rose-800 border-rose-200'
  };

  const getSpo2Status = (val) => {
    if (noSpo2Device) return { text: 'Chưa có thiết bị đo', color: 'text-slate-500' };
    if (val >= 95) return { text: 'Ổn định (≥ 95%)', color: 'text-emerald-700' };
    if (val >= 92) return { text: 'Cảnh báo giảm nhẹ (92–94%)', color: 'text-amber-700 font-bold' };
    return { text: 'Nguy hiểm (< 92% thiếu oxy)', color: 'text-rose-700 font-black' };
  };

  const spo2Status = getSpo2Status(spo2);

  return (
    <section aria-label="Khối sinh hiệu hô hấp" className="bg-white rounded-[14px] border border-[#e2e8f0] p-5 sm:p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-[#e2e8f0] pb-3">
        <div className="p-2.5 rounded-[10px] bg-[#eff6ff] text-[#2568d4] border border-[#dbeafe] shrink-0">
          <Wind className="w-5 h-5" />
        </div>
        <div>
          <h3 className="font-semibold text-[#172b3a] text-base sm:text-lg flex items-center gap-2 flex-wrap">
            1. Sinh Hiệu Hô Hấp Buổi Sáng
            <span className="text-xs font-medium text-[#475569] bg-[#f8fafc] px-2.5 py-0.5 rounded-md border border-[#e2e8f0]">
              Chỉ số PEF & SpO₂
            </span>
          </h3>
          <p className="text-[13px] sm:text-sm text-[#475569] font-normal leading-[1.55]">
            Đo lưu lượng đỉnh 3 lần lấy số cao nhất trước khi dùng thuốc xịt
          </p>
        </div>
      </div>

      {/* PEF Input & Slider */}
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <label htmlFor="pef-number-input" className="text-sm font-semibold text-[#172b3a] flex items-center gap-1.5">
            <Activity className="w-4 h-4 text-[#2568d4]" />
            Lưu lượng đỉnh (PEF):
          </label>
          <div className="flex items-center gap-2">
            <input
              id="pef-number-input"
              type="number"
              min="100"
              max="800"
              value={pef}
              onChange={(e) => setPef(Number(e.target.value))}
              className="w-24 text-center font-semibold text-lg text-[#172b3a] bg-[#f8fafc] border border-[#cbd5e1] rounded-lg py-1.5 px-2 focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#2568d4] focus:border-[#2568d4]"
              aria-label="Chỉ số PEF đo được"
            />
            <span className="text-xs sm:text-[13px] font-medium text-[#475569]">L/phút</span>
            <span className={`text-xs font-semibold px-2.5 py-1 rounded-md border ${zoneBadgeClasses[currentZone] || zoneBadgeClasses.green}`}>
              {pefRatio}% chuẩn
            </span>
          </div>
        </div>

        {/* Range Slider */}
        <input
          id="pef-input-slider"
          type="range"
          min="100"
          max={Math.max(800, Math.round(personalBestPef * 1.2))}
          value={pef}
          onChange={(e) => setPef(Number(e.target.value))}
          className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-[#2568d4]"
          aria-label="Thanh trượt lưu lượng đỉnh PEF"
        />

        <div className="flex justify-between items-center text-xs font-medium text-[#475569]">
          <span>100 L/phút</span>
          <span className="text-[#475569] font-medium bg-[#f8fafc] px-2.5 py-0.5 rounded-md border border-[#e2e8f0]">
            Chuẩn cá nhân: {personalBestPef} L/phút
          </span>
          <span>800 L/phút</span>
        </div>
      </div>

      {/* SpO2 Section */}
      <div className="pt-3 border-t border-[#e2e8f0] space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <label htmlFor="spo2-number-input" className="text-sm font-semibold text-[#172b3a] flex items-center gap-1.5">
            <HeartPulse className="w-4 h-4 text-rose-600" />
            Nồng độ oxy trong máu (SpO₂):
          </label>
          <div className="flex items-center gap-2">
            <input
              id="spo2-number-input"
              type="number"
              min="70"
              max="100"
              disabled={noSpo2Device}
              value={noSpo2Device ? '' : spo2}
              placeholder={noSpo2Device ? '--' : '98'}
              onChange={(e) => setSpo2(Number(e.target.value))}
              className="w-20 text-center font-semibold text-base text-[#172b3a] bg-[#f8fafc] border border-[#cbd5e1] rounded-lg py-1.5 px-2 focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#2568d4] focus:border-[#2568d4] disabled:opacity-50"
              aria-label="Nồng độ SpO2"
            />
            <span className="text-xs sm:text-[13px] font-medium text-[#475569]">%</span>
            <span className={`text-xs ${spo2Status.color}`}>
              {spo2Status.text}
            </span>
          </div>
        </div>

        {setNoSpo2Device && (
          <label className="inline-flex items-center gap-2 cursor-pointer text-xs sm:text-[13px] text-[#475569] hover:text-[#172b3a]">
            <input
              type="checkbox"
              checked={noSpo2Device}
              onChange={(e) => setNoSpo2Device(e.target.checked)}
              className="w-4 h-4 accent-[#2568d4] rounded border-[#cbd5e1] focus:ring-[#2568d4]"
            />
            <span>Tôi chưa có máy đo SpO₂ tại nhà hôm nay</span>
          </label>
        )}
      </div>
    </section>
  );
}
