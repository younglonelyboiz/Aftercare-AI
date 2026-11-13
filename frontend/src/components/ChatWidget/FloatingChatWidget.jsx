import React, { useState, useEffect, useRef } from 'react';
import { MessageSquare, X, Send, ShieldAlert, BookOpen, AlertTriangle, Maximize2, Minimize2, FileText, PhoneCall, Plus, Trash2 } from 'lucide-react';
import { sendChatMessage, getConversations, getConversation, deleteConversation, getMemory, deleteMemory, errorMessage } from '../../services/api';
import PdfViewerModal from './PdfViewerModal';

export default function FloatingChatWidget({
  patientId,
  patientName,
  isOpen,
  setIsOpen,
  initialAlertMessage,
  hideFab = false,
  patientLauncher = false,
}) {
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [hasOlder, setHasOlder] = useState(false);
  const [error, setError] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);
  const [showMemory, setShowMemory] = useState(false);
  const [memory, setMemory] = useState([]);
  const [activePdfModal, setActivePdfModal] = useState({ isOpen: false, documentTag: '', documentName: '', pdfPage: 1 });
  const messagesEndRef = useRef(null);
  const busyRef = useRef(false);
  const inputRef = useRef(null);
  const closeBtnRef = useRef(null);
  const lastOpenerRef = useRef(null);
  const wasOpenRef = useRef(isOpen);
  const asMessage = m => ({ id: m.id, sender: m.role === 'user' ? 'user' : 'bot', text: m.content, safety_status: m.safety_status, citations: m.citations || [], sequence: m.sequence });

  useEffect(() => {
    let active = true;
    if (!patientId) return;
    getConversations(patientId).then(async list => {
      if (!active) return;
      setConversations(list);
      if (list.length) {
        const detail = await getConversation(list[0].id);
        if (!active) return;
        setConversationId(detail.id); setMessages(detail.messages.map(asMessage)); setHasOlder(detail.has_older);
      }
    }).catch(err => { if (active) setError(errorMessage(err)); }).finally(() => { if (active) setHistoryLoading(false); });
    return () => { active = false; };
  }, [patientId]);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, isOpen]);
  useEffect(() => { if (initialAlertMessage) setIsOpen(true); }, [initialAlertMessage, setIsOpen]);
  useEffect(() => {
    const wasOpen = wasOpenRef.current;
    wasOpenRef.current = isOpen;
    if (!wasOpen && isOpen) {
      const active = document.activeElement;
      if (active instanceof HTMLElement && !active.closest('.chat-popup')) {
        lastOpenerRef.current = active;
      }
      requestAnimationFrame(() => {
        if (inputRef.current && !inputRef.current.disabled) {
          inputRef.current.focus();
        } else {
          closeBtnRef.current?.focus();
        }
      });
    } else if (wasOpen && !isOpen) {
      const opener = lastOpenerRef.current;
      lastOpenerRef.current = null;
      if (opener && opener.isConnected && typeof opener.focus === 'function') {
        requestAnimationFrame(() => opener.focus());
      }
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return undefined;
    const onEscape = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        setIsOpen(false);
      }
    };
    document.addEventListener('keydown', onEscape);
    return () => document.removeEventListener('keydown', onEscape);
  }, [isOpen, setIsOpen]);

  const selectConversation = async id => {
    if (busyRef.current) return;
    setHistoryLoading(true); setError(''); setShowMemory(false);
    try {
      if (!id) { setConversationId(null); setMessages([]); setHasOlder(false); return; }
      const detail = await getConversation(id);
      setConversationId(id); setMessages(detail.messages.map(asMessage)); setHasOlder(detail.has_older);
    } catch (err) { setError(errorMessage(err)); }
    finally { setHistoryLoading(false); }
  };
  const olderMessages = async () => {
    setHistoryLoading(true);
    try {
      const detail = await getConversation(conversationId, messages[0]?.sequence);
      setMessages(prev => [...detail.messages.map(asMessage), ...prev]); setHasOlder(detail.has_older);
    } catch (err) { setError(errorMessage(err)); }
    finally { setHistoryLoading(false); }
  };
  const removeConversation = async () => {
    if (!conversationId || !window.confirm('Xóa cuộc trò chuyện này và các ghi nhớ phát sinh từ cuộc trò chuyện?')) return;
    setHistoryLoading(true);
    try {
      await deleteConversation(conversationId);
      setConversations(prev => prev.filter(c => c.id !== conversationId));
      setConversationId(null); setMessages([]); setHasOlder(false); setShowMemory(false);
    } catch (err) { setError(errorMessage(err)); }
    finally { setHistoryLoading(false); }
  };
  const toggleMemory = async () => {
    if (showMemory) { setShowMemory(false); return; }
    try { setMemory(await getMemory(patientId)); setShowMemory(true); }
    catch (err) { setError(errorMessage(err)); }
  };
  const forget = async id => {
    try { await deleteMemory(id); setMemory(prev => prev.filter(n => n.id !== id)); }
    catch (err) { setError(errorMessage(err)); }
  };
  const getConciseCitationLabel = c => `${c.document_tag?.includes('byt') || c.citation?.includes('1851') ? 'BYT QĐ 1851' : 'GINA 2023'} • Tr. ${c.pdf_page || 1}`;
  const handleOpenPdf = c => setActivePdfModal({ isOpen: true, documentTag: c.document_tag || (c.citation?.includes('1851') ? 'byt_1851' : 'gina_2023'), documentName: c.document_name || c.citation || 'Tài liệu y khoa', pdfPage: c.pdf_page || 1 });

  const handleSend = async textToSend => {
    const query = (textToSend || inputText).trim();
    if (!query || busyRef.current || historyLoading || !patientId) return;
    busyRef.current = true; setIsLoading(true); setError(''); setInputText('');
    const id = crypto.randomUUID();
    setMessages(prev => [...prev, { id, sender: 'user', text: query }]);
    try {
      const data = await sendChatMessage(patientId, query, conversationId);
      setConversationId(data.conversation_id);
      setMessages(prev => [...prev, { id: data.message_id, sender: 'bot', text: data.response, safety_status: data.safety_status, citations: data.citations || [] }]);
      if (showMemory) getMemory(patientId).then(setMemory).catch(() => {});
      getConversations(patientId).then(setConversations).catch(() => {});
    } catch (err) {
      setMessages(prev => prev.filter(m => m.id !== id)); setInputText(query); setError(errorMessage(err));
    } finally { busyRef.current = false; setIsLoading(false); }
  };

  const quickQuestions = [
    'Cách xịt thuốc cắt cơn đúng kỹ thuật?',
    'Tôi cần kiêng các loại thức ăn nào?',
    'Khi nào tôi cần đi tái khám?'
  ];

  return (
    <>
      {/* Floating Action Button (hidden on Patient Wellness portal where HOPI has dedicated triggers) */}
      {!hideFab && (
        <button
          type="button"
          className={`chat-fab ${patientLauncher ? 'hopi-patient-launcher' : ''} ${initialAlertMessage?.safety_status === 'RED_ZONE' ? 'pulse-red' : ''}`}
          onClick={() => setIsOpen(!isOpen)}
          aria-label={isOpen ? "Đóng trò chuyện HOPI" : "Mở trò chuyện HOPI"}
          aria-expanded={isOpen}
        >
          {patientLauncher ? <img src="/pictures/hopi-mascot-clean.png" width={48} height={48} alt="" /> : <><MessageSquare size={20} /><span>Trợ lý Hen AI</span></>}
        </button>
      )}

      {/* Pop-up Window */}
      {isOpen && (
        <div
          className={`chat-popup ${isExpanded ? 'expanded' : ''}`}
          role="dialog"
          aria-modal="false"
          aria-label="Trợ Lý Hen Phế Quản Aftercare-AI"
          onKeyDown={(e) => {
            if (e.key === 'Escape') {
              e.stopPropagation();
              setIsOpen(false);
            }
          }}
        >
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
                ref={closeBtnRef}
                type="button"
                className="close-chat-btn"
                onClick={() => setIsOpen(false)}
                aria-label="Đóng chat"
                title="Đóng chat"
              >
                <X size={20} />
              </button>
            </div>
          </div>

          <div className="chat-history-toolbar">
            <select aria-label="Lịch sử trò chuyện" value={conversationId || ''} onChange={e => selectConversation(e.target.value)} disabled={isLoading || historyLoading}>
              <option value="">Cuộc trò chuyện mới</option>
              {conversations.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
            </select>
            <button onClick={() => selectConversation('')} disabled={isLoading || historyLoading} aria-label="Tạo cuộc trò chuyện mới" title="Cuộc trò chuyện mới"><Plus size={17} /></button>
            <button onClick={toggleMemory} disabled={isLoading || historyLoading}>Ghi nhớ</button>
            <button onClick={removeConversation} disabled={!conversationId || isLoading || historyLoading} aria-label="Xóa cuộc trò chuyện"><Trash2 size={16} /></button>
          </div>
          {error && <p className="chat-memory-error" role="alert">{error}</p>}
          {showMemory && <section className="chat-memory-panel" aria-label="Ghi nhớ dài hạn">
            <strong>Những điều bạn đã chia sẻ</strong>
            <p>Lời kể chưa xác minh, không thay thế hồ sơ điều trị. Xóa ghi nhớ không xóa tin nhắn gốc; muốn xóa cả lịch sử, hãy xóa cuộc trò chuyện.</p>
            {!memory.length && <p>Chưa có ghi nhớ.</p>}
            {memory.map(note => <article key={note.id}><p>{note.content}</p><small>{new Date(note.created_at + 'Z').toLocaleString('vi-VN')}</small><button onClick={() => forget(note.id)}>Xóa ghi nhớ</button></article>)}
          </section>}
          <div className="chat-messages-container">
            {historyLoading && <p role="status">Đang tải lịch sử…</p>}
            {hasOlder && <button className="chat-load-older" onClick={olderMessages} disabled={historyLoading}>Xem tin nhắn cũ hơn</button>}
            {!messages.length && !historyLoading && <div className="chat-bubble">Xin chào {patientName || 'bạn'}. Bạn cần hỗ trợ điều gì hôm nay? Các cuộc trò chuyện được lưu để bạn có thể tiếp tục sau.</div>}
            {initialAlertMessage && <div className={`chat-bubble-wrap bot ${initialAlertMessage.safety_status}`}><div className="chat-bubble">{initialAlertMessage.text}</div></div>}

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
                disabled={isLoading || historyLoading}
              >
                {q}
              </button>
            ))}
          </div>

          {/* Emergency Fast-Dial Bar (Kích hoạt khi gặp cờ đỏ RED_ZONE) */}
          {messages.length > 0 && messages[messages.length - 1].safety_status === 'RED_ZONE' && (
            <div style={{
              padding: '8px 12px',
              backgroundColor: '#fee2e2',
              borderTop: '1px solid #f87171',
              borderBottom: '1px solid #f87171',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 8
            }}>
              <span style={{ fontSize: '0.8rem', color: '#991b1b', fontWeight: 600 }}>
                🚨 Triệu chứng nguy cấp! Vui lòng gọi cấp cứu:
              </span>
              <a
                href="tel:115"
                style={{
                  padding: '6px 12px',
                  backgroundColor: '#dc2626',
                  color: 'white',
                  borderRadius: 6,
                  textDecoration: 'none',
                  fontWeight: 700,
                  fontSize: '0.82rem',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6
                }}
              >
                <PhoneCall size={14} /> Gọi 115
              </a>
            </div>
          )}

          {/* Input Area */}
          <div className="chat-input-area">
            <input
              ref={inputRef}
              type="text"
              className="chat-input-field"
              placeholder="Nhập câu hỏi hoặc triệu chứng của bạn..."
              value={inputText}
              maxLength={6000}
              aria-label="Tin nhắn cho trợ lý"
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              disabled={isLoading || historyLoading}
            />
            <button
              className="chat-submit-btn"
              onClick={() => handleSend()}
              disabled={isLoading || historyLoading || !inputText.trim()}
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
