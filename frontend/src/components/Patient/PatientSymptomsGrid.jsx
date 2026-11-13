import React from 'react';
import { ClipboardList, Moon, Flame, Footprints, AlertTriangle, CheckCircle2, Pill } from 'lucide-react';

export default function PatientSymptomsGrid({
  symptoms = {},
  toggleSymptom,
  medsTaken = false,
  setMedsTaken
}) {
  const symptomItems = [
    {
      key: 'nightWaking',
      icon: Moon,
      label: 'Tỉnh giấc ban đêm',
      desc: 'Thức giấc nửa đêm hoặc gần sáng vì ho, khó thở, thở khò khè',
      isDanger: false
    },
    {
      key: 'relieverUsed',
      icon: Flame,
      label: 'Cần xịt cắt cơn',
      desc: 'Phải xịt thuốc cắt cơn (Ventolin/Bricanyl) từ 2 lần trở lên trong ngày',
      isDanger: false
    },
    {
      key: 'activityLimited',
      icon: Footprints,
      label: 'Hạn chế sinh hoạt',
      desc: 'Cảm thấy hụt hơi, mệt mỏi khi đi lại nhẹ nhàng hoặc làm việc nhà',
      isDanger: false
    },
    {
      key: 'dangerSign',
      icon: AlertTriangle,
      label: 'Dấu hiệu nguy cấp',
      desc: 'Khó thở dữ dội, không nói trọn câu, co kéo cơ ngực hoặc cánh mũi phập phồng',
      isDanger: true
    }
  ];

  return (
    <section aria-label="Khối triệu chứng và tuân thủ thuốc" className="bg-white rounded-[14px] border border-[#e2e8f0] p-5 sm:p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-[#e2e8f0] pb-3">
        <div className="p-2.5 rounded-[10px] bg-[#eff6ff] text-[#2568d4] border border-[#dbeafe] shrink-0">
          <ClipboardList className="w-5 h-5" />
        </div>
        <div>
          <h3 className="font-semibold text-[#172b3a] text-base sm:text-lg flex items-center gap-2 flex-wrap">
            2. Triệu Chứng Trong 24 Giờ Qua
            <span className="text-xs font-medium text-[#475569] bg-[#f8fafc] px-2.5 py-0.5 rounded-md border border-[#e2e8f0]">
              Tiêu chuẩn GINA 2023
            </span>
          </h3>
          <p className="text-[13px] sm:text-sm text-[#475569] font-normal leading-[1.55]">
            Chọn tất cả các biểu hiện bạn đã gặp để trợ lý tính toán vùng an toàn
          </p>
        </div>
      </div>

      {/* Symptoms Interactive Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {symptomItems.map(({ key, icon: Icon, label, desc, isDanger }) => {
          const isChecked = !!symptoms[key];
          let cardStyle = 'border border-[#e2e8f0] bg-[#f8fafc] hover:bg-[#eff6ff]/60 text-[#172b3a]';

          if (isChecked) {
            cardStyle = isDanger
              ? 'border-2 border-rose-600 bg-rose-50 text-rose-950'
              : 'border-2 border-[#2568d4] bg-[#eff6ff] text-[#172b3a]';
          } else if (isDanger) {
            cardStyle = 'border border-rose-200 bg-rose-50/30 hover:bg-rose-50/60 text-[#172b3a]';
          }

          return (
            <button
              key={key}
              type="button"
              onClick={() => toggleSymptom(key)}
              aria-pressed={isChecked}
              className={`text-left p-3.5 rounded-[10px] transition-colors cursor-pointer flex items-start gap-3 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#2568d4] ${cardStyle}`}
            >
              <div className={`p-2 rounded-lg shrink-0 mt-0.5 ${isChecked ? (isDanger ? 'bg-rose-200 text-rose-800' : 'bg-[#dbeafe] text-[#1d4ed8]') : 'bg-white text-[#64748b] border border-[#e2e8f0]'}`}>
                <Icon className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold tracking-tight">
                    {label}
                  </span>
                  {isChecked && (
                    <span className={`text-xs font-semibold flex items-center gap-1 shrink-0 ${isDanger ? 'text-rose-800' : 'text-[#1d4ed8]'}`}>
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Đã chọn
                    </span>
                  )}
                </div>
                <p className="text-[13px] sm:text-sm text-[#475569] font-normal leading-[1.55] mt-1">
                  {desc}
                </p>
              </div>
            </button>
          );
        })}
      </div>

      {/* Medication Adherence Section */}
      <div className="pt-3 border-t border-[#e2e8f0]">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#f8fafc] rounded-[10px] border border-[#e2e8f0] p-3.5">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-white border border-[#e2e8f0] text-[#2568d4] shrink-0">
              <Pill className="w-4 h-4" />
            </div>
            <div>
              <p className="text-sm font-semibold text-[#172b3a]">
                Tuân thủ thuốc kiểm soát duy trì
              </p>
              <p className="text-xs sm:text-[13px] text-[#475569] font-normal leading-relaxed mt-0.5">
                Bạn đã xịt đúng và đủ liều thuốc duy trì sáng nay chưa?
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => setMedsTaken(!medsTaken)}
            aria-pressed={medsTaken}
            className={`min-h-[40px] px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold transition-colors flex items-center justify-center gap-2 shrink-0 cursor-pointer ${
              medsTaken
                ? 'bg-emerald-700 text-white hover:bg-emerald-800'
                : 'bg-white text-[#172b3a] border border-[#cbd5e1] hover:bg-[#f8fafc]'
            }`}
          >
            <CheckCircle2 className="w-4 h-4" />
            {medsTaken ? 'Đã dùng thuốc sáng nay' : 'Chưa dùng thuốc'}
          </button>
        </div>
      </div>
    </section>
  );
}
