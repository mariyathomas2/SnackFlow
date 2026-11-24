from flask import request
from flask_login import current_user
from app import db
from app.models.audit import AuditLog

def log_audit(action, entity_type, entity_id, description, user=None):
    """
    Central audit logging function.
    Safely captures user ID, username, IP address, action, and description.
    """
    try:
        user_id = None
        username = 'System'

        if user:
            user_id = user.id
            username = user.username
        elif current_user and current_user.is_authenticated:
            user_id = current_user.id
            username = current_user.username

        ip_addr = None
        try:
            if request:
                ip_addr = request.remote_addr
        except Exception:
            pass

        log_entry = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            description=description,
            ip_address=ip_addr
        )
        db.session.add(log_entry)
        db.session.commit()
        return log_entry
    except Exception as e:
        db.session.rollback()
        # In audit logging, don't crash the main transaction if logging fails, but log to stderr
        print(f"Audit log failed: {e}")
        return None
