from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    tasks         = db.relationship('Task', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {'id': self.id, 'username': self.username}


class Category(db.Model):
    __tablename__ = 'categories'
    id    = db.Column(db.Integer, primary_key=True)
    name  = db.Column(db.String(50), nullable=False)
    tasks = db.relationship('Task', backref='category', lazy=True)

    def to_dict(self):
        return {'id': self.id, 'name': self.name}


class Task(db.Model):
    __tablename__ = 'tasks'
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    priority    = db.Column(db.String(10), default='medium')   # high / medium / low
    status      = db.Column(db.String(20), default='pending')  # pending / in_progress / done
    due_date    = db.Column(db.String(20), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)

    def to_dict(self):
        return {
            'id':          self.id,
            'title':       self.title,
            'description': self.description,
            'priority':    self.priority,
            'status':      self.status,
            'due_date':    self.due_date,
            'created_at':  self.created_at.isoformat(),
            'user_id':     self.user_id,
            'category_id': self.category_id,
        }