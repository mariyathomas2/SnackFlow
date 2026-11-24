from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date
from app import db
from app.models.production import ProductionRun, ProductionConsumption
from app.models.costing import ProductionExpense, ExpenseCategory
from app.models.master import Product, BOM, RawMaterial
from app.models.inventory import StockItemType, StockTransactionType
from app.services.inventory_service import get_current_stock, record_stock_movement
from app.services.audit_service import log_audit

def calculate_planned_materials(bom_id, planned_quantity):
    """
    Given a BOM and a planned batch quantity, calculates standard required materials.
    """
    bom = BOM.query.get(bom_id)
    if not bom:
        raise ValueError(f"BOM {bom_id} not found.")

    planned_qty = Decimal(str(planned_quantity))
    scaling_factor = planned_qty / bom.batch_size

    requirements = []
    for item in bom.items:
        required_qty = (item.standard_quantity * scaling_factor).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        current_stock = get_current_stock(StockItemType.RAW_MATERIAL, item.raw_material_id)
        shortage = max(Decimal('0'), required_qty - current_stock)
        
        requirements.append({
            'raw_material_id': item.raw_material_id,
            'material_name': item.raw_material.name,
            'unit': item.unit,
            'standard_qty': item.standard_quantity,
            'required_qty': required_qty,
            'current_stock': current_stock,
            'shortage': shortage,
            'unit_cost': item.raw_material.cost,
            'estimated_cost': (required_qty * item.raw_material.cost).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        })

    return requirements

