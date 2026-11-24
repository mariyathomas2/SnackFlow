import unittest
from decimal import Decimal
from datetime import date
from app import create_app, db
from app.config import Config
from app.models.user import User, Role
from app.models.master import Product, Customer, Supplier, RawMaterial, BOM, BOMItem
from app.models.inventory import StockLedger, StockItemType, StockTransactionType
from app.models.purchase import PurchaseOrder, PurchaseItem
from app.models.production import ProductionRun, ProductionConsumption
from app.models.sales import SalesOrder, SalesOrderItem, OrderStatus
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from app.models.dispatch import DispatchRecord, DispatchItem
from app.models.payment import Payment, PaymentMethod
from app.services.inventory_service import get_current_stock, record_stock_movement
from app.services.production_service import create_production_run
from app.services.sales_service import create_sales_order, approve_sales_order, review_stock_and_shortage
from app.services.invoice_service import create_invoice_from_order
from app.services.dispatch_service import create_dispatch
from app.services.payment_service import record_customer_payment

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

class BenchmarkScenarioTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Seed users
        self.owner = User(username='owner', email='o@s.com', full_name='Owner', role=Role.OWNER)
        self.admin = User(username='admin', email='a@s.com', full_name='Admin', role=Role.FACTORY_ADMIN)
        self.supervisor = User(username='supervisor', email='sup@s.com', full_name='Supervisor', role=Role.PRODUCTION_SUPERVISOR)
        self.salesman_a = User(username='salesman_a', email='sa@s.com', full_name='Salesman A', role=Role.SALESMAN)
        self.salesman_b = User(username='salesman_b', email='sb@s.com', full_name='Salesman B', role=Role.SALESMAN)
        for u in [self.owner, self.admin, self.supervisor, self.salesman_a, self.salesman_b]:
            u.set_password('admin123')
            db.session.add(u)

        # Product: Murukku 200g
        self.murukku = Product(
            name="Murukku 200g",
            sku="MUR-200G",
            selling_price=Decimal('50.00'),
            hsn="19059040",
            gst_rate=Decimal('5.00'),
            unit="Packets",
            status="Active"
        )
        db.session.add(self.murukku)

        # Raw materials
        self.flour = RawMaterial(name="Flour", code="RM-FLOUR", unit="kg", stock_threshold=Decimal('20.00'), cost=Decimal('45.00'))
        self.oil = RawMaterial(name="Cooking oil", code="RM-OIL", unit="litre", stock_threshold=Decimal('10.00'), cost=Decimal('130.00'))
        self.spices = RawMaterial(name="Salt/spice mix", code="RM-SPICE", unit="kg", stock_threshold=Decimal('2.00'), cost=Decimal('100.00'))
        self.pouches = RawMaterial(name="200g pouch", code="RM-POUCH", unit="pcs", stock_threshold=Decimal('100.00'), cost=Decimal('1.50'))
        self.cartons = RawMaterial(name="Cartons", code="RM-CARTON", unit="pcs", stock_threshold=Decimal('10.00'), cost=Decimal('25.00'))
        for rm in [self.flour, self.oil, self.spices, self.pouches, self.cartons]:
            db.session.add(rm)

        # BOM for 200 Packets
        self.bom = BOM(product_id=1, name="Standard Murukku BOM", batch_size=Decimal('200.00'), unit="Packets", is_active=True)
        db.session.add(self.bom)
        db.session.flush()

        for rm, qty, u in [
            (self.flour, Decimal('40.0000'), "kg"),
            (self.oil, Decimal('10.0000'), "litre"),
            (self.spices, Decimal('1.2000'), "kg"),
            (self.pouches, Decimal('200.0000'), "pcs"),
            (self.cartons, Decimal('10.0000'), "pcs")
        ]:
            db.session.add(BOMItem(bom_id=self.bom.id, raw_material_id=rm.id, standard_quantity=qty, unit=u))

        # Customers
        self.retailer_a = Customer(
            name="Retailer A",
            state="Tamil Nadu",
            state_code="33",
            gstin="33ABCDE1234F1Z1",
            address="Madurai, Tamil Nadu",
            customer_type="Retailer"
        )
        self.distributor_b = Customer(
            name="Distributor B",
            state="Karnataka",
            state_code="29",
            gstin="29XYZAB5678C1Z2",
            address="Bengaluru, Karnataka",
            customer_type="Distributor"
        )
        db.session.add(self.retailer_a)
        db.session.add(self.distributor_b)

        # Supplier
        self.supplier = Supplier(
            name="Annapoorna Flour Mills",
            state="Tamil Nadu",
            gst_details="33AABCA5555M1Z8",
            address="Dindigul, Tamil Nadu"
        )
        db.session.add(self.supplier)

        # Opening Stock
        for itype, item_id, iname, qty, unit, cost in [
            (StockItemType.RAW_MATERIAL, self.flour.id, "Flour", Decimal('100.0000'), "kg", Decimal('45.00')),
            (StockItemType.RAW_MATERIAL, self.oil.id, "Cooking oil", Decimal('30.0000'), "litre", Decimal('130.00')),
            (StockItemType.RAW_MATERIAL, self.spices.id, "Salt/spice mix", Decimal('5.0000'), "kg", Decimal('100.00')),
            (StockItemType.RAW_MATERIAL, self.pouches.id, "200g pouch", Decimal('500.0000'), "pcs", Decimal('1.50')),
            (StockItemType.RAW_MATERIAL, self.cartons.id, "Cartons", Decimal('30.0000'), "pcs", Decimal('25.00')),
            (StockItemType.FINISHED_GOOD, self.murukku.id, "Murukku 200g", Decimal('50.0000'), "Packets", Decimal('50.00'))
        ]:
            record_stock_movement(
                item_type=itype,
                item_id=item_id,
                item_name=iname,
                transaction_type=StockTransactionType.OPENING_STOCK,
                quantity_in=qty,
                unit=unit,
                unit_cost=cost
            )
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_full_benchmark_flow(self):
        """
        Executes Steps 1 to 9 of the prompt benchmark scenario
        and asserts every expected numerical value.
        """
        # Step 1: Purchase 60 kg flour at Rs. 45/kg
        po = PurchaseOrder(
            po_number="PO-TEST-001",
            supplier_id=self.supplier.id,
            purchase_date=date.today(),
            status="RECEIVED",
            total_amount=Decimal('2700.00')
        )
        db.session.add(po)
        db.session.flush()

        record_stock_movement(
            item_type=StockItemType.RAW_MATERIAL,
            item_id=self.flour.id,
            item_name="Flour",
            transaction_type=StockTransactionType.PURCHASE_RECEIPT,
            quantity_in=Decimal('60.0000'),
            unit="kg",
            unit_cost=Decimal('45.00'),
            reference_type="PURCHASE_ORDER",
            reference_id=po.po_number
        )
        db.session.commit()

        # Check Flour stock after Step 1: 100 + 60 = 160 kg
        self.assertEqual(get_current_stock(StockItemType.RAW_MATERIAL, self.flour.id), Decimal('160.0000'))

        # Step 2: Production run
        consumptions = [
            {'raw_material_id': self.flour.id, 'planned_qty': Decimal('40.0000'), 'actual_qty': Decimal('40.0000'), 'wastage_qty': Decimal('0')},
            {'raw_material_id': self.oil.id, 'planned_qty': Decimal('10.0000'), 'actual_qty': Decimal('10.5000'), 'wastage_qty': Decimal('0')},
            {'raw_material_id': self.spices.id, 'planned_qty': Decimal('1.2000'), 'actual_qty': Decimal('1.2000'), 'wastage_qty': Decimal('0')},
            {'raw_material_id': self.pouches.id, 'planned_qty': Decimal('200.0000'), 'actual_qty': Decimal('188.0000'), 'wastage_qty': Decimal('6.0000')},
            {'raw_material_id': self.cartons.id, 'planned_qty': Decimal('10.0000'), 'actual_qty': Decimal('9.0000'), 'wastage_qty': Decimal('0')}
        ]

        run = create_production_run(
            product_id=self.murukku.id,
            bom_id=self.bom.id,
            planned_quantity=Decimal('200.00'),
            actual_output_good=Decimal('188.00'),
            damaged_units=Decimal('6.00'),
            cartons_used=Decimal('9.00'),
            material_consumptions=consumptions,
            direct_labor_cost=Decimal('1200.00'),
            power_fuel_cost=Decimal('600.00')
        )

        # Expected Stock Balances after Production:
        # Flour: 160 - 40 = 120 kg
        self.assertEqual(get_current_stock(StockItemType.RAW_MATERIAL, self.flour.id), Decimal('120.0000'))
        # Oil: 30 - 10.5 = 19.5 L
        self.assertEqual(get_current_stock(StockItemType.RAW_MATERIAL, self.oil.id), Decimal('19.5000'))
        # Pouches: 500 - 188 - 6 = 306 pcs
        self.assertEqual(get_current_stock(StockItemType.RAW_MATERIAL, self.pouches.id), Decimal('306.0000'))
        # Finished goods: 50 + 188 = 238 pkts
        self.assertEqual(get_current_stock(StockItemType.FINISHED_GOOD, self.murukku.id), Decimal('238.0000'))

        # Yield variance: 188 vs 200 = -6.00%
        self.assertEqual(run.yield_variance_pct, Decimal('-6.00'))
        self.assertTrue(run.has_yield_variance_alert)

        # Production Cost: Materials (3,801) + Labour (1,200) + Power (600) = 5,601
        self.assertEqual(run.total_material_cost, Decimal('3801.00'))
        self.assertEqual(run.total_production_cost, Decimal('5601.00'))
        # Cost per packet = 5,601 / 188 = 29.79
        self.assertEqual(run.cost_per_packet, Decimal('29.79'))

        # Step 3: Salesman A order for 150 pkts for Retailer A
        order_a = create_sales_order(
            customer_id=self.retailer_a.id,
            salesman_id=self.salesman_a.id,
            items_data=[{'product_id': self.murukku.id, 'quantity': Decimal('150.00')}]
        )
        self.assertEqual(order_a.status, OrderStatus.PENDING)

        # Step 4: Admin approves, generates invoice, dispatches 150 pkts
        approve_sales_order(order_a.id, self.admin.id)
        self.assertEqual(order_a.status, OrderStatus.APPROVED)

        invoice_a = create_invoice_from_order(order_a.id, self.admin.id)
        # Taxable: 150 * 50 = 7,500
        self.assertEqual(invoice_a.taxable_amount, Decimal('7500.00'))
        # Intra-state Tamil Nadu: CGST 2.5% = 187.50, SGST 2.5% = 187.50
        self.assertEqual(invoice_a.cgst_amount, Decimal('187.50'))
        self.assertEqual(invoice_a.sgst_amount, Decimal('187.50'))
        self.assertEqual(invoice_a.igst_amount, Decimal('0.00'))
        # Total invoice = 7,875.00
        self.assertEqual(invoice_a.total_amount, Decimal('7875.00'))

        # Dispatch 150 packets
        create_dispatch(order_a.id, invoice_id=invoice_a.id, user_id=self.admin.id)
        # Finished goods after dispatch: 238 - 150 = 88 pkts
        self.assertEqual(get_current_stock(StockItemType.FINISHED_GOOD, self.murukku.id), Decimal('88.0000'))

        # Step 5: Salesman B order for 120 pkts for Distributor B
        order_b = create_sales_order(
            customer_id=self.distributor_b.id,
            salesman_id=self.salesman_b.id,
            items_data=[{'product_id': self.murukku.id, 'quantity': Decimal('120.00')}]
        )

        # Step 6: Verify stock shortage: 120 ordered vs 88 stock = 32 shortage
        rev = review_stock_and_shortage(order_b.id)
        item_rev = rev['items'][0]
        self.assertEqual(item_rev['available_stock'], Decimal('88.0000'))
        self.assertEqual(item_rev['ordered_qty'], Decimal('120.00'))
        self.assertEqual(item_rev['shortage_qty'], Decimal('32.0000'))
        self.assertTrue(rev['has_shortage'])

        # Enforce cannot approve beyond available stock
        with self.assertRaises(ValueError):
            approve_sales_order(order_b.id, self.admin.id, approved_items={item_rev['item_id']: Decimal('120.00')})

        # Step 7: Record payment of Rs. 4,000 from Retailer A
        payment = record_customer_payment(
            invoice_id=invoice_a.id,
            amount=Decimal('4000.00'),
            payment_method=PaymentMethod.BANK_TRANSFER
        )
        self.assertEqual(payment.amount, Decimal('4000.00'))
        # Invoice balance due: 7,875 - 4,000 = 3,875
        self.assertEqual(invoice_a.balance_due, Decimal('3875.00'))
        self.assertEqual(invoice_a.status, InvoiceStatus.PARTIALLY_PAID)

        # Enforce payment cannot exceed balance due
        with self.assertRaises(ValueError):
            record_customer_payment(invoice_id=invoice_a.id, amount=Decimal('5000.00'))

if __name__ == '__main__':
    unittest.main()
