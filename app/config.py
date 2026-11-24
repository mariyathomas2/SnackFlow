import os
from decimal import Decimal

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'snackflow-secret-internship-key-2026')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.join(BASE_DIR, "snackflow.db")}')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Factory Profile (Benchmark details)
    COMPANY_NAME = "SnackFlow Foods Pvt. Ltd."
    FACTORY_NAME = "SnackFlow Madurai Plant"
    FACTORY_ADDRESS = "Plot 42, SIDCO Industrial Estate, Kappalur, Madurai, Tamil Nadu - 625008"
    FACTORY_STATE = "Tamil Nadu"
    FACTORY_STATE_CODE = "33"
    FACTORY_GSTIN = "33AAAAA0000A1Z5"
    FACTORY_PHONE = "+91 94421 87654"
    FACTORY_EMAIL = "operations@snackflow.com"
    FACTORY_BANK_NAME = "State Bank of India"
    FACTORY_BANK_ACC = "398712345678"
    FACTORY_BANK_IFSC = "SBIN0001234"
    
    # Benchmark defaults
    MUR_GST_RATE = Decimal('5.00')
    DEFAULT_CURRENCY = "₹"
