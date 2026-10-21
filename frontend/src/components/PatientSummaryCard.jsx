import React from 'react';
import { FileText, Wind, HeartPulse, Pill, Calendar } from 'lucide-react';

export default function PatientSummaryCard({ profile }) {
  if (!profile) return null;

  const { patient_info, clinical_status, current_medications, follow_up } = profile;

  return (
    <div className="card-panel">
      <div className="card-header-row">
        <div className="card-title">
          <FileText size={20} color="var(--primary)" />
          Hồ sơ điều trị xuất viện
        </div>
        <span className="patient-id-badge">{patient_info.patient_id}</span>
      </div>

      <div className="patient-profile-header">
        <div>
          <div className="patient-name">{patient_info.full_name}</div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            {patient_info.age} tuổi • Giới tính: {patient_info.gender} • Xuất viện: {patient_info.discharge_date}
          </div>
        </div>
      </div>

      <div className="vital-stats-grid">
        <div className="stat-box">
          <div className="stat-label">
            <Wind size={14} style={{ display: 'inline', marginRight: 4 }} />
            PEF Tốt Nhất Cá Nhân
          </div>
          <div className="stat-value">
            {clinical_status.personal_best_pef} <span className="stat-unit">L/phút</span>
          </div>
        </div>

        <div className="stat-box">
          <div className="stat-label">
            <HeartPulse size={14} style={{ display: 'inline', marginRight: 4 }} />
            SpO2 Nền Tảng
          </div>
          <div className="stat-value">
            {clinical_status.baseline_spo2} <span className="stat-unit">%</span>
          </div>
        </div>
      </div>

      <div className="diagnosis-box">
        <strong>Chẩn đoán:</strong> {clinical_status.diagnosis}
        <br />
        <strong>Dị nguyên cần tránh:</strong> {clinical_status.known_triggers?.join(', ') || 'Chưa ghi nhận'}
      </div>

      <div className="meds-list">
        <div className="med-item">
          <div className="med-title">
            <Pill size={16} color="#0284c7" /> Thuốc duy trì hàng ngày:
          </div>
          <div className="med-desc">{current_medications.controller_med}</div>
        </div>
        <div className="med-item">
          <div className="med-title">
            <Pill size={16} color="#d97706" /> Thuốc cắt cơn khẩn cấp:
          </div>
          <div className="med-desc">{current_medications.reliever_med}</div>
        </div>
      </div>

      <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', borderTop: '1px solid var(--border-subtle)', paddingTop: 12 }}>
        <Calendar size={14} style={{ display: 'inline', marginRight: 4 }} />
        Tái khám: <strong>{follow_up?.next_appointment}</strong> tại {follow_up?.hospital}
      </div>
    </div>
  );
}
