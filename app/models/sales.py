from datetime import datetime
from decimal import Decimal
from app import db

class OrderStatus:
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'
    INVOICED = 'INVOICED'
    PARTIALLY_DISPATCHED = 'PARTIALLY_DISPATCHED'
    DISPATCHED = 'DISPATCHED'
    CANCELLED = 'CANCELLED'

    ALL = [PENDING, APPROVED, REJECTED, INVOICED, PARTIALLY_DISPATCHED, DISPATCHED, CANCELLED]

class SalesOrder(db.Model):
    __tablename__ = 'sales_orders'

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    salesman_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    order_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    status = db.Column(db.String(30), nullable=False, default=OrderStatus.PENDING)
    
    total_taxable_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    total_tax_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    total_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    
    # Review details
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    review_notes = db.Column(db.Text, nullable=True)
    
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    customer = db.relationship('Customer', back_populates='orders')
    salesman = db.relationship('User', foreign_keys=[salesman_id])
    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_id])
    items = db.relationship('SalesOrderItem', back_populates='order', cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', back_populates='order')

    @property
    def has_shortage(self):
        return any(item.shortage_quantity > Decimal('0.00') for item in self.items)

    @property
    def total_shortage_units(self):
        return sum(item.shortage_quantity for item in self.items)

    def __repr__(self):
        return f'<SalesOrder {self.order_number} ({self.status}) - ₹{self.total_amount}>'

class SalesOrderItem(db.Model):
    __tablename__ = 'sales_order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('sales_orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    
    ordered_quantity = db.Column(db.Numeric(12, 2), nullable=False)
    approved_quantity = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    unit_price = db.Column(db.Numeric(12, 2), nullable=False) # Before tax
    gst_rate = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('5.00'))
    
    taxable_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    tax_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    total_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    
    # Stock check fields
    available_stock_at_review = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    shortage_quantity = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))

    order = db.relationship('SalesOrder', back_populates='items')
    product = db.relationship('Product')

    def __repr__(self):
        return f'<SalesOrderItem {self.product.name}: Ordered {self.ordered_quantity}, Approved {self.approved_quantity}>'
