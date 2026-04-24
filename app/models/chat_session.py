from datetime import datetime

from app.extensions import db


class ChatSessionRegistry(db.Model):
    __tablename__ = 'chat_session_registry'

    id = db.Column(db.Integer, primary_key=True)
    weknora_session_id = db.Column(db.String(128), nullable=False, unique=True, index=True)
    owner_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner_user = db.relationship('User')

    def to_dict(self):
        return {
            'id': self.weknora_session_id,
            'local_id': self.id,
            'title': self.title or '',
            'description': self.description or '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
