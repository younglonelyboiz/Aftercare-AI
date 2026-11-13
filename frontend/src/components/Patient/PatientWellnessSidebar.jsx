import React from 'react';
import { Activity, ClipboardCheck, Clock, FileText, Bot, LogOut } from 'lucide-react';

const NAV_ITEMS = [
  { id: 'overview', label: 'Hôm nay', icon: Activity },
  { id: 'checkin', label: 'Check-in', icon: ClipboardCheck },
  { id: 'history', label: 'Lịch sử', icon: Clock },
  { id: 'plan', label: 'Hồ sơ & Kế hoạch', icon: FileText },
];

export default function PatientWellnessSidebar({
  tab = 'overview',
  onSelectTab,
  onOpenChat,
  zone = 'green',
  user,
  onSwitchPortal,
  onResetDemo,
  isResetting = false,
  onLogout,
}) {
  const showAlertTag = zone === 'yellow' || zone === 'red';

  return (
    <aside className="pw-sidebar" aria-label="Điều hướng cổng bệnh nhân">
      <div>
        <div className="pw-brand">
          <div className="pw-brand-avatar">
            <img
              src="/pictures/hopi-mascot-clean.png"
              alt="AfterCare AI"
              width={32}
              height={32}
              className="w-8 h-8 object-contain"
            />
          </div>
          <div className="min-w-0">
            <div className="pw-brand-title">AfterCare AI</div>
            <div className="pw-brand-sub">Theo dõi Hen GINA</div>
          </div>
        </div>

        <nav className="pw-nav-list" aria-label="Menu chính bệnh nhân">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = tab === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelectTab?.(item.id)}
                aria-current={isActive ? 'page' : undefined}
                className={`pw-nav-btn ${isActive ? 'active' : ''}`}
              >
                <Icon size={17} strokeWidth={2.2} aria-hidden="true" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      <div className="pw-sidebar-footer">
        {user && user.role !== 'patient' && (
          <div className="pw-staff-box">
            <span className="pw-staff-label">Chế độ nhân viên</span>
            <div className="pw-staff-pills">
              <button
                type="button"
                className="pw-staff-pill"
                onClick={() => onSwitchPortal?.('nurse')}
              >
                Điều dưỡng
              </button>
              {user.role === 'admin' && (
                <>
                  <button
                    type="button"
                    className="pw-staff-pill"
                    onClick={() => onSwitchPortal?.('admin')}
                  >
                    Quản trị
                  </button>
                  {onResetDemo && (
                    <button
                      type="button"
                      className="pw-staff-pill"
                      onClick={onResetDemo}
                      disabled={isResetting}
                    >
                      {isResetting ? 'Đang reset...' : 'Reset Demo'}
                    </button>
                  )}
                </>
              )}
            </div>
          </div>
        )}

        <button
          type="button"
          onClick={onOpenChat}
          className="pw-utility-btn hopi"
        >
          <Bot size={16} aria-hidden="true" />
          <span>Hỏi trợ lý HOPI</span>
          {showAlertTag && (
            <span
              className={`ml-auto shrink-0 whitespace-nowrap inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold text-white ${
                zone === 'red' ? 'bg-rose-700' : 'bg-amber-800'
              }`}
            >
              {zone === 'red' ? 'Cấp cứu' : 'Lưu ý'}
            </span>
          )}
        </button>

        {onLogout && (
          <button
            type="button"
            onClick={onLogout}
            className="pw-utility-btn"
          >
            <LogOut size={16} aria-hidden="true" />
            <span>Đăng xuất</span>
          </button>
        )}
      </div>
    </aside>
  );
}
