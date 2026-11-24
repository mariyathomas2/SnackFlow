from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.user import Role
from app.models.master import Product, Customer, Supplier, RawMaterial, BOM, BOMItem, UnitOfMeasure
from app.routes.auth import role_required
from app.services.audit_service import log_audit

master_bp = Blueprint('master', __name__)

# --- PRODUCTS ---
@master_bp.route('/products', methods=['GET', 'POST'])
@role_required(Role.FACTORY_ADMIN, Role.PRODUCTION_SUPERVISOR, Role.OWNER)
def products():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        sku = request.form.get('sku', '').strip().upper()
        description = request.form.get('description', '').strip()
        selling_price = Decimal(request.form.get('selling_price', '0.00'))
        hsn = request.form.get('hsn', '19059040').strip()
        gst_rate = Decimal(request.form.get('gst_rate', '5.00'))
        unit = request.form.get('unit', 'Packets').strip()
        status = request.form.get('status', 'Active')

        existing = Product.query.filter((Product.sku == sku) | (Product.name == name)).first()
        if existing:
            flash(f"Product with name '{name}' or SKU '{sku}' already exists.", "danger")
        else:
            product = Product(
                name=name,
                sku=sku,
                description=description,
                selling_price=selling_price,
                hsn=hsn,
                gst_rate=gst_rate,
                unit=unit,
                status=status
            )
            db.session.add(product)
            db.session.commit()
            log_audit("CREATE_PRODUCT", "Product", product.id, f"Created product {product.name} (SKU: {product.sku})")
            flash(f"Product '{product.name}' created successfully.", "success")
        return redirect(url_for('master.products'))

    product_list = Product.query.order_by(Product.name.asc()).all()
    return render_template('master/products.html', products=product_list)

@master_bp.route('/products/<int:id>/edit', methods=['POST'])
@role_required(Role.FACTORY_ADMIN, Role.OWNER)
def edit_product(id):
    product = Product.query.get_or_404(id)
    product.name = request.form.get('name', product.name).strip()
    product.selling_price = Decimal(request.form.get('selling_price', str(product.selling_price)))
    product.hsn = request.form.get('hsn', product.hsn).strip()
    product.gst_rate = Decimal(request.form.get('gst_rate', str(product.gst_rate)))
    product.status = request.form.get('status', product.status)
    product.description = request.form.get('description', product.description).strip()
    
    db.session.commit()
    log_audit("UPDATE_PRODUCT", "Product", product.id, f"Updated product {product.name}")
    flash(f"Product '{product.name}' updated successfully.", "success")
    return redirect(url_for('master.products'))

