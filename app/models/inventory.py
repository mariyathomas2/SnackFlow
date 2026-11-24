from datetime import datetime
from decimal import Decimal
from app import db

class StockTransactionType:
    OPENING_STOCK = 'OPENING_STOCK'
    PURCHASE_RECEIPT = 'PURCHASE_RECEIPT'
    PRODUCTION_ISSUE = 'PRODUCTION_ISSUE'
    MATERIAL_WASTAGE = 'MATERIAL_WASTAGE'
    FG_PRODUCTION_OUTPUT = 'FG_PRODUCTION_OUTPUT'
    DISPATCH = 'DISPATCH'
    STOCK_ADJUSTMENT = 'STOCK_ADJUSTMENT'

    ALL = [
        OPENING_STOCK,
        PURCHASE_RECEIPT,
        PRODUCTION_ISSUE,
        MATERIAL_WASTAGE,
        FG_PRODUCTION_OUTPUT,
        DISPATCH,
        STOCK_ADJUSTMENT
    ]

class StockItemType:
    RAW_MATERIAL = 'RAW_MATERIAL'
    FINISHED_GOOD = 'FINISHED_GOOD'

class StockLedger(db.Model):
    __tablename__ = 'stock_ledger'

    id = db.Column(db.Integer, primary_key=True)
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    item_type = db.Column(db.String(30), nullable=False, index=True) # RAW_MATERIAL, FINISHED_GOOD
    item_id = db.Column(db.Integer, nullable=False, index=True) # RawMaterial.id or Product.id
    item_name = db.Column(db.String(150), nullable=False)
    transaction_type = db.Column(db.String(40), nullable=False, index=True)
    quantity_in = db.Column(db.Numeric(12, 4), nullable=False, default=Decimal('0.0000'))
    quantity_out = db.Column(db.Numeric(12, 4), nullable=False, default=Decimal('0.0000'))
    balance_after = db.Column(db.Numeric(12, 4), nullable=False, default=Decimal('0.0000'))
    unit = db.Column(db.String(20), nullable=False)
    unit_cost = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    total_cost = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    reference_type = db.Column(db.String(50), nullable=True) # PURCHASE_ORDER, PRODUCTION_RUN, DISPATCH, etc.
    reference_id = db.Column(db.String(50), nullable=True) # e.g. PO-001, PR-2026-001, DISP-001
    notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    created_by = db.relationship('User', foreign_keys=[created_by_id])

    @property
    def net_movement(self):
        return self.quantity_in - self.quantity_out

    def __repr__(self):
        return f'<StockLedger {self.transaction_type} {self.item_name}: +{self.quantity_in}/-{self.quantity_out} Bal={self.balance_after}>'
