import React, { useMemo } from 'react';
import MedicationReminderBanner from '../CareTracker/MedicationReminderBanner';
import {
  AlertTriangle,
  ArrowRight,
  CalendarClock,
  CheckCircle2,
  ClipboardList,
  Clock,
  HeartPulse,
  ShieldAlert,
  ShieldCheck,
  Wind,
} from 'lucide-react';
import {
  formatCheckinDateTimeVN,
  formatCheckinShortDateVN,
  getLatestCheckin,
  getSortedHistoryAsc,
  hasCheckedInTodayVN,
} from '../../utils/patientDate';

const ZONE_META = {
  GREEN: {
    label: 'Ổn định',
    tag: 'Vùng Xanh',
    chipClass: 'green',
    icon: ShieldCheck,
  },
  YELLOW: {
    label: 'Cảnh báo',
    tag: 'Vùng Vàng',
    chipClass: 'yellow',
    icon: AlertTriangle,
  },
  RED: {
    label: 'Cấp cứu',
    tag: 'Vùng Đỏ',
    chipClass: 'red',
    icon: ShieldAlert,
  },
};

function getZoneMeta(zone, pefPct) {
  const normalized = String(zone || '').toUpperCase();
  if (ZONE_META[normalized]) return ZONE_META[normalized];
  if (typeof pefPct === 'number') {
    if (pefPct < 60) return ZONE_META.RED;
    if (pefPct < 80) return ZONE_META.YELLOW;
    return ZONE_META.GREEN;
  }
  return {
    label: 'Chưa có',
    tag: 'Chưa đánh giá',
    chipClass: 'unknown',
    icon: Clock,
  };
}

