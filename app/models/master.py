from datetime import datetime
from decimal import Decimal
from app import db

class UnitOfMeasure(db.Model):
    __tablename__ = 'units_of_measure'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False) # kg, litre, pcs, packets, cartons
    name = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f'<UnitOfMeasure {self.code}>'

class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    sku = db.Column(db.String(50), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)
    selling_price = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    hsn = db.Column(db.String(20), nullable=False, default='19059040') # HSN for Namkeen/Murukku
    gst_rate = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('5.00')) # 5% default
    unit = db.Column(db.String(20), nullable=False, default='Packets')
    status = db.Column(db.String(20), nullable=False, default='Active') # Active, Inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    boms = db.relationship('BOM', back_populates='product', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Product {self.sku} - {self.name}>'

class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    contact = db.Column(db.String(100), nullable=True) # Contact person name
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.Text, nullable=False)
    state = db.Column(db.String(50), nullable=False, default='Tamil Nadu')
    state_code = db.Column(db.String(10), nullable=False, default='33') # 33 for TN, 29 for KA, etc.
    gstin = db.Column(db.String(20), nullable=True) # 15 chars GSTIN
    customer_type = db.Column(db.String(30), nullable=False, default='Retailer') # Retailer, Distributor, Wholesaler
    status = db.Column(db.String(20), nullable=False, default='Active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    orders = db.relationship('SalesOrder', back_populates='customer')
    invoices = db.relationship('Invoice', back_populates='customer')

    def __repr__(self):
        return f'<Customer {self.name} ({self.state})>'

class Supplier(db.Model):
    __tablename__ = 'suppliers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    contact = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.Text, nullable=False)
    state = db.Column(db.String(50), nullable=False, default='Tamil Nadu')
    gst_details = db.Column(db.String(30), nullable=True) # Supplier GSTIN
    status = db.Column(db.String(20), nullable=False, default='Active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    purchases = db.relationship('PurchaseOrder', back_populates='supplier')

    def __repr__(self):
        return f'<Supplier {self.name}>'

class RawMaterial(db.Model):
    __tablename__ = 'raw_materials'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True, index=True)
    code = db.Column(db.String(50), nullable=False, unique=True)
    unit = db.Column(db.String(20), nullable=False) # kg, litre, pcs
    stock_threshold = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('10.00')) # Low-stock alert threshold
    cost = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00')) # Standard unit cost in INR
    status = db.Column(db.String(20), nullable=False, default='Active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<RawMaterial {self.name} ({self.unit})>'

class BOM(db.Model):
    __tablename__ = 'boms'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    batch_size = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('200.00')) # e.g. 200 packets
    unit = db.Column(db.String(20), nullable=False, default='Packets')
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product', back_populates='boms')
    items = db.relationship('BOMItem', back_populates='bom', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<BOM {self.name} for {self.batch_size} {self.unit}>'

class BOMItem(db.Model):
    __tablename__ = 'bom_items'

    id = db.Column(db.Integer, primary_key=True)
    bom_id = db.Column(db.Integer, db.ForeignKey('boms.id'), nullable=False)
    raw_material_id = db.Column(db.Integer, db.ForeignKey('raw_materials.id'), nullable=False)
    standard_quantity = db.Column(db.Numeric(12, 4), nullable=False) # Quantity needed for batch_size
    unit = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.String(200), nullable=True)

    bom = db.relationship('BOM', back_populates='items')
    raw_material = db.relationship('RawMaterial')

    def __repr__(self):
        return f'<BOMItem {self.raw_material.name}: {self.standard_quantity} {self.unit}>'
