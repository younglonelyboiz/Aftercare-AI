import { useCallback, useEffect, useState } from 'react';
import {
  createUser,
  errorMessage,
  getAuditEvents,
  getAuditMetrics,
  getAuditTrace,
  getUsers,
  updateAssignments,
  updateUser,
  verifyAuditChain,
} from '../../services/api';

const roleLabels = {
  admin: 'Quản trị viên',
  nurse: 'Điều dưỡng',
  patient: 'Bệnh nhân',
  agent: 'Tác tử AI',
  worker: 'Tiến trình ngầm',
  system: 'Hệ thống',
  anonymous: 'Khách chưa đăng nhập',
};

const categoryLabels = {
  AUTH: 'Xác thực (AUTH)',
  ADMIN: 'Quản trị (ADMIN)',
  CLINICAL: 'Lâm sàng & Check-in (CLINICAL)',
  AGENT: 'Điều phối AI (AGENT)',
  ESCALATION: 'Cảnh báo & Leo thang (ESCALATION)',
  WORKER: 'Tiến trình ngầm (WORKER)',
  CHAT: 'Hội thoại (CHAT)',
  DOCUMENT: 'Tài liệu y khoa (DOCUMENT)',
  SYSTEM: 'Hệ thống (SYSTEM)',
};

const vnAuditDateFormatter = new Intl.DateTimeFormat('vi-VN', {
  timeZone: 'Asia/Ho_Chi_Minh',
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
});

const vnAuditTimeFormatter = new Intl.DateTimeFormat('vi-VN', {
  timeZone: 'Asia/Ho_Chi_Minh',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
});

function formatAuditDateTimeVN(isoValue) {
  if (!isoValue) return '-';
  const raw = String(isoValue).trim();
  const hasOffset = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(raw);
  const dt = new Date(hasOffset ? raw : `${raw}Z`);
  if (Number.isNaN(dt.getTime())) return raw.replace('T', ' ').slice(0, 19);
  return `${vnAuditTimeFormatter.format(dt)} · ${vnAuditDateFormatter.format(dt)}`;
}

function UserRow({ account, patients, actorId, onChange, report }) {
  const [role, setRole] = useState(account.role);
  const [patientId, setPatientId] = useState(account.patient_id || patients[0]?.patient_id || '');
  const [assigned, setAssigned] = useState(account.assigned_patient_ids);
  const [busy, setBusy] = useState(false);
  const apply = async action => {
    setBusy(true);
    try {
      await action();
      await onChange();
      report('Đã lưu thay đổi.');
    } catch (err) {
      report(errorMessage(err), true);
    } finally {
      setBusy(false);
    }
  };
  return (
    <article className="admin-user-row">
      <div>
        <strong>{account.full_name}</strong>
        <small>
          {account.username} · {roleLabels[account.role] || account.role} ·{' '}
          {account.is_active ? 'Đang hoạt động' : 'Đã khóa'}
        </small>
      </div>
      <div className="admin-user-actions">
        <select
          aria-label={`Vai trò của ${account.full_name}`}
          value={role}
          onChange={e => setRole(e.target.value)}
          disabled={busy || account.id === actorId}
        >
          {['admin', 'nurse', 'patient'].map(id => (
            <option key={id} value={id}>
              {roleLabels[id]}
            </option>
          ))}
        </select>
        {role === 'patient' && (
          <select
            aria-label={`Hồ sơ của ${account.full_name}`}
            value={patientId}
            onChange={e => setPatientId(e.target.value)}
            disabled={busy}
          >
            {patients.map(p => (
              <option key={p.patient_id} value={p.patient_id}>
                {p.full_name}
              </option>
            ))}
          </select>
        )}
        <button
          disabled={busy || account.id === actorId}
          onClick={() =>
            apply(() =>
              updateUser(account.id, { role, patient_id: role === 'patient' ? patientId : null })
            )
          }
        >
          Lưu quyền
        </button>
        <button
          disabled={busy || account.id === actorId}
          onClick={() => apply(() => updateUser(account.id, { is_active: !account.is_active }))}
        >
          {account.is_active ? 'Khóa tài khoản' : 'Mở khóa'}
        </button>
      </div>
      {account.role === 'nurse' && (
        <div className="admin-assignments">
          <span>Phân công:</span>
          {patients.map(p => (
            <label key={p.patient_id}>
              <input
                type="checkbox"
                checked={assigned.includes(p.patient_id)}
                disabled={busy}
                onChange={e =>
                  setAssigned(prev =>
                    e.target.checked
                      ? [...prev, p.patient_id]
                      : prev.filter(id => id !== p.patient_id)
                  )
                }
              />
              {p.full_name}
            </label>
          ))}
          <button
            className="demo-reset-btn"
            disabled={busy}
            onClick={() => apply(() => updateAssignments(account.id, assigned))}
          >
            Lưu phân công
          </button>
        </div>
      )}
    </article>
  );
}

