# SnackFlow – Order-to-Audit Management System for a Small Food Manufacturer

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask_3.1-black.svg)](https://flask.palletsprojects.com/)
[![Database](https://img.shields.io/badge/Database-SQLite_/_SQLAlchemy-green.svg)](https://www.sqlite.org/)
[![Bootstrap](https://img.shields.io/badge/UI-Bootstrap_5-purple.svg)](https://getbootstrap.com/)
[![Tests](https://img.shields.io/badge/Tests-Passing_100%25-brightgreen.svg)]()

> **SnackFlow** is a full-stack, enterprise-grade ERP prototype engineered for a packaged food manufacturer in Tamil Nadu, India. It seamlessly connects sales, purchases, raw-material inventory, batch manufacturing, finished goods, GST tax invoicing, dispatch, collections, costing, and statutory audit reports.

---

## 🌟 Key Functional Highlights

1. **Role-Based Access Control (RBAC):**
   - 5 distinct user roles: `SALESMAN`, `FACTORY_ADMIN`, `PRODUCTION_SUPERVISOR`, `ACCOUNTANT`, and `OWNER`.
   - Dedicated role-specific dashboards with computed KPIs, live alerts, and quick actions.
   - Demo 1-Click Role Switcher in the top navigation bar for seamless evaluation.
2. **Double-Entry Style Stock Ledger:**
   - Every movement (opening stock, purchase receipt, production issue, material wastage, finished goods output, dispatch, and manual adjustments) is recorded in an immutable `StockLedger` table.
   - Balances are derived dynamically from ledger rows; silent balance overrides and negative stock are strictly prohibited.
3. **Bill of Materials (BOM) & Variance Engine:**
   - Dynamic formula scaling for standard batch quantities.
   - Live **Yield Variance** tracking (Benchmark: $-6.00\%$ flagged).
   - Live **Consumption Variance** tracking (Benchmark: $+5.00\%$ oil flagged).
   - Packaging scrap & damaged pouch tracking.
4. **Mobile-Friendly Salesman & Shortage Handling:**
   - Sales reps book customer orders with instant turnover and tax estimates.
   - Factory Admin reviews stock in real-time. If stock is insufficient, the system flags the exact shortage (Benchmark: $120$ ordered vs $88$ available = $32$ shortage) and supports partial fulfillment.
5. **Statutory Indian GST Invoicing:**
   - Detects Intra-State (Tamil Nadu: CGST 2.5% + SGST 2.5%) vs Inter-State (Outside TN: IGST 5.0%).
   - Sequential, gap-free financial year based numbering (`INV/2026-27/0001`).
   - Downloadable, official GST Tax Invoice PDFs generated dynamically using **ReportLab**.
   - No silent deletions: posted invoices require credit-note cancellation with audit reason.
6. **Collections & Receivables Ageing:**
   - Partial payment recording with balance due validation.
   - Real-time customer receivables ageing buckets ($0\text{--}30$, $31\text{--}60$, $61\text{--}90$, and $90+$ days).
7. **Batch Absorption Costing:**
   - Direct materials + packaging scrap + direct labour ($₹1,200$) + power/gas ($₹600$).
   - Calculates true unit cost per good marketable packet ($₹29.79$) and wholesale gross margins ($40.42\%$).
8. **Exportable Audit Reports & Event Log:**
   - Monthly Sales Register, GST Summary, Purchase Register, Stock Summaries, Production Variance, and Receivables Ageing with **1-click CSV exports**.
   - Comprehensive compliance audit log tracking user, action, entity, timestamp, and IP address.

---

## 🛠️ Technology Stack

- **Backend:** Python 3.12, Flask, Flask-SQLAlchemy, Flask-Login, Werkzeug Security
- **Database:** SQLite (local zero-configuration embedded database)
- **PDF Generation:** ReportLab
- **Frontend:** HTML5, CSS3, JavaScript (ES6), Bootstrap 5.3, Bootstrap Icons, Chart.js
- **Testing:** Pytest / Python `unittest`

---

## 🚀 Installation & Local Setup (Windows)

### Prerequisites:
- Python 3.10+ installed on Windows. (Verify with `python --version` in PowerShell or Command Prompt).

### Step 1: Open Terminal in Project Directory
```powershell
cd c:\Users\ADMIN\OneDrive\Desktop\SnackFlow
```

### Step 2: (Optional) Create & Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If on Command Prompt: `venv\Scripts\activate.bat`)*

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Initialize & Seed Database with Benchmark Scenario
```powershell
python seed.py --reset
```
*This command creates the SQLite database (`snackflow.db`), provisions all 5 demo user accounts, configures master products/customers/suppliers/BOMs, and executes all Steps 1–9 of the primary manufacturing benchmark scenario.*

### Step 5: Start the Web Application
```powershell
python run.py
```
Open your web browser and navigate to:
👉 **`http://127.0.0.1:5000`**

---

## 🔑 Demo User Credentials

All demo user accounts are pre-configured with the default password: **`admin123`**

| Role | Username | Password | Key Responsibilities & Capabilities |
|---|---|---|---|
| **Business Owner** | `owner` | `admin123` | Executive dashboard, company turnover, stock valuation, production output, full system access |
| **Factory Admin** | `admin` | `admin123` | Verify sales orders, manage stock shortages, generate GST invoices, dispatch shipments, receive purchases |
| **Salesman A** | `salesman_a` | `admin123` | Book customer orders (Tamil Nadu territory), view order statuses, track customer deliveries |
| **Salesman B** | `salesman_b` | `admin123` | Book customer orders (Inter-state Karnataka territory), check shortages |
| **Production Supervisor**| `supervisor`| `admin123` | Monitor raw-material inventory, plan & execute batch runs, record damaged pouches, inspect variances |
| **Accountant / Auditor** | `accountant` | `admin123` | Read-only financial oversight, GST summaries, collections, receivables ageing reports, CSV exports |

> **Tip for Evaluators:** The login screen provides **1-Click Quick Login Buttons** that autofill credentials. When logged in, you can switch between any role on the fly using the **"Role: ..."** dropdown in the top navbar!

---

## 📊 Benchmark Scenario Walkthrough (Step-by-Step)

SnackFlow comes pre-loaded with the exact internship challenge benchmark scenario:

- **Factory:** SnackFlow Madurai Plant, Tamil Nadu (State Code: `33`, GSTIN: `33AAAAA0000A1Z5`)
- **Product:** Murukku 200g (Selling price: $₹50.00$, GST: $5.0\%$, HSN: `19059040`)
- **Standard BOM (200 packets):** Flour: 40 kg, Oil: 10 L, Spices: 1.2 kg, Pouches: 200 pcs, Cartons: 10 pcs
- **Opening Stock:** Flour: 100 kg, Oil: 30 L, Spices: 5 kg, Pouches: 500 pcs, Cartons: 30 pcs, Finished Murukku: 50 packets

### Benchmark Transactions Executed:
1. **Step 1 (Purchase):** Purchased 60 kg flour @ $₹45/\text{kg}$.  
   *Flour stock: $100 + 60 = 160\text{ kg}$.*
2. **Step 2 (Production Run):**  
   - Consumed: Flour 40 kg, Oil 10.5 L (planned 10 L $\rightarrow \mathbf{+5.0\%}$ variance alert), Spices 1.2 kg, Pouches 188 good + 6 damaged = 194 pcs, Cartons 9 pcs.
   - Good output: 188 packets (planned 200 $\rightarrow \mathbf{-6.0\%}$ yield variance alert).
   - Overheads: Direct labour $₹1,200$, Gas & Power $₹600$.
   - **Costing:** Total Batch Cost = $₹5,601.00$ $\rightarrow$ **Cost per packet = $₹29.79$**. Gross margin = $₹20.21$ ($40.42\%$).
   - *Finished goods stock: $50 + 188 = 238\text{ packets}$.*
3. **Step 3 (Sales Order A):** Salesman A booked order for 150 packets for **Retailer A** (Tamil Nadu).
4. **Step 4 (Approval, Invoicing & Dispatch):**  
   - Factory Admin approved order.
   - Generated GST Invoice `INV/2026-27/0001`: Taxable = $₹7,500.00$, CGST (2.5%) = $₹187.50$, SGST (2.5%) = $₹187.50$. **Invoice Total = $₹7,875.00$**.
   - Dispatched 150 packets via stock ledger.  
   - *Finished goods stock: $238 - 150 = \mathbf{88\text{ packets}}$.*
5. **Step 5 (Sales Order B):** Salesman B booked order for 120 packets for **Distributor B** (Karnataka).
6. **Step 6 (Shortage Handling):**  
   - System verified stock: $88\text{ packets}$ available vs $120\text{ packets}$ ordered.
   - **Shortage Detected: $\mathbf{32\text{ packets}}$**. Highlighted in high-visibility alert banner.
7. **Step 7 (Customer Payment):**  
   - Retailer A paid $₹4,000.00$ via NEFT bank transfer.
   - **Remaining Outstanding Balance = $\mathbf{₹3,875.00}$**.
8. **Step 8 (Costing):**  
   - Labour ($₹1,200$) and Power/Gas ($₹600$) recorded and allocated to batch cost.
9. **Step 9 (Monthly Reports):**  
   - Filterable Sales Register, GST Tax Summary, Stock Ledger, and Receivables Ageing generated and exportable to CSV.

---

## 🧪 Running Automated Tests

SnackFlow includes automated integration tests that run against an in-memory SQLite database to verify all calculations, stock movements, variances, and GST rules:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

### Verified Test Cases:
- `test_full_benchmark_flow`: Asserts all 9 benchmark steps, closing stocks, variances, invoices, and payments.
- `test_prevent_negative_inventory`: Asserts that stock ledger blocks any deduction causing balance $< 0$.
- `test_interstate_igst_calculation`: Asserts that interstate sales to Karnataka charge 100% IGST (5%) without CGST/SGST.
- `test_invoice_cancellation`: Asserts cancellation credit-note workflow without record deletion.
- `test_user_authentication_and_password_hashing`: Asserts PBKDF2/SHA256 password hashing.

---

## 📁 Project Structure

```
SnackFlow/
├── app/
│   ├── __init__.py                # App factory, extensions, Jinja custom filters
│   ├── config.py                  # Factory profile settings & database configuration
│   ├── models/                    # SQLAlchemy database models (exact Decimal arithmetic)
│   │   ├── audit.py               # Immutable audit trail
│   │   ├── costing.py             # Production overhead expenses
│   │   ├── dispatch.py            # Shipment tracking
│   │   ├── inventory.py           # Immutable Stock Ledger
│   │   ├── invoice.py             # GST Tax Invoices & line items
│   │   ├── master.py              # Products, Raw Materials, BOM, Customers, Suppliers
│   │   ├── payment.py             # Collections & settlements
│   │   ├── production.py          # Batch runs, variances, and consumptions
│   │   ├── purchase.py            # Procurement purchase orders
│   │   ├── sales.py               # Customer sales orders & shortage fields
│   │   └── user.py                # User credentials & RBAC roles
│   ├── services/                  # Encapsulated business logic services
│   │   ├── audit_service.py       # Centralized audit logger
│   │   ├── dispatch_service.py    # Finished goods deduction & tracking
│   │   ├── inventory_service.py   # Ledger double-entry, dynamic balances, stock checks
│   │   ├── invoice_service.py     # Indian GST tax engine & FY numbering
│   │   ├── payment_service.py     # Payment recording & 90-day ageing buckets
│   │   ├── pdf_service.py         # ReportLab invoice PDF generator
│   │   ├── production_service.py  # BOM scaling, variance calculation, absorption costing
│   │   └── sales_service.py       # Order workflow & shortage detection
│   ├── routes/                    # Modular controllers (Blueprints)
│   │   ├── audit.py               # Audit log browser
│   │   ├── auth.py                # Authentication, logout, and demo role switcher
│   │   ├── costing.py             # Batch costing and expense management
│   │   ├── dashboard.py           # 5 distinct role-specific dashboards
│   │   ├── dispatch.py            # Dispatch queue and shipment authorization
│   │   ├── inventory.py           # Raw material, finished goods, and ledger views
│   │   ├── invoices.py            # Invoicing, PDF download, and cancellations
│   │   ├── master.py              # Master data CRUD operations
│   │   ├── payments.py            # Collections and customer receivables ageing
│   │   ├── production.py          # Batch runs execution and dynamic BOM API
│   │   ├── purchases.py           # Purchase orders and material inward receipts
│   │   ├── reports.py             # Statutory reports and dynamic CSV streaming
│   │   └── sales.py               # Sales orders creation and verification
│   ├── static/
│   │   ├── css/style.css          # Modern SaaS dashboard theme
│   │   └── js/main.js             # Client interactivity, dialogs, auto-dismiss alerts
│   └── templates/                 # Jinja2 templates organized by domain
├── tests/
│   ├── test_benchmark.py          # Complete benchmark end-to-end test suite
│   └── test_services.py           # Services, GST, and negative stock unit tests
├── seed.py                        # Benchmark seeder (idempotent, supports --reset)
├── run.py                         # Application entry point with auto-initialization
├── requirements.txt               # Pinned Python package dependencies
├── README.md                      # Project manual and installation guide
├── DESIGN.md                      # System architecture and technical design document
└── .gitignore                     # Git ignore rules
```

---

## 💡 How to Present this Project in an Internship Interview

If presenting SnackFlow to technical interviewers or hiring managers:
1. **Explain the Architecture First:**  
   Emphasize the **separation of concerns** between Controllers (Blueprints), Services (Business Logic), and Models (Data Access). Explain that business rules like GST calculation and ledger integrity are kept in dedicated services, not scattered in view functions.
2. **Highlight the Stock Ledger Innovation:**  
   Explain why you chose an **immutable stock ledger** over a simple `stock_count` column. Mention that real manufacturing audits require proving where every single kilogram of flour or pouch went, and how you strictly prevent negative inventory.
3. **Demonstrate Real Benchmark Calculations:**  
   Show the live numbers in the database:
   - Yield variance of $-6\%$ on 188 actual vs 200 planned packets.
   - Oil consumption variance of $+5\%$ on 10.5 L vs 10 L standard.
   - Unit packet cost of $₹29.79$ calculated from materials ($₹3,801$) + labour ($₹1,200$) + power ($₹600$) divided by 188 good packets.
   - Customer A invoice total of $₹7,875.00$ ($₹7,500$ taxable + $₹187.50$ CGST + $₹187.50$ SGST) and remaining balance of $₹3,875.00$ after the $₹4,000$ payment.
   - Shortage of 32 packets flagged when Customer B ordered 120 packets with only 88 packets remaining in warehouse.
4. **Point Out Enterprise Polish:**  
   Showcase the 1-click CSV exports, the dynamic ReportLab PDF invoice generation, the mobile-responsive sidebar, the demo role switcher, and the complete audit trail.

---

## ⚠️ Project Limitations & Future Roadmap

- **Multi-warehouse routing:** Currently models a single factory warehouse (Madurai Plant). Multi-location transfer orders (e.g. branch depots) can be added as an extension.
- **Direct Bank API Integration:** Payments are currently recorded manually; future iterations can integrate Razorpay or ICICI/SBI corporate banking APIs for automatic webhook reconciliation.
- **Production Scheduling Gantt:** Currently executes immediate batch runs; a scheduling queue with machine availability calendars can be introduced.

---

## 📄 License & Credits
Developed as an individual software developer challenge for packaged snack manufacturing management. Free to use for demonstration, educational, and evaluation purposes.
