import React, { useState, useEffect, useRef } from 'react';
import { MessageSquare, X, Send, ShieldAlert, BookOpen, AlertTriangle, ExternalLink, Maximize2, Minimize2, FileText } from 'lucide-react';
import { sendChatMessage, getDocumentPdfUrl } from '../../services/api';
import PdfViewerModal from './PdfViewerModal';

export default function FloatingChatWidget({
  patientId,
  patientName,
  isOpen,
  setIsOpen,
  initialAlertMessage
}) {
  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: 'bot',
      text: `Xin chào ${patientName || 'bác/cô/chú'}. Cháu là Trợ lý AI Chăm sóc Sau Xuất Viện Hen Phế Quản. Mọi tư vấn đều được trích dẫn từ phác đồ Bộ Y Tế & GINA 2023. Hôm nay hô hấp của mình thế nào ạ?`,
      safety_status: 'NORMAL',
      citations: []
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [activePdfModal, setActivePdfModal] = useState({
    isOpen: false,
    documentTag: '',
    documentName: '',
    pdfPage: 1
  });
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isOpen]);

  // Helper function to format concise citation labels
  const getConciseCitationLabel = (c) => {
    const isBYT = c.document_tag?.includes('byt') || c.citation?.includes('1851');
    const sourceLabel = isBYT ? 'BYT QĐ 1851' : 'GINA 2023';
    const pageNum = c.pdf_page || c.page_index || 1;
    return `${sourceLabel} • Tr. ${pageNum}`;
  };

  const handleOpenPdf = (c) => {
    setActivePdfModal({
      isOpen: true,
      documentTag: c.document_tag || (c.citation?.includes('1851') ? 'byt_1851' : 'gina_2023'),
      documentName: c.document_name || (c.citation?.includes('1851') ? 'Bộ Y Tế - QĐ 1851/QĐ-BYT (Hen Phế Quản Người Lớn)' : 'GINA 2023 - Hướng Dẫn Chiến Lược Hen Toàn Cầu'),
      pdfPage: c.pdf_page || 1
    });
  };

  // Handle proactive alert triggered from Check-in
  useEffect(() => {
    if (initialAlertMessage) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now(),
          sender: 'bot',
          text: initialAlertMessage.text,
          safety_status: initialAlertMessage.safety_status,
          citations: []
        }
      ]);
      setIsOpen(true);
    }
  }, [initialAlertMessage, setIsOpen]);

  const handleSend = async (textToSend) => {
    const query = textToSend || inputText;
    if (!query.trim() || isLoading) return;

    const userMsg = {
      id: Date.now(),
      sender: 'user',
      text: query
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText('');
    setIsLoading(true);

    try {
      const data = await sendChatMessage(patientId, query);
      const botMsg = {
        id: Date.now() + 1,
        sender: 'bot',
        text: data.response,
        safety_status: data.safety_status,
        citations: data.citations || []
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          sender: 'bot',
          text: 'Xin lỗi, hiện tại hệ thống chưa kết nối được tới máy chủ bác sĩ AI. Vui lòng thử lại sau giây lát hoặc liên hệ số cấp cứu nếu nguy hiểm.',
          safety_status: 'NORMAL',
          citations: []
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const quickQuestions = [
    'Cách xịt thuốc cắt cơn đúng kỹ thuật?',
    'Tôi cần kiêng các loại thức ăn nào?',
    'Khi nào tôi cần đi tái khám?'
  ];

  return (
    <>
      {/* Floating Action Button */}
      <button
        className={`chat-fab ${initialAlertMessage?.safety_status === 'RED_ZONE' ? 'pulse-red' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Mở trợ lý AI"
      >
        <MessageSquare size={20} />
        <span>Trợ lý Hen AI</span>
      </button>

      {/* Pop-up Window */}
      {isOpen && (
        <div className={`chat-popup ${isExpanded ? 'expanded' : ''}`}>
          <div className="chat-popup-header">
            <div>
              <div className="chat-header-title">Trợ Lý Hen Phế Quản Aftercare-AI</div>
              <div className="chat-header-sub">Tư vấn cá nhân hóa cho {patientName}</div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <button
                className="close-chat-btn"
                onClick={() => setIsExpanded(!isExpanded)}
                aria-label={isExpanded ? 'Thu nhỏ cửa sổ' : 'Phóng to cửa sổ'}
                title={isExpanded ? 'Thu nhỏ cửa sổ' : 'Phóng to cửa sổ'}
              >
                {isExpanded ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
              </button>
              <button
                className="close-chat-btn"
                onClick={() => setIsOpen(false)}
                aria-label="Đóng chat"
                title="Đóng chat"
              >
                <X size={20} />
              </button>
            </div>
          </div>

          <div className="chat-messages-container">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`chat-bubble-wrap ${m.sender} ${m.safety_status || ''}`}
              >
                {m.sender === 'bot' && m.safety_status && (
                  <span className={`safety-pill ${m.safety_status}`}>
                    {m.safety_status === 'RED_ZONE' && <ShieldAlert size={12} />}
                    {m.safety_status === 'YELLOW_ZONE' && <AlertTriangle size={12} />}
                    {m.safety_status === 'RED_ZONE' ? 'CỜ ĐỎ CẤP CỨU' : (m.safety_status === 'YELLOW_ZONE' ? 'CẢNH BÁO HEN VÀNG' : 'TƯ VẤN Y KHOA')}
                  </span>
                )}
                <div className="chat-bubble" style={{ whiteSpace: 'pre-line' }}>
                  {m.text}
                </div>

                {/* Grounding Citations */}
                {m.citations && m.citations.length > 0 && (
                  <div className="citations-box">
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4 }}>
                      <BookOpen size={12} /> Căn cứ đối chiếu y khoa (Bấm xem tài liệu):
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {m.citations.map((c) => (
                        <button
                          key={c.chunk_id}
                          type="button"
                          onClick={() => handleOpenPdf(c)}
                          className="citation-tag compact-badge"
                          title={`Xem tài liệu đối chứng: ${c.section_title || c.document_name || 'Phác đồ'}`}
                        >
                          <FileText size={11} />
                          <span>{getConciseCitationLabel(c)}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
            {isLoading && (
              <div className="chat-bubble-wrap bot">
                <div className="chat-bubble" style={{ color: 'var(--text-muted)' }}>
                  Đang tra cứu kho dữ liệu Bộ Y Tế & GINA...
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Prompts */}
          <div className="quick-prompts-bar">
            {quickQuestions.map((q, idx) => (
              <button
                key={idx}
                className="quick-prompt-chip"
                onClick={() => handleSend(q)}
                disabled={isLoading}
              >
                {q}
              </button>
            ))}
          </div>

          {/* Input Area */}
          <div className="chat-input-area">
            <input
              type="text"
              className="chat-input-field"
              placeholder="Nhập câu hỏi hoặc triệu chứng của bạn..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              disabled={isLoading}
            />
            <button
              className="chat-submit-btn"
              onClick={() => handleSend()}
              disabled={isLoading || !inputText.trim()}
              aria-label="Gửi tin nhắn"
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Embedded PDF Viewer Modal */}
      <PdfViewerModal
        isOpen={activePdfModal.isOpen}
        onClose={() => setActivePdfModal((prev) => ({ ...prev, isOpen: false }))}
        documentTag={activePdfModal.documentTag}
        documentName={activePdfModal.documentName}
        pdfPage={activePdfModal.pdfPage}
      />
    </>
  );
}
