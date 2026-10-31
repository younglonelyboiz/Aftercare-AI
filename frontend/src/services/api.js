import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getPatients = async () => {
  const response = await apiClient.get('/patients/');
  return response.data;
};

export const getPatientDetail = async (patientId) => {
  const response = await apiClient.get(`/patients/${patientId}`);
  return response.data;
};

export const sendChatMessage = async (patientId, message) => {
  const response = await apiClient.post('/chat/chat', {
    patient_id: patientId,
    message: message,
  });
  return response.data;
};

export const getDocumentPdfUrl = (documentTag, pdfPage) => {
  if (!documentTag) return null;
  const pageAnchor = pdfPage ? `#page=${pdfPage}` : '';
  return `${API_BASE_URL}/documents/view/${documentTag}${pageAnchor}`;
};

// -------------------------------------------------------------
// CARE PLAN, NHẮC THUỐC & CHECK-IN TRACKER APIS
// -------------------------------------------------------------
export const getCarePlan = async (patientId) => {
  const response = await apiClient.get(`/care-tracker/care-plans/${patientId}`);
  return response.data;
};

export const updateCarePlan = async (carePlanData) => {
  const response = await apiClient.post('/care-tracker/care-plans/', carePlanData);
  return response.data;
};

export const submitCheckin = async (checkinData) => {
  const response = await apiClient.post('/care-tracker/checkin/', checkinData);
  return response.data;
};

export const getCheckinHistory = async (patientId, days = 30) => {
  const response = await apiClient.get(`/care-tracker/checkin/history/${patientId}?days=${days}`);
  return response.data;
};

export const getActiveReminders = async (patientId) => {
  const response = await apiClient.get(`/care-tracker/reminders/active/${patientId}`);
  return response.data;
};

export const actOnReminder = async (reminderId, action) => {
  const response = await apiClient.post(`/care-tracker/reminders/${reminderId}/action`, { action });
  return response.data;
};

export const getNurseOverview = async () => {
  const response = await apiClient.get('/care-tracker/nurse/patients-overview');
  return response.data;
};

// -------------------------------------------------------------
// SYMPTOM SCREENER ENGINE EVALUATION
// -------------------------------------------------------------
export const evaluateScreener = async (screenerInput) => {
  const response = await apiClient.post('/screener/evaluate', screenerInput);
  return response.data;
};

// -------------------------------------------------------------
// RESET DEMO DATA
// -------------------------------------------------------------
export const resetDemoData = async () => {
  const response = await apiClient.post('/care-tracker/reset-demo');
  return response.data;
};

