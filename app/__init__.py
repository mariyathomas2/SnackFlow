import os
from decimal import Decimal
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

def create_app(config_class=None):
    app = Flask(__name__)
    
    if config_class is None:
        from app.config import Config
        app.config.from_object(Config)
    else:
        app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # User loader
    from app.models.user import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Jinja template helpers & filters
    @app.template_filter('currency')
    def currency_filter(value):
        if value is None:
            return "₹0.00"
        try:
            val = Decimal(str(value))
            return f"₹{val:,.2f}"
        except Exception:
            return f"₹{value}"

    @app.template_filter('format_qty')
    def format_qty_filter(value, unit=""):
        if value is None:
            return f"0 {unit}".strip()
        try:
            val = Decimal(str(value))
            # If whole integer, show no decimals, else up to 2
            if val == val.to_integral():
                formatted = f"{int(val):,}"
            else:
                formatted = f"{val:,.2f}".rstrip('0').rstrip('.')
            return f"{formatted} {unit}".strip()
        except Exception:
            return f"{value} {unit}".strip()

    @app.template_filter('date_format')
    def date_format_filter(value, fmt="%d-%b-%Y"):
        if not value:
            return "-"
        try:
            return value.strftime(fmt)
        except Exception:
            return str(value)

    # Context processor for global template variables
    @app.context_processor
    def inject_globals():
        from app.models.user import Role
        return {
            'COMPANY_NAME': app.config.get('COMPANY_NAME', 'SnackFlow Foods Pvt. Ltd.'),
            'FACTORY_NAME': app.config.get('FACTORY_NAME', 'SnackFlow Madurai Plant'),
            'FACTORY_STATE': app.config.get('FACTORY_STATE', 'Tamil Nadu'),
            'Role': Role
        }

    # Register Blueprints
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

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(master_bp, url_prefix='/master')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(purchases_bp, url_prefix='/purchases')
    app.register_blueprint(production_bp, url_prefix='/production')
    app.register_blueprint(sales_bp, url_prefix='/sales')
    app.register_blueprint(invoices_bp, url_prefix='/invoices')
    app.register_blueprint(dispatch_bp, url_prefix='/dispatch')
    app.register_blueprint(payments_bp, url_prefix='/payments')
    app.register_blueprint(costing_bp, url_prefix='/costing')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(audit_bp, url_prefix='/audit')

    return app
