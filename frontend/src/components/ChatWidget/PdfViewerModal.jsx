import React from 'react';
import { X, ExternalLink, FileText } from 'lucide-react';

export default function PdfViewerModal({ isOpen, onClose, documentTag, documentName, pdfPage }) {
  if (!isOpen) return null;

  const pdfUrl = `http://localhost:8000/api/v1/documents/view/${documentTag}#page=${pdfPage || 1}`;

  return (
    <div className="pdf-modal-overlay" onClick={onClose}>
      <div className="pdf-modal-container" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="pdf-modal-header">
          <div className="pdf-modal-title">
            <FileText size={18} color="#0284c7" />
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>
                {documentName || 'Tài liệu hướng dẫn lâm sàng'}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Đang mở tại <strong>Trang {pdfPage || 1}</strong> (Nguồn: Bộ Y Tế / GINA)
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <a
              href={pdfUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="open-external-btn"
              title="Mở tài liệu trong tab mới"
            >
              <span>Mở tab mới</span>
              <ExternalLink size={14} />
            </a>
            <button className="close-chat-btn" onClick={onClose} aria-label="Đóng">
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Modal Body: Full Native PDF Viewer */}
        <div className="pdf-modal-body">
          <div className="pdf-iframe-wrap">
            <iframe
              src={pdfUrl}
              title="PDF Document Viewer"
              className="pdf-iframe"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
