from decimal import Decimal
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.user import Role
from app.models.production import ProductionRun, ProductionConsumption
from app.models.master import Product, BOM, RawMaterial
from app.routes.auth import role_required
from app.services.production_service import calculate_planned_materials, create_production_run

production_bp = Blueprint('production', __name__)

@production_bp.route('/')
@role_required(Role.PRODUCTION_SUPERVISOR, Role.FACTORY_ADMIN, Role.ACCOUNTANT, Role.OWNER)
def index():
    runs = ProductionRun.query.order_by(ProductionRun.run_date.desc(), ProductionRun.id.desc()).all()
    return render_template('production/index.html', runs=runs)

@production_bp.route('/<int:id>')
@role_required(Role.PRODUCTION_SUPERVISOR, Role.FACTORY_ADMIN, Role.ACCOUNTANT, Role.OWNER)
def view(id):
    run = ProductionRun.query.get_or_404(id)
    return render_template('production/view.html', run=run)

@production_bp.route('/bom-calc/<int:bom_id>/<planned_qty>')
@login_required
def bom_calc(bom_id, planned_qty):
    """
    API endpoint for dynamic BOM calculation in the production run form.
    Returns calculated material requirements and stock availability.
    """
    try:
        qty = Decimal(planned_qty)
        requirements = calculate_planned_materials(bom_id, qty)
        return jsonify({
            'success': True,
            'requirements': [
                {
                    'raw_material_id': r['raw_material_id'],
                    'material_name': r['material_name'],
                    'unit': r['unit'],
                    'standard_qty': float(r['standard_qty']),
                    'required_qty': float(r['required_qty']),
                    'current_stock': float(r['current_stock']),
                    'shortage': float(r['shortage']),
                    'unit_cost': float(r['unit_cost']),
                    'estimated_cost': float(r['estimated_cost'])
                }
                for r in requirements
            ]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@production_bp.route('/create', methods=['GET', 'POST'])
@role_required(Role.PRODUCTION_SUPERVISOR, Role.FACTORY_ADMIN, Role.OWNER)
def create():
    if request.method == 'POST':
        product_id = int(request.form.get('product_id'))
        bom_id = int(request.form.get('bom_id')) if request.form.get('bom_id') else None
        planned_quantity = Decimal(request.form.get('planned_quantity', '200'))
        actual_output_good = Decimal(request.form.get('actual_output_good', '0'))
        damaged_units = Decimal(request.form.get('damaged_units', '0'))
        cartons_used = Decimal(request.form.get('cartons_used', '0'))
        
        labor_cost = Decimal(request.form.get('direct_labor_cost', '0'))
        power_cost = Decimal(request.form.get('power_fuel_cost', '0'))
        other_overheads = Decimal(request.form.get('other_overheads', '0'))
        notes = request.form.get('notes', '').strip()

        # Parse consumed materials
        raw_ids = request.form.getlist('raw_material_id[]')
        planned_qtys = request.form.getlist('planned_qty[]')
        actual_qtys = request.form.getlist('actual_qty[]')
        wastage_qtys = request.form.getlist('wastage_qty[]')

        consumptions = []
        for r_id, p_qty, a_qty, w_qty in zip(raw_ids, planned_qtys, actual_qtys, wastage_qtys):
            if r_id:
                consumptions.append({
                    'raw_material_id': int(r_id),
                    'planned_qty': Decimal(str(p_qty or '0')),
                    'actual_qty': Decimal(str(a_qty or '0')),
                    'wastage_qty': Decimal(str(w_qty or '0'))
                })

        try:
            prod_run = create_production_run(
                product_id=product_id,
                bom_id=bom_id,
                planned_quantity=planned_quantity,
                actual_output_good=actual_output_good,
                damaged_units=damaged_units,
                cartons_used=cartons_used,
                material_consumptions=consumptions,
                direct_labor_cost=labor_cost,
                power_fuel_cost=power_cost,
                other_overheads=other_overheads,
                notes=notes,
                user_id=current_user.id
            )

            # Flash alerts if yield variance or consumption variance occurred
            msg = f"Production run '{prod_run.batch_number}' completed! Output: {prod_run.actual_output_good} good packets."
            if prod_run.yield_variance_pct < Decimal('-2.00'):
                msg += f" (ALERT: Yield Variance is {prod_run.yield_variance_pct}%)"
            flash(msg, "warning" if prod_run.yield_variance_pct < Decimal('-2.00') else "success")

            return redirect(url_for('production.view', id=prod_run.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error completing production run: {str(e)}", "danger")
            return redirect(url_for('production.create'))

    products = Product.query.filter_by(status='Active').all()
    boms = BOM.query.filter_by(is_active=True).all()
    raw_materials = RawMaterial.query.filter_by(status='Active').all()

    return render_template(
        'production/create.html',
        products=products,
        boms=boms,
        raw_materials=raw_materials,
        today=date.today()
    )
