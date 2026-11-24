from datetime import datetime
from decimal import Decimal
from app import db

class ProductionRun(db.Model):
    __tablename__ = 'production_runs'

    id = db.Column(db.Integer, primary_key=True)
    batch_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    bom_id = db.Column(db.Integer, db.ForeignKey('boms.id'), nullable=True)
    run_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    status = db.Column(db.String(20), nullable=False, default='COMPLETED') # DRAFT, COMPLETED, CANCELLED

    # Quantities
    planned_quantity = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('200.00')) # e.g. 200 pkts
    actual_output_good = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00')) # e.g. 188 pkts
    damaged_units = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00')) # e.g. 6 pkts/pouches
    wastage_units = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    cartons_used = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00')) # e.g. 9 cartons
    
    # Variances
    yield_variance_pct = db.Column(db.Numeric(6, 2), nullable=False, default=Decimal('0.00')) # e.g. -6.00%
    
    # Financial Costing Breakdown
    total_material_cost = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    direct_labor_cost = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    power_fuel_cost = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    other_overheads = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    total_production_cost = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    cost_per_packet = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    selling_price_at_run = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('50.00'))
    gross_margin_per_packet = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    gross_margin_pct = db.Column(db.Numeric(6, 2), nullable=False, default=Decimal('0.00'))

    notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    product = db.relationship('Product')
    bom = db.relationship('BOM')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    consumptions = db.relationship('ProductionConsumption', back_populates='production_run', cascade='all, delete-orphan')

    @property
    def has_yield_variance_alert(self):
        # Alert if yield variance is worse than -2%
        return self.yield_variance_pct < Decimal('-2.00')

    def __repr__(self):
        return f'<ProductionRun {self.batch_number} - Output: {self.actual_output_good} Good pkts>'

class ProductionConsumption(db.Model):
    __tablename__ = 'production_consumptions'

    id = db.Column(db.Integer, primary_key=True)
    production_run_id = db.Column(db.Integer, db.ForeignKey('production_runs.id'), nullable=False)
    raw_material_id = db.Column(db.Integer, db.ForeignKey('raw_materials.id'), nullable=False)
    planned_quantity = db.Column(db.Numeric(12, 4), nullable=False, default=Decimal('0.0000'))
    actual_quantity = db.Column(db.Numeric(12, 4), nullable=False, default=Decimal('0.0000'))
    wastage_quantity = db.Column(db.Numeric(12, 4), nullable=False, default=Decimal('0.0000'))
    unit = db.Column(db.String(20), nullable=False)
    unit_cost = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    total_cost = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    variance_quantity = db.Column(db.Numeric(12, 4), nullable=False, default=Decimal('0.0000')) # actual - planned
    variance_pct = db.Column(db.Numeric(6, 2), nullable=False, default=Decimal('0.00')) # ((actual - planned)/planned)*100
    notes = db.Column(db.String(200), nullable=True)

    production_run = db.relationship('ProductionRun', back_populates='consumptions')
    raw_material = db.relationship('RawMaterial')

    @property
    def has_consumption_variance_alert(self):
        # Alert if actual exceeds planned by > 2%
        return self.variance_pct > Decimal('2.00')

    def __repr__(self):
        return f'<ProductionConsumption {self.raw_material.name}: Plan {self.planned_quantity} -> Act {self.actual_quantity} ({self.variance_pct}%)>'
