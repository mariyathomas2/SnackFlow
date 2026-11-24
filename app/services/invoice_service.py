from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date
from flask import current_app
from app import db
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from app.models.sales import SalesOrder, OrderStatus
from app.models.master import Customer, Product
from app.services.audit_service import log_audit

def get_financial_year(dt=None):
    """
    Returns Indian Financial Year format string: e.g. '2026-27'
    """
    if dt is None:
        dt = date.today()
    elif isinstance(dt, datetime):
        dt = dt.date()

    if dt.month >= 4:
        start_year = dt.year
        end_year = (dt.year + 1) % 100
    else:
        start_year = dt.year - 1
        end_year = dt.year % 100

    return f"{start_year}-{end_year:02d}"

def generate_invoice_number(invoice_date=None):
    """
    Generates next sequential, gap-free invoice number for the current FY.
    e.g. 'INV/2026-27/0001'
    """
    fy = get_financial_year(invoice_date)
    prefix = f"INV/{fy}/"
    
    # Query highest existing invoice number with this prefix
    last_inv = Invoice.query.filter(
        Invoice.invoice_number.like(f"{prefix}%")
    ).order_by(Invoice.id.desc()).first()

    if last_inv:
        try:
            last_seq = int(last_inv.invoice_number.split('/')[-1])
            new_seq = last_seq + 1
        except Exception:
            new_seq = 1
    else:
        new_seq = 1

    return f"{prefix}{new_seq:04d}"

def is_interstate_sale(customer_state, factory_state=None):
    """
    Determines if a transaction is inter-state (IGST) or intra-state (CGST+SGST).
    """
    if factory_state is None:
        factory_state = current_app.config.get('FACTORY_STATE', 'Tamil Nadu')
    
    return customer_state.strip().lower() != factory_state.strip().lower()

def create_invoice_from_order(order_id, user_id=None, invoice_date=None):
    """
    Generates a full GST Tax Invoice from an approved SalesOrder.
    Calculates CGST + SGST for intra-state or IGST for inter-state.
    """
    order = SalesOrder.query.get(order_id)
    if not order:
        raise ValueError(f"Sales order {order_id} not found.")

    if order.status not in [OrderStatus.APPROVED, OrderStatus.PARTIALLY_DISPATCHED]:
        raise ValueError(f"Cannot invoice order {order.order_number} in status '{order.status}'. Order must be APPROVED.")

    customer = order.customer
    inv_date = invoice_date or date.today()
    invoice_number = generate_invoice_number(inv_date)

    factory_state = current_app.config.get('FACTORY_STATE', 'Tamil Nadu')
    interstate = is_interstate_sale(customer.state, factory_state)

    invoice = Invoice(
        invoice_number=invoice_number,
        order_id=order.id,
        customer_id=customer.id,
        invoice_date=inv_date,
        due_date=date.fromordinal(inv_date.toordinal() + 30), # 30 days credit term
        status=InvoiceStatus.POSTED,
        customer_name=customer.name,
        customer_address=customer.address,
        customer_state=customer.state,
        customer_state_code=customer.state_code,
        customer_gstin=customer.gstin,
        is_interstate=interstate,
        created_by_id=user_id
    )
    db.session.add(invoice)
    db.session.flush()

    total_taxable = Decimal('0.00')
    total_cgst = Decimal('0.00')
    total_sgst = Decimal('0.00')
    total_igst = Decimal('0.00')

    for item in order.items:
        # Use approved quantity if approved, otherwise ordered quantity
        qty = item.approved_quantity if item.approved_quantity > Decimal('0') else item.ordered_quantity
        if qty <= Decimal('0'):
            continue

        product = item.product
        unit_price = item.unit_price
        gst_rate = item.gst_rate

        taxable = (qty * unit_price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        if interstate:
            # Inter-state: 100% IGST
            cgst_rate = Decimal('0.00')
            cgst_amt = Decimal('0.00')
            sgst_rate = Decimal('0.00')
            sgst_amt = Decimal('0.00')
            igst_rate = gst_rate
            igst_amt = (taxable * (igst_rate / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            line_tax = igst_amt
        else:
            # Intra-state (Tamil Nadu): 50% CGST + 50% SGST
            cgst_rate = (gst_rate / Decimal('2')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            cgst_amt = (taxable * (cgst_rate / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            sgst_rate = (gst_rate / Decimal('2')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            sgst_amt = (taxable * (sgst_rate / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            igst_rate = Decimal('0.00')
            igst_amt = Decimal('0.00')
            line_tax = cgst_amt + sgst_amt

        line_total = taxable + line_tax

        inv_item = InvoiceItem(
            invoice_id=invoice.id,
            product_id=product.id,
            product_name=product.name,
            hsn=product.hsn,
            quantity=qty,
            unit=product.unit,
            unit_price=unit_price,
            taxable_amount=taxable,
            gst_rate=gst_rate,
            cgst_rate=cgst_rate,
            cgst_amount=cgst_amt,
            sgst_rate=sgst_rate,
            sgst_amount=sgst_amt,
            igst_rate=igst_rate,
            igst_amount=igst_amt,
            total_tax=line_tax,
            total_amount=line_total
        )
        db.session.add(inv_item)

        total_taxable += taxable
        total_cgst += cgst_amt
        total_sgst += sgst_amt
        total_igst += igst_amt

    total_tax = total_cgst + total_sgst + total_igst
    total_amount = total_taxable + total_tax

    invoice.taxable_amount = total_taxable
    invoice.cgst_amount = total_cgst
    invoice.sgst_amount = total_sgst
    invoice.igst_amount = total_igst
    invoice.total_tax_amount = total_tax
    invoice.total_amount = total_amount
    invoice.paid_amount = Decimal('0.00')
    invoice.balance_due = total_amount

    # Update order status
    order.status = OrderStatus.INVOICED

    db.session.commit()

    log_audit(
        action="CREATE_INVOICE",
        entity_type="Invoice",
        entity_id=invoice.id,
        description=f"Generated GST invoice {invoice.invoice_number} for {customer.name}. Taxable: ₹{total_taxable}, Total: ₹{total_amount} ({'Interstate IGST' if interstate else 'Intra-state CGST+SGST'})."
    )

    return invoice

def cancel_invoice(invoice_id, reason, user_id=None):
    """
    Cancels an invoice with credit note reason. Prevents hard deletion.
    """
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        raise ValueError(f"Invoice {invoice_id} not found.")

    if invoice.status == InvoiceStatus.CANCELLED:
        raise ValueError("Invoice is already cancelled.")

    if invoice.paid_amount > Decimal('0.00'):
        raise ValueError(f"Cannot cancel invoice with recorded payments (₹{invoice.paid_amount}). Refund or adjust payments first.")

    invoice.status = InvoiceStatus.CANCELLED
    invoice.cancellation_reason = reason
    invoice.cancelled_at = datetime.utcnow()
    invoice.cancelled_by_id = user_id
    invoice.balance_due = Decimal('0.00')

    db.session.commit()

    log_audit(
        action="CANCEL_INVOICE",
        entity_type="Invoice",
        entity_id=invoice.id,
        description=f"Cancelled invoice {invoice.invoice_number}. Reason: {reason}"
    )

    return invoice
