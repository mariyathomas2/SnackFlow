from decimal import Decimal
from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models.user import Role
from app.models.sales import SalesOrder, SalesOrderItem, OrderStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.models.purchase import PurchaseOrder
from app.models.production import ProductionRun, ProductionConsumption
from app.models.payment import Payment
from app.models.audit import AuditLog
from app.models.master import Customer, Product, RawMaterial
from app.models.inventory import StockItemType
from app.services.inventory_service import (
    get_raw_materials_summary, get_finished_goods_summary, get_current_stock
)
from app.services.payment_service import get_customer_receivables_summary

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    role = current_user.role

    # 1. OWNER DASHBOARD
    if role == Role.OWNER:
        total_sales = db.session.query(func.coalesce(func.sum(Invoice.total_amount), Decimal('0.00'))).filter(
            Invoice.status != InvoiceStatus.CANCELLED
        ).scalar()

        total_collected = db.session.query(func.coalesce(func.sum(Payment.amount), Decimal('0.00'))).scalar()
        
        total_outstanding = db.session.query(func.coalesce(func.sum(Invoice.balance_due), Decimal('0.00'))).filter(
            Invoice.status.in_([InvoiceStatus.POSTED, InvoiceStatus.PARTIALLY_PAID])
        ).scalar()

        pending_orders_count = SalesOrder.query.filter_by(status=OrderStatus.PENDING).count()
        total_batches = ProductionRun.query.count()
        
        total_pkts_produced = db.session.query(func.coalesce(func.sum(ProductionRun.actual_output_good), Decimal('0.00'))).scalar()

        raw_summary = get_raw_materials_summary()
        fg_summary = get_finished_goods_summary()

        rm_stock_val = sum(item['stock_value'] for item in raw_summary)
        fg_stock_val = sum(item['stock_value'] for item in fg_summary)
        low_stock_count = sum(1 for item in raw_summary if item['is_low_stock'])

        # Variances
        yield_alerts = ProductionRun.query.filter(ProductionRun.yield_variance_pct < Decimal('-2.00')).count()
        consumption_alerts = ProductionConsumption.query.filter(ProductionConsumption.variance_pct > Decimal('2.00')).count()

        recent_activity = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(8).all()
        recent_orders = SalesOrder.query.order_by(SalesOrder.created_at.desc()).limit(5).all()

        return render_template(
            'dashboard/owner.html',
            total_sales=total_sales,
            total_collected=total_collected,
            total_outstanding=total_outstanding,
            pending_orders_count=pending_orders_count,
            total_batches=total_batches,
            total_pkts_produced=total_pkts_produced,
            rm_stock_val=rm_stock_val,
            fg_stock_val=fg_stock_val,
            low_stock_count=low_stock_count,
            yield_alerts=yield_alerts,
            consumption_alerts=consumption_alerts,
            recent_activity=recent_activity,
            recent_orders=recent_orders,
            raw_summary=raw_summary,
            fg_summary=fg_summary
        )

    # 2. SALESMAN DASHBOARD
    elif role == Role.SALESMAN:
        my_orders = SalesOrder.query.filter_by(salesman_id=current_user.id).order_by(SalesOrder.created_at.desc()).all()
        my_pending = [o for o in my_orders if o.status == OrderStatus.PENDING]
        my_approved = [o for o in my_orders if o.status in [OrderStatus.APPROVED, OrderStatus.INVOICED, OrderStatus.DISPATCHED]]
        
        my_total_sales = sum(o.total_amount for o in my_orders if o.status != OrderStatus.REJECTED)
        customers = Customer.query.filter_by(status='Active').all()
        products = Product.query.filter_by(status='Active').all()

        return render_template(
            'dashboard/salesman.html',
            my_orders=my_orders,
            my_pending=my_pending,
            my_approved=my_approved,
            my_total_sales=my_total_sales,
            customers=customers,
            products=products
        )

    # 3. FACTORY ADMIN DASHBOARD
    elif role == Role.FACTORY_ADMIN:
        pending_orders = SalesOrder.query.filter_by(status=OrderStatus.PENDING).order_by(SalesOrder.created_at.asc()).all()
        approved_orders = SalesOrder.query.filter_by(status=OrderStatus.APPROVED).order_by(SalesOrder.created_at.desc()).all()
        ready_for_dispatch = SalesOrder.query.filter_by(status=OrderStatus.INVOICED).order_by(SalesOrder.created_at.desc()).all()
        
        recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(5).all()
        raw_summary = get_raw_materials_summary()
        fg_summary = get_finished_goods_summary()
        low_stock_count = sum(1 for item in raw_summary if item['is_low_stock'])

        return render_template(
            'dashboard/admin.html',
            pending_orders=pending_orders,
            approved_orders=approved_orders,
            ready_for_dispatch=ready_for_dispatch,
            recent_invoices=recent_invoices,
            raw_summary=raw_summary,
            fg_summary=fg_summary,
            low_stock_count=low_stock_count
        )

    # 4. PRODUCTION SUPERVISOR DASHBOARD
    elif role == Role.PRODUCTION_SUPERVISOR:
        raw_summary = get_raw_materials_summary()
        recent_runs = ProductionRun.query.order_by(ProductionRun.created_at.desc()).limit(6).all()
        
        yield_alerts_list = ProductionRun.query.filter(ProductionRun.yield_variance_pct < Decimal('-2.00')).order_by(ProductionRun.created_at.desc()).all()
        consumption_alerts_list = ProductionConsumption.query.filter(ProductionConsumption.variance_pct > Decimal('2.00')).order_by(ProductionConsumption.id.desc()).limit(5).all()
        
        total_batches = ProductionRun.query.count()
        total_output = db.session.query(func.coalesce(func.sum(ProductionRun.actual_output_good), Decimal('0.00'))).scalar()

        return render_template(
            'dashboard/supervisor.html',
            raw_summary=raw_summary,
            recent_runs=recent_runs,
            yield_alerts_list=yield_alerts_list,
            consumption_alerts_list=consumption_alerts_list,
            total_batches=total_batches,
            total_output=total_output
        )

    # 5. ACCOUNTANT / AUDITOR DASHBOARD
    elif role == Role.ACCOUNTANT:
        total_sales = db.session.query(func.coalesce(func.sum(Invoice.total_amount), Decimal('0.00'))).filter(
            Invoice.status != InvoiceStatus.CANCELLED
        ).scalar()
        
        total_cgst = db.session.query(func.coalesce(func.sum(Invoice.cgst_amount), Decimal('0.00'))).filter(
            Invoice.status != InvoiceStatus.CANCELLED
        ).scalar()

        total_sgst = db.session.query(func.coalesce(func.sum(Invoice.sgst_amount), Decimal('0.00'))).filter(
            Invoice.status != InvoiceStatus.CANCELLED
        ).scalar()

        total_igst = db.session.query(func.coalesce(func.sum(Invoice.igst_amount), Decimal('0.00'))).filter(
            Invoice.status != InvoiceStatus.CANCELLED
        ).scalar()

        total_tax = total_cgst + total_sgst + total_igst

        total_collected = db.session.query(func.coalesce(func.sum(Payment.amount), Decimal('0.00'))).scalar()
        
        total_outstanding = db.session.query(func.coalesce(func.sum(Invoice.balance_due), Decimal('0.00'))).filter(
            Invoice.status.in_([InvoiceStatus.POSTED, InvoiceStatus.PARTIALLY_PAID])
        ).scalar()

        total_purchases = db.session.query(func.coalesce(func.sum(PurchaseOrder.total_amount), Decimal('0.00'))).scalar()

        receivables_summary = get_customer_receivables_summary()
        recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(6).all()
        recent_payments = Payment.query.order_by(Payment.created_at.desc()).limit(6).all()

        return render_template(
            'dashboard/accountant.html',
            total_sales=total_sales,
            total_cgst=total_cgst,
            total_sgst=total_sgst,
            total_igst=total_igst,
            total_tax=total_tax,
            total_collected=total_collected,
            total_outstanding=total_outstanding,
            total_purchases=total_purchases,
            receivables_summary=receivables_summary,
            recent_invoices=recent_invoices,
            recent_payments=recent_payments
        )

    # Fallback
    return redirect(url_for('auth.login'))
