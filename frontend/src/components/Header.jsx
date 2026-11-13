import { Activity, User, RotateCcw, LogOut, ShieldCheck } from 'lucide-react';

export default function Header({
  patients,
  selectedPatientId,
  onSelectPatient,
  currentPortal,
  onSwitchPortal,
  onResetDemo,
  isResetting,
  user,
  onLogout
}) {
  const roles = { patient: 'BỆNH NHÂN', nurse: 'ĐIỀU DƯỠNG', admin: 'QUẢN TRỊ' };
  return (
    <header className="p052-header">
      <div className="p052-header-inner"><div className="p052-brand"><img src="/pictures/hopi-mascot-clean.png" alt="" width="40" height="40" /><div><div className="p052-brand-line"><h1>AfterCare AI</h1><span>{roles[currentPortal]}</span></div><p>Trợ lý Hopi • Chăm sóc hen phế quản</p></div></div>

      {/* PORTAL SWITCHER: BỆNH NHÂN VS ĐIỀU DƯỠNG */}
      <div className="p052-header-actions"><div className="p052-portal-tabs">
        <button
          className={currentPortal === 'patient' ? 'active' : ''}
          onClick={() => onSwitchPortal('patient')}
        >
          <User size={14} />
          Bệnh nhân
        </button>
        {user.role !== 'patient' && <button
          className={currentPortal === 'nurse' ? 'active' : ''}
          onClick={() => onSwitchPortal('nurse')}
        >
          <Activity size={14} />
          Điều dưỡng
        </button>}
        {user.role === 'admin' && <button className={currentPortal === 'admin' ? 'active' : ''} onClick={() => onSwitchPortal('admin')}><ShieldCheck size={14} />Quản trị</button>}
      </div></div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span className="p052-user"><User size={14} />{user.full_name}</span>
        {user.role === 'admin' && <button className="p052-reset" onClick={onResetDemo} disabled={isResetting}><RotateCcw size={15} />{isResetting ? 'Đang đặt lại…' : 'Reset Demo'}</button>}
        <button onClick={onLogout} className="p052-logout" aria-label="Đăng xuất"><LogOut size={16} /><span>Đăng xuất</span></button>
      </div></div>
      {user.role !== 'patient' && currentPortal === 'patient' && <div className="p052-patient-select"><label htmlFor="patient-select">Hồ sơ bệnh nhân</label>
          <select
            id="patient-select"
            className="p052-select"
            value={selectedPatientId}
            onChange={(e) => onSelectPatient(e.target.value)}
          >
            {patients.map((p) => (
              <option key={p.patient_id} value={p.patient_id}>
                {p.full_name} ({p.age} tuổi - {p.patient_id})
              </option>
            ))}
          </select>
        </div>}
    </header>
  );
}

