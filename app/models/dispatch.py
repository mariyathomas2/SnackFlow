from datetime import datetime, date
from decimal import Decimal
from app import db

class DispatchRecord(db.Model):
    __tablename__ = 'dispatch_records'

    id = db.Column(db.Integer, primary_key=True)
    dispatch_number = db.Column(db.String(50), unique=True, nullable=False, index=True) # e.g. DSP-2026-0001
    order_id = db.Column(db.Integer, db.ForeignKey('sales_orders.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=True)
    dispatch_date = db.Column(db.Date, nullable=False, default=date.today)
    carrier_name = db.Column(db.String(100), nullable=True) # e.g. VRL Logistics, Self Delivery
    vehicle_number = db.Column(db.String(50), nullable=True)
    tracking_number = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(30), nullable=False, default='DISPATCHED') # DISPATCHED, DELIVERED
    
    total_quantity = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    order = db.relationship('SalesOrder')
    invoice = db.relationship('Invoice', back_populates='dispatches')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    items = db.relationship('DispatchItem', back_populates='dispatch', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<DispatchRecord {self.dispatch_number} for Order {self.order_id} - Qty {self.total_quantity}>'

class DispatchItem(db.Model):
    __tablename__ = 'dispatch_items'

    id = db.Column(db.Integer, primary_key=True)
    dispatch_id = db.Column(db.Integer, db.ForeignKey('dispatch_records.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Numeric(12, 2), nullable=False)
    unit = db.Column(db.String(20), nullable=False, default='Packets')

    dispatch = db.relationship('DispatchRecord', back_populates='items')
    product = db.relationship('Product')

    def __repr__(self):
        return f'<DispatchItem {self.product.name}: {self.quantity} {self.unit}>'
