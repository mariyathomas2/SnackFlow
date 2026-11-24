from decimal import Decimal
from datetime import datetime
from sqlalchemy import func
from app import db
from app.models.inventory import StockLedger, StockTransactionType, StockItemType
from app.models.master import RawMaterial, Product
from app.services.audit_service import log_audit

def get_current_stock(item_type, item_id):
    """
    Computes current stock balance dynamically from the immutable stock ledger.
    Every balance is directly derived from ledger transactions.
    """
    result = db.session.query(
        func.coalesce(func.sum(StockLedger.quantity_in - StockLedger.quantity_out), Decimal('0.0000'))
    ).filter(
        StockLedger.item_type == item_type,
        StockLedger.item_id == item_id
    ).scalar()
    
    return Decimal(str(result or '0.0000'))

def record_stock_movement(
    item_type,
    item_id,
    item_name,
    transaction_type,
    quantity_in=Decimal('0.0000'),
    quantity_out=Decimal('0.0000'),
    unit="",
    unit_cost=Decimal('0.00'),
    reference_type=None,
    reference_id=None,
    notes=None,
    user_id=None,
    allow_negative=False
):
    """
    Creates a new immutable StockLedger entry.
    Enforces no silent updates and strictly prevents negative stock.
    """
    qty_in = Decimal(str(quantity_in or '0'))
    qty_out = Decimal(str(quantity_out or '0'))
    cost_per_unit = Decimal(str(unit_cost or '0'))
    
    # Calculate previous balance from ledger
    current_bal = get_current_stock(item_type, item_id)
    new_bal = current_bal + qty_in - qty_out

    if new_bal < Decimal('0') and not allow_negative:
        raise ValueError(
            f"Cannot complete movement for '{item_name}'. "
            f"Requested deduction: {qty_out} {unit}, Current available: {current_bal} {unit}. "
            f"Negative inventory is strictly prohibited."
        )

    total_cost = (qty_in if qty_in > 0 else qty_out) * cost_per_unit

    ledger_entry = StockLedger(
        transaction_date=datetime.utcnow(),
        item_type=item_type,
        item_id=item_id,
        item_name=item_name,
        transaction_type=transaction_type,
        quantity_in=qty_in,
        quantity_out=qty_out,
        balance_after=new_bal,
        unit=unit,
        unit_cost=cost_per_unit,
        total_cost=total_cost,
        reference_type=reference_type,
        reference_id=reference_id,
        notes=notes,
        created_by_id=user_id
    )

    db.session.add(ledger_entry)
    db.session.flush() # Get ID without committing so caller controls transaction boundary

    log_audit(
        action=f"STOCK_{transaction_type}",
        entity_type="StockLedger",
        entity_id=ledger_entry.id,
        description=f"{transaction_type} for {item_name}: +{qty_in}/-{qty_out} {unit}. Balance: {new_bal} {unit}."
    )

    return ledger_entry

def get_raw_materials_summary():
    """
    Returns summary of all raw materials with current stock derived from ledger,
    threshold, unit cost, and stock valuation.
    """
    materials = RawMaterial.query.filter_by(status='Active').all()
    summary = []
    
    for rm in materials:
        current_stock = get_current_stock(StockItemType.RAW_MATERIAL, rm.id)
        is_low_stock = current_stock <= rm.stock_threshold
        stock_value = current_stock * rm.cost
        
        summary.append({
            'id': rm.id,
            'name': rm.name,
            'code': rm.code,
            'unit': rm.unit,
            'current_stock': current_stock,
            'threshold': rm.stock_threshold,
            'cost': rm.cost,
            'stock_value': stock_value,
            'is_low_stock': is_low_stock,
            'status': 'Low Stock' if is_low_stock else 'Optimal'
        })
    return summary

def get_finished_goods_summary():
    """
    Returns summary of all finished goods with current stock from ledger,
    selling price, and total retail valuation.
    """
    products = Product.query.filter_by(status='Active').all()
    summary = []
    
    for prod in products:
        current_stock = get_current_stock(StockItemType.FINISHED_GOOD, prod.id)
        stock_value = current_stock * prod.selling_price
        
        summary.append({
            'id': prod.id,
            'name': prod.name,
            'sku': prod.sku,
            'unit': prod.unit,
            'selling_price': prod.selling_price,
            'current_stock': current_stock,
            'stock_value': stock_value,
            'gst_rate': prod.gst_rate
        })
    return summary
