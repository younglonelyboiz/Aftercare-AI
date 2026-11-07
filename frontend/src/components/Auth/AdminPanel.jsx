import { useEffect, useState } from 'react';
import { createUser, errorMessage, getUsers, updateAssignments, updateUser } from '../../services/api';

const roleLabels = { admin: 'Quản trị viên', nurse: 'Điều dưỡng', patient: 'Bệnh nhân' };

function UserRow({ account, patients, actorId, onChange, report }) {
  const [role, setRole] = useState(account.role);
  const [patientId, setPatientId] = useState(account.patient_id || patients[0]?.patient_id || '');
  const [assigned, setAssigned] = useState(account.assigned_patient_ids);
  const [busy, setBusy] = useState(false);
  const apply = async action => {
    setBusy(true);
    try { await action(); await onChange(); report('Đã lưu thay đổi.'); }
    catch (err) { report(errorMessage(err), true); }
    finally { setBusy(false); }
  };
  return <article className="admin-user-row">
    <div><strong>{account.full_name}</strong><small>{account.username} · {roleLabels[account.role]} · {account.is_active ? 'Đang hoạt động' : 'Đã khóa'}</small></div>
    <div className="admin-user-actions">
      <select aria-label={`Vai trò của ${account.full_name}`} value={role} onChange={e => setRole(e.target.value)} disabled={busy || account.id === actorId}>
        {Object.entries(roleLabels).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
      </select>
      {role === 'patient' && <select aria-label={`Hồ sơ của ${account.full_name}`} value={patientId} onChange={e => setPatientId(e.target.value)} disabled={busy}>
        {patients.map(p => <option key={p.patient_id} value={p.patient_id}>{p.full_name}</option>)}
      </select>}
      <button disabled={busy || account.id === actorId} onClick={() => apply(() => updateUser(account.id, { role, patient_id: role === 'patient' ? patientId : null }))}>Lưu quyền</button>
      <button disabled={busy || account.id === actorId} onClick={() => apply(() => updateUser(account.id, { is_active: !account.is_active }))}>{account.is_active ? 'Khóa tài khoản' : 'Mở khóa'}</button>
    </div>
    {account.role === 'nurse' && <div className="admin-assignments">
      <span>Phân công:</span>
      {patients.map(p => <label key={p.patient_id}><input type="checkbox" checked={assigned.includes(p.patient_id)} disabled={busy} onChange={e => setAssigned(prev => e.target.checked ? [...prev, p.patient_id] : prev.filter(id => id !== p.patient_id))} />{p.full_name}</label>)}
      <button className="demo-reset-btn" disabled={busy} onClick={() => apply(() => updateAssignments(account.id, assigned))}>Lưu phân công</button>
    </div>}
  </article>;
}

export default function AdminPanel({ user, patients }) {
  const [users, setUsers] = useState([]);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ username: '', full_name: '', password: '', role: 'patient', patient_id: patients[0]?.patient_id || '' });
  const refresh = async () => setUsers(await getUsers());
  useEffect(() => {
    let active = true;
    getUsers().then(data => { if (active) setUsers(data); }).catch(err => { if (active) setNotice({ text: errorMessage(err), error: true }); });
    return () => { active = false; };
  }, []);
  const create = async e => {
    e.preventDefault(); setBusy(true); setNotice(null);
    try {
      await createUser({ ...form, patient_id: form.role === 'patient' ? form.patient_id : null });
      setForm(prev => ({ ...prev, username: '', full_name: '', password: '' }));
      await refresh(); setNotice({ text: 'Đã tạo tài khoản.' });
    } catch (err) { setNotice({ text: errorMessage(err), error: true }); }
    finally { setBusy(false); }
  };
  const field = key => ({ value: form[key], onChange: e => setForm(prev => ({ ...prev, [key]: e.target.value })) });
  return <main className="admin-panel">
    <h2>Tài khoản và phân quyền</h2><p>Quản lý vai trò, trạng thái tài khoản và bệnh nhân phụ trách của điều dưỡng.</p>
    <form className="admin-create-form" onSubmit={create}>
      <label>Họ và tên<input {...field('full_name')} required maxLength={200} /></label>
      <label>Tên đăng nhập<input {...field('username')} required pattern="[a-zA-Z0-9_.\-]{3,100}" autoComplete="off" /></label>
      <label>Mật khẩu ban đầu<input {...field('password')} required type="password" minLength={10} maxLength={256} autoComplete="new-password" /></label>
      <label>Vai trò<select {...field('role')}>{Object.entries(roleLabels).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>
      {form.role === 'patient' && <label>Hồ sơ bệnh nhân<select {...field('patient_id')} required><option value="">Chọn bệnh nhân</option>{patients.map(p => <option key={p.patient_id} value={p.patient_id}>{p.full_name}</option>)}</select></label>}
      <button className="auth-primary" disabled={busy}>{busy ? 'Đang tạo…' : 'Tạo tài khoản'}</button>
    </form>
    {notice && <p className={notice.error ? 'auth-error' : ''} role={notice.error ? 'alert' : 'status'}>{notice.text}</p>}
    <div className="admin-user-list">{users.map(u => <UserRow key={`${u.id}:${u.role}:${u.is_active}:${u.assigned_patient_ids.join(',')}`} account={u} patients={patients} actorId={user.id} onChange={refresh} report={(text, error = false) => setNotice({ text, error })} />)}</div>
  </main>;
}
