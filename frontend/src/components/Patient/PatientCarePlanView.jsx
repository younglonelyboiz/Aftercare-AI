import React, { useState } from 'react';
import { ClipboardList, Pill, Wind, Stethoscope, ArrowRight } from 'lucide-react';

export default function PatientCarePlanView({ carePlan, onCheckinToday, compactHeader = false }) {
  const [completedItems, setCompletedItems] = useState({});

  if (!carePlan || !carePlan.items) {
    if (compactHeader) {
      return (
        <div className="pw-empty-inline flex flex-col items-center gap-1.5">
          <ClipboardList className="w-7 h-7 text-[#64748b]" aria-hidden="true" />
          <p className="text-sm font-semibold text-[#172b3a] m-0">Chưa có kế hoạch chăm sóc được thiết lập</p>
          <p className="text-xs text-[#475569] m-0">Điều dưỡng phụ trách sẽ cập nhật phác đồ cho bạn sớm.</p>
        </div>
      );
    }
    return (
      <div className="bg-white rounded-[14px] border border-dashed border-[#cbd5e1] p-6 text-center text-[#475569] space-y-2">
        <ClipboardList className="w-8 h-8 mx-auto text-[#64748b]" aria-hidden="true" />
        <p className="text-sm font-semibold text-[#172b3a]">Chưa có kế hoạch chăm sóc được thiết lập</p>
        <p className="text-xs sm:text-[13px] text-[#475569]">Điều dưỡng phụ trách sẽ cập nhật phác đồ cho bạn sớm.</p>
      </div>
    );
  }

  const toggleItem = (itemId) => {
    setCompletedItems(prev => ({
      ...prev,
      [itemId]: !prev[itemId]
    }));
  };

  const controllers = carePlan.items.filter(i => i.item_type === 'CONTROLLER_MED');
  const measures = carePlan.items.filter(i => i.item_type === 'PEF_MEASURE');
  const comorbidities = carePlan.items.filter(i => i.item_type === 'COMORBIDITY_MED');

  const containerClassName = compactHeader
    ? 'space-y-4'
    : 'bg-white rounded-[14px] border border-[#e2e8f0] p-4 sm:p-6 space-y-4';

  return (
    <section aria-label="Kế hoạch chăm sóc và thuốc" className={containerClassName}>
      {/* Header */}
      {!compactHeader && (
        <div className="flex items-center justify-between border-b border-[#e2e8f0] pb-3 gap-2 flex-wrap">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-[10px] bg-[#eff6ff] text-[#2568d4] border border-[#dbeafe] shrink-0">
              <ClipboardList className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-semibold text-[#172b3a] text-sm sm:text-base">
                Nhiệm Vụ Điều Trị Hôm Nay
              </h3>
              <p className="text-xs sm:text-[13px] text-[#475569] font-normal leading-relaxed">
                Checklist ghi nhớ tạm trên trình duyệt theo phác đồ xuất viện
              </p>
            </div>
          </div>

          <span className="text-xs font-semibold text-[#1d4ed8] bg-[#eff6ff] px-2.5 py-1 rounded-md border border-[#dbeafe] shrink-0">
            PEF Mục tiêu: <strong>{carePlan.personal_best_pef || 500} L/phút</strong>
          </span>
        </div>
      )}

      {/* 1. Thuốc kiểm soát duy trì */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-[13px] font-semibold text-[#172b3a]">
          <Pill className="w-4 h-4 text-[#2568d4]" aria-hidden="true" />
          <span>Thuốc kiểm soát duy trì (Hằng ngày)</span>
        </div>

        {controllers.length === 0 ? (
          <p className="text-xs sm:text-[13px] text-[#475569] italic bg-[#f8fafc] p-3 rounded-[10px] border border-[#e2e8f0]">
            Không có thuốc duy trì hằng ngày (Bậc 1 theo GINA).
          </p>
        ) : (
          <div className="divide-y divide-[#e2e8f0] border-t border-b border-[#e2e8f0]">
            {controllers.map(item => {
              const isDone = !!completedItems[item.id];
              const checkboxId = `careplan-item-${item.id}`;
              return (
                <label
                  key={item.id}
                  htmlFor={checkboxId}
                  className={`py-3 px-2.5 sm:px-3 transition-colors cursor-pointer flex items-start gap-3 ${
                    isDone
                      ? 'bg-[#f0fdf4] text-[#475569]'
                      : 'bg-white hover:bg-[#f8fafc] text-[#172b3a]'
                  }`}
                >
                  <input
                    id={checkboxId}
                    type="checkbox"
                    checked={isDone}
                    onChange={() => toggleItem(item.id)}
                    className="w-5 h-5 mt-0.5 shrink-0 rounded border-[#94a3b8] accent-[#2568d4] cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#2568d4]"
                  />

                  <div className="flex-1 min-w-0">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1.5 min-w-0">
                      <strong className={`text-sm font-semibold leading-snug min-w-0 break-words ${isDone ? 'line-through text-[#64748b]' : 'text-[#172b3a]'}`}>
                        {item.title}
                      </strong>
                      {item.dosage && (
                        <span className="self-start max-w-full break-words text-xs font-medium text-[#475569] bg-[#f8fafc] px-2 py-0.5 rounded-md border border-[#e2e8f0]">
                          {item.dosage}
                        </span>
                      )}
                    </div>

                    {item.instructions && (
                      <p className="text-[13px] sm:text-sm text-[#475569] font-normal leading-[1.55] mt-1 break-words">
                        {item.instructions}
                      </p>
                    )}

                    {item.schedule_times?.length > 0 && (
                      <div className="text-xs sm:text-[13px] text-[#475569] font-medium mt-1">
                        Giờ xịt: {item.schedule_times.join(', ')}
                      </div>
                    )}
                  </div>
                </label>
              );
            })}
          </div>
        )}
      </div>

      {/* 2. Đo PEF & Nhiệm vụ khác */}
      {measures.length > 0 && (
        <div className="space-y-2 pt-1">
          <div className="flex items-center gap-2 text-[13px] font-semibold text-[#172b3a]">
            <Wind className="w-4 h-4 text-[#2568d4]" aria-hidden="true" />
            <span>Đo lưu lượng đỉnh (PEF)</span>
          </div>

          <div className="divide-y divide-[#e2e8f0] border-t border-b border-[#e2e8f0]">
            {measures.map(item => {
              const isDone = !!completedItems[item.id];
              const checkboxId = `careplan-measure-${item.id}`;
              return (
                <div
                  key={item.id}
                  className={`py-3 px-2.5 sm:px-3 transition-colors flex flex-wrap items-start justify-between gap-3 ${
                    isDone
                      ? 'bg-[#f0fdf4]'
                      : 'bg-white hover:bg-[#f8fafc]'
                  }`}
                >
                  <label
                    htmlFor={checkboxId}
                    className="flex items-start gap-3 flex-1 min-w-0 cursor-pointer"
                  >
                    <input
                      id={checkboxId}
                      type="checkbox"
                      checked={isDone}
                      onChange={() => toggleItem(item.id)}
                      className="w-5 h-5 mt-0.5 shrink-0 rounded border-[#94a3b8] accent-[#2568d4] cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#2568d4]"
                    />
                    <div className="flex-1 min-w-0">
                      <strong className={`text-sm font-semibold leading-snug block break-words ${isDone ? 'line-through text-[#64748b]' : 'text-[#172b3a]'}`}>
                        {item.title}
                      </strong>
                      {item.instructions && (
                        <p className="text-[13px] sm:text-sm text-[#475569] font-normal leading-[1.55] mt-1 break-words">
                          {item.instructions}
                        </p>
                      )}
                    </div>
                  </label>

                  {onCheckinToday && (
                    <button
                      type="button"
                      onClick={onCheckinToday}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-[#1d4ed8] bg-[#eff6ff] hover:bg-[#dbeafe] border border-[#bfdbfe] rounded-lg px-3 py-1.5 cursor-pointer shrink-0 self-start focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#2568d4]"
                    >
                      <span>Đo ngay</span>
                      <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 3. Bệnh đồng mắc nếu có */}
      {comorbidities.length > 0 && (
        <div className="space-y-2 pt-1">
          <div className="flex items-center gap-2 text-[13px] font-semibold text-[#172b3a]">
            <Stethoscope className="w-4 h-4 text-[#2568d4]" aria-hidden="true" />
            <span>Thuốc bệnh đồng mắc</span>
          </div>
          <div className="divide-y divide-[#e2e8f0] border-t border-b border-[#e2e8f0]">
            {comorbidities.map(item => (
              <div key={item.id} className="py-3 px-2.5 sm:px-3 bg-white text-xs sm:text-sm min-w-0 break-words">
                <strong className="font-semibold text-[#172b3a] break-words">{item.title}</strong> — <span className="font-medium text-[#475569] break-words">{item.dosage}</span>
                {item.instructions && (
                  <p className="text-[13px] text-[#475569] font-normal leading-[1.55] mt-1 break-words">{item.instructions}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
