from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.user import Role
from app.models.purchase import PurchaseOrder, PurchaseItem
from app.models.master import Supplier, RawMaterial
from app.models.inventory import StockItemType, StockTransactionType
from app.routes.auth import role_required
from app.services.inventory_service import record_stock_movement
from app.services.audit_service import log_audit

purchases_bp = Blueprint('purchases', __name__)

@purchases_bp.route('/')
@role_required(Role.FACTORY_ADMIN, Role.ACCOUNTANT, Role.OWNER)
def index():
    orders = PurchaseOrder.query.order_by(PurchaseOrder.purchase_date.desc(), PurchaseOrder.id.desc()).all()
    total_spend = sum(po.total_amount for po in orders)
    return render_template('purchases/index.html', orders=orders, total_spend=total_spend)

@purchases_bp.route('/create', methods=['GET', 'POST'])
@role_required(Role.FACTORY_ADMIN, Role.OWNER)
def create():
    if request.method == 'POST':
        supplier_id = int(request.form.get('supplier_id'))
        purchase_date_str = request.form.get('purchase_date')
        notes = request.form.get('notes', '').strip()

        raw_ids = request.form.getlist('raw_material_id[]')
        quantities = request.form.getlist('quantity[]')
        unit_costs = request.form.getlist('unit_cost[]')

        if not raw_ids or not any(raw_ids):
            flash("Please add at least one material to the purchase receipt.", "danger")
            return redirect(url_for('purchases.create'))

        supplier = Supplier.query.get_or_404(supplier_id)
        p_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date() if purchase_date_str else date.today()

        # Generate sequential PO number PO-YYYYMMDD-XXXX
        count_today = PurchaseOrder.query.filter(
            PurchaseOrder.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
        ).count() + 1
        po_number = f"PO-{datetime.utcnow().strftime('%Y%m%d')}-{count_today:04d}"

        po = PurchaseOrder(
            po_number=po_number,
            supplier_id=supplier.id,
            purchase_date=p_date,
            status='RECEIVED',
            notes=notes,
            created_by_id=current_user.id
        )
        db.session.add(po)
        db.session.flush()

        total_amount = Decimal('0.00')

        for r_id, qty, cost in zip(raw_ids, quantities, unit_costs):
            if r_id and qty and cost:
                rm = RawMaterial.query.get(int(r_id))
                qty_dec = Decimal(str(qty))
                cost_dec = Decimal(str(cost))
                line_total = (qty_dec * cost_dec).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                total_amount += line_total

                item = PurchaseItem(
                    purchase_id=po.id,
                    raw_material_id=rm.id,
                    quantity=qty_dec,
                    unit=rm.unit,
                    unit_cost=cost_dec,
                    total_cost=line_total
                )
                db.session.add(item)

                # Record stock receipt in immutable stock ledger
                record_stock_movement(
                    item_type=StockItemType.RAW_MATERIAL,
                    item_id=rm.id,
                    item_name=rm.name,
                    transaction_type=StockTransactionType.PURCHASE_RECEIPT,
                    quantity_in=qty_dec,
                    unit=rm.unit,
                    unit_cost=cost_dec,
                    reference_type="PURCHASE_ORDER",
                    reference_id=po.po_number,
                    notes=f"Received from {supplier.name}",
                    user_id=current_user.id
                )

        po.total_amount = total_amount
        db.session.commit()

        log_audit(
            action="CREATE_PURCHASE_RECEIPT",
            entity_type="PurchaseOrder",
            entity_id=po.id,
            description=f"Recorded purchase receipt {po.po_number} from {supplier.name}. Total: ₹{total_amount}"
        )

        flash(f"Purchase receipt '{po.po_number}' recorded and raw materials added to inventory.", "success")
        return redirect(url_for('purchases.index'))

    suppliers = Supplier.query.filter_by(status='Active').all()
    raw_materials = RawMaterial.query.filter_by(status='Active').all()
    return render_template('purchases/create.html', suppliers=suppliers, raw_materials=raw_materials, today=date.today())
