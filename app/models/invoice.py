from datetime import datetime, date
from decimal import Decimal
from app import db

class InvoiceStatus:
    POSTED = 'POSTED'
    PARTIALLY_PAID = 'PARTIALLY_PAID'
    PAID = 'PAID'
    CANCELLED = 'CANCELLED'

    ALL = [POSTED, PARTIALLY_PAID, PAID, CANCELLED]

class Invoice(db.Model):
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False, index=True) # e.g. INV/2026-27/0001
    order_id = db.Column(db.Integer, db.ForeignKey('sales_orders.id'), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    invoice_date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(30), nullable=False, default=InvoiceStatus.POSTED)
    
    # Customer snapshot at invoice generation
    customer_name = db.Column(db.String(150), nullable=False)
    customer_address = db.Column(db.Text, nullable=False)
    customer_state = db.Column(db.String(50), nullable=False)
    customer_state_code = db.Column(db.String(10), nullable=False)
    customer_gstin = db.Column(db.String(20), nullable=True)
    is_interstate = db.Column(db.Boolean, nullable=False, default=False)
    
    # Financial breakdown
    taxable_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    cgst_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    sgst_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    igst_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    total_tax_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    total_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    paid_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    balance_due = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))

    # Cancellation / Credit note details
    cancellation_reason = db.Column(db.Text, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    cancelled_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    customer = db.relationship('Customer', back_populates='invoices')
    order = db.relationship('SalesOrder', back_populates='invoices')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    cancelled_by = db.relationship('User', foreign_keys=[cancelled_by_id])
    items = db.relationship('InvoiceItem', back_populates='invoice', cascade='all, delete-orphan')
    payments = db.relationship('Payment', back_populates='invoice')
    dispatches = db.relationship('DispatchRecord', back_populates='invoice')

    @property
    def is_paid(self):
        return self.balance_due <= Decimal('0.00')

    @property
    def days_overdue(self):
        if not self.due_date:
            return 0
        delta = (date.today() - self.due_date).days
        return max(0, delta)

    def __repr__(self):
        return f'<Invoice {self.invoice_number} ({self.status}) Total: ₹{self.total_amount} Due: ₹{self.balance_due}>'

class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    
    product_name = db.Column(db.String(150), nullable=False)
    hsn = db.Column(db.String(20), nullable=False, default='19059040')
    quantity = db.Column(db.Numeric(12, 2), nullable=False)
    unit = db.Column(db.String(20), nullable=False, default='Packets')
    unit_price = db.Column(db.Numeric(12, 2), nullable=False) # Before tax
    taxable_amount = db.Column(db.Numeric(12, 2), nullable=False)
    
    gst_rate = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('5.00'))
    cgst_rate = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('0.00'))
    cgst_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    sgst_rate = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('0.00'))
    sgst_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    igst_rate = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('0.00'))
    igst_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    total_tax = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    total_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))

    invoice = db.relationship('Invoice', back_populates='items')
    product = db.relationship('Product')

    def __repr__(self):
        return f'<InvoiceItem {self.product_name} x {self.quantity} = ₹{self.total_amount}>'
