import React from 'react';
import { ShieldCheck, AlertTriangle, AlertCircle, PhoneCall, MessageSquare } from 'lucide-react';

export default function ActionZoneBanner({ zone, actionPlan, onOpenChatWithAlert }) {
  if (zone === 'green') {
    return (
      <div className="action-zone-banner green">
        <ShieldCheck size={28} color="#059669" style={{ flexShrink: 0 }} />
        <div>
          <div className="zone-header-title">VÙNG XANH - KIỂM SOÁT TỐT (PEF ≥ 80%)</div>
          <div className="zone-body-text">
            {actionPlan?.green_zone || 'Tình trạng hô hấp ổn định. Hãy xịt thuốc duy trì đúng giờ và tiếp tục sinh hoạt bình thường.'}
          </div>
        </div>
      </div>
    );
  }

  if (zone === 'yellow') {
    return (
      <div className="action-zone-banner yellow">
        <AlertTriangle size={28} color="#d97706" style={{ flexShrink: 0 }} />
        <div style={{ flex: 1 }}>
          <div className="zone-header-title">VÙNG VÀNG - CẢNH BÁO HEN TRỞ NẶNG (60% ≤ PEF &lt; 80%)</div>
          <div className="zone-body-text">
            {actionPlan?.yellow_zone || 'Cần dùng ngay thuốc cắt cơn theo kế hoạch hành động. Theo dõi sát trong 20-30 phút.'}
          </div>
          <button
            onClick={() => onOpenChatWithAlert('YELLOW_ZONE')}
            style={{
              marginTop: 10,
              padding: '6px 14px',
              backgroundColor: '#d97706',
              color: 'white',
              border: 'none',
              borderRadius: 6,
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.82rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6
            }}
          >
            <MessageSquare size={14} /> Nhận hướng dẫn xử trí cắt cơn từ AI
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="action-zone-banner red">
      <AlertCircle size={28} color="#dc2626" style={{ flexShrink: 0 }} />
      <div style={{ flex: 1 }}>
        <div className="zone-header-title">VÙNG ĐỎ - CỜ ĐỎ CẤP CỨU (PEF &lt; 60% HOẶC NGUY HIỂM)</div>
        <div className="zone-body-text">
          {actionPlan?.red_zone || 'Cần dùng ngay thuốc cắt cơn và di chuyển khẩn cấp tới cơ sở y tế gần nhất!'}
        </div>
        <div style={{ display: 'flex', gap: 10, marginTop: 12 }}>
          <button
            onClick={() => onOpenChatWithAlert('RED_ZONE')}
            style={{
              padding: '8px 14px',
              backgroundColor: '#dc2626',
              color: 'white',
              border: 'none',
              borderRadius: 6,
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: '0.85rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6
            }}
          >
            <MessageSquare size={16} /> Bật hướng dẫn cấp cứu AI
          </button>
          <a
            href="tel:115"
            style={{
              padding: '8px 14px',
              backgroundColor: 'white',
              color: '#dc2626',
              border: '1.5px solid #dc2626',
              borderRadius: 6,
              textDecoration: 'none',
              fontWeight: 700,
              fontSize: '0.85rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6
            }}
          >
            <PhoneCall size={16} /> Gọi 115
          </a>
        </div>
      </div>
    </div>
  );
}
