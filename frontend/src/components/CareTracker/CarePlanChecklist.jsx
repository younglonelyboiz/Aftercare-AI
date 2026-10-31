import React, { useState } from 'react';
import { ClipboardList, Pill, Wind, Stethoscope, ArrowRight, Check } from 'lucide-react';

export default function CarePlanChecklist({ carePlan, onCheckinToday }) {
  const [completedItems, setCompletedItems] = useState({});

  if (!carePlan || !carePlan.items) return null;

  const toggleItem = (itemId) => {
    setCompletedItems(prev => ({
      ...prev,
      [itemId]: !prev[itemId]
    }));
  };

  const controllers = carePlan.items.filter(i => i.item_type === 'CONTROLLER_MED');
  const measures = carePlan.items.filter(i => i.item_type === 'PEF_MEASURE');
  const comorbidities = carePlan.items.filter(i => i.item_type === 'COMORBIDITY_MED');

  return (
    <div className="care-checklist-card">
      <div className="checklist-header">
        <h3 className="section-title">
          <ClipboardList size={18} color="var(--primary)" style={{ marginRight: 6, verticalAlign: 'middle' }} />
          Kế Hoạch Chăm Sóc & Nhiệm Vụ Hôm Nay
        </h3>
        <span className="badge-best-pef">
          PEF Mục Tiêu: <strong>{carePlan.personal_best_pef} L/phút</strong>
        </span>
      </div>

      <div className="task-group">
        <h4 className="group-title">
          <Pill size={15} color="var(--primary)" style={{ marginRight: 6, verticalAlign: 'middle' }} />
          Thuốc Kiểm Soát Duy Trì (Chống Hen Tái Phát)
        </h4>
        {controllers.length === 0 ? (
          <p className="empty-sub">Không có thuốc duy trì hàng ngày (Bậc 1 GINA).</p>
        ) : (
          controllers.map(item => {
            const isDone = completedItems[item.id];
            return (
              <div key={item.id} className={`task-row ${isDone ? 'done' : ''}`}>
                <label className="checkbox-wrap">
                  <input 
                    type="checkbox" 
                    checked={!!isDone} 
                    onChange={() => toggleItem(item.id)} 
                  />
                  <span className="checkmark"></span>
                </label>
                <div className="task-content">
                  <div className="task-name">
                    <strong>{item.title}</strong> — <span className="task-dose">{item.dosage}</span>
                  </div>
                  <div className="task-instruction">
                    {item.instructions}
                  </div>
                  <div className="task-times">
                    Giờ xịt: {item.schedule_times.join(', ')}
                  </div>
                </div>
                {isDone && (
                  <span className="done-pill">
                    <Check size={12} style={{ marginRight: 2, verticalAlign: 'middle' }} />
                    Đã xịt
                  </span>
                )}
              </div>
            );
          })
        )}
      </div>

      <div className="task-group">
        <h4 className="group-title">
          <Wind size={15} color="var(--primary)" style={{ marginRight: 6, verticalAlign: 'middle' }} />
          Đo Lưu Lượng Đỉnh & Kiểm Tra Triệu Chứng
        </h4>
        {measures.map(item => {
          const isDone = completedItems[item.id];
          return (
            <div key={item.id} className={`task-row ${isDone ? 'done' : ''}`}>
              <label className="checkbox-wrap">
                <input 
                  type="checkbox" 
                  checked={!!isDone} 
                  onChange={() => toggleItem(item.id)} 
                />
                <span className="checkmark"></span>
              </label>
              <div className="task-content">
                <div className="task-name">
                  <strong>{item.title}</strong> ({item.dosage})
                </div>
                <div className="task-instruction">
                  {item.instructions}
                </div>
                <div className="task-times">
                  Khung giờ: {item.schedule_times.join(', ')}
                </div>
              </div>
              <button 
                className="btn-quick-checkin"
                onClick={onCheckinToday}
              >
                Nhập số đo <ArrowRight size={13} style={{ marginLeft: 3, verticalAlign: 'middle' }} />
              </button>
            </div>
          );
        })}
      </div>

      {comorbidities.length > 0 && (
        <div className="task-group">
          <h4 className="group-title">
            <Stethoscope size={15} color="var(--primary)" style={{ marginRight: 6, verticalAlign: 'middle' }} />
            Thuốc Bệnh Kèm Theo
          </h4>
          {comorbidities.map(item => {
            const isDone = completedItems[item.id];
            return (
              <div key={item.id} className={`task-row ${isDone ? 'done' : ''}`}>
                <label className="checkbox-wrap">
                  <input 
                    type="checkbox" 
                    checked={!!isDone} 
                    onChange={() => toggleItem(item.id)} 
                  />
                  <span className="checkmark"></span>
                </label>
                <div className="task-content">
                  <div className="task-name">
                    <strong>{item.title}</strong> — <span>{item.dosage}</span>
                  </div>
                  <div className="task-instruction">
                    {item.instructions}
                  </div>
                  <div className="task-times">
                    Giờ uống: {item.schedule_times.join(', ')}
                  </div>
                </div>
                {isDone && (
                  <span className="done-pill">
                    <Check size={12} style={{ marginRight: 2, verticalAlign: 'middle' }} />
                    Đã uống
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
