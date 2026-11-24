from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date
from app import db
from app.models.sales import SalesOrder, SalesOrderItem, OrderStatus
from app.models.master import Customer, Product
from app.models.inventory import StockItemType
from app.services.inventory_service import get_current_stock
from app.services.audit_service import log_audit

def create_sales_order(customer_id, salesman_id, items_data, notes=None, order_date=None):
    """
    Creates a new SalesOrder in PENDING status.
    items_data: list of dicts: {'product_id': id, 'quantity': qty}
    """
    customer = Customer.query.get(customer_id)
    if not customer:
        raise ValueError(f"Customer {customer_id} not found.")

    if not items_data or len(items_data) == 0:
        raise ValueError("Order must contain at least one product.")

    # Generate sequential order number SO-YYYYMMDD-XXXX
    count_today = SalesOrder.query.filter(
        SalesOrder.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
    ).count() + 1
    order_number = f"SO-{datetime.utcnow().strftime('%Y%m%d')}-{count_today:04d}"

    order = SalesOrder(
        order_number=order_number,
        customer_id=customer.id,
        salesman_id=salesman_id,
        order_date=order_date or date.today(),
        status=OrderStatus.PENDING,
        notes=notes
    )
    db.session.add(order)
    db.session.flush()

    total_taxable = Decimal('0.00')
    total_tax = Decimal('0.00')

    for itm in items_data:
        product = Product.query.get(itm['product_id'])
        if not product:
            raise ValueError(f"Product {itm['product_id']} not found.")

        qty = Decimal(str(itm['quantity']))
        if qty <= Decimal('0'):
            raise ValueError(f"Quantity for {product.name} must be greater than zero.")

        # Unit price is product's selling price
        unit_price = product.selling_price
        gst_rate = product.gst_rate
        taxable = (qty * unit_price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        tax = (taxable * (gst_rate / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        line_total = taxable + tax

        # Check stock availability at creation
        available_stock = get_current_stock(StockItemType.FINISHED_GOOD, product.id)
        shortage = max(Decimal('0.00'), qty - available_stock)

        order_item = SalesOrderItem(
            order_id=order.id,
            product_id=product.id,
            ordered_quantity=qty,
            approved_quantity=Decimal('0.00'),
            unit_price=unit_price,
            gst_rate=gst_rate,
            taxable_amount=taxable,
            tax_amount=tax,
            total_amount=line_total,
            available_stock_at_review=available_stock,
            shortage_quantity=shortage
        )
        db.session.add(order_item)

        total_taxable += taxable
        total_tax += tax

    order.total_taxable_amount = total_taxable
    order.total_tax_amount = total_tax
    order.total_amount = total_taxable + total_tax

    db.session.commit()

    log_audit(
        action="CREATE_SALES_ORDER",
        entity_type="SalesOrder",
        entity_id=order.id,
        description=f"Salesman created order {order.order_number} for {customer.name}. Total: ₹{order.total_amount}"
    )

    return order

def review_stock_and_shortage(order_id):
    """
    Refreshes the live stock availability and shortage calculation for an order.
    """
    order = SalesOrder.query.get(order_id)
    if not order:
        raise ValueError(f"Order {order_id} not found.")

    details = []
    has_shortage = False

    for item in order.items:
        current_stock = get_current_stock(StockItemType.FINISHED_GOOD, item.product_id)
        shortage = max(Decimal('0.00'), item.ordered_quantity - current_stock)
        
        item.available_stock_at_review = current_stock
        item.shortage_quantity = shortage
        if shortage > Decimal('0.00'):
            has_shortage = True

        details.append({
            'item_id': item.id,
            'product_name': item.product.name,
            'sku': item.product.sku,
            'ordered_qty': item.ordered_quantity,
            'available_stock': current_stock,
            'shortage_qty': shortage,
            'unit_price': item.unit_price,
            'taxable_amount': item.taxable_amount,
            'total_amount': item.total_amount
        })

    db.session.commit()
    return {
        'order': order,
        'has_shortage': has_shortage,
        'items': details
    }

def approve_sales_order(order_id, admin_user_id, approved_items=None, review_notes=None):
    """
    Approves a sales order.
    Enforces that approved quantity cannot exceed available stock!
    Allows partial fulfillment if specified, or full fulfillment if stock is sufficient.
    """
    order = SalesOrder.query.get(order_id)
    if not order:
        raise ValueError(f"Order {order_id} not found.")

    if order.status != OrderStatus.PENDING:
        raise ValueError(f"Order {order.order_number} is already in {order.status} state.")

    # Refresh stock check
    review_stock_and_shortage(order.id)

    total_taxable = Decimal('0.00')
    total_tax = Decimal('0.00')

    # If specific approved_items dict is passed {item_id: approved_qty}
    approved_map = {}
    if approved_items:
        approved_map = {int(k): Decimal(str(v)) for k, v in approved_items.items()}

    for item in order.items:
        current_stock = get_current_stock(StockItemType.FINISHED_GOOD, item.product_id)
        
        if item.id in approved_map:
            app_qty = approved_map[item.id]
        else:
            # Default to min of ordered and available
            app_qty = min(item.ordered_quantity, current_stock)

        if app_qty > current_stock:
            raise ValueError(
                f"Cannot approve {app_qty} units for {item.product.name}. "
                f"Only {current_stock} units currently available in inventory."
            )

        item.approved_quantity = app_qty
        item.available_stock_at_review = current_stock
        item.shortage_quantity = max(Decimal('0.00'), item.ordered_quantity - app_qty)

        taxable = (app_qty * item.unit_price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        tax = (taxable * (item.gst_rate / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        item.taxable_amount = taxable
        item.tax_amount = tax
        item.total_amount = taxable + tax

        total_taxable += taxable
        total_tax += tax

    order.total_taxable_amount = total_taxable
    order.total_tax_amount = total_tax
    order.total_amount = total_taxable + total_tax
    order.status = OrderStatus.APPROVED
    order.reviewed_by_id = admin_user_id
    order.reviewed_at = datetime.utcnow()
    order.review_notes = review_notes

    db.session.commit()

    log_audit(
        action="APPROVE_SALES_ORDER",
        entity_type="SalesOrder",
        entity_id=order.id,
        description=f"Admin approved order {order.order_number}. Approved Amount: ₹{order.total_amount}. Shortage: {order.total_shortage_units} units."
    )

    return order

def reject_sales_order(order_id, admin_user_id, reason=None):
    """
    Rejects a sales order.
    """
    order = SalesOrder.query.get(order_id)
    if not order:
        raise ValueError(f"Order {order_id} not found.")

    order.status = OrderStatus.REJECTED
    order.reviewed_by_id = admin_user_id
    order.reviewed_at = datetime.utcnow()
    order.review_notes = reason

    db.session.commit()

    log_audit(
        action="REJECT_SALES_ORDER",
        entity_type="SalesOrder",
        entity_id=order.id,
        description=f"Admin rejected order {order.order_number}. Reason: {reason}"
    )

    return order
