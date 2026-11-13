import React, { useState } from 'react';
import { Bell, Bot, Calendar, LogOut } from 'lucide-react';
import { formatHeaderTodayVN } from '../../utils/patientDate';

function getInitials(name = '') {
  const parts = String(name).trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return 'BN';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

const TAB_TITLES = {
  overview: 'Hôm nay',
  checkin: 'Check-in hằng ngày',
  plan: 'Hồ sơ & Kế hoạch',
  history: 'Lịch sử theo dõi',
};

export default function PatientWellnessTopbar({
  activeTab = 'overview',
  reminders = [],
  showNotifications = false,
  onToggleNotifications,
  patients = [],
  selectedPatientId = '',
  onSelectPatient,
  user,
  patientName = '',
  onOpenChat,
  onSwitchPortal,
  onLogout,
}) {
  const displayName = patientName || user?.full_name || 'Bệnh nhân';
  const [todayLabel] = useState(() => formatHeaderTodayVN());
  const tabTitle = TAB_TITLES[activeTab] || 'Hôm nay';
  const roleSubtitle =
    user?.role === 'admin'
      ? 'Xem cổng BN (Quản trị)'
      : user?.role === 'nurse'
      ? 'Xem cổng BN (Điều dưỡng)'
      : 'Hồ sơ bệnh nhân';

  return (
    <>
      {/* Mobile Header Strip (<= 900px where sidebar collapses to bottom nav) */}
      <div className="pw-mobile-bar">
        <div className="pw-mobile-brand">
          <div className="w-7 h-7 rounded-lg bg-[#f8fafc] border border-[#e2e8f0] flex items-center justify-center p-0.5 shrink-0">
            <img
              src="/pictures/hopi-mascot-clean.png"
              alt="AfterCare AI"
              width={24}
              height={24}
              className="w-full h-full object-contain"
            />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-bold text-[#172b3a] leading-tight truncate">AfterCare AI</div>
          </div>
        </div>

        <div className="pw-mobile-actions">
          {user && user.role !== 'patient' && onSwitchPortal && (
            <button
              type="button"
              className="pw-staff-pill"
              onClick={() => onSwitchPortal('nurse')}
            >
              Điều dưỡng
            </button>
          )}
          <button
            type="button"
            className="pw-icon-btn"
            onClick={onOpenChat}
            aria-label="Hỏi trợ lý HOPI"
            title="Hỏi trợ lý HOPI"
          >
            <Bot size={16} aria-hidden="true" />
          </button>
          {onLogout && (
            <button
              type="button"
              className="pw-icon-btn"
              onClick={onLogout}
              aria-label="Đăng xuất"
              title="Đăng xuất"
            >
              <LogOut size={16} aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      {/* Main Wellness Topbar */}
      <header className="pw-topbar">
        <div className="pw-topbar-left">
          <span className="pw-topbar-tab-label">{tabTitle}</span>
          <span className="pw-date-chip">
            <Calendar size={13} className="text-[#2568d4] shrink-0" aria-hidden="true" />
            <span>{todayLabel}</span>
          </span>
        </div>

        <div className="pw-topbar-right">
          {user && user.role !== 'patient' && patients.length > 0 && (
            <label className="pw-patient-switcher">
              <span>Bệnh nhân:</span>
              <select
                aria-label="Chọn bệnh nhân"
                value={selectedPatientId}
                onChange={(e) => onSelectPatient?.(e.target.value)}
              >
                {patients.map((p) => (
                  <option key={p.patient_id} value={p.patient_id}>
                    {p.full_name} ({p.patient_id})
                  </option>
                ))}
              </select>
            </label>
          )}

          <button
            type="button"
            className="pw-icon-btn"
            onClick={onToggleNotifications}
            aria-label={
              reminders.length > 0
                ? `Thông báo nhắc nhở (${reminders.length})`
                : 'Thông báo nhắc nhở'
            }
            aria-expanded={showNotifications}
            title="Thông báo nhắc nhở"
          >
            <Bell size={18} aria-hidden="true" />
            {reminders.length > 0 && (
              <span className="pw-notif-badge">{reminders.length}</span>
            )}
          </button>

          <div className="pw-user-pill">
            <div className="pw-user-avatar" aria-hidden="true">
              {getInitials(displayName)}
            </div>
            <div className="pw-user-meta">
              <span className="pw-user-name">{displayName}</span>
              <span className="pw-user-sub">{roleSubtitle}</span>
            </div>
          </div>
        </div>
      </header>
    </>
  );
}
