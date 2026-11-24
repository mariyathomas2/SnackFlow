from datetime import datetime
from app import db

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    username = db.Column(db.String(64), nullable=True)
    action = db.Column(db.String(64), nullable=False) # e.g. 'CREATE_ORDER', 'APPROVE_ORDER', 'RECORD_PRODUCTION'
    entity_type = db.Column(db.String(64), nullable=False) # e.g. 'Order', 'ProductionRun', 'Invoice', 'StockLedger'
    entity_id = db.Column(db.String(64), nullable=True)
    description = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', foreign_keys=[user_id], lazy=True)

    def __repr__(self):
        return f'<AuditLog {self.action} on {self.entity_type}:{self.entity_id} at {self.timestamp}>'
