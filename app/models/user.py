from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class Role:
    SALESMAN = 'SALESMAN'
    FACTORY_ADMIN = 'FACTORY_ADMIN'
    PRODUCTION_SUPERVISOR = 'PRODUCTION_SUPERVISOR'
    ACCOUNTANT = 'ACCOUNTANT'
    OWNER = 'OWNER'

    ALL = [SALESMAN, FACTORY_ADMIN, PRODUCTION_SUPERVISOR, ACCOUNTANT, OWNER]

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(32), nullable=False)  # Role enum string
    phone = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_role(self, *roles):
        return self.role in roles

    @property
    def role_display(self):
        role_map = {
            Role.SALESMAN: 'Sales Representative',
            Role.FACTORY_ADMIN: 'Factory Administrator',
            Role.PRODUCTION_SUPERVISOR: 'Production Supervisor',
            Role.ACCOUNTANT: 'Accountant & Auditor',
            Role.OWNER: 'Business Owner & Director'
        }
        return role_map.get(self.role, self.role)

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'
