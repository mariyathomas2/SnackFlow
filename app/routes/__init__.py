from app.routes.auth import auth_bp
from app.routes.dashboard import dashboard_bp
from app.routes.master import master_bp
from app.routes.inventory import inventory_bp
from app.routes.purchases import purchases_bp
from app.routes.production import production_bp
from app.routes.sales import sales_bp
from app.routes.invoices import invoices_bp
from app.routes.dispatch import dispatch_bp
from app.routes.payments import payments_bp
from app.routes.costing import costing_bp
from app.routes.reports import reports_bp
from app.routes.audit import audit_bp

__all__ = [
    'auth_bp',
    'dashboard_bp',
    'master_bp',
    'inventory_bp',
    'purchases_bp',
    'production_bp',
    'sales_bp',
    'invoices_bp',
    'dispatch_bp',
    'payments_bp',
    'costing_bp',
    'reports_bp',
    'audit_bp'
]
