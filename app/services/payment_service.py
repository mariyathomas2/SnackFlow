from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date
from sqlalchemy import func
from app import db
from app.models.payment import Payment, PaymentMethod
from app.models.invoice import Invoice, InvoiceStatus
from app.models.master import Customer
from app.services.audit_service import log_audit

def record_customer_payment(
    invoice_id,
    amount,
    payment_method=PaymentMethod.BANK_TRANSFER,
    reference_number=None,
    payment_date=None,
    notes=None,
    user_id=None
):
    """
    Records a payment against an invoice.
    Validates that amount does not exceed invoice balance due.
    Updates invoice paid_amount, balance_due, and status.
    """
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        raise ValueError(f"Invoice {invoice_id} not found.")

    if invoice.status == InvoiceStatus.CANCELLED:
        raise ValueError(f"Cannot accept payment on CANCELLED invoice {invoice.invoice_number}.")

    pay_amount = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if pay_amount <= Decimal('0.00'):
        raise ValueError("Payment amount must be greater than zero.")

    if pay_amount > invoice.balance_due:
        raise ValueError(
            f"Payment amount ₹{pay_amount} exceeds outstanding balance of ₹{invoice.balance_due} on invoice {invoice.invoice_number}."
        )

    # Generate sequential payment number REC-YYYYMMDD-XXXX
    count_today = Payment.query.filter(
        Payment.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
    ).count() + 1
    payment_number = f"REC-{datetime.utcnow().strftime('%Y%m%d')}-{count_today:04d}"

    pay_date = payment_date or date.today()

    payment = Payment(
        payment_number=payment_number,
        invoice_id=invoice.id,
        customer_id=invoice.customer_id,
        payment_date=pay_date,
        amount=pay_amount,
        payment_method=payment_method,
        reference_number=reference_number,
        notes=notes,
        created_by_id=user_id
    )
    db.session.add(payment)

    # Update invoice financial state
    invoice.paid_amount += pay_amount
    invoice.balance_due -= pay_amount

    if invoice.balance_due == Decimal('0.00'):
        invoice.status = InvoiceStatus.PAID
    else:
        invoice.status = InvoiceStatus.PARTIALLY_PAID

    db.session.commit()

    log_audit(
        action="RECORD_PAYMENT",
        entity_type="Payment",
        entity_id=payment.id,
        description=f"Recorded payment of ₹{pay_amount} ({payment_method}) for invoice {invoice.invoice_number}. New balance due: ₹{invoice.balance_due}."
    )

    return payment

def get_customer_receivables_summary():
    """
    Computes outstanding balance and ageing breakdown for every customer:
    Current (0-30 days), 31-60 days, 61-90 days, 90+ days.
    """
    customers = Customer.query.filter_by(status='Active').all()
    today = date.today()
    summary = []

    for cust in customers:
        invoices = Invoice.query.filter(
            Invoice.customer_id == cust.id,
            Invoice.status.in_([InvoiceStatus.POSTED, InvoiceStatus.PARTIALLY_PAID])
        ).all()

        total_outstanding = Decimal('0.00')
        bucket_0_30 = Decimal('0.00')
        bucket_31_60 = Decimal('0.00')
        bucket_61_90 = Decimal('0.00')
        bucket_90_plus = Decimal('0.00')

        for inv in invoices:
            bal = inv.balance_due
            total_outstanding += bal
            
            # Age based on invoice date
            days_old = (today - inv.invoice_date).days
            if days_old <= 30:
                bucket_0_30 += bal
            elif days_old <= 60:
                bucket_31_60 += bal
            elif days_old <= 90:
                bucket_61_90 += bal
            else:
                bucket_90_plus += bal

        if total_outstanding > Decimal('0.00') or len(cust.invoices) > 0:
            summary.append({
                'customer_id': cust.id,
                'customer_name': cust.name,
                'state': cust.state,
                'gstin': cust.gstin or 'Unregistered',
                'contact': cust.contact,
                'total_outstanding': total_outstanding,
                'bucket_0_30': bucket_0_30,
                'bucket_31_60': bucket_31_60,
                'bucket_61_90': bucket_61_90,
                'bucket_90_plus': bucket_90_plus,
                'open_invoices_count': len(invoices)
            })

    return summary