export default function PatientOverviewBento({
  profile,
  history = [],
  carePlan,
  reminders = [],
  onGoTodayCheckin,
  onOpenHistory,
  onOpenRecord,
  onAcknowledgeReminder,
  onSnoozeReminder,
}) {
  const personalBest =
    carePlan?.personal_best_pef ||
    profile?.clinical_status?.personal_best_pef ||
    500;
  const fullName = profile?.patient_info?.full_name || 'Bệnh nhân';
  const nextAppointment = profile?.follow_up?.next_appointment;
  const followUpHospital = profile?.follow_up?.hospital;
  const doctorInCharge = profile?.follow_up?.doctor_in_charge;

  const sortedAsc = useMemo(() => getSortedHistoryAsc(history), [history]);
  const latestSaved = useMemo(() => getLatestCheckin(sortedAsc), [sortedAsc]);
  const checkedInToday = useMemo(() => hasCheckedInTodayVN(sortedAsc), [sortedAsc]);

  const savedPefPct = useMemo(() => {
    if (!latestSaved || latestSaved.pef_value == null) return null;
    if (latestSaved.pef_percent != null) return Math.round(Number(latestSaved.pef_percent));
    return Math.round((Number(latestSaved.pef_value) / personalBest) * 100);
  }, [latestSaved, personalBest]);

  const latestZoneMeta = getZoneMeta(latestSaved?.action_zone, savedPefPct);
  const LatestZoneIcon = latestZoneMeta.icon;

  // Pick next reminder/task strictly from existing state without inventing priorities or schedules
  const nextTaskSummary = useMemo(() => {
    if (Array.isArray(reminders) && reminders.length > 0) {
      const overdue = reminders.find((r) => r && (r.status === 'OVERDUE' || r.is_overdue));
      const target = overdue || reminders[0];
      const isOverdue = Boolean(target && (target.status === 'OVERDUE' || target.is_overdue));
      return {
        kind: 'reminder',
        reminder: target,
        isOverdue,
        title: target?.title || 'Nhắc nhở điều trị',
        time: target?.scheduled_time ? String(target.scheduled_time).slice(0, 5) : null,
        extraCount: Math.max(0, reminders.length - 1),
      };
    }

    const items = carePlan?.items;
    if (Array.isArray(items) && items.length > 0) {
      const scheduledItem = items.find(
        (item) => Array.isArray(item?.schedule_times) && item.schedule_times.length > 0
      );
      if (scheduledItem) {
        return {
          kind: 'careplan_scheduled',
          title: scheduledItem.title,
          scheduleText: scheduledItem.schedule_times.join(', '),
          totalItems: items.length,
        };
      }
      return {
        kind: 'careplan_unscheduled',
        title: items[0]?.title || 'Nhiệm vụ theo phác đồ',
        totalItems: items.length,
      };
    }

    return { kind: 'none' };
  }, [reminders, carePlan]);

  return (
    <div className="pw-overview-grid">
      {/* 1. Welcome, Single Today Status & Single Primary Check-in CTA */}
      <section className="pw-welcome-card" aria-label="Chào mừng và trạng thái hôm nay">
        <div className="pw-welcome-top">
          <div className="min-w-0">
            <h1 className="pw-welcome-heading">Chào {fullName}</h1>
            <p className="pw-welcome-desc">
              {profile?.clinical_status?.asthma_severity
                ? `Phân loại: ${profile.clinical_status.asthma_severity}.`
                : 'Theo dõi hô hấp & kế hoạch hành động GINA mỗi ngày.'}
            </p>
          </div>
        </div>

        <div className="pw-welcome-meta">
          {checkedInToday ? (
            <span className="pw-status-chip checked">
              <CheckCircle2 size={14} aria-hidden="true" />
              <span>Đã check-in hôm nay</span>
            </span>
          ) : (
            <span className="pw-status-chip unknown">
              <Clock size={14} aria-hidden="true" />
              <span>Chưa check-in hôm nay</span>
            </span>
          )}

          <span className={`pw-status-chip ${latestZoneMeta.chipClass}`}>
            <LatestZoneIcon size={14} aria-hidden="true" />
            <span>
              {latestSaved
                ? checkedInToday
                  ? `${latestZoneMeta.tag} • ${latestZoneMeta.label}`
                  : `Lần cuối (${formatCheckinShortDateVN(latestSaved)}): ${latestZoneMeta.tag}`
                : 'Chưa có đánh giá đã lưu'}
            </span>
          </span>
        </div>

        <div className="pw-welcome-actions">
          <button
            type="button"
            onClick={onGoTodayCheckin}
            className="pw-btn-primary"
          >
            <span>{checkedInToday ? 'Cập nhật check-in hôm nay' : 'Check-in hôm nay'}</span>
            <ArrowRight size={16} aria-hidden="true" />
          </button>
        </div>
      </section>

      {/* 3. Next Task / Reminder Summary & Follow-up Appointment */}
      <section className="pw-card pw-overview-next-card" aria-label="Việc cần làm tiếp theo và tái khám">
        <div className="pw-card-header mb-0 flex-wrap">
          <h2 className="pw-card-title">
            <ClipboardList size={18} className="text-[#2568d4]" aria-hidden="true" />
            <span>Hôm nay cần làm gì?</span>
          </h2>
          <button
            type="button"
            onClick={onOpenRecord}
            className="pw-link-btn !min-h-[32px] !py-1 !px-1.5 text-xs"
          >
            Hồ sơ & Kế hoạch
          </button>
        </div>

        <div className="pw-next-task-body">
          {nextTaskSummary.kind === 'reminder' && (
            <div>
              <MedicationReminderBanner
                reminders={[...reminders].sort((a, b) => Number(Boolean(b.is_overdue || b.status === 'OVERDUE')) - Number(Boolean(a.is_overdue || a.status === 'OVERDUE')))}
                onAcknowledge={onAcknowledgeReminder}
                onSnooze={onSnoozeReminder}
                onMeasure={onGoTodayCheckin}
              />
            </div>
          )}

          {nextTaskSummary.kind !== 'reminder' && carePlan?.items?.length > 0 && (
            <div className="pw-today-schedule">
              <p className="pw-card-sub">Lịch theo kế hoạch cá nhân. Hiện không có nhắc nhở đang chờ.</p>
              {carePlan.items.map(item => (
                <article className="pw-plan-reference" key={item.id}>
                  <h3>{item.title}</h3>
                  {item.dosage && <p>{item.dosage}</p>}
                  <p>{item.schedule_times?.length ? item.schedule_times.join(' · ') : 'Chưa có giờ cụ thể'}</p>
                  {item.item_type === 'PEF_MEASURE' && (
                    <button type="button" className="pw-btn-soft" onClick={onGoTodayCheckin}>Nhập chỉ số</button>
                  )}
                </article>
              ))}
            </div>
          )}

          {nextTaskSummary.kind === 'none' && (
            <p className="text-xs text-[#475569] m-0">
              Hiện không có nhắc nhở đang chờ. Bạn có thể kiểm tra hoặc cập nhật check-in hôm nay.
            </p>
          )}
        </div>

        {(nextAppointment || followUpHospital || doctorInCharge) && (
          <div className="pw-followup-row">
            <CalendarClock size={16} className="text-[#2568d4] shrink-0" aria-hidden="true" />
            <div className="min-w-0 text-xs text-[#172b3a]">
              <span className="font-semibold">
                {nextAppointment
                  ? `Lịch tái khám dự kiến: ${nextAppointment}`
                  : 'Thông tin tái khám:'}
              </span>
              {(followUpHospital || doctorInCharge) && (
                <span className="text-[#475569]">
                  {' '}• {[doctorInCharge, followUpHospital].filter(Boolean).join(' — ')}
                </span>
              )}
            </div>
          </div>
        )}
      </section>
      {/* 2. Latest Saved Metrics (PEF + SpO2 at the same measurement timestamp) */}
      <section className="pw-blue-metric-card" aria-label="Chỉ số đã lưu gần nhất">
        <div className="pw-card-header mb-0 flex-wrap">
          <h2 className="pw-card-title">
            <Wind size={18} className="text-[#2568d4]" aria-hidden="true" />
            <span>Chỉ số đã lưu gần nhất</span>
          </h2>
          <button
            type="button"
            onClick={onOpenHistory}
            className="pw-link-btn !min-h-[32px] !py-1 !px-1.5 text-xs"
          >
            Xem lịch sử
          </button>
        </div>

        {latestSaved ? (
          <>
            <div className="pw-saved-metrics-pair">
              <div className="pw-saved-metric-box">
                <div className="pw-mini-label">
                  <Wind size={14} className="text-[#2568d4]" aria-hidden="true" />
                  <span>PEF gần nhất</span>
                </div>
                <div className="pw-big-metric">
                  {latestSaved.pef_value != null ? latestSaved.pef_value : '--'}{' '}
                  <span className="pw-big-unit">L/phút</span>
                </div>
                <p className="pw-blue-sub m-0">
                  {savedPefPct != null
                    ? `${savedPefPct}% mức tốt nhất (${personalBest} L/p)`
                    : `Mức chuẩn: ${personalBest} L/p`}
                </p>
              </div>

              <div className="pw-saved-metric-box">
                <div className="pw-mini-label">
                  <HeartPulse size={14} className="text-[#2568d4]" aria-hidden="true" />
                  <span>SpO₂ cùng lúc</span>
                </div>
                <div className="pw-mini-value">
                  {latestSaved.spo2_value != null ? `${latestSaved.spo2_value}%` : 'Không máy'}
                </div>
                <p className="pw-blue-sub m-0">
                  Thuốc cắt cơn: {latestSaved.reliever_puffs ?? 0} nhát
                </p>
              </div>
            </div>

            <div className="pw-blue-pill">
              <Clock size={12} aria-hidden="true" />
              <span>Đo lúc: {formatCheckinDateTimeVN(latestSaved)}</span>
            </div>
          </>
        ) : (
          <>
            <div className="pw-saved-metrics-pair">
              <div className="pw-saved-metric-box">
                <div className="pw-mini-label">
                  <Wind size={14} className="text-[#2568d4]" aria-hidden="true" />
                  <span>PEF gần nhất</span>
                </div>
                <div className="pw-big-metric">
                  -- <span className="pw-big-unit">L/phút</span>
                </div>
                <p className="pw-blue-sub m-0">Chưa có kết quả PEF đã lưu</p>
              </div>

              <div className="pw-saved-metric-box">
                <div className="pw-mini-label">
                  <HeartPulse size={14} className="text-[#2568d4]" aria-hidden="true" />
                  <span>SpO₂ cùng lúc</span>
                </div>
                <div className="pw-mini-value">--</div>
                <p className="pw-blue-sub m-0">Chưa có bản ghi đã lưu</p>
              </div>
            </div>

            <div className="pw-blue-pill">
              <span>Mức chuẩn cá nhân: {personalBest} L/phút</span>
            </div>
          </>
        )}
      </section>

    </div>
  );
}
