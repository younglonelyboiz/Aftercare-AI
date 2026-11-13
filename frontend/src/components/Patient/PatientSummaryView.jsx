import React from 'react';
import { FileText, Wind, HeartPulse, Pill } from 'lucide-react';

export default function PatientSummaryView({ profile }) {
  if (!profile) {
    return (
      <div className="bg-white rounded-[14px] border border-dashed border-[#cbd5e1] p-8 text-center text-[#475569] space-y-2">
        <FileText className="w-8 h-8 mx-auto text-[#64748b]" />
        <p className="text-sm font-semibold text-[#172b3a]">Chưa có thông tin hồ sơ bệnh án</p>
        <p className="text-xs sm:text-[13px] text-[#475569]">Dữ liệu hồ sơ sẽ tự động đồng bộ từ hệ thống bệnh viện.</p>
      </div>
    );
  }

  const { patient_info = {}, clinical_status = {}, current_medications = {}, follow_up = {}, action_plan_rules = {} } = profile;

  return (
    <div className="space-y-5">
      {/* 1. Header Card */}
      <section aria-label="Tóm tắt thông tin bệnh nhân" className="bg-white rounded-[14px] border border-[#e2e8f0] p-5 sm:p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#e2e8f0] pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-[10px] bg-[#eff6ff] text-[#2568d4] border border-[#dbeafe] shrink-0">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base sm:text-lg font-semibold text-[#172b3a] tracking-tight flex items-center gap-2 flex-wrap">
                Hồ Sơ Xuất Viện & Kế Hoạch Cá Nhân
                <span className="text-xs font-medium text-[#1d4ed8] bg-[#eff6ff] px-2.5 py-0.5 rounded-md border border-[#dbeafe]">
                  {patient_info.patient_id || 'BN-ASTHMA'}
                </span>
              </h2>
              <p className="text-[13px] text-[#475569] font-normal leading-relaxed">
                Hồ sơ y bạ điện tử theo dõi điều trị ngoại trú
              </p>
            </div>
          </div>

          <div className="text-xs font-medium text-[#475569] bg-[#f8fafc] border border-[#e2e8f0] px-3 py-1.5 rounded-lg shrink-0 self-start sm:self-auto">
            Xuất viện: <strong className="font-semibold text-[#172b3a]">{patient_info.discharge_date || 'Chưa cập nhật'}</strong>
          </div>
        </div>

        {/* Patient Details */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="p-3 bg-[#f8fafc] rounded-[10px] border border-[#e2e8f0]">
            <span className="text-xs font-medium text-[#475569] block">Họ và tên</span>
            <span className="text-sm font-semibold text-[#172b3a] mt-0.5 block">{patient_info.full_name || 'Bệnh nhân'}</span>
          </div>
          <div className="p-3 bg-[#f8fafc] rounded-[10px] border border-[#e2e8f0]">
            <span className="text-xs font-medium text-[#475569] block">Tuổi & Giới tính</span>
            <span className="text-sm font-semibold text-[#172b3a] mt-0.5 block">{patient_info.age || '--'} tuổi • {patient_info.gender || '--'}</span>
          </div>
          <div className="p-3 bg-[#f8fafc] rounded-[10px] border border-[#e2e8f0]">
            <span className="text-xs font-medium text-[#475569] block">Bệnh viện theo dõi</span>
            <span className="text-sm font-semibold text-[#172b3a] mt-0.5 block">{follow_up.hospital || 'BV Phổi TW'}</span>
          </div>
          <div className="p-3 bg-[#f8fafc] rounded-[10px] border border-[#e2e8f0]">
            <span className="text-xs font-medium text-[#475569] block">Tái khám dự kiến</span>
            <span className="text-sm font-semibold text-[#1d4ed8] mt-0.5 block">{follow_up.next_appointment || 'Theo hẹn'}</span>
          </div>
        </div>
      </section>

      {/* 2. Baseline Clinical Vitals */}
      <section aria-label="Mức chuẩn sinh hiệu lâm sàng" className="bg-white rounded-[14px] border border-[#e2e8f0] p-5 sm:p-6 space-y-4">
        <h3 className="text-xs font-semibold text-[#475569] uppercase tracking-wider">
          Mức Chuẩn Sinh Hiệu Cá Nhân Hóa (Personal Best)
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="p-4 bg-[#eff6ff] rounded-[10px] border border-[#dbeafe] flex items-center gap-3.5">
            <div className="p-3 bg-white rounded-[10px] border border-[#dbeafe] text-[#2568d4] shrink-0">
              <Wind className="w-6 h-6" />
            </div>
            <div>
              <span className="text-xs font-semibold text-[#172b3a] uppercase tracking-wide block">
                Lưu lượng đỉnh (PEF) tốt nhất
              </span>
              <div className="text-xl sm:text-2xl font-bold text-[#2568d4] mt-0.5">
                {clinical_status.personal_best_pef || 500} <span className="text-xs font-semibold text-[#475569]">L/phút</span>
              </div>
              <p className="text-xs text-[#475569] font-normal mt-0.5 leading-relaxed">
                Mốc tham chiếu 100% để phân vùng Vàng (60–80%) và Đỏ (&lt;60%)
              </p>
            </div>
          </div>

          <div className="p-4 bg-[#f8fafc] rounded-[10px] border border-[#e2e8f0] flex items-center gap-3.5">
            <div className="p-3 bg-white rounded-[10px] border border-[#e2e8f0] text-rose-600 shrink-0">
              <HeartPulse className="w-6 h-6" />
            </div>
            <div>
              <span className="text-xs font-semibold text-[#172b3a] uppercase tracking-wide block">
                Nồng độ SpO₂ nền tảng
              </span>
              <div className="text-xl sm:text-2xl font-bold text-[#172b3a] mt-0.5">
                {clinical_status.baseline_spo2 || 98} <span className="text-xs font-semibold text-[#475569]">%</span>
              </div>
              <p className="text-xs text-[#475569] font-normal mt-0.5 leading-relaxed">
                Mức oxy đo khi cơ thể hoàn toàn nghỉ ngơi và ổn định
              </p>
            </div>
          </div>
        </div>

        {/* Diagnosis & Triggers */}
        <div className="p-4 bg-[#f8fafc] rounded-[10px] border border-[#e2e8f0] space-y-2 text-xs sm:text-sm">
          <div>
            <strong className="font-semibold text-[#172b3a]">Chẩn đoán ra viện:</strong>{' '}
            <span className="text-[#475569]">{clinical_status.diagnosis || 'Hen phế quản ngoại trú'}</span>
          </div>
          <div>
            <strong className="font-semibold text-[#172b3a]">Dị nguyên cần tránh:</strong>{' '}
            <span className="text-[#475569]">
              {clinical_status.known_triggers?.length > 0
                ? clinical_status.known_triggers.join(', ')
                : 'Khói thuốc lá, phấn hoa, mạt bụi nhà, không khí lạnh'}
            </span>
          </div>
        </div>
      </section>

      {/* 3. Medications Plan */}
      <section aria-label="Phác đồ thuốc điều trị" className="bg-white rounded-[14px] border border-[#e2e8f0] p-5 sm:p-6 space-y-4">
        <h3 className="text-xs font-semibold text-[#475569] uppercase tracking-wider">
          Phác Đồ Thuốc Ra Viện
        </h3>

        <div className="space-y-3">
          {/* Controller */}
          <div className="p-4 rounded-[10px] border border-[#e2e8f0] bg-[#f8fafc] space-y-1">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#172b3a] uppercase">
              <Pill className="w-4 h-4 text-[#2568d4]" />
              <span>Thuốc duy trì kiểm soát hằng ngày:</span>
            </div>
            <p className="text-xs sm:text-sm text-[#475569] font-normal leading-relaxed pl-6">
              {current_medications.controller_med || 'Không dùng thuốc duy trì hàng ngày (Bậc 1).'}
            </p>
          </div>

          {/* Reliever */}
          <div className="p-4 rounded-[10px] border border-[#e2e8f0] bg-[#f8fafc] space-y-1">
            <div className="flex items-center gap-2 text-xs font-semibold text-amber-800 uppercase">
              <Pill className="w-4 h-4 text-amber-700" />
              <span>Thuốc cắt cơn khẩn cấp khi có triệu chứng:</span>
            </div>
            <p className="text-xs sm:text-sm text-[#475569] font-normal leading-relaxed pl-6">
              {current_medications.reliever_med || 'Budesonide/Formoterol hoặc SABA xịt khi có triệu chứng khó thở hoặc trước khi vận động.'}
            </p>
          </div>
        </div>
      </section>

      {/* 4. Action Plan Guidelines */}
      {action_plan_rules && (
        <section aria-label="Hướng dẫn vùng hành động" className="bg-white rounded-[14px] border border-[#e2e8f0] p-5 sm:p-6 space-y-3">
          <h3 className="text-xs font-semibold text-[#475569] uppercase tracking-wider">
            Hướng Dẫn Phân Vùng Hành Động Cá Nhân
          </h3>

          <div className="space-y-2.5 text-xs">
            {action_plan_rules.green_zone && (
              <div className="p-3 rounded-[10px] border border-emerald-200 bg-[#f0fdf4] text-emerald-950">
                <strong className="text-emerald-900 font-semibold block mb-1">VÙNG XANH (PEF ≥ 80%):</strong>
                <p className="whitespace-pre-line text-emerald-800">{action_plan_rules.green_zone}</p>
              </div>
            )}
            {action_plan_rules.yellow_zone && (
              <div className="p-3 rounded-[10px] border border-amber-200 bg-amber-50/70 text-amber-950">
                <strong className="text-amber-900 font-semibold block mb-1">VÙNG VÀNG (PEF 60–80%):</strong>
                <p className="whitespace-pre-line text-amber-800">{action_plan_rules.yellow_zone}</p>
              </div>
            )}
            {action_plan_rules.red_zone && (
              <div className="p-3 rounded-[10px] border border-rose-200 bg-rose-50/70 text-rose-950">
                <strong className="text-rose-900 font-semibold block mb-1">VÙNG ĐỎ (PEF &lt; 60%):</strong>
                <p className="whitespace-pre-line text-rose-800">{action_plan_rules.red_zone}</p>
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