function AuditLogDashboard({ patients }) {
  const [filters, setFilters] = useState({
    category: '',
    severity: '',
    patient_id: '',
    trace_id: '',
    limit: 100,
  });
  const [eventsData, setEventsData] = useState({ total: 0, events: [] });
  const [chainStatus, setChainStatus] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [selectedTrace, setSelectedTrace] = useState(null);
  const [traceLoading, setTraceLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errText, setErrText] = useState(null);

  const loadAuditData = useCallback(async (overrideFilters = null) => {
    setLoading(true);
    setErrText(null);
    try {
      const activeFilters = overrideFilters || filters;
      const [evRes, chainRes, metRes] = await Promise.all([
        getAuditEvents(activeFilters),
        verifyAuditChain(1000),
        getAuditMetrics(),
      ]);
      setEventsData(evRes);
      setChainStatus(chainRes);
      setMetrics(metRes);
    } catch (err) {
      setErrText(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadAuditData();
  }, [loadAuditData]);

  const inspectTrace = async traceId => {
    if (!traceId) return;
    setTraceLoading(true);
    setErrText(null);
    try {
      const detail = await getAuditTrace(traceId);
      setSelectedTrace(detail);
    } catch (err) {
      setErrText(errorMessage(err));
    } finally {
      setTraceLoading(false);
    }
  };

  const nodeLatencies = metrics?.node_latency_ms || {};

  return (
    <section className="audit-dashboard" aria-label="Bảng giám sát nhật ký kiểm toán">
      <div className="audit-summary-grid">
        <div className={`audit-card ${chainStatus?.valid === false ? 'audit-card-danger' : 'audit-card-ok'}`}>
          <div className="audit-card-header">
            <strong>Chuỗi băm chống giả mạo (SHA-256 Chain)</strong>
            <span className={`audit-badge ${chainStatus?.valid === false ? 'sev-CRITICAL' : 'sev-INFO'}`}>
              {chainStatus
                ? chainStatus.valid
                  ? 'TOÀN VẸN HỢP LỆ'
                  : 'PHÁT HIỆN CAN THIỆP'
                : 'Đang kiểm tra...'}
            </span>
          </div>
          {chainStatus && (
            <div className="audit-card-body">
              <p>
                Số bản ghi đã đối chiếu: <strong>{chainStatus.checked_records}</strong>
              </p>
              {chainStatus.tail_hash && (
                <p className="audit-mono">
                  Mã băm cuối chuỗi: {chainStatus.tail_hash.slice(0, 24)}...
                </p>
              )}
              {!chainStatus.valid && (
                <p className="auth-error">
                  {chainStatus.reason} (Bản ghi: {chainStatus.broken_at_id})
                </p>
              )}
            </div>
          )}
        </div>

        <div className="audit-card">
          <div className="audit-card-header">
            <strong>Độ trễ Đồ thị Điều phối AI (P50 / P95)</strong>
            <span className="audit-badge sev-INFO">
              {metrics?.total_turns ?? 0} lượt hội thoại
            </span>
          </div>
          <div className="audit-metrics-pills">
            {Object.keys(nodeLatencies).length === 0 ? (
              <small>Chưa có lượt hội thoại nào trong phiên máy chủ hiện tại.</small>
            ) : (
              Object.entries(nodeLatencies).map(([node, stat]) => (
                <span key={node} className="audit-metric-pill">
                  <strong>{node}</strong>: P50={stat.p50}ms · P95={stat.p95}ms
                </span>
              ))
            )}
          </div>
        </div>
      </div>

      <form
        className="audit-filter-bar"
        onSubmit={e => {
          e.preventDefault();
          loadAuditData(filters);
        }}
      >
        <label>
          Nhóm hành động
          <select
            value={filters.category}
            onChange={e => setFilters(prev => ({ ...prev, category: e.target.value }))}
          >
            <option value="">Tất cả nhóm</option>
            {Object.entries(categoryLabels).map(([code, label]) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </select>
        </label>

        <label>
          Mức độ nghiêm trọng
          <select
            value={filters.severity}
            onChange={e => setFilters(prev => ({ ...prev, severity: e.target.value }))}
          >
            <option value="">Tất cả mức độ</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="HIGH">HIGH</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="ERROR">ERROR</option>
          </select>
        </label>

        <label>
          Bệnh nhân
          <select
            value={filters.patient_id}
            onChange={e => setFilters(prev => ({ ...prev, patient_id: e.target.value }))}
          >
            <option value="">Tất cả bệnh nhân</option>
            {patients.map(p => (
              <option key={p.patient_id} value={p.patient_id}>
                {p.full_name} ({p.patient_id})
              </option>
            ))}
          </select>
        </label>

        <label>
          Mã truy vết (trace_id)
          <input
            type="text"
            placeholder="Nhập trace_id..."
            value={filters.trace_id}
            onChange={e => setFilters(prev => ({ ...prev, trace_id: e.target.value }))}
          />
        </label>

        <div className="audit-filter-actions">
          <button type="submit" className="auth-primary" disabled={loading}>
            {loading ? 'Đang tải...' : 'Lọc nhật ký'}
          </button>
          <button
            type="button"
            className="audit-secondary-btn"
            disabled={loading}
            onClick={() => {
              const cleared = { category: '', severity: '', patient_id: '', trace_id: '', limit: 100 };
              setFilters(cleared);
              loadAuditData(cleared);
            }}
          >
            Đặt lại
          </button>
        </div>
      </form>

      {errText && (
        <p className="auth-error" role="alert">
          {errText}
        </p>
      )}

      {selectedTrace && (
        <div className="audit-trace-inspector">
          <div className="audit-trace-header">
            <div>
              <h3>Chi tiết Dấu vết Hợp nhất: {selectedTrace.trace_id}</h3>
              <small>
                Hợp nhất dữ liệu từ bảng agent_actions_log, audit_logs và system_audit_logs
              </small>
            </div>
            <button
              type="button"
              className="audit-secondary-btn"
              onClick={() => setSelectedTrace(null)}
            >
              Đóng chi tiết
            </button>
          </div>

          {selectedTrace.action ? (
            <div className="audit-trace-section">
              <h4>1. Bản ghi Tổng hợp Đồ thị Điều phối (agent_actions_log)</h4>
              <div className="audit-kv-grid">
                <div>
                  <span>Bệnh nhân:</span> <strong>{selectedTrace.action.patient_id}</strong>
                </div>
                <div>
                  <span>Phân tầng nguy cơ:</span>{' '}
                  <strong className={`audit-badge sev-${selectedTrace.action.risk_level === 'RED_ZONE' ? 'CRITICAL' : selectedTrace.action.risk_level === 'YELLOW_ZONE' ? 'HIGH' : 'INFO'}`}>
                    {selectedTrace.action.risk_level}
                  </strong>
                </div>
                <div>
                  <span>Chính sách đầu vào:</span>{' '}
                  <strong>
                    {selectedTrace.action.policy_decision || 'N/A'} (
                    {selectedTrace.action.policy_rule_id || 'Bỏ qua'})
                  </strong>
                </div>
                <div>
                  <span>Kiểm duyệt đầu ra:</span>{' '}
                  <strong>{selectedTrace.action.output_guard_decision || 'N/A'}</strong>
                </div>
                <div>
                  <span>Tổng độ trễ:</span> <strong>{selectedTrace.action.total_latency_ms} ms</strong>
                </div>
                <div>
                  <span>Mã băm SHA-256 tin nhắn:</span>{' '}
                  <code className="audit-mono">
                    {selectedTrace.action.message_sha256?.slice(0, 20)}...
                  </code>
                </div>
              </div>
              <p className="audit-redacted-box">
                <strong>Tin nhắn đã ẩn danh PII:</strong> {selectedTrace.action.redacted_message}
              </p>
            </div>
          ) : (
            <p className="audit-muted">
              Mã truy vết này là hành động hệ thống trực tiếp (không đi qua đồ thị hội thoại AI).
            </p>
          )}

          {selectedTrace.events && selectedTrace.events.length > 0 && (
            <div className="audit-trace-section">
              <h4>2. Chuỗi Sự kiện Hàng rào An toàn (audit_logs — L0 đến L7)</h4>
              <div className="audit-table-wrap">
                <table className="audit-table">
                  <thead>
                    <tr>
                      <th>Bước</th>
                      <th>Tầng bảo vệ</th>
                      <th>Nút đồ thị</th>
                      <th>Mã quy tắc</th>
                      <th>Quyết định</th>
                      <th>Độ trễ</th>
                      <th>Chi tiết (đã ẩn danh PII)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedTrace.events.map(ev => (
                      <tr key={ev.id}>
                        <td>#{ev.sequence}</td>
                        <td>
                          <code>{ev.layer}</code>
                        </td>
                        <td>{ev.node}</td>
                        <td>
                          <code>{ev.rule_id}</code>
                        </td>
                        <td>
                          <span className={`audit-badge decision-${ev.decision}`}>
                            {ev.decision}
                          </span>
                        </td>
                        <td>{ev.latency_ms} ms</td>
                        <td>{ev.detail}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {selectedTrace.system_events && selectedTrace.system_events.length > 0 && (
            <div className="audit-trace-section">
              <h4>3. Các Sự kiện Hệ thống Liên kết Cùng trace_id (system_audit_logs)</h4>
              <div className="audit-table-wrap">
                <table className="audit-table">
                  <thead>
                    <tr>
                      <th>Chuỗi</th>
                      <th>Mã hành động</th>
                      <th>Tác nhân</th>
                      <th>Tài nguyên</th>
                      <th>Trạng thái sau thay đổi (after_state)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedTrace.system_events.map(sev => (
                      <tr key={sev.id}>
                        <td>#{sev.chain_seq || '-'}</td>
                        <td>
                          <code>{sev.action_code}</code>
                        </td>
                        <td>
                          {sev.actor_role}:{sev.actor_id}
                        </td>
                        <td>
                          {sev.resource_type || '-'} {sev.resource_id ? `(${sev.resource_id})` : ''}
                        </td>
                        <td>
                          <code className="audit-mono">
                            {JSON.stringify(sev.after_state || {})}
                          </code>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="audit-table-header">
        <strong>
          Danh sách Sự kiện Toàn hệ thống ({eventsData.total} bản ghi gần nhất)
        </strong>
      </div>
      <div className="audit-table-wrap">
        <table className="audit-table">
          <thead>
            <tr>
              <th>Thời gian (Giờ VN)</th>
              <th>Nhóm</th>
              <th>Mã hành động</th>
              <th>Tác nhân</th>
              <th>Bệnh nhân</th>
              <th>Mức độ</th>
              <th>Đường dẫn / Kênh</th>
              <th>Mã băm (record_hash)</th>
              <th>Truy vết</th>
            </tr>
          </thead>
          <tbody>
            {eventsData.events.length === 0 ? (
              <tr>
                <td colSpan={9} className="audit-empty-cell">
                  Không có bản ghi kiểm toán nào khớp với bộ lọc hiện tại.
                </td>
              </tr>
            ) : (
              eventsData.events.map(ev => (
                <tr key={ev.id}>
                  <td className="audit-mono">
                    {formatAuditDateTimeVN(ev.created_at)}
                  </td>
                  <td>{ev.category}</td>
                  <td>
                    <code>{ev.action_code}</code>
                  </td>
                  <td>
                    <strong>{ev.actor_id}</strong>
                    <small className="audit-subtext">
                      {roleLabels[ev.actor_role] || ev.actor_role}
                    </small>
                  </td>
                  <td>{ev.patient_id || '-'}</td>
                  <td>
                    <span className={`audit-badge sev-${ev.severity}`}>{ev.severity}</span>
                  </td>
                  <td className="audit-mono">
                    {ev.http_method} {ev.http_path || ''} ({ev.status_code})
                  </td>
                  <td className="audit-mono" title={`prev: ${ev.prev_hash}\nrecord: ${ev.record_hash}`}>
                    {ev.record_hash ? `${ev.record_hash.slice(0, 12)}...` : '-'}
                  </td>
                  <td>
                    <button
                      type="button"
                      className="audit-trace-btn"
                      disabled={traceLoading}
                      onClick={() => inspectTrace(ev.trace_id)}
                    >
                      {ev.trace_id?.slice(0, 12)}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function AdminPanel({ user, patients }) {
  const [activeTab, setActiveTab] = useState('audit');
  const [users, setUsers] = useState([]);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    username: '',
    full_name: '',
    password: '',
    role: 'patient',
    patient_id: patients[0]?.patient_id || '',
  });
  const refresh = async () => setUsers(await getUsers());
  useEffect(() => {
    let active = true;
    getUsers()
      .then(data => {
        if (active) setUsers(data);
      })
      .catch(err => {
        if (active) setNotice({ text: errorMessage(err), error: true });
      });
    return () => {
      active = false;
    };
  }, []);
  const create = async e => {
    e.preventDefault();
    setBusy(true);
    setNotice(null);
    try {
      await createUser({
        ...form,
        patient_id: form.role === 'patient' ? form.patient_id : null,
      });
      setForm(prev => ({ ...prev, username: '', full_name: '', password: '' }));
      await refresh();
      setNotice({ text: 'Đã tạo tài khoản.' });
    } catch (err) {
      setNotice({ text: errorMessage(err), error: true });
    } finally {
      setBusy(false);
    }
  };
  const field = key => ({
    value: form[key],
    onChange: e => setForm(prev => ({ ...prev, [key]: e.target.value })),
  });
  return (
    <main className="admin-panel">
      <div className="admin-tabs-header">
        <div>
          <h2>Trung tâm Quản trị Hệ thống & Kiểm toán An toàn Y tế</h2>
          <p>
            Giám sát nhật ký kiểm toán bất biến toàn hệ thống, chuỗi băm chống giả mạo và phân quyền
            tài khoản.
          </p>
        </div>
        <div className="admin-tab-switcher" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'audit'}
            className={activeTab === 'audit' ? 'admin-tab-btn active' : 'admin-tab-btn'}
            onClick={() => setActiveTab('audit')}
          >
            Nhật ký Kiểm toán & Truy vết AI
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'users'}
            className={activeTab === 'users' ? 'admin-tab-btn active' : 'admin-tab-btn'}
            onClick={() => setActiveTab('users')}
          >
            Tài khoản & Phân quyền ({users.length})
          </button>
        </div>
      </div>

      {activeTab === 'audit' ? (
        <AuditLogDashboard patients={patients} />
      ) : (
        <section aria-label="Quản lý tài khoản và phân quyền">
          <form className="admin-create-form" onSubmit={create}>
            <label>
              Họ và tên
              <input {...field('full_name')} required maxLength={200} />
            </label>
            <label>
              Tên đăng nhập
              <input
                {...field('username')}
                required
                pattern="[a-zA-Z0-9_.\-]{3,100}"
                autoComplete="off"
              />
            </label>
            <label>
              Mật khẩu ban đầu
              <input
                {...field('password')}
                required
                type="password"
                minLength={10}
                maxLength={256}
                autoComplete="new-password"
              />
            </label>
            <label>
              Vai trò
              <select {...field('role')}>
                {['admin', 'nurse', 'patient'].map(id => (
                  <option key={id} value={id}>
                    {roleLabels[id]}
                  </option>
                ))}
              </select>
            </label>
            {form.role === 'patient' && (
              <label>
                Hồ sơ bệnh nhân
                <select {...field('patient_id')} required>
                  <option value="">Chọn bệnh nhân</option>
                  {patients.map(p => (
                    <option key={p.patient_id} value={p.patient_id}>
                      {p.full_name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <button className="auth-primary" disabled={busy}>
              {busy ? 'Đang tạo…' : 'Tạo tài khoản'}
            </button>
          </form>
          {notice && (
            <p
              className={notice.error ? 'auth-error' : ''}
              role={notice.error ? 'alert' : 'status'}
            >
              {notice.text}
            </p>
          )}
          <div className="admin-user-list">
            {users.map(u => (
              <UserRow
                key={`${u.id}:${u.role}:${u.is_active}:${u.assigned_patient_ids.join(',')}`}
                account={u}
                patients={patients}
                actorId={user.id}
                onChange={refresh}
                report={(text, error = false) => setNotice({ text, error })}
              />
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
