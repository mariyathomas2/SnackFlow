from datetime import datetime
from decimal import Decimal
from app import db

class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_orders'

    id = db.Column(db.Integer, primary_key=True)
    po_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    purchase_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    status = db.Column(db.String(20), nullable=False, default='RECEIVED') # RECEIVED, PENDING, CANCELLED
    total_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    supplier = db.relationship('Supplier', back_populates='purchases')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    items = db.relationship('PurchaseItem', back_populates='purchase_order', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<PurchaseOrder {self.po_number} - ₹{self.total_amount}>'

class PurchaseItem(db.Model):
    __tablename__ = 'purchase_items'

    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=False)
    raw_material_id = db.Column(db.Integer, db.ForeignKey('raw_materials.id'), nullable=False)
    quantity = db.Column(db.Numeric(12, 4), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    unit_cost = db.Column(db.Numeric(12, 2), nullable=False)
    total_cost = db.Column(db.Numeric(12, 2), nullable=False)

    purchase_order = db.relationship('PurchaseOrder', back_populates='items')
    raw_material = db.relationship('RawMaterial')

    def __repr__(self):
        return f'<PurchaseItem {self.raw_material.name}: {self.quantity} {self.unit} @ ₹{self.unit_cost}>'
