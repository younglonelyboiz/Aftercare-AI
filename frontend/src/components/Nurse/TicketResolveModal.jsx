import React, { useState } from 'react';
import { X, CheckCircle, ShieldAlert, Phone, UserCheck, FileText } from 'lucide-react';

export default function TicketResolveModal({ ticket, onClose, onResolve }) {
  const [nurseName, setNurseName] = useState('ĐD. Nguyễn Thu Hà (Kíp trực Hô Hấp)');
  const [actionCategory, setActionCategory] = useState('Đã gọi điện thoại trực tiếp cho bệnh nhân');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  if (!ticket) return null;

  const quickTemplates = [
    'Đã gọi điện cho bệnh nhân: Hướng dẫn xịt thêm 2 nhát Ventolin qua buồng đệm, tư thế ngồi cúi người. Nhịp thở đã dịu, SpO2 lên 95%.',
    'Đã liên hệ người nhà: Bệnh nhân khó thở nhiều, đã hướng dẫn gọi 115 và đang trên đường di chuyển tới Bệnh viện Phổi.',
    'Bệnh nhân xác nhận đã uống thuốc đầy đủ, do đi làm về trễ nên quên check-in. Đã đo lại PEF đạt Vùng Xanh an toàn.'
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    if (!notes.trim()) {
      setErrorMessage('Vui lòng nhập biên bản can thiệp lâm sàng chi tiết trước khi đóng vé.');
      return;
    }

    setSubmitting(true);
    try {
      const fullNotes = `[${actionCategory}] ${notes.trim()}`;
      await onResolve(ticket.id, nurseName, fullNotes);
      onClose();
    } catch (err) {
      setErrorMessage('Lỗi giải quyết vé: ' + err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop-escalation">
      <div className="modal-card-escalation">
        <div className="modal-header-escalation">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className="badge-p0-modal">
              <ShieldAlert size={20} />
            </span>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.15rem', color: '#0f172a', fontWeight: 600 }}>
                Biên Bản Xử Lý Cảnh Báo Lâm Sàng
              </h3>
              <span style={{ fontSize: '0.8rem', color: '#64748b' }}>
                Mã vé: <strong>{ticket.id}</strong> • Bệnh nhân: <strong style={{ color: '#0284c7' }}>{ticket.patient_name || ticket.patient_id}</strong>
              </span>
            </div>
          </div>
          <button className="btn-close-modal" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-body-escalation">
          {/* Thông tin lâm sàng tóm tắt */}
          <div className="clinical-alert-summary">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#991b1b' }}>
                LÝ DO KÍCH HOẠT LEO THANG:
              </span>
              <span style={{ fontSize: '0.78rem', color: '#64748b' }}>
                {new Date(ticket.created_at).toLocaleTimeString('vi-VN')}
              </span>
            </div>
            <p style={{ margin: 0, fontSize: '0.88rem', color: '#7f1d1d', lineHeight: 1.4, fontWeight: 500 }}>
              {ticket.trigger_reason}
            </p>
          </div>

          <div className="form-group-esc">
            <label>Điều dưỡng / Bác sĩ trực phụ trách:</label>
            <input
              type="text"
              value={nurseName}
              onChange={(e) => setNurseName(e.target.value)}
              required
              className="input-esc"
            />
          </div>

          <div className="form-group-esc">
            <label>Hình thức can thiệp y tế:</label>
            <select
              value={actionCategory}
              onChange={(e) => setActionCategory(e.target.value)}
              className="input-esc"
            >
              <option value="Đã gọi điện thoại trực tiếp cho bệnh nhân">📞 Đã gọi điện thoại trực tiếp cho bệnh nhân</option>
              <option value="Đã liên hệ số điện thoại người nhà khẩn cấp">👨‍👩‍👧 Đã liên hệ số điện thoại người nhà khẩn cấp</option>
              <option value="Đã hướng dẫn sơ cứu xịt cắt cơn & theo dõi tiếp">💨 Đã hướng dẫn sơ cứu xịt cắt cơn & theo dõi tiếp</option>
              <option value="Đã kích hoạt điều động Cấp cứu 115 / Chuyển viện khẩn cấp">🚑 Đã kích hoạt điều động Cấp cứu 115 / Chuyển viện khẩn cấp</option>
              <option value="Bệnh nhân phản hồi do nhầm lẫn / Đã đo lại an toàn">✅ Bệnh nhân phản hồi do nhầm lẫn / Đã đo lại an toàn</option>
            </select>
          </div>

          <div className="form-group-esc">
            <label>Biên bản can thiệp & Kết quả lâm sàng (Bắt buộc):</label>
            <textarea
              rows={4}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Ghi nhận diễn biến sau can thiệp: SpO2, nhịp thở, tình trạng tỉnh táo, có cần nhập viện cấp cứu hay tiếp tục theo dõi..."
              required
              className="textarea-esc"
            />
          </div>

          {/* Mẫu gợi ý nhanh */}
          <div className="quick-templates-box">
            <span style={{ fontSize: '0.74rem', fontWeight: 600, color: '#475569', display: 'block', marginBottom: 4 }}>
              Gợi ý mẫu biên bản nhanh:
            </span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {quickTemplates.map((tmpl, idx) => (
                <button
                  type="button"
                  key={idx}
                  className="btn-template-chip"
                  onClick={() => setNotes(tmpl)}
                >
                  {tmpl}
                </button>
              ))}
            </div>
          </div>

          {errorMessage && (
            <div style={{ padding: '8px 12px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '6px', color: '#b91c1c', fontSize: '0.84rem' }}>
              ⚠️ {errorMessage}
            </div>
          )}

          <div className="modal-footer-escalation">
            <button type="button" className="btn-cancel-esc" onClick={onClose} disabled={submitting}>
              Đóng
            </button>
            <button type="submit" className="btn-submit-resolve" disabled={submitting}>
              <CheckCircle size={16} style={{ marginRight: 6, verticalAlign: 'middle' }} />
              {submitting ? 'Đang lưu biên bản...' : 'Ký Biên Bản & Hoàn Tất Xử Lý'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

