import { useEffect, useState } from 'react';
import { HeartPulse, ShieldCheck, Stethoscope, UserRound } from 'lucide-react';
import App from '../../App';
import { demoLogin, errorMessage, getCurrentUser, getDemoAccounts, login, logout } from '../../services/api';
import './auth.css';

const ROLES = [
  { id: 'patient', label: 'Bệnh nhân', description: 'Theo dõi sức khỏe và trò chuyện với trợ lý.', Icon: UserRound },
  { id: 'nurse', label: 'Điều dưỡng', description: 'Chăm sóc bệnh nhân được phân công.', Icon: Stethoscope },
  { id: 'admin', label: 'Quản trị viên', description: 'Quản lý tài khoản và phân quyền.', Icon: ShieldCheck },
];

export default function AuthRoot() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);
  const [accounts, setAccounts] = useState([]);
  const [role, setRole] = useState('patient');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  useEffect(() => {
    let active = true;
    Promise.allSettled([getCurrentUser(), getDemoAccounts()]).then(([me, demo]) => {
      if (!active) return;
      if (me.status === 'fulfilled') setUser(me.value);
      else if (me.reason.response?.status !== 401) setError('Chưa kết nối được máy chủ. Vui lòng thử lại.');
      if (demo.status === 'fulfilled' && demo.value.enabled) setAccounts(demo.value.accounts);
      setChecking(false);
    });
    const expire = () => { setUser(null); setError('Phiên đăng nhập đã kết thúc. Vui lòng đăng nhập lại.'); };
    window.addEventListener('aftercare-session-expired', expire);
    return () => { active = false; window.removeEventListener('aftercare-session-expired', expire); };
  }, []);

  const authenticate = async (action) => {
    setBusy(true); setError('');
    try { setUser(await action()); setPassword(''); }
    catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  };
  const signOut = async () => {
    try { await logout(); setUser(null); setError(''); }
    catch (err) { setError(errorMessage(err)); }
  };

  if (checking) return <main className="auth-shell"><p role="status">Đang kiểm tra phiên đăng nhập…</p></main>;
  if (user) return <><App key={user.id} user={user} onLogout={signOut} />{error && <p className="auth-session-error" role="alert">{error}</p>}</>;
  return (
    <main className="auth-shell">
      <section className="auth-intro">
        <div className="auth-brand"><HeartPulse size={32} /><span>Aftercare-AI</span></div>
        <h1>Đồng hành sau<br />ngày xuất viện.</h1>
        <p>Cập nhật sức khỏe, theo dõi kế hoạch chăm sóc và kết nối với đội ngũ điều dưỡng.</p>
        <div className="auth-intro-note"><ShieldCheck size={20} /><span>Mỗi vai trò có phạm vi truy cập riêng. Lịch sử trò chuyện được lưu theo từng bệnh nhân và tài khoản.</span></div>
      </section>
      <section className="auth-card" aria-label="Đăng nhập">
        <h2>Chào mừng trở lại</h2><p>Đăng nhập để tiếp tục chăm sóc.</p>
        <form onSubmit={e => { e.preventDefault(); authenticate(() => login(username, password)); }}>
          <label htmlFor="login-username">Tên đăng nhập</label>
          <input id="login-username" autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} required maxLength={100} />
          <label htmlFor="login-password">Mật khẩu</label>
          <input id="login-password" type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} required maxLength={256} />
          <button className="auth-primary" disabled={busy}>{busy ? 'Đang đăng nhập…' : 'Đăng nhập'}</button>
        </form>
        {accounts.length > 0 && <div className="auth-demo">
          <h3>Trải nghiệm nhanh bản demo</h3>
          <p>Chọn vai trò, sau đó chọn tài khoản mẫu.</p>
          <div className="auth-role-options" aria-label="Vai trò demo">
            {ROLES.map(({ id, label, Icon }) => <button key={id} type="button" aria-pressed={role === id} className={role === id ? 'selected' : ''} onClick={() => setRole(id)} disabled={busy}><Icon size={19} />{label}</button>)}
          </div>
          <p className="auth-role-description">{ROLES.find(r => r.id === role).description}</p>
          <div className="auth-demo-accounts">{accounts.filter(a => a.role === role).map(a => <button key={a.id} disabled={busy} onClick={() => authenticate(() => demoLogin(a.id))}>
            <span>{a.full_name}</span><span aria-hidden="true">›</span>
          </button>)}</div>
          <small>Chế độ demo cho phép vào tài khoản mẫu không cần mật khẩu.</small>
        </div>}
        {error && <p className="auth-error" role="alert">{error}</p>}
      </section>
    </main>
  );
}
