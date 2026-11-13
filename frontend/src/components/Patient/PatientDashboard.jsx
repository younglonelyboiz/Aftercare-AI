import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Bell,
  Bot,
  ClipboardCheck,
  Clock,
  FileText,
  Phone,
  RefreshCw,
} from 'lucide-react';
import '../../styles/patient-wellness.css';
import PatientWellnessSidebar from './PatientWellnessSidebar';
import PatientWellnessTopbar from './PatientWellnessTopbar';
import PatientOverviewBento from './PatientOverviewBento';
import PatientCheckinForm from './PatientCheckinForm';
import PatientHistoryView from './PatientHistoryView';
import PatientSummaryView from './PatientSummaryView';
import PatientCarePlanView from './PatientCarePlanView';
import MedicationReminderBanner from '../CareTracker/MedicationReminderBanner';
import { ACTION_ZONE_ALERT_COPY } from './actionZoneCopy';
import {
  formatMonthPillVN,
  getMonthKeyVN,
  getTodayLatestCheckinVN,
  hasCheckedInTodayVN,
} from '../../utils/patientDate';

const VALID_TABS = new Set(['overview', 'checkin', 'plan', 'history']);

function getTabFromLocation() {
  if (typeof window === 'undefined') return 'overview';
  const raw = new URLSearchParams(window.location.search).get('tab');
  return raw && VALID_TABS.has(raw) ? raw : 'overview';
}

function syncUrlTab(nextTab, { replace = false } = {}) {
  if (typeof window === 'undefined') return;
  const url = new URL(window.location.href);
  if (url.searchParams.get('tab') === nextTab) return;
  url.searchParams.set('tab', nextTab);
  if (replace) {
    window.history.replaceState({ tab: nextTab }, '', url.toString());
  } else {
    window.history.pushState({ tab: nextTab }, '', url.toString());
  }
}

