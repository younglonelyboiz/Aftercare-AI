import React from 'react';
import { ShieldCheck, AlertTriangle, AlertCircle, PhoneCall, MessageSquare, Check, ArrowRight } from 'lucide-react';

// Helper để parse chuỗi actionText thành các phần có cấu trúc
function formatActionContent(text) {
  if (!text) return null;
  // Làm sạch các emoji đầu dòng thường gặp trong backend message
  const cleanedText = text
    .replace(/^[🚨⚠️✅🟢🟡🔴]\s*/gm, '')
    .trim();

  // Tách dòng
  const lines = cleanedText.split('\n').map(l => l.trim()).filter(Boolean);
  if (lines.length === 0) return null;

  const headerSummary = lines[0]; // Dòng tóm tắt đầu tiên
  const detailItems = lines.slice(1);

  return {
    summary: headerSummary,
    items: detailItems.map(item => {
      // Loại bỏ dấu bullet hoặc số đầu dòng để render đẹp
      return item.replace(/^[•\-\*]\s*/, '').replace(/^\d+\.\s*/, '');
    })
  };
}

export default function ActionZoneBanner({ zone, actionPlan, screenerResult, onOpenChatWithAlert }) {
  // Chuẩn hóa zone thành 'green' | 'yellow' | 'red'
  let normalizedZone = zone || 'green';
  if (screenerResult?.risk_level) {
    if (screenerResult.risk_level === 'RED_ZONE') normalizedZone = 'red';
    else if (screenerResult.risk_level === 'YELLOW_ZONE') normalizedZone = 'yellow';
    else normalizedZone = 'green';
  }

  const reasons = screenerResult?.matched_reasons || [];
  const rawActionText = screenerResult?.action_instructions || (
    normalizedZone === 'green' ? actionPlan?.green_zone :
    normalizedZone === 'yellow' ? actionPlan?.yellow_zone :
    actionPlan?.red_zone
  );

  const formattedContent = formatActionContent(rawActionText);
  const disclaimer = screenerResult?.disclaimer || 'Lưu ý y tế: Kết quả sàng lọc chỉ nhằm đánh giá mức độ khẩn cấp và hướng dẫn xử trí ban đầu, tuyệt đối không thay thế chẩn đoán của bác sĩ chuyên khoa.';

  if (normalizedZone === 'green') {
    return (
      <div
        className="action-zone-banner green"
        style={{
          borderRadius: '8px',
          border: '1px solid #a7f3d0',
          backgroundColor: '#f0fdf4',
          padding: '16px 20px',
          display: 'flex',
          gap: '14px',
          alignItems: 'flex-start',
          boxShadow: '0 1px 3px rgba(16, 185, 129, 0.05)'
        }}
      >
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: '50%',
            backgroundColor: '#dcfce7',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            marginTop: 2
          }}
        >
          <ShieldCheck size={22} color="#059669" />
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <span
              style={{
                fontSize: '0.72rem',
                fontWeight: 600,
                letterSpacing: '0.04em',
                textTransform: 'uppercase',
                backgroundColor: '#d1fae5',
                color: '#065f46',
                padding: '2px 8px',
                borderRadius: '4px'
              }}
            >
              VÙNG XANH
            </span>
            <span style={{ fontSize: '0.92rem', fontWeight: 600, color: '#065f46' }}>
              Hô hấp ổn định - Kiểm soát tốt
            </span>
          </div>

          {formattedContent?.summary && (
            <p
              style={{
                fontSize: '0.88rem',
                color: '#064e3b',
                margin: '0 0 10px 0',
                lineHeight: 1.55,
                fontWeight: 500
              }}
            >
              {formattedContent.summary}
            </p>
          )}

          {formattedContent?.items && formattedContent.items.length > 0 && (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: 8,
                marginTop: 8,
                backgroundColor: '#ffffff',
                border: '1px solid #e2e8f0',
                borderRadius: '6px',
                padding: '10px 14px'
              }}
            >
              {formattedContent.items.map((item, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                  <div
                    style={{
                      width: 18,
                      height: 18,
                      borderRadius: '50%',
                      backgroundColor: '#ecfdf5',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                      marginTop: 2
                    }}
                  >
                    <Check size={12} color="#059669" strokeWidth={2.5} />
                  </div>
                  <span style={{ fontSize: '0.86rem', color: '#1e293b', lineHeight: 1.5 }}>
                    {item}
                  </span>
                </div>
              ))}
            </div>
          )}

          <div
            style={{
              fontSize: '0.75rem',
              color: '#047857',
              marginTop: 12,
              paddingTop: 8,
              borderTop: '1px solid #d1fae5',
              lineHeight: 1.45
            }}
          >
            {disclaimer}
          </div>
        </div>
      </div>
    );
  }

  if (normalizedZone === 'yellow') {
    return (
      <div
        className="action-zone-banner yellow"
        style={{
          borderRadius: '8px',
          border: '1px solid #fde68a',
          backgroundColor: '#fffbeb',
          padding: '16px 20px',
          display: 'flex',
          gap: '14px',
          alignItems: 'flex-start',
          boxShadow: '0 1px 3px rgba(245, 158, 11, 0.05)'
        }}
      >
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: '50%',
            backgroundColor: '#fef3c7',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            marginTop: 2
          }}
        >
          <AlertTriangle size={22} color="#d97706" />
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <span
              style={{
                fontSize: '0.72rem',
                fontWeight: 600,
                letterSpacing: '0.04em',
                textTransform: 'uppercase',
                backgroundColor: '#fde68a',
                color: '#92400e',
                padding: '2px 8px',
                borderRadius: '4px'
              }}
            >
              VÙNG VÀNG
            </span>
            <span style={{ fontSize: '0.92rem', fontWeight: 600, color: '#92400e' }}>
              Cảnh báo hen trở nặng - Cần chú ý
            </span>
          </div>

          {reasons.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, margin: '8px 0' }}>
              {reasons.map((r, i) => (
                <span
                  key={i}
                  style={{
                    backgroundColor: '#ffffff',
                    border: '1px solid #fcd34d',
                    color: '#92400e',
                    fontSize: '0.76rem',
                    padding: '3px 8px',
                    borderRadius: '4px',
                    fontWeight: 500
                  }}
                >
                  Ghi nhận: {r}
                </span>
              ))}
            </div>
          )}

          {formattedContent?.summary && (
            <p
              style={{
                fontSize: '0.88rem',
                color: '#78350f',
                margin: '0 0 10px 0',
                lineHeight: 1.55,
                fontWeight: 500
              }}
            >
              {formattedContent.summary}
            </p>
          )}

          {formattedContent?.items && formattedContent.items.length > 0 && (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: 8,
                marginTop: 8,
                backgroundColor: '#ffffff',
                border: '1px solid #fde68a',
                borderRadius: '6px',
                padding: '10px 14px'
              }}
            >
              {formattedContent.items.map((item, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                  <div
                    style={{
                      width: 20,
                      height: 20,
                      borderRadius: '50%',
                      backgroundColor: '#fef3c7',
                      color: '#b45309',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                      marginTop: 1
                    }}
                  >
                    {idx + 1}
                  </div>
                  <span style={{ fontSize: '0.86rem', color: '#1e293b', lineHeight: 1.5 }}>
                    {item}
                  </span>
                </div>
              ))}
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 12 }}>
            <button
              onClick={() => onOpenChatWithAlert('YELLOW_ZONE')}
              style={{
                padding: '7px 14px',
                backgroundColor: '#d97706',
                color: 'white',
                border: 'none',
                borderRadius: 6,
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.82rem',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                boxShadow: '0 1px 2px rgba(217, 119, 6, 0.2)'
              }}
            >
              <MessageSquare size={14} /> Hướng dẫn xịt cắt cơn
            </button>
            <span style={{ fontSize: '0.78rem', color: '#92400e', fontWeight: 500 }}>
              Đánh giá lại sau 20 - 30 phút
            </span>
          </div>

          <div
            style={{
              fontSize: '0.75rem',
              color: '#92400e',
              marginTop: 12,
              paddingTop: 8,
              borderTop: '1px solid #fde68a',
              lineHeight: 1.45
            }}
          >
            {disclaimer}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="action-zone-banner red"
      style={{
        borderRadius: '8px',
        border: '1.5px solid #f87171',
        backgroundColor: '#fef2f2',
        padding: '16px 20px',
        display: 'flex',
        gap: '14px',
        alignItems: 'flex-start',
        boxShadow: '0 1px 4px rgba(220, 38, 38, 0.08)'
      }}
    >
      <div
        style={{
          width: 38,
          height: 38,
          borderRadius: '50%',
          backgroundColor: '#fee2e2',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          marginTop: 2
        }}
      >
        <AlertCircle size={24} color="#dc2626" />
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <span
            style={{
              fontSize: '0.72rem',
              fontWeight: 700,
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
              backgroundColor: '#fee2e2',
              color: '#991b1b',
              padding: '2px 8px',
              borderRadius: '4px'
            }}
          >
            VÙNG ĐỎ CẤP CỨU
          </span>
          <span style={{ fontSize: '0.95rem', fontWeight: 700, color: '#991b1b' }}>
            Dấu hiệu nguy kịch - Cần hỗ trợ y tế ngay!
          </span>
        </div>

        {reasons.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, margin: '8px 0' }}>
            {reasons.map((r, i) => (
              <span
                key={i}
                style={{
                  backgroundColor: '#ffffff',
                  border: '1px solid #fca5a5',
                  color: '#991b1b',
                  fontSize: '0.76rem',
                  padding: '3px 8px',
                  borderRadius: '4px',
                  fontWeight: 600
                }}
              >
                Cảnh báo: {r}
              </span>
            ))}
          </div>
        )}

        {formattedContent?.summary && (
          <p
            style={{
              fontSize: '0.88rem',
              color: '#7f1d1d',
              margin: '0 0 10px 0',
              lineHeight: 1.55,
              fontWeight: 600
            }}
          >
            {formattedContent.summary}
          </p>
        )}

        {formattedContent?.items && formattedContent.items.length > 0 && (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
              marginTop: 8,
              backgroundColor: '#ffffff',
              border: '1px solid #fecaca',
              borderRadius: '6px',
              padding: '10px 14px'
            }}
          >
            {formattedContent.items.map((item, idx) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                <div
                  style={{
                    width: 20,
                    height: 20,
                    borderRadius: '50%',
                    backgroundColor: '#fee2e2',
                    color: '#991b1b',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    marginTop: 1
                  }}
                >
                  {idx + 1}
                </div>
                <span style={{ fontSize: '0.86rem', color: '#1e293b', lineHeight: 1.5, fontWeight: 500 }}>
                  {item}
                </span>
              </div>
            ))}
          </div>
        )}

        <div style={{ display: 'flex', gap: 10, marginTop: 14 }}>
          <a
            href="tel:115"
            style={{
              padding: '8px 16px',
              backgroundColor: '#dc2626',
              color: 'white',
              borderRadius: 6,
              textDecoration: 'none',
              fontWeight: 700,
              fontSize: '0.86rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              boxShadow: '0 2px 4px rgba(220, 38, 38, 0.3)'
            }}
          >
            <PhoneCall size={16} /> Gọi Cấp cứu 115 Ngay
          </a>
          <button
            onClick={() => onOpenChatWithAlert('RED_ZONE')}
            style={{
              padding: '8px 14px',
              backgroundColor: 'white',
              color: '#dc2626',
              border: '1px solid #dc2626',
              borderRadius: 6,
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.84rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6
            }}
          >
            <MessageSquare size={16} /> Hướng dẫn sơ cứu khẩn cấp
          </button>
        </div>

        <div
          style={{
            fontSize: '0.75rem',
            color: '#b91c1c',
            marginTop: 12,
            paddingTop: 8,
            borderTop: '1px solid #fecaca',
            lineHeight: 1.45
          }}
        >
          {disclaimer}
        </div>
      </div>
    </div>
  );
}

