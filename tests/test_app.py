import pytest
from app import app as flask_app
from models import db, User, Task, Category

@pytest.fixture
def app():
    flask_app.config['TESTING']                  = True
    flask_app.config['SQLALCHEMY_DATABASE_URI']  = 'sqlite:///:memory:'
    flask_app.config['WTF_CSRF_ENABLED']         = False
    flask_app.config['LOGIN_DISABLED']           = False
    with flask_app.app_context():
        db.create_all()
        cat = Category(name='Work')
        db.session.add(cat)
        db.session.commit()
    yield flask_app
    with flask_app.app_context():
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_client(client):
    client.post('/auth/register', json={'username': 'testuser', 'password': 'testpass123'})
    client.post('/auth/login',    json={'username': 'testuser', 'password': 'testpass123'})
    return client

# ── Unit tests — Auth ────────────────────────────────────────────────────────
def test_register_success(client):
    res = client.post('/auth/register', json={'username': 'alice', 'password': 'pass123'})
    assert res.status_code == 201
    assert res.get_json()['user']['username'] == 'alice'

def test_register_duplicate_username(client):
    client.post('/auth/register', json={'username': 'bob', 'password': 'pass123'})
    res = client.post('/auth/register', json={'username': 'bob', 'password': 'otherpass'})
    assert res.status_code == 409
    assert 'error' in res.get_json()

def test_register_missing_fields(client):
    res = client.post('/auth/register', json={'username': 'nopass'})
    assert res.status_code == 400

def test_login_success(client):
    client.post('/auth/register', json={'username': 'carol', 'password': 'mypass'})
    res = client.post('/auth/login', json={'username': 'carol', 'password': 'mypass'})
    assert res.status_code == 200
    assert 'user' in res.get_json()

def test_login_wrong_password(client):
    client.post('/auth/register', json={'username': 'dave', 'password': 'correct'})
    res = client.post('/auth/login', json={'username': 'dave', 'password': 'wrong'})
    assert res.status_code == 401

# ── Unit tests — Tasks ───────────────────────────────────────────────────────
def test_create_task_success(auth_client):
    res = auth_client.post('/api/tasks', json={'title': 'Write report', 'priority': 'high'})
    assert res.status_code == 201
    data = res.get_json()
    assert data['title']    == 'Write report'
    assert data['priority'] == 'high'
    assert data['status']   == 'pending'

def test_create_task_missing_title(auth_client):
    res = auth_client.post('/api/tasks', json={'priority': 'low'})
    assert res.status_code == 400

def test_create_task_invalid_priority(auth_client):
    res = auth_client.post('/api/tasks', json={'title': 'Test', 'priority': 'urgent'})
    assert res.status_code == 400

def test_get_tasks_returns_list(auth_client):
    auth_client.post('/api/tasks', json={'title': 'Task A'})
    auth_client.post('/api/tasks', json={'title': 'Task B'})
    res = auth_client.get('/api/tasks')
    assert res.status_code == 200
    data = res.get_json()
    assert data['count'] == 2

def test_get_tasks_filter_by_priority(auth_client):
    auth_client.post('/api/tasks', json={'title': 'High task', 'priority': 'high'})
    auth_client.post('/api/tasks', json={'title': 'Low task',  'priority': 'low'})
    res = auth_client.get('/api/tasks?priority=high')
    data = res.get_json()
    assert all(t['priority'] == 'high' for t in data['tasks'])

# ── Integration tests ────────────────────────────────────────────────────────
def test_update_task_status(auth_client):
    create = auth_client.post('/api/tasks', json={'title': 'Finish feature'})
    task_id = create.get_json()['id']
    res = auth_client.put(f'/api/tasks/{task_id}', json={'status': 'in_progress'})
    assert res.status_code == 200
    assert res.get_json()['status'] == 'in_progress'

def test_delete_task(auth_client):
    create = auth_client.post('/api/tasks', json={'title': 'Temp task'})
    task_id = create.get_json()['id']
    auth_client.delete(f'/api/tasks/{task_id}')
    res = auth_client.get(f'/api/tasks/{task_id}')
    assert res.status_code == 404

def test_stats_endpoint(auth_client):
    auth_client.post('/api/tasks', json={'title': 'T1', 'priority': 'high'})
    auth_client.post('/api/tasks', json={'title': 'T2', 'priority': 'low'})
    res = auth_client.get('/api/stats')
    assert res.status_code == 200
    data = res.get_json()
    assert data['total'] == 2
    assert data['high']  == 1

# ── End-to-end / system tests ─────────────────────────────────────────────
def test_health_endpoint(client):
    res = client.get('/health')
    assert res.status_code == 200
    assert res.get_json()['status'] == 'healthy'

def test_full_task_lifecycle(auth_client):
    create = auth_client.post('/api/tasks', json={'title': 'E2E task', 'priority': 'medium'})
    assert create.status_code == 201
    task_id = create.get_json()['id']

    update = auth_client.put(f'/api/tasks/{task_id}', json={'status': 'in_progress'})
    assert update.get_json()['status'] == 'in_progress'

    complete = auth_client.put(f'/api/tasks/{task_id}', json={'status': 'done'})
    assert complete.get_json()['status'] == 'done'

    delete = auth_client.delete(f'/api/tasks/{task_id}')
    assert delete.status_code == 200

    gone = auth_client.get(f'/api/tasks/{task_id}')
    assert gone.status_code == 404