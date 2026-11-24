from decimal import Decimal
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.user import Role
from app.models.payment import Payment, PaymentMethod
from app.models.invoice import Invoice, InvoiceStatus
from app.routes.auth import role_required
from app.services.payment_service import record_customer_payment, get_customer_receivables_summary

payments_bp = Blueprint('payments', __name__)

@payments_bp.route('/')
@role_required(Role.FACTORY_ADMIN, Role.ACCOUNTANT, Role.OWNER)
def index():
    payments = Payment.query.order_by(Payment.payment_date.desc(), Payment.id.desc()).all()
    total_collections = sum(p.amount for p in payments)
    return render_template('payments/index.html', payments=payments, total_collections=total_collections)

@payments_bp.route('/receivables')
@role_required(Role.FACTORY_ADMIN, Role.ACCOUNTANT, Role.OWNER)
def receivables():
    summary = get_customer_receivables_summary()
    total_receivables = sum(c['total_outstanding'] for c in summary)
    total_0_30 = sum(c['bucket_0_30'] for c in summary)
    total_31_60 = sum(c['bucket_31_60'] for c in summary)
    total_61_90 = sum(c['bucket_61_90'] for c in summary)
    total_90_plus = sum(c['bucket_90_plus'] for c in summary)

    return render_template(
        'payments/receivables.html',
        summary=summary,
        total_receivables=total_receivables,
        total_0_30=total_0_30,
        total_31_60=total_31_60,
        total_61_90=total_61_90,
        total_90_plus=total_90_plus
    )

@payments_bp.route('/create', methods=['GET', 'POST'])
@role_required(Role.FACTORY_ADMIN, Role.ACCOUNTANT, Role.OWNER)
def create():
    if request.method == 'POST':
        invoice_id = int(request.form.get('invoice_id'))
        amount = Decimal(request.form.get('amount', '0.00'))
        payment_method = request.form.get('payment_method', PaymentMethod.BANK_TRANSFER)
        reference_number = request.form.get('reference_number', '').strip()
        notes = request.form.get('notes', '').strip()

        try:
            payment = record_customer_payment(
                invoice_id=invoice_id,
                amount=amount,
                payment_method=payment_method,
                reference_number=reference_number,
                notes=notes,
                user_id=current_user.id
            )
            flash(f"Payment '{payment.payment_number}' of ₹{payment.amount:,.2f} recorded successfully!", "success")
            return redirect(url_for('payments.index'))
        except Exception as e:
            flash(f"Error recording payment: {str(e)}", "danger")
            return redirect(url_for('payments.create', invoice_id=invoice_id))

    selected_inv_id = request.args.get('invoice_id', type=int)
    open_invoices = Invoice.query.filter(
        Invoice.status.in_([InvoiceStatus.POSTED, InvoiceStatus.PARTIALLY_PAID])
    ).order_by(Invoice.invoice_date.asc()).all()

    return render_template(
        'payments/create.html',
        open_invoices=open_invoices,
        selected_inv_id=selected_inv_id,
        payment_methods=PaymentMethod.ALL,
        today=date.today()
    )
