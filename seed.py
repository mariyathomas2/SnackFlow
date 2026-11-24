import sys
from decimal import Decimal
from datetime import datetime, date
from app import create_app, db
from app.models.user import User, Role
from app.models.master import Product, Customer, Supplier, RawMaterial, BOM, BOMItem, UnitOfMeasure
from app.models.inventory import StockLedger, StockItemType, StockTransactionType
from app.models.purchase import PurchaseOrder, PurchaseItem
from app.models.production import ProductionRun, ProductionConsumption
from app.models.sales import SalesOrder, SalesOrderItem, OrderStatus
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from app.models.dispatch import DispatchRecord, DispatchItem
from app.models.payment import Payment, PaymentMethod
from app.models.costing import ProductionExpense, ExpenseCategory
from app.models.audit import AuditLog
from app.services.inventory_service import get_current_stock, record_stock_movement
from app.services.production_service import create_production_run
from app.services.sales_service import create_sales_order, approve_sales_order, review_stock_and_shortage
from app.services.invoice_service import create_invoice_from_order
from app.services.dispatch_service import create_dispatch
from app.services.payment_service import record_customer_payment

def seed_database(reset=False):
    app = create_app()
    with app.app_context():
        if reset or '--reset' in sys.argv:
            print("Resetting database tables...")
            db.drop_all()

        db.create_all()

        # Check if already seeded and not resetting
        if User.query.filter_by(username='owner').first() and not ('--reset' in sys.argv or reset):
            print("Database already contains benchmark seed data. Run with --reset to re-seed from scratch.")
            return

        print("\n=======================================================")
        print("  SNACKFLOW ERP - SEEDING BENCHMARK MANUFACTURING DATA")
        print("=======================================================")

        # -----------------------------------------------------------------
        # 1. CREATE USER ACCOUNTS FOR ALL 5 ROLES
        # -----------------------------------------------------------------
        print("\n[1/7] Creating User Accounts for All 5 Roles...")
        users_data = [
            ('owner', 'owner@snackflow.com', 'Sundaram Ramanathan', Role.OWNER, 'admin123', '+91 94421 11111'),
            ('admin', 'admin@snackflow.com', 'Priya Shanmugam', Role.FACTORY_ADMIN, 'admin123', '+91 94421 22222'),
            ('supervisor', 'supervisor@snackflow.com', 'Muthuvel Karuppasamy', Role.PRODUCTION_SUPERVISOR, 'admin123', '+91 94421 33333'),
            ('accountant', 'accountant@snackflow.com', 'Venkatesh Iyer', Role.ACCOUNTANT, 'admin123', '+91 94421 44444'),
            ('salesman_a', 'salesman.a@snackflow.com', 'Ramesh Kumar (Salesman A)', Role.SALESMAN, 'admin123', '+91 94421 55555'),
            ('salesman_b', 'salesman.b@snackflow.com', 'Suresh Babu (Salesman B)', Role.SALESMAN, 'admin123', '+91 94421 66666')
        ]

        users = {}
        for username, email, name, role, password, phone in users_data:
            user = User(
                username=username,
                email=email,
                full_name=name,
                role=role,
                phone=phone,
                is_active=True
            )
            user.set_password(password)
            db.session.add(user)
            users[username] = user
        db.session.commit()
        print("  ✓ Created 6 demo accounts (Password for all: 'admin123')")

        # -----------------------------------------------------------------
        # 2. SEED MASTER DATA
        # -----------------------------------------------------------------
        print("\n[2/7] Seeding Master Data (Product, Customers, Suppliers, Raw Materials, BOM)...")
        
        # Product: Murukku 200g
        murukku = Product(
            name="Murukku 200g",
            sku="MUR-200G",
            description="Traditional crunchy South Indian savoury snack made with rice flour and seasoned with cumin and sesame.",
            selling_price=Decimal('50.00'),
            hsn="19059040",
            gst_rate=Decimal('5.00'),
            unit="Packets",
            status="Active"
        )
        db.session.add(murukku)
        db.session.flush()

        # Raw Materials
        materials_data = [
            ("Flour", "RM-FLOUR", "kg", Decimal('20.00'), Decimal('45.00')),
            ("Cooking oil", "RM-OIL", "litre", Decimal('10.00'), Decimal('130.00')),
            ("Salt/spice mix", "RM-SPICE", "kg", Decimal('2.00'), Decimal('100.00')),
            ("200g pouch", "RM-POUCH", "pcs", Decimal('100.00'), Decimal('1.50')),
            ("Cartons", "RM-CARTON", "pcs", Decimal('10.00'), Decimal('25.00'))
        ]
        raw_materials = {}
        for name, code, unit, thresh, cost in materials_data:
            rm = RawMaterial(
                name=name,
                code=code,
                unit=unit,
                stock_threshold=thresh,
                cost=cost,
                status="Active"
            )
            db.session.add(rm)
            db.session.flush()
            raw_materials[name] = rm

        # Bill of Materials (BOM) for 200 packets
        bom = BOM(
            product_id=murukku.id,
            name="Standard Murukku 200g Recipe",
            batch_size=Decimal('200.00'),
            unit="Packets",
            description="Standard recipe for 200 packets (40kg batch output)",
            is_active=True
        )
        db.session.add(bom)
        db.session.flush()

        bom_items_data = [
            (raw_materials["Flour"], Decimal('40.0000'), "kg"),
            (raw_materials["Cooking oil"], Decimal('10.0000'), "litre"),
            (raw_materials["Salt/spice mix"], Decimal('1.2000'), "kg"),
            (raw_materials["200g pouch"], Decimal('200.0000'), "pcs"),
            (raw_materials["Cartons"], Decimal('10.0000'), "pcs")
        ]
        for rm, std_qty, u in bom_items_data:
            db.session.add(BOMItem(
                bom_id=bom.id,
                raw_material_id=rm.id,
                standard_quantity=std_qty,
                unit=u
            ))

        # Customers
        retailer_a = Customer(
            name="Retailer A",
            contact="K. Murugan",
            phone="+91 94431 88888",
            email="retailer.a@tnsnacks.in",
            address="142, West Car Street, Madurai, Tamil Nadu - 625001",
            state="Tamil Nadu",
            state_code="33",
            gstin="33ABCDE1234F1Z1",
            customer_type="Retailer",
            status="Active"
        )
        distributor_b = Customer(
            name="Distributor B",
            contact="Naveen Hegde",
            phone="+91 98860 99999",
            email="orders@distributorb.com",
            address="Plot 56, Peenya Industrial Area, 3rd Stage, Bengaluru, Karnataka - 560058",
            state="Karnataka",
            state_code="29",
            gstin="29XYZAB5678C1Z2",
            customer_type="Distributor",
            status="Active"
        )
        db.session.add(retailer_a)
        db.session.add(distributor_b)

        # Supplier
        flour_supplier = Supplier(
            name="Annapoorna Flour Mills",
            contact="Selvam Shanmugam",
            phone="+91 94432 77777",
            email="sales@annapoornaflour.com",
            address="Mill Road, Dindigul, Tamil Nadu - 624003",
            state="Tamil Nadu",
            gst_details="33AABCA5555M1Z8",
            status="Active"
        )
        db.session.add(flour_supplier)
        db.session.commit()
        print("  ✓ Created Murukku 200g product, 5 Raw Materials, BOM for 200 pkts, 2 Customers, and Supplier")

        # -----------------------------------------------------------------
        # 3. RECORD OPENING STOCK IN STOCK LEDGER
        # -----------------------------------------------------------------
        print("\n[3/7] Recording Opening Stock via Immutable Stock Ledger...")
        admin_user = users['admin']

        opening_stock_data = [
            (StockItemType.RAW_MATERIAL, raw_materials["Flour"].id, "Flour", Decimal('100.0000'), "kg", Decimal('45.00')),
            (StockItemType.RAW_MATERIAL, raw_materials["Cooking oil"].id, "Cooking oil", Decimal('30.0000'), "litre", Decimal('130.00')),
            (StockItemType.RAW_MATERIAL, raw_materials["Salt/spice mix"].id, "Salt/spice mix", Decimal('5.0000'), "kg", Decimal('100.00')),
            (StockItemType.RAW_MATERIAL, raw_materials["200g pouch"].id, "200g pouch", Decimal('500.0000'), "pcs", Decimal('1.50')),
            (StockItemType.RAW_MATERIAL, raw_materials["Cartons"].id, "Cartons", Decimal('30.0000'), "pcs", Decimal('25.00')),
            (StockItemType.FINISHED_GOOD, murukku.id, "Murukku 200g", Decimal('50.0000'), "Packets", Decimal('50.00'))
        ]

        for itype, i_id, iname, qty, unit, cost in opening_stock_data:
            record_stock_movement(
                item_type=itype,
                item_id=i_id,
                item_name=iname,
                transaction_type=StockTransactionType.OPENING_STOCK,
                quantity_in=qty,
                unit=unit,
                unit_cost=cost,
                reference_type="INITIAL_SEED",
                reference_id="INIT-2026",
                notes="Initial opening stock for factory operations",
                user_id=admin_user.id
            )
        db.session.commit()
        print("  ✓ Recorded Opening Stock: Flour=100kg, Oil=30L, Spice=5kg, Pouches=500, Cartons=30, Murukku=50 pkts")

        # -----------------------------------------------------------------
        # 4. STEP 1: PURCHASE 60 KG FLOUR @ RS. 45/KG
        # -----------------------------------------------------------------
        print("\n[4/7] Step 1: Purchasing 60 kg Flour at Rs. 45/kg from Annapoorna Flour Mills...")
        po = PurchaseOrder(
            po_number="PO-20261124-0001",
            supplier_id=flour_supplier.id,
            purchase_date=date.today(),
            status="RECEIVED",
            total_amount=Decimal('2700.00'),
            notes="Benchmark Step 1: Purchase 60 kg flour at Rs. 45/kg",
            created_by_id=admin_user.id
        )
        db.session.add(po)
        db.session.flush()

        db.session.add(PurchaseItem(
            purchase_id=po.id,
            raw_material_id=raw_materials["Flour"].id,
            quantity=Decimal('60.0000'),
            unit="kg",
            unit_cost=Decimal('45.00'),
            total_cost=Decimal('2700.00')
        ))

        # Receive into inventory ledger
        record_stock_movement(
            item_type=StockItemType.RAW_MATERIAL,
            item_id=raw_materials["Flour"].id,
            item_name="Flour",
            transaction_type=StockTransactionType.PURCHASE_RECEIPT,
            quantity_in=Decimal('60.0000'),
            unit="kg",
            unit_cost=Decimal('45.00'),
            reference_type="PURCHASE_ORDER",
            reference_id=po.po_number,
            notes=f"Received PO {po.po_number}",
            user_id=admin_user.id
        )
        db.session.commit()
        flour_bal_step1 = get_current_stock(StockItemType.RAW_MATERIAL, raw_materials["Flour"].id)
        print(f"  ✓ Step 1 Complete: Flour Stock is now {flour_bal_step1} kg (Expected: 160 kg)")

        # -----------------------------------------------------------------
        # 5. STEP 2: EXECUTE PRODUCTION RUN
        # -----------------------------------------------------------------
        print("\n[5/7] Step 2: Executing Production Run (Murukku 200g)...")
        supervisor_user = users['supervisor']
        
        consumptions_step2 = [
            {'raw_material_id': raw_materials["Flour"].id, 'planned_qty': Decimal('40.0000'), 'actual_qty': Decimal('40.0000'), 'wastage_qty': Decimal('0')},
            {'raw_material_id': raw_materials["Cooking oil"].id, 'planned_qty': Decimal('10.0000'), 'actual_qty': Decimal('10.5000'), 'wastage_qty': Decimal('0')},
            {'raw_material_id': raw_materials["Salt/spice mix"].id, 'planned_qty': Decimal('1.2000'), 'actual_qty': Decimal('1.2000'), 'wastage_qty': Decimal('0')},
            {'raw_material_id': raw_materials["200g pouch"].id, 'planned_qty': Decimal('200.0000'), 'actual_qty': Decimal('188.0000'), 'wastage_qty': Decimal('6.0000')},
            {'raw_material_id': raw_materials["Cartons"].id, 'planned_qty': Decimal('10.0000'), 'actual_qty': Decimal('9.0000'), 'wastage_qty': Decimal('0')}
        ]

        prod_run = create_production_run(
            product_id=murukku.id,
            bom_id=bom.id,
            planned_quantity=Decimal('200.00'),
            actual_output_good=Decimal('188.00'),
            damaged_units=Decimal('6.00'),
            cartons_used=Decimal('9.00'),
            material_consumptions=consumptions_step2,
            direct_labor_cost=Decimal('1200.00'), # Step 8
            power_fuel_cost=Decimal('600.00'),    # Step 8
            other_overheads=Decimal('0.00'),
            notes="Benchmark Step 2: Murukku 200g run with 6 damaged pouches and +5% oil variance",
            user_id=supervisor_user.id
        )

        fg_after_prod = get_current_stock(StockItemType.FINISHED_GOOD, murukku.id)
        print(f"  ✓ Step 2 Complete: Yield Variance = {prod_run.yield_variance_pct}% (Expected: -6.00%)")
        print(f"  ✓ Production Costing: Total Batch Cost = ₹{prod_run.total_production_cost}, Cost/Packet = ₹{prod_run.cost_per_packet} (Expected: ₹29.79)")
        print(f"  ✓ Finished Goods Stock = {fg_after_prod} Packets (Expected: 238 pkts)")

        # -----------------------------------------------------------------
        # 6. STEP 3 & 4: SALESMAN A ORDER (150 PKTS), APPROVE, INVOICE, DISPATCH
        # -----------------------------------------------------------------
        print("\n[6/7] Step 3 & 4: Salesman A Order for Retailer A (150 pkts), Invoice & Dispatch...")
        salesman_a = users['salesman_a']
        
        # Step 3: Create Order
        order_a = create_sales_order(
            customer_id=retailer_a.id,
            salesman_id=salesman_a.id,
            items_data=[{'product_id': murukku.id, 'quantity': Decimal('150.00')}],
            notes="Benchmark Step 3: 150 packets for Retailer A in Tamil Nadu"
        )
        print(f"  ✓ Step 3: Created Order {order_a.order_number} for Retailer A (150 pkts)")

        # Step 4: Admin Approves, Invoices, Dispatches
        approve_sales_order(order_a.id, admin_user.id)
        invoice_a = create_invoice_from_order(order_a.id, admin_user.id)
        dispatch_a = create_dispatch(order_a.id, invoice_id=invoice_a.id, user_id=admin_user.id)

        fg_after_dispatch = get_current_stock(StockItemType.FINISHED_GOOD, murukku.id)
        print(f"  ✓ Step 4: Generated GST Invoice {invoice_a.invoice_number}")
        print(f"    - Taxable Value: ₹{invoice_a.taxable_amount} (Expected: ₹7,500.00)")
        print(f"    - CGST: ₹{invoice_a.cgst_amount} | SGST: ₹{invoice_a.sgst_amount} (Expected: ₹187.50 each)")
        print(f"    - Total Amount: ₹{invoice_a.total_amount} (Expected: ₹7,875.00)")
        print(f"  ✓ Step 4: Dispatched 150 packets. Finished Goods Stock = {fg_after_dispatch} pkts (Expected: 88 pkts)")

        # -----------------------------------------------------------------
        # 7. STEP 5 & 6: SALESMAN B ORDER (120 PKTS) & SHORTAGE DETECTION
        # -----------------------------------------------------------------
        print("\n[7/7] Step 5 & 6: Salesman B Order for Distributor B (120 pkts) & Shortage Detection...")
        salesman_b = users['salesman_b']

        order_b = create_sales_order(
            customer_id=distributor_b.id,
            salesman_id=salesman_b.id,
            items_data=[{'product_id': murukku.id, 'quantity': Decimal('120.00')}],
            notes="Benchmark Step 5: 120 packets for Distributor B in Karnataka"
        )
        
        # Step 6: Review Stock & Shortage
        review_res = review_stock_and_shortage(order_b.id)
        item_review = review_res['items'][0]
        print(f"  ✓ Step 5: Created Order {order_b.order_number} for Distributor B (120 pkts ordered)")
        print(f"  ✓ Step 6: Stock Verification Result:")
        print(f"    - Available Stock: {item_review['available_stock']} pkts (Expected: 88 pkts)")
        print(f"    - Ordered Quantity: {item_review['ordered_qty']} pkts (Expected: 120 pkts)")
        print(f"    - Shortage Detected: {item_review['shortage_qty']} pkts (Expected: 32 pkts)")

        # -----------------------------------------------------------------
        # 8. STEP 7: RECORD PAYMENT OF RS. 4,000 FROM RETAILER A
        # -----------------------------------------------------------------
        print("\n[8/7] Step 7: Record Payment of Rs. 4,000 from Retailer A...")
        payment_a = record_customer_payment(
            invoice_id=invoice_a.id,
            amount=Decimal('4000.00'),
            payment_method=PaymentMethod.BANK_TRANSFER,
            reference_number="NEFT-SBI-20261124-8899",
            notes="Benchmark Step 7: Part payment of Rs. 4,000 from Retailer A",
            user_id=admin_user.id
        )
        print(f"  ✓ Step 7: Recorded Payment of ₹{payment_a.amount}")
        print(f"    - Invoice Total: ₹{invoice_a.total_amount}")
        print(f"    - Paid to Date: ₹{invoice_a.paid_amount}")
        print(f"    - Remaining Outstanding: ₹{invoice_a.balance_due} (Expected: ₹3,875.00)")

        # -----------------------------------------------------------------
        # VERIFICATION REPORT SUMMARY
        # -----------------------------------------------------------------
        flour_final = get_current_stock(StockItemType.RAW_MATERIAL, raw_materials["Flour"].id)
        oil_final = get_current_stock(StockItemType.RAW_MATERIAL, raw_materials["Cooking oil"].id)
        pouch_final = get_current_stock(StockItemType.RAW_MATERIAL, raw_materials["200g pouch"].id)

        print("\n=======================================================")
        print("  BENCHMARK RESULTS RECONCILIATION SUMMARY")
        print("=======================================================")
        print(f"  Flour Closing Stock:    {flour_final} kg       [Expected: 120 kg]    -> {'PASS' if flour_final == Decimal('120') else 'FAIL'}")
        print(f"  Oil Closing Stock:      {oil_final} litres   [Expected: 19.5 L]    -> {'PASS' if oil_final == Decimal('19.5') else 'FAIL'}")
        print(f"  Pouches Closing Stock:  {pouch_final} pcs      [Expected: 306 pcs]   -> {'PASS' if pouch_final == Decimal('306') else 'FAIL'}")
        print(f"  FG Stock After Disp:    {fg_after_dispatch} pkts     [Expected: 88 pkts]   -> {'PASS' if fg_after_dispatch == Decimal('88') else 'FAIL'}")
        print(f"  Yield Variance:         {prod_run.yield_variance_pct}%      [Expected: -6.00%]    -> {'PASS' if prod_run.yield_variance_pct == Decimal('-6.00') else 'FAIL'}")
        print(f"  Murukku Invoice Total:  ₹{invoice_a.total_amount}   [Expected: ₹7,875.00] -> {'PASS' if invoice_a.total_amount == Decimal('7875.00') else 'FAIL'}")
        print(f"  Retailer A Balance Due: ₹{invoice_a.balance_due}   [Expected: ₹3,875.00] -> {'PASS' if invoice_a.balance_due == Decimal('3875.00') else 'FAIL'}")
        print(f"  Distributor B Shortage: {item_review['shortage_qty']} pkts     [Expected: 32 pkts]   -> {'PASS' if item_review['shortage_qty'] == Decimal('32') else 'FAIL'}")
        print("=======================================================\n")
        print("Benchmark seeding completed successfully! All database records match expected values.\n")

if __name__ == '__main__':
    seed_database()
