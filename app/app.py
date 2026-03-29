from flask import Flask, jsonify, request, render_template, redirect, url_for, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from models import db, User, Task, Category
import time, os

app = Flask(__name__)
app.config['SECRET_KEY']           = 'dev-secret-key-change-in-prod'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///taskmanager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login_page'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ── Prometheus metrics ──────────────────────────────────────────────────────
REQUEST_COUNT   = Counter('app_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('app_request_latency_seconds', 'Latency', ['endpoint'])
TASK_GAUGE      = Gauge('app_tasks_total', 'Total tasks in DB')
USER_GAUGE      = Gauge('app_users_total', 'Total users in DB')

@app.before_request
def start_timer():
    request._start_time = time.time()

@app.after_request
def record_metrics(response):
    latency = time.time() - request._start_time
    REQUEST_COUNT.labels(request.method, request.path, response.status_code).inc()
    REQUEST_LATENCY.labels(request.path).observe(latency)
    return response

# ── Page routes ─────────────────────────────────────────────────────────────
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

# ── Auth API ────────────────────────────────────────────────────────────────
@app.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password required'}), 400
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already taken'}), 409
    user = User(username=data['username'])
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    USER_GAUGE.set(User.query.count())
    return jsonify({'message': 'Registered successfully', 'user': user.to_dict()}), 201

@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    user = User.query.filter_by(username=data.get('username')).first()
    if not user or not user.check_password(data.get('password', '')):
        return jsonify({'error': 'Invalid credentials'}), 401
    login_user(user)
    return jsonify({'message': 'Login successful', 'user': user.to_dict()})

@app.route('/auth/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out'})

# ── Tasks API ───────────────────────────────────────────────────────────────
@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks():
    priority = request.args.get('priority')
    status   = request.args.get('status')
    query    = Task.query.filter_by(user_id=current_user.id)
    if priority:
        query = query.filter_by(priority=priority)
    if status:
        query = query.filter_by(status=status)
    tasks = query.order_by(Task.created_at.desc()).all()
    return jsonify({'tasks': [t.to_dict() for t in tasks], 'count': len(tasks)})

@app.route('/api/tasks', methods=['POST'])
@login_required
def create_task():
    data = request.get_json()
    if not data or not data.get('title'):
        return jsonify({'error': 'Title is required'}), 400
    priority = data.get('priority', 'medium')
    if priority not in ('high', 'medium', 'low'):
        return jsonify({'error': 'Priority must be high, medium, or low'}), 400
    task = Task(
        title       = data['title'],
        description = data.get('description', ''),
        priority    = priority,
        status      = 'pending',
        due_date    = data.get('due_date'),
        user_id     = current_user.id,
        category_id = data.get('category_id'),
    )
    db.session.add(task)
    db.session.commit()
    TASK_GAUGE.set(Task.query.count())
    return jsonify(task.to_dict()), 201

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
@login_required
def get_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify(task.to_dict())

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    data = request.get_json()
    if 'title'       in data: task.title       = data['title']
    if 'description' in data: task.description = data['description']
    if 'priority'    in data: task.priority    = data['priority']
    if 'status'      in data: task.status      = data['status']
    if 'due_date'    in data: task.due_date    = data['due_date']
    db.session.commit()
    return jsonify(task.to_dict())

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    db.session.delete(task)
    db.session.commit()
    TASK_GAUGE.set(Task.query.count())
    return jsonify({'message': 'Task deleted'})

# ── Stats API ───────────────────────────────────────────────────────────────
@app.route('/api/stats')
@login_required
def stats():
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    return jsonify({
        'total':       len(tasks),
        'pending':     sum(1 for t in tasks if t.status == 'pending'),
        'in_progress': sum(1 for t in tasks if t.status == 'in_progress'),
        'done':        sum(1 for t in tasks if t.status == 'done'),
        'high':        sum(1 for t in tasks if t.priority == 'high'),
        'medium':      sum(1 for t in tasks if t.priority == 'medium'),
        'low':         sum(1 for t in tasks if t.priority == 'low'),
    })

# ── Categories API ──────────────────────────────────────────────────────────
@app.route('/api/categories', methods=['GET'])
@login_required
def get_categories():
    cats = Category.query.all()
    return jsonify({'categories': [c.to_dict() for c in cats]})

# ── System ──────────────────────────────────────────────────────────────────
@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'db': 'connected'})

@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

def seed_data():
    if not Category.query.first():
        for name in ['Work', 'Personal', 'Study', 'Health']:
            db.session.add(Category(name=name))
        db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_data()
    app.run(host='0.0.0.0', port=5000, debug=True)