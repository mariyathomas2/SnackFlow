from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.user import Role
from app.models.inventory import StockLedger, StockTransactionType, StockItemType
from app.models.master import RawMaterial, Product
from app.routes.auth import role_required
from app.services.inventory_service import (
    get_raw_materials_summary, get_finished_goods_summary,
    record_stock_movement, get_current_stock
)
from app.services.audit_service import log_audit

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/raw-materials')
@login_required
def raw_materials():
    summary = get_raw_materials_summary()
    total_valuation = sum(item['stock_value'] for item in summary)
    low_stock_count = sum(1 for item in summary if item['is_low_stock'])
    return render_template(
        'inventory/raw_materials.html',
        summary=summary,
        total_valuation=total_valuation,
        low_stock_count=low_stock_count
    )

@inventory_bp.route('/finished-goods')
@login_required
def finished_goods():
    summary = get_finished_goods_summary()
    total_retail_val = sum(item['stock_value'] for item in summary)
    return render_template(
        'inventory/finished_goods.html',
        summary=summary,
        total_retail_val=total_retail_val
    )

@inventory_bp.route('/ledger')
@login_required
def ledger():
    item_type = request.args.get('item_type', '')
    transaction_type = request.args.get('transaction_type', '')
    search = request.args.get('search', '').strip()

    query = StockLedger.query.order_by(StockLedger.id.desc())

    if item_type:
        query = query.filter(StockLedger.item_type == item_type)
    if transaction_type:
        query = query.filter(StockLedger.transaction_type == transaction_type)
    if search:
        query = query.filter(StockLedger.item_name.ilike(f"%{search}%") | StockLedger.reference_id.ilike(f"%{search}%"))

    entries = query.limit(200).all()

    return render_template(
        'inventory/ledger.html',
        entries=entries,
        current_item_type=item_type,
        current_tx_type=transaction_type,
        search=search,
        transaction_types=StockTransactionType.ALL
    )

@inventory_bp.route('/adjust', methods=['GET', 'POST'])
@role_required(Role.FACTORY_ADMIN, Role.OWNER)
def adjust():
    if request.method == 'POST':
        item_type = request.form.get('item_type')
        item_id = int(request.form.get('item_id'))
        adjustment_type = request.form.get('adjustment_type') # 'ADD' or 'DEDUCT'
        quantity = Decimal(request.form.get('quantity', '0'))
        reason = request.form.get('reason', '').strip()

        if quantity <= Decimal('0'):
            flash("Adjustment quantity must be greater than zero.", "danger")
            return redirect(url_for('inventory.adjust'))

        if not reason:
            flash("Audit reason is mandatory for manual stock adjustments.", "danger")
            return redirect(url_for('inventory.adjust'))

        try:
            if item_type == StockItemType.RAW_MATERIAL:
                item = RawMaterial.query.get_or_404(item_id)
                unit_cost = item.cost
            else:
                item = Product.query.get_or_404(item_id)
                unit_cost = item.selling_price

            qty_in = quantity if adjustment_type == 'ADD' else Decimal('0.0000')
            qty_out = quantity if adjustment_type == 'DEDUCT' else Decimal('0.0000')

            record_stock_movement(
                item_type=item_type,
                item_id=item.id,
                item_name=item.name,
                transaction_type=StockTransactionType.STOCK_ADJUSTMENT,
                quantity_in=qty_in,
                quantity_out=qty_out,
                unit=item.unit,
                unit_cost=unit_cost,
                reference_type="MANUAL_ADJUSTMENT",
                reference_id=f"ADJ-{current_user.username}",
                notes=reason,
                user_id=current_user.id
            )
            db.session.commit()
            flash(f"Stock adjustment recorded successfully for '{item.name}'.", "success")
            return redirect(url_for('inventory.ledger'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error performing adjustment: {str(e)}", "danger")
            return redirect(url_for('inventory.adjust'))

    raw_materials = RawMaterial.query.filter_by(status='Active').all()
    products = Product.query.filter_by(status='Active').all()
    return render_template('inventory/adjust.html', raw_materials=raw_materials, products=products)
