from decimal import Decimal
from datetime import datetime, date
from app import db
from app.models.dispatch import DispatchRecord, DispatchItem
from app.models.invoice import Invoice
from app.models.sales import SalesOrder, OrderStatus
from app.models.inventory import StockItemType, StockTransactionType
from app.services.inventory_service import get_current_stock, record_stock_movement
from app.services.audit_service import log_audit

def create_dispatch(
    order_id,
    invoice_id=None,
    carrier_name=None,
    vehicle_number=None,
    tracking_number=None,
    dispatch_date=None,
    notes=None,
    user_id=None
):
    """
    Creates a dispatch record and performs the atomic Finished Goods deduction
    via the stock ledger. Prevents duplicate stock deductions.
    """
    order = SalesOrder.query.get(order_id)
    if not order:
        raise ValueError(f"Sales order {order_id} not found.")

    invoice = None
    if invoice_id:
        invoice = Invoice.query.get(invoice_id)
    elif order.invoices:
        invoice = order.invoices[0]

    # Generate sequential dispatch number DSP-YYYYMMDD-XXXX
    count_today = DispatchRecord.query.filter(
        DispatchRecord.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
    ).count() + 1
    dispatch_number = f"DSP-{datetime.utcnow().strftime('%Y%m%d')}-{count_today:04d}"

    dsp_date = dispatch_date or date.today()

    dispatch = DispatchRecord(
        dispatch_number=dispatch_number,
        order_id=order.id,
        invoice_id=invoice.id if invoice else None,
        dispatch_date=dsp_date,
        carrier_name=carrier_name or "Factory Direct / Transport",
        vehicle_number=vehicle_number,
        tracking_number=tracking_number,
        status='DISPATCHED',
        notes=notes,
        created_by_id=user_id
    )
    db.session.add(dispatch)
    db.session.flush()

    total_qty = Decimal('0.00')

    # Deduct finished goods for each approved order item
    for item in order.items:
        qty_to_dispatch = item.approved_quantity if item.approved_quantity > Decimal('0') else item.ordered_quantity
        if qty_to_dispatch <= Decimal('0'):
            continue

        product = item.product

        # Check stock before dispatching
        current_stock = get_current_stock(StockItemType.FINISHED_GOOD, product.id)
        if qty_to_dispatch > current_stock:
            raise ValueError(
                f"Cannot dispatch {qty_to_dispatch} {product.unit} of '{product.name}'. "
                f"Only {current_stock} available in finished goods stock."
            )

        dispatch_item = DispatchItem(
            dispatch_id=dispatch.id,
            product_id=product.id,
            quantity=qty_to_dispatch,
            unit=product.unit
        )
        db.session.add(dispatch_item)
        total_qty += qty_to_dispatch

        # Atomic Finished Goods stock deduction via StockLedger
        record_stock_movement(
            item_type=StockItemType.FINISHED_GOOD,
            item_id=product.id,
            item_name=product.name,
            transaction_type=StockTransactionType.DISPATCH,
            quantity_out=qty_to_dispatch,
            unit=product.unit,
            unit_cost=product.selling_price,
            reference_type="SALES_DISPATCH",
            reference_id=dispatch_number,
            notes=f"Dispatched against order {order.order_number} / inv {invoice.invoice_number if invoice else 'N/A'}",
            user_id=user_id
        )

    dispatch.total_quantity = total_qty
    order.status = OrderStatus.DISPATCHED

    db.session.commit()

    log_audit(
        action="DISPATCH_ORDER",
        entity_type="DispatchRecord",
        entity_id=dispatch.id,
        description=f"Dispatched {total_qty} units under {dispatch_number} for order {order.order_number}."
    )

    return dispatch