export default function PatientDashboard({
  profile,
  history = [],
  carePlan,
  checkinProps,
  onOpenChat,
  user,
  patients = [],
  selectedPatientId = '',
  onSelectPatient,
  currentPortal = 'patient',
  onSwitchPortal,
  onResetDemo,
  isResetting = false,
  onLogout,
  reminders = [],
  onAcknowledgeReminder,
  onSnoozeReminder,
  loadError = null,
  onRetryLoad,
}) {
  const [tab, setTab] = useState(() => getTabFromLocation());
  const [trendRange, setTrendRange] = useState('14d');
  const [showNotifications, setShowNotifications] = useState(false);
  const shouldFocusCheckinRef = useRef(false);

  useEffect(() => {
    const url = new URL(window.location.href);
    const raw = url.searchParams.get('tab');
    if (raw !== null && !VALID_TABS.has(raw)) {
      syncUrlTab('overview', { replace: true });
    }
    const handlePopState = () => {
      setTab(getTabFromLocation());
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const zone = checkinProps?.currentZone || 'green';
  const checkedInToday = useMemo(() => hasCheckedInTodayVN(history), [history]);
  const todaySavedCheckin = useMemo(() => getTodayLatestCheckinVN(history), [history]);

  // Distinct real months present in history for HistoryView range pills
  const monthOptions = useMemo(() => {
    const uniqueKeys = new Set();
    history.forEach((item) => {
      const mKey = getMonthKeyVN(item);
      if (/^\d{4}-\d{2}$/.test(mKey)) uniqueKeys.add(mKey);
    });
    return Array.from(uniqueKeys)
      .sort((a, b) => b.localeCompare(a))
      .slice(0, 2)
      .map((key) => ({ key, label: formatMonthPillVN(key) }));
  }, [history]);

  const effectiveTrendRange =
    trendRange !== '7d' &&
    trendRange !== '14d' &&
    !monthOptions.some((opt) => opt.key === trendRange)
      ? '14d'
      : trendRange;

  const overdueReminders = useMemo(
    () => reminders.filter((r) => r && (r.status === 'OVERDUE' || r.is_overdue)),
    [reminders]
  );

  const sortedReminders = useMemo(() => {
    const overdue = reminders.filter((r) => r && (r.status === 'OVERDUE' || r.is_overdue));
    const pending = reminders.filter((r) => r && r.status !== 'OVERDUE' && !r.is_overdue);
    return [...overdue, ...pending];
  }, [reminders]);

  const activeAlertZone = useMemo(() => {
    const fz = String(zone || '').toLowerCase();
    if (fz === 'red' || fz === 'yellow') return fz;
    return null;
  }, [zone]);
  const activeAlertCopy = activeAlertZone ? ACTION_ZONE_ALERT_COPY[activeAlertZone] : null;

  const navigateToTab = useCallback((tabId) => {
    if (!VALID_TABS.has(tabId)) return;
    setTab(tabId);
    syncUrlTab(tabId);
  }, []);

  const showCheckin = useCallback(() => {
    shouldFocusCheckinRef.current = true;
    navigateToTab('checkin');
  }, [navigateToTab]);

  useEffect(() => {
    if (tab !== 'checkin' || !shouldFocusCheckinRef.current) return;
    shouldFocusCheckinRef.current = false;

    const frameId = requestAnimationFrame(() => {
      const prefersReducedMotion =
        typeof window !== 'undefined' &&
        typeof window.matchMedia === 'function' &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const target =
        document.getElementById('pef-number-input') ||
        document.getElementById('pef-input-slider');
      target?.scrollIntoView({
        behavior: prefersReducedMotion ? 'auto' : 'smooth',
        block: 'center',
      });
      const numberInput = document.getElementById('pef-number-input');
      if (numberInput && typeof numberInput.focus === 'function') {
        numberInput.focus({ preventScroll: true });
      }
    });

    return () => cancelAnimationFrame(frameId);
  }, [tab]);

  const handleViewActionZone = useCallback(() => {
    if (tab !== 'checkin') {
      navigateToTab('checkin');
    }
    requestAnimationFrame(() => {
      const prefersReducedMotion =
        typeof window !== 'undefined' &&
        typeof window.matchMedia === 'function' &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const zoneSection = document.querySelector(
        '#patient-checkin-section section[aria-label="Khối vùng hành động và khuyến nghị an toàn"]'
      );
      zoneSection?.scrollIntoView({
        behavior: prefersReducedMotion ? 'auto' : 'smooth',
        block: 'center',
      });
    });
  }, [tab, navigateToTab]);

  return (
    <div className="pw-shell">
      <PatientWellnessSidebar
        tab={tab}
        onSelectTab={navigateToTab}
        onOpenChat={onOpenChat}
        zone={zone}
        user={user}
        currentPortal={currentPortal}
        onSwitchPortal={onSwitchPortal}
        onResetDemo={onResetDemo}
        isResetting={isResetting}
        onLogout={onLogout}
      />

      <div className="pw-main">
        <PatientWellnessTopbar
          activeTab={tab}
          reminders={reminders}
          showNotifications={showNotifications}
          onToggleNotifications={() => setShowNotifications((prev) => !prev)}
          patients={patients}
          selectedPatientId={selectedPatientId}
          onSelectPatient={onSelectPatient}
          user={user}
          patientName={profile?.patient_info?.full_name}
          onOpenChat={onOpenChat}
          onSwitchPortal={onSwitchPortal}
          onLogout={onLogout}
        />

        {loadError && (
          <div className="pw-notice-strip error" role="alert">
            <span className="inline-flex items-center gap-2">
              <AlertTriangle size={16} aria-hidden="true" />
              <span>{loadError}</span>
            </span>
            {onRetryLoad && (
              <button
                type="button"
                className="pw-notice-btn inline-flex items-center gap-1.5"
                onClick={onRetryLoad}
              >
                <RefreshCw size={13} aria-hidden="true" />
                <span>Thử lại</span>
              </button>
            )}
          </div>
        )}

        {showNotifications && (
          <div className="pw-notice-strip info" role="status">
            <span className="inline-flex items-center gap-2">
              <Bell size={16} className="text-[#2568d4]" aria-hidden="true" />
              <span>
                {reminders.length > 0
                  ? `Bạn có ${reminders.length} nhắc nhở uống thuốc / đo PEF đang chờ xác nhận trong tab Kế hoạch.`
                  : 'Hiện không có nhắc nhở uống thuốc hoặc đo PEF nào đang chờ.'}
              </span>
            </span>
            <div className="flex items-center gap-2">
              {tab !== 'plan' && reminders.length > 0 && (
                <button
                  type="button"
                  className="pw-notice-btn"
                  onClick={() => {
                    navigateToTab('plan');
                    setShowNotifications(false);
                  }}
                >
                  Xem trong Kế hoạch
                </button>
              )}
              <button
                type="button"
                className="pw-notice-btn"
                onClick={() => setShowNotifications(false)}
              >
                Đóng
              </button>
            </div>
          </div>
        )}

        {/* Shell-level overdue reminder notice across all 4 tabs (non-emergency status) */}
        {overdueReminders.length > 0 && (
          <div className="pw-overdue-strip" role="status">
            <span className="inline-flex items-center gap-2 min-w-0">
              <Clock size={16} className="text-amber-800 shrink-0" aria-hidden="true" />
              <span>
                <strong>Nhắc nhở quá hạn ({overdueReminders.length}):</strong>{' '}
                {overdueReminders[0].title}
                {overdueReminders[0].scheduled_time
                  ? ` (giờ hẹn ${String(overdueReminders[0].scheduled_time).slice(0, 5)})`
                  : ''}
                {overdueReminders.length > 1 ? ` và ${overdueReminders.length - 1} mục khác` : ''}
              </span>
            </span>
            {tab !== 'plan' && (
              <button
                type="button"
                className="pw-notice-btn shrink-0"
                onClick={() => navigateToTab('plan')}
              >
                Mở Kế hoạch
              </button>
            )}
          </div>
        )}

        {/* Persistent live-form Yellow / Red Zone Alert across all 4 tabs */}
        {activeAlertCopy && (
          <div className={`pw-priority-zone ${activeAlertZone}`} role="alert">
            <div className="pw-priority-zone-text">
              <strong>{activeAlertCopy.heading}</strong>{' '}
              <span>{activeAlertCopy.subtitle}</span>
            </div>
            <div className="pw-priority-zone-actions">
              {activeAlertZone === 'red' && (
                <a className="pw-priority-btn danger" href="tel:115">
                  <Phone size={14} aria-hidden="true" />
                  <span>{activeAlertCopy.emergencyCta}</span>
                </a>
              )}
              <button type="button" className="pw-priority-btn" onClick={onOpenChat}>
                <Bot size={14} aria-hidden="true" />
                <span>{activeAlertCopy.hopiCta}</span>
              </button>
              <button type="button" className="pw-priority-btn" onClick={handleViewActionZone}>
                <span>Xem xử trí</span>
              </button>
            </div>
          </div>
        )}

        <main aria-label="Nội dung cổng bệnh nhân" className="pw-main-panels">
          {/* Tab 1: Overview */}
          <section
            id="patient-overview-section"
            hidden={tab !== 'overview'}
            inert={tab !== 'overview'}
            aria-label="Tổng quan sức khỏe"
          >
            <PatientOverviewBento
              profile={profile}
              history={history}
              carePlan={carePlan}
              reminders={reminders}
              onGoTodayCheckin={showCheckin}
              onOpenHistory={() => navigateToTab('history')}
              onOpenRecord={() => navigateToTab('plan')}
              onOpenChat={onOpenChat}
            />
          </section>

          {/* Tab 2: Check-in (always mounted so inputs & 20m timer persist across tab switches/resize) */}
          <section
            id="patient-checkin-section"
            className="pw-checkin-wrap"
            hidden={tab !== 'checkin'}
            inert={tab !== 'checkin'}
            aria-label="Khảo sát kiểm soát hen hằng ngày"
          >
            <div className="pw-checkin-section-header">
              <div>
                <h1 className="pw-welcome-heading">Biểu mẫu Check-in Hô hấp Hằng ngày</h1>
                <p className="pw-card-sub m-0 mt-1">
                  Nhập chỉ số buổi sáng và triệu chứng 24 giờ qua để đánh giá và lưu hồ sơ theo dõi
                </p>
              </div>
            </div>

            <PatientCheckinForm
              {...checkinProps}
              hasCheckedInToday={checkedInToday}
              todaySavedCheckin={todaySavedCheckin}
            />
          </section>

          {/* Tab 3: Plan (mounted so temporary checklist state persists across tab switches/resize) */}
          <section
            id="patient-plan-section"
            className="pw-plan-wrap space-y-5"
            hidden={tab !== 'plan'}
            inert={tab !== 'plan'}
            aria-label="Kế hoạch điều trị và hồ sơ"
          >
            <div className="pw-card">
              <div className="pw-card-header mb-0 flex-wrap gap-3">
                <div>
                  <h1 className="pw-welcome-heading">Kế hoạch điều trị &amp; Nhắc nhở</h1>
                  <p className="pw-card-sub mt-1 m-0">
                    Nhắc nhở uống thuốc/đo PEF, checklist nhiệm vụ hằng ngày và hồ sơ xuất viện cá nhân
                  </p>
                </div>
                <button
                  type="button"
                  onClick={showCheckin}
                  className="pw-btn-soft"
                >
                  Đi tới Check-in
                </button>
              </div>
            </div>

            <section className="pw-card space-y-3" aria-label="Nhắc nhở uống thuốc và đo PEF">
              <div className="pw-card-header mb-0">
                <h2 className="pw-card-title">
                  <Bell size={18} className="text-[#2568d4]" aria-hidden="true" />
                  <span>Nhắc nhở đang hoạt động</span>
                </h2>
                <span className="pw-card-sub">
                  {sortedReminders.length > 0 ? `${sortedReminders.length} nhắc nhở` : 'Không có nhắc nhở chờ'}
                </span>
              </div>

              {sortedReminders.length > 0 ? (
                <MedicationReminderBanner
                  reminders={sortedReminders}
                  onAcknowledge={onAcknowledgeReminder}
                  onSnooze={onSnoozeReminder}
                />
              ) : (
                <div className="pw-empty-inline">
                  Hiện không có nhắc nhở uống thuốc hoặc đo PEF nào đang chờ xác nhận.
                </div>
              )}
            </section>

            <PatientCarePlanView carePlan={carePlan} onCheckinToday={showCheckin} />
            <PatientSummaryView profile={profile} />
          </section>

          {/* Tab 4: History (mounted so selected chart point & selected calendar day persist) */}
          <section
            id="patient-history-section"
            hidden={tab !== 'history'}
            inert={tab !== 'history'}
            aria-label="Lịch sử check-in và xu hướng PEF"
          >
            <PatientHistoryView
              history={history}
              carePlan={carePlan}
              profile={profile}
              trendRange={effectiveTrendRange}
              onSelectTrendRange={setTrendRange}
              monthOptions={monthOptions}
              onOpenCheckin={showCheckin}
            />
          </section>
        </main>
      </div>

      {/* Bottom Bar Mobile (<= 900px) — 4 tabs matching desktop navigation; HOPI stays in mobile header */}
      <nav className="p052-bottom-nav" aria-label="Điều hướng bệnh nhân">
        <button
          type="button"
          className={`p052-bottom-btn ${tab === 'overview' ? 'active' : ''}`}
          aria-current={tab === 'overview' ? 'page' : undefined}
          onClick={() => navigateToTab('overview')}
        >
          <Activity size={18} aria-hidden="true" />
          <span>Tổng quan</span>
        </button>

        <button
          type="button"
          className={`p052-bottom-btn ${tab === 'checkin' ? 'active' : ''}`}
          aria-current={tab === 'checkin' ? 'page' : undefined}
          onClick={() => navigateToTab('checkin')}
        >
          <ClipboardCheck size={18} aria-hidden="true" />
          <span>Check-in</span>
        </button>

        <button
          type="button"
          className={`p052-bottom-btn ${tab === 'plan' ? 'active' : ''}`}
          aria-current={tab === 'plan' ? 'page' : undefined}
          onClick={() => navigateToTab('plan')}
        >
          <FileText size={18} aria-hidden="true" />
          <span>Kế hoạch</span>
        </button>

        <button
          type="button"
          className={`p052-bottom-btn ${tab === 'history' ? 'active' : ''}`}
          aria-current={tab === 'history' ? 'page' : undefined}
          onClick={() => navigateToTab('history')}
        >
          <Clock size={18} aria-hidden="true" />
          <span>Lịch sử</span>
        </button>
      </nav>
    </div>
  );
}
