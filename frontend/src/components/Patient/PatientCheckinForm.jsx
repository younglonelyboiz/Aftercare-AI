import React, { useState, useEffect } from 'react';
import { Activity, Calendar, CheckCircle2, Loader2, ArrowRight, Eye } from 'lucide-react';
import PatientVitalsCard from './PatientVitalsCard';
import PatientSymptomsGrid from './PatientSymptomsGrid';
import PatientActionZoneCard from './PatientActionZoneCard';
import { evaluateScreener, confirmPatientSafety20m } from '../../services/api';
import { formatCheckinDateTimeVN, formatHeaderTodayVN } from '../../utils/patientDate';

export default function PatientCheckinForm({
  patientId,
  personalBestPef = 500,
  actionPlan: _actionPlan,
  pef,
  setPef,
  spo2,
  setSpo2,
  symptoms = {},
  setSymptoms,
  medsTaken = false,
  setMedsTaken,
  currentZone = 'green',
  hasCheckedInToday = false,
  todaySavedCheckin = null,
  onOpenChatWithAlert,
  onSubmitCheckin
}) {
  const [countdownSeconds, setCountdownSeconds] = useState(1200);
  const [safetyConfirmed, setSafetyConfirmed] = useState(false);
  const [noSpo2Device, setNoSpo2Device] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  const [screenerResult, setScreenerResult] = useState({
    risk_level: "NORMAL",
    matched_flags: [],
    matched_reasons: ["Các chỉ số sinh hiệu và triệu chứng ghi nhận đều trong giới hạn an toàn bình thường."],
    action_instructions: "Tình trạng ổn định. Tiếp tục duy trì phác đồ điều trị."
  });

  const pefRatio = personalBestPef > 0 ? Math.round((pef / personalBestPef) * 100) : 100;

  // Gọi evaluateScreener khi bệnh nhân thay đổi chỉ số
  useEffect(() => {
    let isMounted = true;
    const fetchScreener = async () => {
      try {
        const selectedList = [];
        if (symptoms.nightWaking) selectedList.push('night_waking');
        if (symptoms.relieverUsed) selectedList.push('reliever_frequent');
        if (symptoms.activityLimited) selectedList.push('activity_limited');
        if (symptoms.dangerSign) selectedList.push('severe_dyspnea');

        const result = await evaluateScreener({
          patient_id: patientId || 'BN-2026-ASTHMA-01',
          pef_value: pef,
          spo2: noSpo2Device ? 98 : spo2,
          reliever_puffs: symptoms.relieverUsed ? 2 : 0,
          selected_symptoms: selectedList
        });

        if (isMounted && result) {
          setScreenerResult(result);
        }
      } catch (err) {
        console.error('Không thể đánh giá sàng lọc:', err);
      }
    };

    fetchScreener();
    return () => {
      isMounted = false;
    };
  }, [patientId, pef, spo2, noSpo2Device, symptoms]);

  // Bộ đếm ngược 20 phút khi ở Vùng Vàng
  useEffect(() => {
    let timer = null;
    if (currentZone === 'yellow' && !safetyConfirmed) {
      timer = setInterval(() => {
        setCountdownSeconds((prev) => (prev > 0 ? prev - 1 : 0));
      }, 1000);
    } else {
      setCountdownSeconds(1200);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [currentZone, safetyConfirmed]);

  const handleConfirmSafety = async () => {
    try {
      await confirmPatientSafety20m(
        patientId || 'BN-2026-ASTHMA-01',
        'Bệnh nhân xác nhận đã dùng thuốc cắt cơn, nghỉ ngơi 20 phút và nhịp thở đã ổn định an toàn.'
      );
      setSafetyConfirmed(true);
    } catch (err) {
      alert('Lỗi xác nhận an toàn: ' + (err.response?.data?.detail || err.message));
    }
  };

  const toggleSymptom = (key) => {
    if (!setSymptoms) return;
    setSymptoms((prev) => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  const handleSubmit = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (isSubmitting) return;

    setIsSubmitting(true);
    setSubmitError(null);
    setSubmitSuccess(false);

    try {
      if (onSubmitCheckin) {
        await onSubmitCheckin();
      }
      setSubmitSuccess(true);
      setTimeout(() => setSubmitSuccess(false), 5000);
    } catch (err) {
      setSubmitError(err.response?.data?.detail || err.message || 'Lỗi khi lưu kết quả check-in');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* Top Banner & Date Info */}
      <div className="bg-white rounded-[14px] border border-[#e2e8f0] p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-[10px] bg-[#eff6ff] text-[#2568d4] border border-[#dbeafe] shrink-0">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base sm:text-lg font-semibold text-[#172b3a] tracking-tight flex items-center gap-2 flex-wrap">
              Khảo Sát Kiểm Soát Hen Hằng Ngày
              <span className="text-xs font-medium text-[#475569] bg-[#f8fafc] px-2.5 py-0.5 rounded-md border border-[#e2e8f0]">
                BYT &amp; GINA 2023
              </span>
            </h2>
            <p className="text-[13px] text-[#475569] font-normal leading-relaxed">
              Chỉ số tự đo được giám sát liên tục bởi điều dưỡng phụ trách ca trực
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 bg-[#f8fafc] border border-[#e2e8f0] rounded-lg text-xs font-medium text-[#475569] shrink-0 self-start sm:self-auto">
          <Calendar className="w-4 h-4 text-[#2568d4]" />
          <span>{formatHeaderTodayVN()}</span>
        </div>
      </div>

      {/* 1. Vitals Card */}
      <PatientVitalsCard
        pef={pef}
        setPef={setPef}
        personalBestPef={personalBestPef}
        pefRatio={pefRatio}
        currentZone={currentZone}
        spo2={spo2}
        setSpo2={setSpo2}
        noSpo2Device={noSpo2Device}
        setNoSpo2Device={setNoSpo2Device}
      />

      {/* 2. Symptoms Grid */}
      <PatientSymptomsGrid
        symptoms={symptoms}
        toggleSymptom={toggleSymptom}
        medsTaken={medsTaken}
        setMedsTaken={setMedsTaken}
      />

      {/* Clarity strip: distinguishes live unsaved preview vs today's saved checkin */}
      <div className="flex items-center justify-between gap-2 flex-wrap px-3.5 py-2.5 rounded-[10px] bg-[#eff6ff] border border-[#dbeafe] text-xs font-medium text-[#172b3a]">
        <span className="inline-flex items-center gap-1.5">
          <Eye className="w-3.5 h-3.5 text-[#2568d4]" aria-hidden="true" />
          <span>Phân tầng bên dưới đang tính xem trước theo chỉ số biểu mẫu hiện tại (chưa tự lưu nếu bạn chưa bấm Gửi Check-in).</span>
        </span>
        {hasCheckedInToday && todaySavedCheckin ? (
          <span className="text-xs font-semibold text-[#065f46] bg-[#ecfdf5] border border-[#a7f3d0] px-2.5 py-0.5 rounded-full">
            Đã gửi hôm nay: {formatCheckinDateTimeVN(todaySavedCheckin)}
          </span>
        ) : (
          <span className="text-xs font-medium text-[#475569] bg-white border border-[#cbd5e1] px-2.5 py-0.5 rounded-full">
            Hôm nay chưa có bản ghi đã lưu
          </span>
        )}
      </div>

      {/* 3. Action Zone & Emergency/Safety Card */}
      <PatientActionZoneCard
        zone={currentZone}
        screenerResult={screenerResult}
        countdownSeconds={countdownSeconds}
        safetyConfirmed={safetyConfirmed}
        onConfirmSafety={handleConfirmSafety}
        onOpenChatWithAlert={onOpenChatWithAlert}
      />

      {/* Success / Error Feedback */}
      {submitSuccess && (
        <div className="p-4 rounded-[10px] border border-emerald-300 bg-[#f0fdf4] text-emerald-900 flex items-center gap-2 text-sm font-semibold">
          <CheckCircle2 className="w-5 h-5 text-emerald-700 shrink-0" />
          Đã lưu đánh giá sức khỏe hôm nay thành công! Dữ liệu đã đồng bộ tới điều dưỡng.
        </div>
      )}

      {submitError && (
        <div className="p-4 rounded-[10px] border border-rose-300 bg-[#fef2f2] text-rose-900 text-sm font-medium">
          Lỗi: {submitError}
        </div>
      )}

      {/* Bottom Save Action Bar */}
      <div className="bg-white rounded-[14px] border border-[#e2e8f0] p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h4 className="text-sm font-semibold text-[#172b3a]">
            Xác nhận lưu nhật ký
          </h4>
          <p className="text-xs sm:text-[13px] text-[#475569] font-normal leading-relaxed mt-0.5">
            Kết quả sẽ được ghi vào lịch theo dõi 14 ngày và đồng bộ tới hệ thống
          </p>
        </div>

        <button
          type="button"
          onClick={handleSubmit}
          disabled={isSubmitting}
          className="min-h-[44px] px-5 py-2.5 rounded-lg bg-[#2568d4] hover:bg-[#1d56b8] disabled:opacity-50 text-white font-semibold text-sm transition-colors flex items-center justify-center gap-2 shrink-0 cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#2568d4]"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Đang lưu đánh giá...
            </>
          ) : (
            <>
              Lưu đánh giá hôm nay
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      </div>
    </div>
  );
}
