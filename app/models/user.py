from datetime import datetime

from app.extensions import db
from app.utils.constants import ROLE_USER


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    login_name = db.Column(db.String(64), unique=True, nullable=False, index=True)
    domain_account = db.Column(db.String(128), nullable=True, index=True)
    full_name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)

    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    department_name = db.Column(db.String(100), nullable=True)

    role_level = db.Column(db.String(32), nullable=False, default=ROLE_USER)
    password_hash = db.Column(db.String(255), nullable=False)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    department = db.relationship('Department', backref='users')

    def to_dict(self):
        return {
            'id': self.id,
            'login_name': self.login_name,
            'domain_account': self.domain_account,
            'full_name': self.full_name,
            'email': self.email,
            'department_id': self.department_id,
            'department_name': self.department_name,
            'role_level': self.role_level,
            'is_enabled': self.is_enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
