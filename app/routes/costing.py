from decimal import Decimal
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.user import Role
from app.models.production import ProductionRun
from app.models.costing import ProductionExpense, ExpenseCategory
from app.routes.auth import role_required
from app.services.audit_service import log_audit

costing_bp = Blueprint('costing', __name__)

@costing_bp.route('/')
@role_required(Role.ACCOUNTANT, Role.OWNER, Role.PRODUCTION_SUPERVISOR)
def index():
    runs = ProductionRun.query.order_by(ProductionRun.run_date.desc(), ProductionRun.id.desc()).all()
    expenses = ProductionExpense.query.order_by(ProductionExpense.expense_date.desc(), ProductionExpense.id.desc()).all()

    total_batch_costs = sum(r.total_production_cost for r in runs)
    total_good_units = sum(r.actual_output_good for r in runs)
    avg_cost_per_packet = (total_batch_costs / total_good_units).quantize(Decimal('0.01')) if total_good_units > Decimal('0') else Decimal('0.00')

    return render_template(
        'costing/index.html',
        runs=runs,
        expenses=expenses,
        total_batch_costs=total_batch_costs,
        total_good_units=total_good_units,
        avg_cost_per_packet=avg_cost_per_packet,
        categories=ExpenseCategory.ALL
    )

@costing_bp.route('/add-expense', methods=['POST'])
@role_required(Role.ACCOUNTANT, Role.OWNER)
def add_expense():
    category = request.form.get('category')
    description = request.form.get('description', '').strip()
    amount = Decimal(request.form.get('amount', '0.00'))
    batch_id = request.form.get('production_run_id')
    notes = request.form.get('notes', '').strip()

    if amount <= Decimal('0.00'):
        flash("Expense amount must be greater than zero.", "danger")
        return redirect(url_for('costing.index'))

    expense = ProductionExpense(
        category=category,
        description=description,
        amount=amount,
        production_run_id=int(batch_id) if batch_id else None,
        notes=notes,
        created_by_id=current_user.id
    )
    db.session.add(expense)
    db.session.commit()

    log_audit(
        action="RECORD_EXPENSE",
        entity_type="ProductionExpense",
        entity_id=expense.id,
        description=f"Recorded expense {category}: ₹{amount} for '{description}'"
    )

    flash(f"Expense of ₹{amount:,.2f} recorded under {category}.", "success")
    return redirect(url_for('costing.index'))
