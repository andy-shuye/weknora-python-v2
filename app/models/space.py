from datetime import datetime

from app.extensions import db


class Space(db.Model):
    __tablename__ = 'spaces'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)

    owner_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    owner_department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)

    weknora_org_id = db.Column(db.String(128), nullable=True, unique=True)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner_user = db.relationship('User', foreign_keys=[owner_user_id])
    owner_department = db.relationship('Department', foreign_keys=[owner_department_id])

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'owner_user_id': self.owner_user_id,
            'owner_department_id': self.owner_department_id,
            'weknora_org_id': self.weknora_org_id,
            'is_enabled': self.is_enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SpaceDepartmentMember(db.Model):
    __tablename__ = 'space_department_members'

    id = db.Column(db.Integer, primary_key=True)
    space_id = db.Column(db.Integer, db.ForeignKey('spaces.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('space_id', 'department_id', name='uk_space_department_member'),)

    space = db.relationship('Space', backref='department_memberships')
    department = db.relationship('Department')

    def to_dict(self):
        return {
            'id': self.id,
            'space_id': self.space_id,
            'department_id': self.department_id,
            'department_name': self.department.name if self.department else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class SpaceUserMember(db.Model):
    __tablename__ = 'space_user_members'

    id = db.Column(db.Integer, primary_key=True)
    space_id = db.Column(db.Integer, db.ForeignKey('spaces.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('space_id', 'user_id', name='uk_space_user_member'),)

    space = db.relationship('Space', backref='user_memberships')
    user = db.relationship('User')

    def to_dict(self):
        return {
            'id': self.id,
            'space_id': self.space_id,
            'user_id': self.user_id,
            'login_name': self.user.login_name if self.user else None,
            'full_name': self.user.full_name if self.user else None,
            'department_id': self.user.department_id if self.user else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class KnowledgeBaseRegistry(db.Model):
    __tablename__ = 'knowledge_base_registry'

    id = db.Column(db.Integer, primary_key=True)
    weknora_kb_id = db.Column(db.String(128), nullable=False, unique=True, index=True)
    name = db.Column(db.String(255), nullable=False)

    owner_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    owner_department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)

    visibility = db.Column(db.String(32), nullable=False, default='private')
    space_id = db.Column(db.Integer, db.ForeignKey('spaces.id'), nullable=True)

    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner_user = db.relationship('User', foreign_keys=[owner_user_id])
    owner_department = db.relationship('Department', foreign_keys=[owner_department_id])
    space = db.relationship('Space', foreign_keys=[space_id])

    def to_dict(self):
        return {
            'id': self.id,
            'weknora_kb_id': self.weknora_kb_id,
            'name': self.name,
            'owner_user_id': self.owner_user_id,
            'owner_department_id': self.owner_department_id,
            'visibility': self.visibility,
            'space_id': self.space_id,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
