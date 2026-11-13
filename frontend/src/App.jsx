import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import PatientSummaryCard from './components/PatientSummaryCard';
import DailyCheckInForm from './components/DailyCheckInForm';
import FloatingChatWidget from './components/ChatWidget/FloatingChatWidget';
import CareCalendar from './components/CareTracker/CareCalendar';
import CarePlanChecklist from './components/CareTracker/CarePlanChecklist';
import NurseCommandCenter from './components/Nurse/NurseCommandCenter';
import AdminPanel from './components/Auth/AdminPanel';
import AuthenticatedShell from './components/Layout/AuthenticatedShell';
import PatientDashboard from './components/Patient/PatientDashboard';
import {
  getPatients,
  getPatientDetail,
  getCarePlan,
  getCheckinHistory,
  getActiveReminders,
  actOnReminder,
  submitCheckin,
  resetDemoData
} from './services/api';

export default function App({ user, onLogout }) {
  const [currentPortal, setCurrentPortal] = useState(user.role === 'admin' ? 'admin' : user.role === 'nurse' ? 'nurse' : 'patient');
  const [patients, setPatients] = useState([]);
  const [selectedPatientId, setSelectedPatientId] = useState(user.patient_id || '');
  const [isResetting, setIsResetting] = useState(false);
  const [patientProfile, setPatientProfile] = useState(null);
  const [carePlan, setCarePlan] = useState(null);
  const [history, setHistory] = useState([]);
  const [reminders, setReminders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [patientLoadError, setPatientLoadError] = useState(null);

  // Check-in State
  const [pef, setPef] = useState(480);
  const [spo2, setSpo2] = useState(98);
  const [symptoms, setSymptoms] = useState({
    nightWaking: false,
    relieverUsed: false,
    activityLimited: false,
    dangerSign: false
  });
  const [medsTaken, setMedsTaken] = useState(true);

  // Chatbot state
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [initialAlertMessage, setInitialAlertMessage] = useState(null);

  const selectPatient = (pid) => {
    if (pid !== selectedPatientId) {
      setInitialAlertMessage(null);
      setIsChatOpen(false);
      setSelectedPatientId(pid);
    }
  };

  // 1. Load sample patients
  useEffect(() => {
    const fetchPatients = async () => {
      try {
        const data = await getPatients();
        setPatients(data);
        const initialId = user.patient_id || data[0]?.patient_id || '';
        setSelectedPatientId(initialId);
        if (!initialId) setLoading(false);
      } catch (err) {
        console.error('Lỗi tải danh sách bệnh nhân:', err);
        setLoading(false);
      }
    };
    fetchPatients();
  }, [user.patient_id]);

  // 2. Load detailed profile, Care Plan, Reminders & History when patient changes
  const loadPatientData = async (pid, isInitial = false) => {
    if (!pid) return;
    setPatientLoadError(null);
    if (isInitial || !patientProfile) {
      setLoading(true);
      setPatientProfile(null); setCarePlan(null); setHistory([]); setReminders([]);
    }
    try {
      const [detail, plan, hist, rems] = await Promise.allSettled([
        getPatientDetail(pid),
        getCarePlan(pid),
        getCheckinHistory(pid, 14),
        getActiveReminders(pid)
      ]);

      if (detail.status === 'fulfilled') {
        setPatientProfile(detail.value);
        if (detail.value.clinical_status && isInitial) {
          setPef(detail.value.clinical_status.personal_best_pef || 500);
          setSpo2(detail.value.clinical_status.baseline_spo2 || 98);
        }
      }

      if (plan.status === 'fulfilled') {
        setCarePlan(plan.value);
      } else if (isInitial) {
        setCarePlan(null);
      }

      if (hist.status === 'fulfilled') {
        setHistory(hist.value);
      }

      if (rems.status === 'fulfilled') {
        setReminders(rems.value);
      }

      if (detail.status === 'rejected' && hist.status === 'rejected') {
        setPatientLoadError('Không thể tải dữ liệu bệnh nhân. Vui lòng kiểm tra kết nối và thử lại.');
      }
    } catch (err) {
      console.error('Lỗi tải dữ liệu bệnh nhân:', err);
      setPatientLoadError('Không thể tải dữ liệu bệnh nhân. Vui lòng thử lại.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedPatientId) {
      loadPatientData(selectedPatientId, true);
    }
  }, [selectedPatientId]);

  // Calculate Action Zone
  const personalBest = carePlan?.personal_best_pef || patientProfile?.clinical_status?.personal_best_pef || 500;
  const pefRatio = (pef / personalBest) * 100;

  let currentZone = 'green';
  if (pefRatio < 60 || spo2 < 92 || symptoms.dangerSign) {
    currentZone = 'red';
  } else if (pefRatio < 80 || spo2 < 95 || symptoms.nightWaking || symptoms.relieverUsed || symptoms.activityLimited) {
    currentZone = 'yellow';
  }

  // Handle Proactive Trigger to open chat
  const handleOpenChatWithAlert = (targetZone) => {
    const zone = targetZone || currentZone;
    const name = patientProfile?.patient_info?.full_name || 'Bác';
    const reliever = patientProfile?.current_medications?.reliever_med || 'Thuốc cắt cơn Ventolin';

    if (zone === 'red' || zone === 'RED_ZONE') {
      setInitialAlertMessage({
        safety_status: 'RED_ZONE',
        text: `🚨 CẢNH BÁO CỜ ĐỎ CẤP CỨU: Chỉ số của ${name} (PEF ${pef} L/phút, SpO2 ${spo2}%) hoặc triệu chứng đang ở mức NGUY KỊCH.\n\n1. Hãy ngồi thẳng, hơi cúi người ra trước, tuyệt đối không nằm.\n2. Dùng ngay ${reliever}.\n3. Nhờ người thân gọi ngay Cấp cứu 115 hoặc đưa tới cơ sở y tế gần nhất!`
      });
      setIsChatOpen(true);
    } else if (zone === 'yellow' || zone === 'YELLOW_ZONE') {
      setInitialAlertMessage({
        safety_status: 'YELLOW_ZONE',
        text: `⚠️ CẢNH BÁO VÙNG VÀNG: Bệnh nhân ${name} đang có dấu hiệu hen bùng phát (PEF ${pef} L/phút = ${Math.round(pefRatio)}% mức tốt nhất).\n\nHãy xịt ngay ${reliever} theo phác đồ Vùng Vàng. Nghỉ ngơi và theo dõi lại nhịp thở sau 20-30 phút.`
      });
      setIsChatOpen(true);
    } else {
      setIsChatOpen(true);
    }
  };

  // Submit check-in to PostgreSQL backend
  const handleSubmitCheckin = async () => {
    try {
      const res = await submitCheckin({
        patient_id: selectedPatientId,
        pef_value: pef,
        spo2_value: spo2,
        symptoms: symptoms,
        meds_taken: { controller: medsTaken },
        reliever_puffs: symptoms.relieverUsed ? 2 : 0,
        notes: `Check-in ngày ${new Date().toLocaleDateString('vi-VN')}`
      });

      // Reload history
      loadPatientData(selectedPatientId);

      if (res.action_zone === 'RED') {
        handleOpenChatWithAlert('red');
      } else if (res.action_zone === 'YELLOW') {
        handleOpenChatWithAlert('yellow');
      } else {
        alert('✓ Đã lưu Check-in vào cơ sở dữ liệu! VÙNG XANH AN TOÀN: Kiểm soát hen rất tốt.');
      }
    } catch (err) {
      alert('Lỗi lưu check-in: ' + err.message);
    }
  };

  // Reminder Actions
  const handleAcknowledgeReminder = async (remId) => {
    try {
      await actOnReminder(remId, 'ACKNOWLEDGE');
      setReminders(prev => prev.filter(r => r.id !== remId));
      alert('✓ Đã ghi nhận: Bạn đã thực hiện xịt thuốc / đo PEF thành công!');
    } catch (err) {
      alert('Lỗi thao tác nhắc nhở: ' + err.message);
    }
  };

  const handleSnoozeReminder = async (remId) => {
    try {
      await actOnReminder(remId, 'SNOOZE');
      setReminders(prev => prev.filter(r => r.id !== remId));
      alert('⏱️ Đã hoãn: Hệ thống sẽ nhắc lại bạn sau 15 phút nữa.');
    } catch (err) {
      alert('Lỗi: ' + err.message);
    }
  };

  // Reset Demo Data cho cả 3 bệnh nhân
  const handleResetDemo = async () => {
    if (!window.confirm('Khôi phục lại dữ liệu mẫu ban đầu cho cả 3 bệnh nhân để trình diễn demo?')) {
      return;
    }
    setIsResetting(true);
    try {
      const res = await resetDemoData();
      alert('✓ ' + (res.message || 'Đã reset dữ liệu demo thành công!'));
      await loadPatientData(selectedPatientId);
    } catch (err) {
      alert('Lỗi khi reset demo: ' + (err.response?.data?.detail || err.message));
    } finally {
      setIsResetting(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', color: 'var(--text-secondary)' }}>
        Đang khởi động hệ thống Aftercare-AI...
      </div>
    );
  }

  const isPatientPortal =
    currentPortal === 'patient' &&
    Boolean(selectedPatientId) &&
    !(currentPortal === 'admin' && user.role === 'admin');

  return (
    <AuthenticatedShell currentPortal={currentPortal}>
      {/* 1. Header & Switcher (Patient Portal hosts its own unified Wellness sidebar + topbar) */}
      {!isPatientPortal && (
        <Header
          user={user}
          onLogout={onLogout}
          patients={patients}
          selectedPatientId={selectedPatientId}
          onSelectPatient={selectPatient}
          currentPortal={currentPortal}
          onSwitchPortal={setCurrentPortal}
          onResetDemo={handleResetDemo}
          isResetting={isResetting}
        />
      )}

      {/* 2. Conditional Portal Rendering */}
      {currentPortal === 'admin' && user.role === 'admin' ? <AdminPanel user={user} patients={patients} /> : !selectedPatientId ? <p>Chưa có bệnh nhân trong phạm vi truy cập. Vui lòng liên hệ quản trị viên để được phân công.</p> : currentPortal === 'nurse' && user.role !== 'patient' ? (
        /* PORTAL ĐIỀU DƯỠNG (CLINICAL COMMAND CENTER) */
        <main className="nurse-portal-wrap">
          <NurseCommandCenter
            patients={patients}
            selectedPatientId={selectedPatientId}
            onSelectPatientId={selectPatient}
          />
        </main>
      ) : (
        /* PORTAL BỆNH NHÂN (PATIENT WELLNESS & CHECKIN) */
        <PatientDashboard
          profile={patientProfile}
          history={history}
          carePlan={carePlan}
          checkinProps={{
            patientId: selectedPatientId,
            personalBestPef: personalBest,
            actionPlan: patientProfile?.action_plan_rules,
            pef, setPef, spo2, setSpo2, symptoms, setSymptoms, medsTaken, setMedsTaken,
            currentZone, onOpenChatWithAlert: handleOpenChatWithAlert, onSubmitCheckin: handleSubmitCheckin,
          }}
          onOpenChat={() => { setInitialAlertMessage(null); setIsChatOpen(true); }}
          user={user}
          patients={patients}
          selectedPatientId={selectedPatientId}
          onSelectPatient={selectPatient}
          currentPortal={currentPortal}
          onSwitchPortal={setCurrentPortal}
          onResetDemo={handleResetDemo}
          isResetting={isResetting}
          onLogout={onLogout}
          reminders={reminders}
          onAcknowledgeReminder={handleAcknowledgeReminder}
          onSnoozeReminder={handleSnoozeReminder}
          loadError={patientLoadError}
          onRetryLoad={() => loadPatientData(selectedPatientId, true)}
        />
      )}

      {/* 3. Floating Popup Chatbot Widget */}
      {selectedPatientId && <FloatingChatWidget
        key={`${user.id}:${selectedPatientId}`}
        patientId={selectedPatientId}
        patientName={patientProfile?.patient_info?.full_name}
        isOpen={isChatOpen}
        setIsOpen={setIsChatOpen}
        initialAlertMessage={initialAlertMessage}
        patientLauncher={isPatientPortal}
      />}
    </AuthenticatedShell>
  );
}

