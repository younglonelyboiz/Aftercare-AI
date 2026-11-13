import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.response.use(response => response, error => {
  if (error.response?.status === 401 && !error.config?.url?.startsWith('/auth/')) {
    window.dispatchEvent(new Event('aftercare-session-expired'));
  }
  return Promise.reject(error);
});

export const getCurrentUser = () => apiClient.get('/auth/me').then(r => r.data);
export const getDemoAccounts = () => apiClient.get('/auth/demo-accounts').then(r => r.data);
export const login = (username, password) => apiClient.post('/auth/login', { username, password }).then(r => r.data);
export const demoLogin = userId => apiClient.post('/auth/demo-login', { user_id: userId }).then(r => r.data);
export const logout = () => apiClient.post('/auth/logout');
export const getUsers = () => apiClient.get('/admin/users').then(r => r.data);
export const createUser = data => apiClient.post('/admin/users', data).then(r => r.data);
export const updateUser = (id, data) => apiClient.patch(`/admin/users/${id}`, data).then(r => r.data);
export const updateAssignments = (id, patientIds) => apiClient.put(`/admin/users/${id}/assignments`, { patient_ids: patientIds }).then(r => r.data);
export const getConversations = patientId => apiClient.get('/chat/conversations', { params: { patient_id: patientId } }).then(r => r.data);
export const createConversation = patientId => apiClient.post('/chat/conversations', { patient_id: patientId }).then(r => r.data);
export const getConversation = (id, before) => apiClient.get(`/chat/conversations/${id}`, { params: { before } }).then(r => r.data);
export const deleteConversation = id => apiClient.delete(`/chat/conversations/${id}`);
export const getMemory = patientId => apiClient.get('/chat/memory', { params: { patient_id: patientId } }).then(r => r.data);
export const deleteMemory = id => apiClient.delete(`/chat/memory/${id}`);
export const errorMessage = error => typeof error.response?.data?.detail === 'string'
  ? error.response.data.detail : 'Không thể thực hiện. Vui lòng thử lại.';

export const getPatients = async () => {
  const response = await apiClient.get('/patients/');
  return response.data;
};

export const getPatientDetail = async (patientId) => {
  const response = await apiClient.get(`/patients/${patientId}`);
  return response.data;
};

export const sendChatMessage = async (patientId, message, conversationId) => {
  const response = await apiClient.post('/chat/chat', {
    patient_id: patientId,
    message: message,
    conversation_id: conversationId || null,
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

// -------------------------------------------------------------
// ESCALATION & REAL-TIME ALERTS APIS
// -------------------------------------------------------------
export const getActiveAlertTickets = async () => {
  const response = await apiClient.get('/escalations/tickets/active');
  return response.data;
};

export const getAlertTicketsHistory = async () => {
  const response = await apiClient.get('/escalations/tickets/history');
  return response.data;
};

export const acknowledgeAlertTicket = async (ticketId, acknowledgedBy = 'Điều dưỡng trực ca') => {
  const response = await apiClient.post(`/escalations/tickets/${ticketId}/acknowledge`, {
    acknowledged_by: acknowledgedBy
  });
  return response.data;
};

export const resolveAlertTicket = async (ticketId, resolvedBy, resolutionNotes) => {
  const response = await apiClient.post(`/escalations/tickets/${ticketId}/resolve`, {
    resolved_by: resolvedBy,
    resolution_notes: resolutionNotes
  });
  return response.data;
};

export const confirmPatientSafety20m = async (patientId, notes = 'Bệnh nhân báo an toàn sau khi xịt thuốc.') => {
  const response = await apiClient.post(`/escalations/patients/${patientId}/safety-confirm-20m`, {
    patient_id: patientId,
    notes: notes
  });
  return response.data;
};

export const triggerNonResponseScan = async () => {
  const response = await apiClient.post('/escalations/scan-non-response');
  return response.data;
};


