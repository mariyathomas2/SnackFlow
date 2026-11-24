from flask import Blueprint, render_template, request
from flask_login import login_required
from app.models.user import Role
from app.models.audit import AuditLog
from app.routes.auth import role_required

audit_bp = Blueprint('audit', __name__)

@audit_bp.route('/')
@role_required(Role.ACCOUNTANT, Role.OWNER, Role.FACTORY_ADMIN)
def index():
    entity_filter = request.args.get('entity_type', '')
    action_filter = request.args.get('action', '')
    search = request.args.get('search', '').strip()

    query = AuditLog.query.order_by(AuditLog.timestamp.desc())

    if entity_filter:
        query = query.filter(AuditLog.entity_type == entity_filter)
    if action_filter:
        query = query.filter(AuditLog.action.ilike(f"%{action_filter}%"))
    if search:
        query = query.filter(AuditLog.description.ilike(f"%{search}%") | AuditLog.username.ilike(f"%{search}%"))

    logs = query.limit(200).all()

    # Get distinct entity types
    entity_types = ['Order', 'SalesOrder', 'ProductionRun', 'Invoice', 'StockLedger', 'Payment', 'PurchaseOrder', 'User', 'Product', 'Customer']

    return render_template(
        'audit/index.html',
        logs=logs,
        current_entity=entity_filter,
        current_action=action_filter,
        search=search,
        entity_types=entity_types
    )
