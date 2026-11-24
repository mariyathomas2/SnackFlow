from decimal import Decimal
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.user import Role
from app.models.sales import SalesOrder, SalesOrderItem, OrderStatus
from app.models.master import Customer, Product
from app.routes.auth import role_required
from app.services.sales_service import (
    create_sales_order, review_stock_and_shortage,
    approve_sales_order, reject_sales_order
)

sales_bp = Blueprint('sales', __name__)

@sales_bp.route('/')
@login_required
def index():
    status_filter = request.args.get('status', '')
    query = SalesOrder.query.order_by(SalesOrder.order_date.desc(), SalesOrder.id.desc())

    # If salesman, only see their own orders
    if current_user.role == Role.SALESMAN:
        query = query.filter(SalesOrder.salesman_id == current_user.id)

    if status_filter:
        query = query.filter(SalesOrder.status == status_filter)

    orders = query.all()
    return render_template(
        'sales/index.html',
        orders=orders,
        current_status=status_filter,
        statuses=OrderStatus.ALL
    )

@sales_bp.route('/<int:id>')
@login_required
def view(id):
    order = SalesOrder.query.get_or_404(id)
    
    # Restrict salesman from viewing other salesmen's orders
    if current_user.role == Role.SALESMAN and order.salesman_id != current_user.id:
        flash("You are only permitted to view your own orders.", "danger")
        return redirect(url_for('sales.index'))

    # Refresh live stock and shortage calculation
    stock_review = review_stock_and_shortage(order.id)

    return render_template('sales/view.html', order=order, stock_review=stock_review)

@sales_bp.route('/create', methods=['GET', 'POST'])
@role_required(Role.SALESMAN, Role.FACTORY_ADMIN, Role.OWNER)
def create():
    if request.method == 'POST':
        customer_id = int(request.form.get('customer_id'))
        order_date_str = request.form.get('order_date')
        notes = request.form.get('notes', '').strip()

        prod_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')

        items_data = []
        for p_id, qty in zip(prod_ids, quantities):
            if p_id and qty:
                items_data.append({
                    'product_id': int(p_id),
                    'quantity': Decimal(str(qty))
                })

        if not items_data:
            flash("Please add at least one product with valid quantity.", "danger")
            return redirect(url_for('sales.create'))

        o_date = datetime.strptime(order_date_str, '%Y-%m-%d').date() if order_date_str else date.today()

        try:
            order = create_sales_order(
                customer_id=customer_id,
                salesman_id=current_user.id,
                items_data=items_data,
                notes=notes,
                order_date=o_date
            )
            flash(f"Sales order '{order.order_number}' submitted successfully! Awaiting factory admin verification.", "success")
            return redirect(url_for('sales.view', id=order.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error submitting order: {str(e)}", "danger")
            return redirect(url_for('sales.create'))

    customers = Customer.query.filter_by(status='Active').all()
    products = Product.query.filter_by(status='Active').all()
    return render_template('sales/create.html', customers=customers, products=products, today=date.today())

@sales_bp.route('/<int:id>/approve', methods=['POST'])
@role_required(Role.FACTORY_ADMIN, Role.OWNER)
def approve(id):
    order = SalesOrder.query.get_or_404(id)
    notes = request.form.get('review_notes', '').strip()

    # Check if partial approval quantities were submitted
    approved_map = {}
    for item in order.items:
        app_qty_val = request.form.get(f'approved_qty_{item.id}')
        if app_qty_val is not None and app_qty_val.strip():
            approved_map[item.id] = Decimal(app_qty_val.strip())

    try:
        approve_sales_order(
            order_id=order.id,
            admin_user_id=current_user.id,
            approved_items=approved_map if approved_map else None,
            review_notes=notes
        )
        flash(f"Order '{order.order_number}' approved successfully! Ready for invoicing & dispatch.", "success")
    except Exception as e:
        flash(f"Failed to approve order: {str(e)}", "danger")

    return redirect(url_for('sales.view', id=order.id))

@sales_bp.route('/<int:id>/reject', methods=['POST'])
@role_required(Role.FACTORY_ADMIN, Role.OWNER)
def reject(id):
    order = SalesOrder.query.get_or_404(id)
    reason = request.form.get('reject_reason', '').strip()

    try:
        reject_sales_order(order_id=order.id, admin_user_id=current_user.id, reason=reason)
        flash(f"Order '{order.order_number}' marked as REJECTED.", "info")
    except Exception as e:
        flash(f"Error rejecting order: {str(e)}", "danger")

    return redirect(url_for('sales.view', id=order.id))
