from decimal import Decimal
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.user import Role
from app.models.dispatch import DispatchRecord
from app.models.sales import SalesOrder, OrderStatus
from app.models.invoice import Invoice
from app.routes.auth import role_required
from app.services.dispatch_service import create_dispatch

dispatch_bp = Blueprint('dispatch', __name__)

@dispatch_bp.route('/')
@role_required(Role.FACTORY_ADMIN, Role.OWNER)
def index():
    dispatches = DispatchRecord.query.order_by(DispatchRecord.dispatch_date.desc(), DispatchRecord.id.desc()).all()
    pending_orders = SalesOrder.query.filter(SalesOrder.status.in_([OrderStatus.APPROVED, OrderStatus.INVOICED])).all()
    return render_template('dispatch/index.html', dispatches=dispatches, pending_orders=pending_orders)

@dispatch_bp.route('/create/<int:order_id>', methods=['GET', 'POST'])
@role_required(Role.FACTORY_ADMIN, Role.OWNER)
def create(order_id):
    order = SalesOrder.query.get_or_404(order_id)
    if order.status not in [OrderStatus.APPROVED, OrderStatus.INVOICED]:
        flash(f"Order {order.order_number} is in status '{order.status}'. Only APPROVED or INVOICED orders can be dispatched.", "warning")
        return redirect(url_for('dispatch.index'))

    if request.method == 'POST':
        carrier_name = request.form.get('carrier_name', '').strip()
        vehicle_number = request.form.get('vehicle_number', '').strip()
        tracking_number = request.form.get('tracking_number', '').strip()
        notes = request.form.get('notes', '').strip()

        try:
            dispatch = create_dispatch(
                order_id=order.id,
                carrier_name=carrier_name,
                vehicle_number=vehicle_number,
                tracking_number=tracking_number,
                notes=notes,
                user_id=current_user.id
            )
            flash(f"Dispatch '{dispatch.dispatch_number}' recorded successfully! {dispatch.total_quantity} finished units deducted from stock ledger.", "success")
            return redirect(url_for('dispatch.index'))
        except Exception as e:
            flash(f"Error executing dispatch: {str(e)}", "danger")
            return redirect(url_for('dispatch.create', order_id=order.id))

    return render_template('dispatch/create.html', order=order, today=date.today())
