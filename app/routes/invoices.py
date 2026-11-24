from decimal import Decimal
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from app import db
from app.models.user import Role
from app.models.invoice import Invoice, InvoiceStatus
from app.models.sales import SalesOrder, OrderStatus
from app.routes.auth import role_required
from app.services.invoice_service import create_invoice_from_order, cancel_invoice
from app.services.pdf_service import generate_invoice_pdf

invoices_bp = Blueprint('invoices', __name__)

@invoices_bp.route('/')
@role_required(Role.FACTORY_ADMIN, Role.ACCOUNTANT, Role.OWNER)
def index():
    status_filter = request.args.get('status', '')
    query = Invoice.query.order_by(Invoice.invoice_date.desc(), Invoice.id.desc())

    if status_filter:
        query = query.filter(Invoice.status == status_filter)

    invoices = query.all()
    total_invoiced = sum(inv.total_amount for inv in invoices if inv.status != InvoiceStatus.CANCELLED)
    total_due = sum(inv.balance_due for inv in invoices if inv.status != InvoiceStatus.CANCELLED)

    return render_template(
        'invoices/index.html',
        invoices=invoices,
        total_invoiced=total_invoiced,
        total_due=total_due,
        current_status=status_filter,
        statuses=InvoiceStatus.ALL
    )

@invoices_bp.route('/<int:id>')
@role_required(Role.FACTORY_ADMIN, Role.ACCOUNTANT, Role.OWNER)
def view(id):
    invoice = Invoice.query.get_or_404(id)
    return render_template('invoices/view.html', invoice=invoice)

@invoices_bp.route('/create-from-order/<int:order_id>', methods=['POST'])
@role_required(Role.FACTORY_ADMIN, Role.OWNER)
def create_from_order(order_id):
    order = SalesOrder.query.get_or_404(order_id)
    try:
        invoice = create_invoice_from_order(order.id, user_id=current_user.id)
        flash(f"GST Tax Invoice '{invoice.invoice_number}' generated successfully!", "success")
        return redirect(url_for('invoices.view', id=invoice.id))
    except Exception as e:
        flash(f"Error generating invoice: {str(e)}", "danger")
        return redirect(url_for('sales.view', id=order.id))

@invoices_bp.route('/<int:id>/pdf')
@role_required(Role.FACTORY_ADMIN, Role.ACCOUNTANT, Role.OWNER)
def download_pdf(id):
    invoice = Invoice.query.get_or_404(id)
    pdf_buffer = generate_invoice_pdf(invoice)
    filename = f"{invoice.invoice_number.replace('/', '_')}.pdf"
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@invoices_bp.route('/<int:id>/cancel', methods=['POST'])
@role_required(Role.FACTORY_ADMIN, Role.ACCOUNTANT, Role.OWNER)
def cancel(id):
    invoice = Invoice.query.get_or_404(id)
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash("Reason is mandatory to cancel an invoice.", "danger")
        return redirect(url_for('invoices.view', id=invoice.id))

    try:
        cancel_invoice(invoice.id, reason, user_id=current_user.id)
        flash(f"Invoice '{invoice.invoice_number}' has been cancelled and audited.", "info")
    except Exception as e:
        flash(f"Error cancelling invoice: {str(e)}", "danger")

    return redirect(url_for('invoices.view', id=invoice.id))
