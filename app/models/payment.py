from datetime import datetime, date
from decimal import Decimal
from app import db

class PaymentMethod:
    BANK_TRANSFER = 'BANK_TRANSFER'
    NEFT_RTGS = 'NEFT_RTGS'
    UPI = 'UPI'
    CHEQUE = 'CHEQUE'
    CASH = 'CASH'

    ALL = [BANK_TRANSFER, NEFT_RTGS, UPI, CHEQUE, CASH]

class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    payment_number = db.Column(db.String(50), unique=True, nullable=False, index=True) # e.g. REC-2026-0001
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    payment_date = db.Column(db.Date, nullable=False, default=date.today)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_method = db.Column(db.String(30), nullable=False, default=PaymentMethod.BANK_TRANSFER)
    reference_number = db.Column(db.String(100), nullable=True) # Transaction ID / UTR / Cheque No
    notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    invoice = db.relationship('Invoice', back_populates='payments')
    customer = db.relationship('Customer')
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    def __repr__(self):
        return f'<Payment {self.payment_number} - ₹{self.amount} for Inv {self.invoice_id}>'
