import unittest
from decimal import Decimal
from app import create_app, db
from app.config import Config
from app.models.user import User, Role
from app.models.master import Product, Customer
from app.models.inventory import StockItemType, StockTransactionType
from app.services.inventory_service import get_current_stock, record_stock_movement
from app.services.sales_service import create_sales_order, approve_sales_order
from app.services.invoice_service import create_invoice_from_order, cancel_invoice

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

class ServicesTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.user = User(username='test_user', email='t@s.com', full_name='Test', role=Role.FACTORY_ADMIN)
        self.user.set_password('secret')
        db.session.add(self.user)

        self.product = Product(
            name="Murukku 200g",
            sku="MUR-200G",
            selling_price=Decimal('50.00'),
            hsn="19059040",
            gst_rate=Decimal('5.00'),
            unit="Packets",
            status="Active"
        )
        db.session.add(self.product)

        # Karnataka customer (Inter-state)
        self.interstate_cust = Customer(
            name="Bengaluru Snacks",
            state="Karnataka",
            state_code="29",
            gstin="29XYZAB5678C1Z2",
            address="Bengaluru",
            customer_type="Distributor"
        )
        db.session.add(self.interstate_cust)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_prevent_negative_inventory(self):
        """
        Verifies that StockLedger strictly disallows negative stock balances.
        """
        # Initially zero stock
        self.assertEqual(get_current_stock(StockItemType.FINISHED_GOOD, self.product.id), Decimal('0.0000'))

        # Attempt to deduct 10 packets when 0 available
        with self.assertRaises(ValueError) as ctx:
            record_stock_movement(
                item_type=StockItemType.FINISHED_GOOD,
                item_id=self.product.id,
                item_name=self.product.name,
                transaction_type=StockTransactionType.DISPATCH,
                quantity_out=Decimal('10.0000'),
                unit="Packets"
            )
        self.assertIn("Negative inventory is strictly prohibited", str(ctx.exception))

    def test_interstate_igst_calculation(self):
        """
        Verifies that sales to outside Tamil Nadu (e.g. Karnataka) levy 100% IGST (5%).
        """
        # Add 100 packets to finished goods stock
        record_stock_movement(
            item_type=StockItemType.FINISHED_GOOD,
            item_id=self.product.id,
            item_name=self.product.name,
            transaction_type=StockTransactionType.OPENING_STOCK,
            quantity_in=Decimal('100.0000'),
            unit="Packets"
        )
        db.session.commit()

        # Create order for 80 packets for Karnataka customer
        order = create_sales_order(
            customer_id=self.interstate_cust.id,
            salesman_id=self.user.id,
            items_data=[{'product_id': self.product.id, 'quantity': Decimal('80.00')}]
        )
        approve_sales_order(order.id, self.user.id)

        # Generate invoice
        invoice = create_invoice_from_order(order.id, self.user.id)
        
        # Taxable = 80 * 50 = Rs. 4,000
        self.assertEqual(invoice.taxable_amount, Decimal('4000.00'))
        # IGST 5% of 4000 = Rs. 200.00
        self.assertEqual(invoice.igst_amount, Decimal('200.00'))
        # CGST and SGST must be 0 for inter-state
        self.assertEqual(invoice.cgst_amount, Decimal('0.00'))
        self.assertEqual(invoice.sgst_amount, Decimal('0.00'))
        self.assertEqual(invoice.total_amount, Decimal('4200.00'))
        self.assertTrue(invoice.is_interstate)

    def test_invoice_cancellation(self):
        """
        Verifies invoice cancellation workflow (no silent deletion).
        """
        record_stock_movement(
            item_type=StockItemType.FINISHED_GOOD,
            item_id=self.product.id,
            item_name=self.product.name,
            transaction_type=StockTransactionType.OPENING_STOCK,
            quantity_in=Decimal('50.0000'),
            unit="Packets"
        )
        db.session.commit()

        order = create_sales_order(
            customer_id=self.interstate_cust.id,
            salesman_id=self.user.id,
            items_data=[{'product_id': self.product.id, 'quantity': Decimal('10.00')}]
        )
        approve_sales_order(order.id, self.user.id)
        invoice = create_invoice_from_order(order.id, self.user.id)

        # Cancel invoice
        cancel_invoice(invoice.id, reason="Customer cancelled before dispatch", user_id=self.user.id)
        self.assertEqual(invoice.status, "CANCELLED")
        self.assertEqual(invoice.balance_due, Decimal('0.00'))
        self.assertEqual(invoice.cancellation_reason, "Customer cancelled before dispatch")

    def test_user_authentication_and_password_hashing(self):
        """
        Verifies secure password hashing and verification.
        """
        self.assertTrue(self.user.check_password('secret'))
        self.assertFalse(self.user.check_password('wrongpass'))
        self.assertNotEqual(self.user.password_hash, 'secret')

if __name__ == '__main__':
    unittest.main()
