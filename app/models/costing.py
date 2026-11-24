from datetime import datetime, date
from decimal import Decimal
from app import db

class ExpenseCategory:
    DIRECT_LABOUR = 'DIRECT_LABOUR'
    POWER_GAS = 'POWER_GAS'
    PACKAGING_CONSUMABLES = 'PACKAGING_CONSUMABLES'
    EQUIPMENT_MAINTENANCE = 'EQUIPMENT_MAINTENANCE'
    FACTORY_OVERHEAD = 'FACTORY_OVERHEAD'

    ALL = [DIRECT_LABOUR, POWER_GAS, PACKAGING_CONSUMABLES, EQUIPMENT_MAINTENANCE, FACTORY_OVERHEAD]

class ProductionExpense(db.Model):
    __tablename__ = 'production_expenses'

    id = db.Column(db.Integer, primary_key=True)
    expense_date = db.Column(db.Date, nullable=False, default=date.today)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    production_run_id = db.Column(db.Integer, db.ForeignKey('production_runs.id'), nullable=True) # If linked to batch
    notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    production_run = db.relationship('ProductionRun')
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    def __repr__(self):
        return f'<ProductionExpense {self.category}: ₹{self.amount}>'
