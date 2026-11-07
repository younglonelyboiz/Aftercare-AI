"""Self-contained RBAC/memory tests. Never touch the configured clinical database."""
import asyncio
import os
import uuid
from datetime import datetime, timedelta
from functools import lru_cache
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select, func, text
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.websockets import WebSocketDisconnect

from backend.app.main import app
from backend.app.core.database import Base, get_db
from backend.app.core.config import settings
from backend.app.core.security import COOKIE_NAME, hash_password, token_hash
from backend.app.models.identity import User, AuthSession, NurseAssignment, Conversation, ChatMessage, MemoryNote
from backend.app.models.asthma import AsthmaCarePlan, AsthmaCheckinLog, AsthmaReminder, AlertTicket
from backend.app.api.v1.endpoints.chat import get_rag_service
from backend.app.api.v1.endpoints import escalations
from backend.app.services.chat_memory import build_memory, SHORT_TERM_MESSAGES

PID1, PID2 = 'BN-2026-ASTHMA-01', 'BN-2026-ASTHMA-02'


@compiles(JSONB, 'sqlite')
def compile_jsonb(element, compiler, **kw):
    return 'JSON'


@lru_cache(maxsize=1)
def demo_hash():
    return hash_password('ValidPassword123!')


class StubRAG:
    def __init__(self):
        self.calls = []
        self.fail = False

    def process_chat(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError('simulated provider failure')
        return {'response': 'Phản hồi kiểm thử', 'safety_status': 'NORMAL', 'citations': []}


@pytest.fixture
def env(monkeypatch):
    admin_engine = None
    if os.getenv('AFTERCARE_TEST_POSTGRES') == '1':
        from backend.app.core.database import engine as admin_engine
        schema = 'auth_memory_test_' + uuid.uuid4().hex[:12]
        with admin_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA {schema}'))
        engine = create_engine(admin_engine.url, connect_args={'options': f'-csearch_path={schema} -ctimezone=UTC'})
    else:
        engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        @event.listens_for(engine, 'connect')
        def foreign_keys(connection, record):
            connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        for name, role, pid in [('admin', 'admin', None), ('nurse', 'nurse', None),
                                ('patient1', 'patient', PID1), ('patient2', 'patient', PID2),
                                ('samepatient', 'patient', PID1)]:
            db.add(User(id=name, username=name, full_name=name, role=role, patient_id=pid,
                        password_hash=demo_hash(), is_demo=name != 'samepatient'))
        db.flush()
        db.add(NurseAssignment(nurse_id='nurse', patient_id=PID1))
        for n, pid in enumerate([PID1, PID2]):
            db.add(AsthmaCarePlan(id=f'plan{n}', patient_id=pid, personal_best_pef=500,
                                 baseline_spo2=98, is_active=True))
            db.add(AsthmaCheckinLog(id=f'check{n}', patient_id=pid, action_zone='GREEN',
                                   pef_value=450, spo2_value=98, checkin_time=datetime.utcnow()))
            db.add(AlertTicket(id=f'ticket{n}', patient_id=pid, priority='P1_HIGH',
                               alert_type='TEST', trigger_reason='Test alert'))
            db.add(AsthmaReminder(id=f'reminder{n}', patient_id=pid, title='Test', message_content='Test',
                                  reminder_type='PEF_CHECKIN', scheduled_time=datetime.utcnow().time()))
        db.commit()
    def db_override():
        with factory() as db:
            yield db
    rag = StubRAG()
    app.dependency_overrides[get_db] = db_override
    app.dependency_overrides[get_rag_service] = lambda: rag
    monkeypatch.setattr(settings, 'DEMO_LOGIN_ENABLED', True)
    monkeypatch.setattr(escalations, 'SessionLocal', factory)
    import backend.app.core.database as database
    monkeypatch.setattr(database, 'SessionLocal', factory)
    clients = []
    def client(name=None):
        c = TestClient(app)
        clients.append(c)
        if name:
            assert c.post('/api/v1/auth/demo-login', json={'user_id': name}).status_code == 200
        return c
    yield SimpleNamespace(db=factory, client=client, rag=rag)
    app.dependency_overrides.clear()
    for c in clients:
        c.close()
    engine.dispose()
    if admin_engine is not None:
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA {schema} CASCADE'))


@pytest.mark.parametrize('path', ['/api/v1/patients/', '/api/v1/care-tracker/nurse/patients-overview',
    '/api/v1/escalations/tickets/active', '/api/v1/auth/me', '/api/v1/admin/users',
    f'/api/v1/chat/conversations?patient_id={PID1}', '/api/v1/documents/view/byt_1851'])
def test_anonymous_is_rejected(env, path):
    assert env.client().get(path).status_code == 401


def test_password_login_cookie_logout_and_expiry(env):
    c = env.client()
    assert c.post('/api/v1/auth/login', json={'username': 'patient1', 'password': 'wrong'}).status_code == 401
    r = c.post('/api/v1/auth/login', json={'username': 'patient1', 'password': 'ValidPassword123!'})
    assert r.status_code == 200 and r.json()['role'] == 'patient'
    assert 'httponly' in r.headers['set-cookie'].lower()
    raw = c.cookies.get(COOKIE_NAME)
    with env.db() as db:
        row = db.get(AuthSession, token_hash(raw))
        assert row and row.token_hash != raw
        row.expires_at = datetime.utcnow() - timedelta(seconds=1)
        db.commit()
    assert c.get('/api/v1/auth/me').status_code == 401
    c = env.client('patient1')
    raw = c.cookies.get(COOKIE_NAME)
    assert c.post('/api/v1/auth/logout').status_code == 204
    c.cookies.set(COOKIE_NAME, raw)
    assert c.get('/api/v1/auth/me').status_code == 401


def test_demo_gate_and_server_owned_role(env, monkeypatch):
    c = env.client()
    assert c.post('/api/v1/auth/demo-login', json={'user_id': 'samepatient', 'role': 'admin'}).status_code == 403
    r = c.post('/api/v1/auth/demo-login', json={'user_id': 'patient1', 'role': 'admin'})
    assert r.json()['role'] == 'patient'
    monkeypatch.setattr(settings, 'DEMO_LOGIN_ENABLED', False)
    assert c.get('/api/v1/auth/demo-accounts').json() == {'enabled': False, 'accounts': []}
    assert c.post('/api/v1/auth/demo-login', json={'user_id': 'admin'}).status_code == 404


def test_csrf_and_cross_site_login(env):
    c = env.client('admin')
    assert c.post('/api/v1/auth/demo-login', json={'user_id': 'admin'}, headers={'Origin': 'https://evil.example'}).status_code == 403
    assert c.post('/api/v1/auth/logout', headers={'Sec-Fetch-Site': 'cross-site'}).status_code == 403
    assert c.post('/api/v1/auth/logout', headers={'Origin': 'http://localhost:5173'}).status_code == 204


def test_failed_password_login_is_throttled(env):
    c = env.client()
    for _ in range(5):
        assert c.post('/api/v1/auth/login', json={'username': 'patient1', 'password': 'wrong'}).status_code == 401
    assert c.post('/api/v1/auth/login', json={'username': 'patient1', 'password': 'ValidPassword123!'}).status_code == 429


def test_empty_care_plan_does_not_restore_seed_drugs(env):
    from backend.app.services.patient_context import clinical_context
    with env.db() as db:
        context = clinical_context(db, PID1)
        assert 'Budesonide' not in context['current_medications']['reliever_med']
        assert 'chưa ghi thuốc cụ thể' in context['current_medications']['reliever_med']
        assert 'chưa có chỉ dẫn' in context['action_plan_rules']['red_zone']


def test_ticket_scope_is_applied_before_limit(env):
    with env.db() as db:
        for n in range(55):
            db.add(AlertTicket(id=f'outside{n}', patient_id=PID2, priority='P0_CRITICAL',
                               alert_type='TEST', trigger_reason='Outside scope', created_at=datetime.utcnow() + timedelta(minutes=n)))
        db.commit()
    nurse = env.client('nurse')
    for path in ('active', 'history'):
        tickets = nurse.get(f'/api/v1/escalations/tickets/{path}').json()
        assert len(tickets) == 1 and tickets[0]['patient_id'] == PID1


def test_patient_and_nurse_scope_everywhere(env):
    patient, nurse = env.client('patient1'), env.client('nurse')
    for c in (patient, nurse):
        assert [p['patient_id'] for p in c.get('/api/v1/patients/').json()] == [PID1]
        for path in [f'/api/v1/patients/{PID2}', f'/api/v1/care-tracker/care-plans/{PID2}',
                     f'/api/v1/care-tracker/checkin/history/{PID2}', f'/api/v1/care-tracker/reminders/active/{PID2}']:
            assert c.get(path).status_code == 403
        assert c.post('/api/v1/care-tracker/checkin/', json={'patient_id': PID2, 'pef_value': 400}).status_code == 403
        assert c.post('/api/v1/care-tracker/reminders/reminder1/action', json={'action': 'ACKNOWLEDGE'}).status_code == 403
        assert c.post('/api/v1/screener/evaluate', json={'patient_id': PID2, 'pef_value': 450}).status_code == 403
        assert c.post(f'/api/v1/escalations/patients/{PID2}/safety-confirm-20m', json={'patient_id': PID2}).status_code == 403
    assert patient.get('/api/v1/care-tracker/nurse/patients-overview').status_code == 403
    assert patient.get('/api/v1/escalations/tickets/active').status_code == 403
    assert patient.get('/api/v1/admin/users').status_code == 403
    assert patient.post('/api/v1/care-tracker/care-plans/', json={'patient_id': PID1}).status_code == 403
    assert nurse.post('/api/v1/care-tracker/reset-demo').status_code == 403
    assert [p['patient_id'] for p in nurse.get('/api/v1/care-tracker/nurse/patients-overview').json()] == [PID1]
    assert [t['patient_id'] for t in nurse.get('/api/v1/escalations/tickets/active').json()] == [PID1]
    assert nurse.post('/api/v1/escalations/tickets/ticket1/acknowledge', json={}).status_code == 403
    acknowledged = nurse.post('/api/v1/escalations/tickets/ticket0/acknowledge', json={'acknowledged_by': 'FAKE ADMIN'})
    assert acknowledged.status_code == 200 and acknowledged.json()['acknowledged_by'] == 'nurse'


def test_admin_user_management_and_revocation(env):
    admin, patient = env.client('admin'), env.client('patient1')
    assert admin.patch('/api/v1/admin/users/admin', json={'role': 'nurse'}).status_code == 409
    created = admin.post('/api/v1/admin/users', json={'username': 'newnurse', 'full_name': 'New nurse', 'password': 'StrongPassword123', 'role': 'nurse'})
    assert created.status_code == 201
    new_id = created.json()['id']
    assert admin.put(f'/api/v1/admin/users/{new_id}/assignments', json={'patient_ids': [PID2]}).json()['assigned_patient_ids'] == [PID2]
    nurse = env.client()
    assert nurse.post('/api/v1/auth/login', json={'username': 'newnurse', 'password': 'StrongPassword123'}).status_code == 200
    assert [p['patient_id'] for p in nurse.get('/api/v1/patients/').json()] == [PID2]
    assert admin.patch('/api/v1/admin/users/patient1', json={'is_active': False}).status_code == 200
    assert patient.get('/api/v1/auth/me').status_code == 401
    assert admin.post('/api/v1/admin/users', json={'username': 'badpatient', 'full_name': 'Bad', 'password': 'StrongPassword123', 'role': 'patient', 'patient_id': 'unknown'}).status_code == 422


def send(c, text, conversation_id=None, patient_id=PID1):
    return c.post('/api/v1/chat/chat', json={'patient_id': patient_id, 'message': text, 'conversation_id': conversation_id})


def test_short_term_and_long_term_across_login_and_new_thread(env):
    c = env.client('patient1')
    first = send(c, 'Tôi bị ho khi tiếp xúc với bụi.').json()
    cid = first['conversation_id']
    assert send(c, 'Tôi cần tránh nó như thế nào?', cid).status_code == 200
    assert env.rag.calls[-1]['history'][0]['content'] == 'Tôi bị ho khi tiếp xúc với bụi.'
    assert env.rag.calls[-1]['profile']['latest_checkin']['pef'] == 450
    c.post('/api/v1/auth/logout')
    c = env.client('patient1')
    assert len(c.get(f'/api/v1/chat/conversations/{cid}').json()['messages']) == 4
    assert send(c, 'Tôi muốn hỏi lại về bụi.').status_code == 200
    call = env.rag.calls[-1]
    assert call['history'] == []
    assert any('bụi' in n['text'] for n in call['memory']['long_term_notes'])
    assert all(n['verification'] == 'user_reported' and n['source_message_id'] for n in call['memory']['long_term_notes'])


def test_memory_window_summary_and_persistence_after_new_service(env):
    c = env.client('patient1')
    cid = None
    for n in range(10):
        r = send(c, f'Lời kể kiểm thử lượt {n}', cid)
        assert r.status_code == 200
        cid = r.json()['conversation_id']
    assert len(env.rag.calls[-1]['history']) <= SHORT_TERM_MESSAGES
    assert 'Lời kể kiểm thử lượt 0' in env.rag.calls[-1]['memory']['older_turns_summary']
    # A new service instance reads the same durable database, not Python session state.
    second = StubRAG()
    app.dependency_overrides[get_rag_service] = lambda: second
    assert send(c, 'Bạn còn nhớ không?', cid).status_code == 200
    assert second.calls[-1]['history'] and second.calls[-1]['memory']['older_turns_summary']


def test_conversation_and_memory_cannot_cross_users_or_patients(env):
    p1, p2, nurse = env.client('patient1'), env.client('patient2'), env.client('nurse')
    cid = send(p1, 'Thông tin riêng của bệnh nhân một').json()['conversation_id']
    assert p2.get(f'/api/v1/chat/conversations/{cid}').status_code == 403
    assert send(p2, 'Đọc thông tin của người khác', cid, PID2).status_code == 403
    assert nurse.get(f'/api/v1/chat/conversations/{cid}').status_code == 200
    assert send(nurse, 'Gửi giả bệnh nhân', cid).status_code == 403
    assert nurse.delete(f'/api/v1/chat/conversations/{cid}').status_code == 403
    c = env.client()
    assert c.post('/api/v1/auth/login', json={'username': 'samepatient', 'password': 'ValidPassword123!'}).status_code == 200
    assert c.get(f'/api/v1/chat/conversations/{cid}').status_code == 403
    assert send(c, 'Một hội thoại riêng khác').status_code == 200
    assert not env.rag.calls[-1]['memory']['long_term_notes']
    assert c.get(f'/api/v1/chat/memory?patient_id={PID1}').json()[0]['content'] == 'Một hội thoại riêng khác'
    assert p2.get(f'/api/v1/chat/memory?patient_id={PID1}').status_code == 403


def test_forget_and_delete_conversation(env):
    c = env.client('patient1')
    cid = send(c, 'Tôi muốn ghi nhớ thông tin này').json()['conversation_id']
    note = c.get(f'/api/v1/chat/memory?patient_id={PID1}').json()[0]
    assert env.client('patient2').delete(f"/api/v1/chat/memory/{note['id']}").status_code == 403
    assert c.delete(f"/api/v1/chat/memory/{note['id']}").status_code == 204
    assert not c.get(f'/api/v1/chat/memory?patient_id={PID1}').json()
    assert send(c, 'Thêm ghi nhớ', cid).status_code == 200
    assert c.delete(f'/api/v1/chat/conversations/{cid}').status_code == 204
    assert c.get(f'/api/v1/chat/conversations/{cid}').status_code == 404
    with env.db() as db:
        assert db.scalar(select(func.count()).select_from(ChatMessage)) == 0
        assert db.scalar(select(func.count()).select_from(MemoryNote)) == 0


def test_failed_provider_rolls_back_and_validates_input(env):
    c = env.client('patient1')
    env.rag.fail = True
    assert send(c, 'Câu hỏi khi provider lỗi').status_code == 503
    with env.db() as db:
        assert db.scalar(select(func.count()).select_from(Conversation)) == 0
        assert db.scalar(select(func.count()).select_from(ChatMessage)) == 0
    assert send(c, '   ').status_code == 422
    assert send(c, 'x' * 6001).status_code == 422


@pytest.mark.skipif(os.getenv('AFTERCARE_TEST_POSTGRES') != '1', reason='PostgreSQL row-lock integration')
def test_concurrent_messages_keep_sequence_and_history(env):
    from concurrent.futures import ThreadPoolExecutor
    c = env.client('patient1')
    cid = send(c, 'Bắt đầu hội thoại').json()['conversation_id']
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda n: send(c, f'Gửi đồng thời {n}', cid), range(2)))
    assert all(r.status_code == 200 for r in results)
    rows = c.get(f'/api/v1/chat/conversations/{cid}').json()['messages']
    assert [r['sequence'] for r in rows] == list(range(1, 7))
    assert sorted(len(call['history']) for call in env.rag.calls) == [0, 2, 4]


