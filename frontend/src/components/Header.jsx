import React from 'react';
import { Activity, User, RotateCcw } from 'lucide-react';

export default function Header({ 
  patients, 
  selectedPatientId, 
  onSelectPatient, 
  currentPortal, 
  onSwitchPortal,
  onResetDemo,
  isResetting 
}) {
  return (
    <header className="app-header">
      <div className="brand-section">
        <div className="brand-icon-box">
          <Activity size={24} />
        </div>
        <div>
          <h1 className="brand-title">Aftercare-AI</h1>
          <p className="brand-subtitle">Trợ lý Y tế Sau Xuất Viện Hen Phế Quản (BYT & GINA)</p>
        </div>
      </div>

      {/* PORTAL SWITCHER: BỆNH NHÂN VS ĐIỀU DƯỠNG */}
      <div className="portal-toggle-group">
        <button 
          className={`portal-btn ${currentPortal === 'patient' ? 'active' : ''}`}
          onClick={() => onSwitchPortal('patient')}
        >
          <User size={15} style={{ marginRight: 6, verticalAlign: 'middle' }} />
          Portal Bệnh Nhân
        </button>
        <button 
          className={`portal-btn ${currentPortal === 'nurse' ? 'active' : ''}`}
          onClick={() => onSwitchPortal('nurse')}
        >
          <Activity size={15} style={{ marginRight: 6, verticalAlign: 'middle' }} />
          Portal Điều Dưỡng
        </button>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div className="patient-selector-wrap">
          <User size={18} color="var(--text-secondary)" />
          <label htmlFor="patient-select" className="selector-label">Đang xem bệnh nhân:</label>
          <select
            id="patient-select"
            className="patient-select"
            value={selectedPatientId}
            onChange={(e) => onSelectPatient(e.target.value)}
          >
            {patients.map((p) => (
              <option key={p.patient_id} value={p.patient_id}>
                {p.full_name} ({p.age} tuổi - {p.patient_id})
              </option>
            ))}
          </select>
        </div>

        {/* NÚT RESET DEMO */}
        <button
          className="demo-reset-btn"
          onClick={onResetDemo}
          disabled={isResetting}
          title="Khôi phục trạng thái ban đầu của cả 3 bệnh nhân để trình diễn demo"
        >
          <RotateCcw size={15} className={isResetting ? "spin-icon" : ""} />
          <span>{isResetting ? "Đang Reset..." : "Reset Demo"}</span>
        </button>
      </div>
    </header>
  );
}