def create_production_run(
    product_id,
    bom_id,
    planned_quantity,
    actual_output_good,
    damaged_units=Decimal('0'),
    cartons_used=Decimal('0'),
    material_consumptions=None, # list of dicts: {raw_material_id, actual_qty, wastage_qty, notes}
    direct_labor_cost=Decimal('0.00'),
    power_fuel_cost=Decimal('0.00'),
    other_overheads=Decimal('0.00'),
    run_date=None,
    notes=None,
    user_id=None
):
    """
    Executes a complete production run:
    1. Validates material inventory before issue
    2. Calculates yield and consumption variances
    3. Records material deductions (PRODUCTION_ISSUE & MATERIAL_WASTAGE)
    4. Records finished goods addition (FG_PRODUCTION_OUTPUT)
    5. Calculates full batch costing and per-packet margin
    6. Logs audit trail
    """
    product = Product.query.get(product_id)
    if not product:
        raise ValueError(f"Product {product_id} not found.")

    bom = BOM.query.get(bom_id) if bom_id else None
    planned_qty = Decimal(str(planned_quantity))
    actual_good = Decimal(str(actual_output_good))
    damaged = Decimal(str(damaged_units or '0'))
    cartons = Decimal(str(cartons_used or '0'))
    labor = Decimal(str(direct_labor_cost or '0'))
    power = Decimal(str(power_fuel_cost or '0'))
    overhead = Decimal(str(other_overheads or '0'))

    if planned_qty <= Decimal('0'):
        raise ValueError("Planned quantity must be greater than zero.")
    if actual_good < Decimal('0'):
        raise ValueError("Actual output cannot be negative.")

    # 1. Pre-validate stock availability for all materials to be consumed
    if material_consumptions:
        for mc in material_consumptions:
            rm = RawMaterial.query.get(mc['raw_material_id'])
            total_needed = Decimal(str(mc.get('actual_qty', '0'))) + Decimal(str(mc.get('wastage_qty', '0')))
            current_stock = get_current_stock(StockItemType.RAW_MATERIAL, rm.id)
            if total_needed > current_stock:
                raise ValueError(
                    f"Insufficient stock for '{rm.name}'. Required: {total_needed} {rm.unit}, Available: {current_stock} {rm.unit}."
                )

    # Generate sequential batch number PR-YYYYMMDD-XXXX
    count_today = ProductionRun.query.filter(
        ProductionRun.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
    ).count() + 1
    batch_number = f"PR-{datetime.utcnow().strftime('%Y%m%d')}-{count_today:04d}"

    # 2. Yield Variance Calculation: ((actual_good - planned_qty) / planned_qty) * 100
    yield_variance_pct = (((actual_good - planned_qty) / planned_qty) * Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # Create ProductionRun instance
    prod_run = ProductionRun(
        batch_number=batch_number,
        product_id=product_id,
        bom_id=bom_id,
        run_date=run_date or date.today(),
        status='COMPLETED',
        planned_quantity=planned_qty,
        actual_output_good=actual_good,
        damaged_units=damaged,
        cartons_used=cartons,
        yield_variance_pct=yield_variance_pct,
        direct_labor_cost=labor,
        power_fuel_cost=power,
        other_overheads=overhead,
        selling_price_at_run=product.selling_price,
        notes=notes,
        created_by_id=user_id
    )
    db.session.add(prod_run)
    db.session.flush()

    total_material_cost = Decimal('0.00')

    # 3. Process Material Consumptions & Stock Ledger Entries
    if material_consumptions:
        for mc in material_consumptions:
            rm = RawMaterial.query.get(mc['raw_material_id'])
            planned_m_qty = Decimal(str(mc.get('planned_qty', '0')))
            actual_m_qty = Decimal(str(mc.get('actual_qty', '0')))
            wastage_m_qty = Decimal(str(mc.get('wastage_qty', '0')))
            unit_cost = rm.cost

            # Consumption variance on primary consumed quantity
            var_qty = actual_m_qty - planned_m_qty
            var_pct = Decimal('0.00')
            if planned_m_qty > Decimal('0'):
                var_pct = ((var_qty / planned_m_qty) * Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            # Material cost includes both consumed and wastage
            total_qty_used = actual_m_qty + wastage_m_qty
            line_cost = (total_qty_used * unit_cost).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_material_cost += line_cost

            consumption = ProductionConsumption(
                production_run_id=prod_run.id,
                raw_material_id=rm.id,
                planned_quantity=planned_m_qty,
                actual_quantity=actual_m_qty,
                wastage_quantity=wastage_m_qty,
                unit=rm.unit,
                unit_cost=unit_cost,
                total_cost=line_cost,
                variance_quantity=var_qty,
                variance_pct=var_pct,
                notes=mc.get('notes')
            )
            db.session.add(consumption)

            # Issue raw material into production
            if actual_m_qty > Decimal('0'):
                record_stock_movement(
                    item_type=StockItemType.RAW_MATERIAL,
                    item_id=rm.id,
                    item_name=rm.name,
                    transaction_type=StockTransactionType.PRODUCTION_ISSUE,
                    quantity_out=actual_m_qty,
                    unit=rm.unit,
                    unit_cost=unit_cost,
                    reference_type="PRODUCTION_RUN",
                    reference_id=batch_number,
                    notes=f"Issued for batch {batch_number}",
                    user_id=user_id
                )

            # Record wastage if any (e.g. damaged pouches)
            if wastage_m_qty > Decimal('0'):
                record_stock_movement(
                    item_type=StockItemType.RAW_MATERIAL,
                    item_id=rm.id,
                    item_name=rm.name,
                    transaction_type=StockTransactionType.MATERIAL_WASTAGE,
                    quantity_out=wastage_m_qty,
                    unit=rm.unit,
                    unit_cost=unit_cost,
                    reference_type="PRODUCTION_RUN",
                    reference_id=batch_number,
                    notes=f"Wastage / damaged during batch {batch_number}",
                    user_id=user_id
                )

    # 4. Record Finished Goods production output into stock ledger
    if actual_good > Decimal('0'):
        record_stock_movement(
            item_type=StockItemType.FINISHED_GOOD,
            item_id=product.id,
            item_name=product.name,
            transaction_type=StockTransactionType.FG_PRODUCTION_OUTPUT,
            quantity_in=actual_good,
            unit=product.unit,
            unit_cost=Decimal('0.00'), # Will be updated with final cost
            reference_type="PRODUCTION_RUN",
            reference_id=batch_number,
            notes=f"Good output from batch {batch_number}",
            user_id=user_id
        )

    # 5. Batch Costing calculations
    total_batch_cost = total_material_cost + labor + power + overhead
    cost_per_packet = Decimal('0.00')
    gross_margin_per_packet = Decimal('0.00')
    gross_margin_pct = Decimal('0.00')

    if actual_good > Decimal('0'):
        cost_per_packet = (total_batch_cost / actual_good).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        gross_margin_per_packet = (product.selling_price - cost_per_packet).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if product.selling_price > Decimal('0'):
            gross_margin_pct = ((gross_margin_per_packet / product.selling_price) * Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    prod_run.total_material_cost = total_material_cost
    prod_run.total_production_cost = total_batch_cost
    prod_run.cost_per_packet = cost_per_packet
    prod_run.gross_margin_per_packet = gross_margin_per_packet
    prod_run.gross_margin_pct = gross_margin_pct

    # Also log expenses in ProductionExpense table if overheads provided
    if labor > Decimal('0'):
        db.session.add(ProductionExpense(
            expense_date=prod_run.run_date,
            category=ExpenseCategory.DIRECT_LABOUR,
            description=f"Direct Labour for {batch_number}",
            amount=labor,
            production_run_id=prod_run.id,
            created_by_id=user_id
        ))
    if power > Decimal('0'):
        db.session.add(ProductionExpense(
            expense_date=prod_run.run_date,
            category=ExpenseCategory.POWER_GAS,
            description=f"Gas and Power for {batch_number}",
            amount=power,
            production_run_id=prod_run.id,
            created_by_id=user_id
        ))

    db.session.commit()

    log_audit(
        action="RECORD_PRODUCTION",
        entity_type="ProductionRun",
        entity_id=prod_run.id,
        description=f"Recorded batch {batch_number}: {actual_good} good pkts (Yield var: {yield_variance_pct}%). Total Cost: ₹{total_batch_cost} (₹{cost_per_packet}/pkt)."
    )

    return prod_run
