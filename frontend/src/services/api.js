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
