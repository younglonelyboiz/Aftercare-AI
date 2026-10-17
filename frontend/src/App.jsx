import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import PatientSummaryCard from './components/PatientSummaryCard';
import DailyCheckInForm from './components/DailyCheckInForm';
import FloatingChatWidget from './components/ChatWidget/FloatingChatWidget';
import { getPatients, getPatientDetail } from './services/api';

export default function App() {
  const [patients, setPatients] = useState([]);
  const [selectedPatientId, setSelectedPatientId] = useState('');
  const [patientProfile, setPatientProfile] = useState(null);
  const [loading, setLoading] = useState(true);

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

  // 1. Load sample patients
  useEffect(() => {
    const fetchPatients = async () => {
      try {
        const data = await getPatients();
        setPatients(data);
        if (data.length > 0) {
          setSelectedPatientId(data[0].patient_id);
        }
      } catch (err) {
        console.error('Lỗi tải danh sách bệnh nhân:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchPatients();
  }, []);

  // 2. Load detailed profile when patient changes
  useEffect(() => {
    if (!selectedPatientId) return;
    const fetchDetail = async () => {
      try {
        const detail = await getPatientDetail(selectedPatientId);
        setPatientProfile(detail);
        // Reset checkin to near normal
        if (detail.clinical_status) {
          setPef(detail.clinical_status.personal_best_pef || 500);
          setSpo2(detail.clinical_status.baseline_spo2 || 98);
        }
        setSymptoms({
          nightWaking: false,
          relieverUsed: false,
          activityLimited: false,
          dangerSign: false
        });
        setMedsTaken(true);
      } catch (err) {
        console.error('Lỗi tải chi tiết bệnh nhân:', err);
      }
    };
    fetchDetail();
  }, [selectedPatientId]);

  // Calculate Action Zone
  const personalBest = patientProfile?.clinical_status?.personal_best_pef || 500;
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
    const reliever = patientProfile?.current_medications?.reliever_med || 'Thuốc cắt cơn';

    if (zone === 'red' || zone === 'RED_ZONE') {
      setInitialAlertMessage({
        safety_status: 'RED_ZONE',
        text: `🚨 CẢNH BÁO CỜ ĐỎ CẤP CỨU: Chỉ số của ${name} (PEF ${pef} L/phút, SpO2 ${spo2}%) hoặc triệu chứng đang ở mức NGUY KỊCH.\n\n1. Hãy ngồi thẳng, hơi cúi người ra trước, tuyệt đối không nằm.\n2. Dùng ngay ${reliever}.\n3. Nhờ người thân gọi ngay Cấp cứu 115 hoặc đưa tới cơ sở y tế gần nhất!`
      });
    } else if (zone === 'yellow' || zone === 'YELLOW_ZONE') {
      setInitialAlertMessage({
        safety_status: 'YELLOW_ZONE',
        text: `⚠️ CẢNH BÁO VÙNG VÀNG: Bệnh nhân ${name} đang có dấu hiệu hen bùng phát (PEF ${pef} L/phút = ${Math.round(pefRatio)}% mức tốt nhất).\n\nHãy xịt ngay ${reliever} theo phác đồ Vùng Vàng. Nghỉ ngơi và theo dõi lại nhịp thở sau 20-30 phút.`
      });
    } else {
      setIsChatOpen(true);
    }
  };

  const handleSubmitCheckin = () => {
    if (currentZone === 'red') {
      handleOpenChatWithAlert('red');
    } else if (currentZone === 'yellow') {
      handleOpenChatWithAlert('yellow');
    } else {
      alert('Đã lưu check-in hôm nay: Chỉ số hô hấp của bạn rất tốt (Vùng Xanh). Tiếp tục duy trì nhé!');
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', color: 'var(--text-secondary)' }}>
        Đang tải hệ thống Aftercare-AI...
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* 1. Header & Switcher */}
      <Header
        patients={patients}
        selectedPatientId={selectedPatientId}
        onSelectPatient={setSelectedPatientId}
      />

      {/* 2. Main Dashboard Grid */}
      <main className="dashboard-grid">
        {/* Left Column: Patient Profile */}
        <PatientSummaryCard profile={patientProfile} />

        {/* Right Column: Daily Health Check-in (Option A) */}
        <DailyCheckInForm
          personalBestPef={personalBest}
          actionPlan={patientProfile?.action_plan_rules}
          pef={pef}
          setPef={setPef}
          spo2={spo2}
          setSpo2={setSpo2}
          symptoms={symptoms}
          setSymptoms={setSymptoms}
          medsTaken={medsTaken}
          setMedsTaken={setMedsTaken}
          currentZone={currentZone}
          onOpenChatWithAlert={handleOpenChatWithAlert}
          onSubmitCheckin={handleSubmitCheckin}
        />
      </main>

      {/* 3. Floating Popup Chatbot Widget */}
      <FloatingChatWidget
        patientId={selectedPatientId}
        patientName={patientProfile?.patient_info?.full_name}
        isOpen={isChatOpen}
        setIsOpen={setIsChatOpen}
        initialAlertMessage={initialAlertMessage}
      />
    </div>
  );
}