def test_websocket_authentication_and_patient_denial(env):
    for c in [env.client(), env.client('patient1')]:
        with pytest.raises(WebSocketDisconnect):
            with c.websocket_connect('/api/v1/escalations/ws/nurse-alerts', headers={'Origin': 'http://localhost:5173'}):
                pass
    nurse = env.client('nurse')
    with nurse.websocket_connect('/api/v1/escalations/ws/nurse-alerts', headers={'Origin': 'http://localhost:5173'}) as ws:
        assert ws.receive_json()['event'] == 'CONNECTED'
        ws.send_text('ping')
        assert ws.receive_text() == 'pong'
        nurse.post('/api/v1/auth/logout')
        ws.send_text('ping')
        with pytest.raises(WebSocketDisconnect):
            ws.receive_text()


def test_llm_prompt_uses_history_profile_and_separate_system_role():
    from backend.app.rag.service import AftercareRAGService
    captured = {}
    service = AftercareRAGService.__new__(AftercareRAGService)
    service.triage = SimpleNamespace(evaluate_risk=lambda text, profile: 'NORMAL')
    service._retriever = SimpleNamespace(retrieve=lambda **kw: [])
    service.openrouter_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: (
        captured.update(kw) or SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='Answer'))])
    ))))
    service.gemini_client = None
    service.process_chat(PID1, 'Thuốc đó thì sao?', profile={'patient_info': {'full_name': 'Test'}, 'latest_checkin': {'pef': 401}},
        history=[{'role': 'user', 'content': 'Trước đó tôi hỏi thuốc X'}, {'role': 'assistant', 'content': 'Câu trước'}],
        memory={'long_term_notes': [{'text': 'Tôi hay quên thuốc', 'verification': 'user_reported'}]})
    assert [m['role'] for m in captured['messages']] == ['system', 'user', 'assistant', 'user']
    assert '401' in captured['messages'][-1]['content'] and 'Tôi hay quên thuốc' in captured['messages'][-1]['content']


def test_red_zone_rule_reply_is_persisted_without_llm(env):
    from backend.app.rag.service import AftercareRAGService
    from backend.app.clinical_agents.triage_agent import TriageAgent
    service = AftercareRAGService.__new__(AftercareRAGService)
    service.triage = TriageAgent()
    app.dependency_overrides[get_rag_service] = lambda: service
    c = env.client('patient1')
    response = send(c, 'Tôi không thở được, tím môi, không nói được')
    assert response.status_code == 200
    assert response.json()['safety_status'] == 'RED_ZONE'
    detail = c.get('/api/v1/chat/conversations/' + response.json()['conversation_id']).json()
    assert detail['messages'][-1]['safety_status'] == 'RED_ZONE'
    assert '115' in detail['messages'][-1]['content']