# --- CUSTOMERS ---
@master_bp.route('/customers', methods=['GET', 'POST'])
@login_required
def customers():
    if request.method == 'POST':
        if not (current_user.has_role(Role.FACTORY_ADMIN, Role.SALESMAN, Role.OWNER)):
            flash("You do not have permission to add customers.", "danger")
            return redirect(url_for('master.customers'))

        name = request.form.get('name', '').strip()
        contact = request.form.get('contact', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        state = request.form.get('state', 'Tamil Nadu').strip()
        state_code = request.form.get('state_code', '33').strip()
        gstin = request.form.get('gstin', '').strip().upper()
        customer_type = request.form.get('customer_type', 'Retailer')

        customer = Customer(
            name=name,
            contact=contact,
            phone=phone,
            email=email,
            address=address,
            state=state,
            state_code=state_code,
            gstin=gstin if gstin else None,
            customer_type=customer_type,
            status='Active'
        )
        db.session.add(customer)
        db.session.commit()
        log_audit("CREATE_CUSTOMER", "Customer", customer.id, f"Created customer {customer.name} ({customer.state})")
        flash(f"Customer '{customer.name}' registered successfully.", "success")
        return redirect(url_for('master.customers'))

    customer_list = Customer.query.order_by(Customer.name.asc()).all()
    return render_template('master/customers.html', customers=customer_list)

# --- SUPPLIERS ---
@master_bp.route('/suppliers', methods=['GET', 'POST'])
@role_required(Role.FACTORY_ADMIN, Role.PRODUCTION_SUPERVISOR, Role.OWNER)
def suppliers():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        contact = request.form.get('contact', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        state = request.form.get('state', 'Tamil Nadu').strip()
        gst_details = request.form.get('gst_details', '').strip().upper()

        supplier = Supplier(
            name=name,
            contact=contact,
            phone=phone,
            email=email,
            address=address,
            state=state,
            gst_details=gst_details if gst_details else None,
            status='Active'
        )
        db.session.add(supplier)
        db.session.commit()
        log_audit("CREATE_SUPPLIER", "Supplier", supplier.id, f"Created supplier {supplier.name}")
        flash(f"Supplier '{supplier.name}' registered successfully.", "success")
        return redirect(url_for('master.suppliers'))

    supplier_list = Supplier.query.order_by(Supplier.name.asc()).all()
    return render_template('master/suppliers.html', suppliers=supplier_list)

# --- RAW MATERIALS ---
@master_bp.route('/raw-materials', methods=['GET', 'POST'])
@role_required(Role.FACTORY_ADMIN, Role.PRODUCTION_SUPERVISOR, Role.OWNER)
def raw_materials():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()
        unit = request.form.get('unit', 'kg').strip()
        stock_threshold = Decimal(request.form.get('stock_threshold', '10.00'))
        cost = Decimal(request.form.get('cost', '0.00'))

        existing = RawMaterial.query.filter((RawMaterial.code == code) | (RawMaterial.name == name)).first()
        if existing:
            flash(f"Raw material '{name}' or code '{code}' already exists.", "danger")
        else:
            rm = RawMaterial(
                name=name,
                code=code,
                unit=unit,
                stock_threshold=stock_threshold,
                cost=cost,
                status='Active'
            )
            db.session.add(rm)
            db.session.commit()
            log_audit("CREATE_RAW_MATERIAL", "RawMaterial", rm.id, f"Created raw material {rm.name} ({rm.unit})")
            flash(f"Raw material '{rm.name}' added successfully.", "success")
        return redirect(url_for('master.raw_materials'))

    materials = RawMaterial.query.order_by(RawMaterial.name.asc()).all()
    return render_template('master/raw_materials.html', materials=materials)

# --- BILL OF MATERIALS (BOM) ---
@master_bp.route('/bom', methods=['GET', 'POST'])
@role_required(Role.FACTORY_ADMIN, Role.PRODUCTION_SUPERVISOR, Role.OWNER)
def bom():
    if request.method == 'POST':
        product_id = int(request.form.get('product_id'))
        name = request.form.get('name', '').strip()
        batch_size = Decimal(request.form.get('batch_size', '200.00'))
        unit = request.form.get('unit', 'Packets').strip()
        description = request.form.get('description', '').strip()

        bom_obj = BOM(
            product_id=product_id,
            name=name,
            batch_size=batch_size,
            unit=unit,
            description=description,
            is_active=True
        )
        db.session.add(bom_obj)
        db.session.flush()

        # Parse dynamic item rows
        raw_ids = request.form.getlist('raw_material_id[]')
        quantities = request.form.getlist('quantity[]')
        units = request.form.getlist('item_unit[]')

        for r_id, qty, u in zip(raw_ids, quantities, units):
            if r_id and qty:
                bom_item = BOMItem(
                    bom_id=bom_obj.id,
                    raw_material_id=int(r_id),
                    standard_quantity=Decimal(str(qty)),
                    unit=u.strip()
                )
                db.session.add(bom_item)

        db.session.commit()
        log_audit("CREATE_BOM", "BOM", bom_obj.id, f"Created BOM '{bom_obj.name}' for batch size {batch_size} {unit}")
        flash(f"BOM '{bom_obj.name}' created successfully.", "success")
        return redirect(url_for('master.bom'))

    boms = BOM.query.order_by(BOM.id.desc()).all()
    products = Product.query.filter_by(status='Active').all()
    raw_materials = RawMaterial.query.filter_by(status='Active').all()
    return render_template('master/bom.html', boms=boms, products=products, raw_materials=raw_materials)
