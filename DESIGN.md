# SnackFlow – Architecture & System Design Document

**Project:** SnackFlow – Order-to-Audit Management System for Packaged Food Manufacturing  
**Domain:** Packaged Snack Production & Wholesale Distribution (Tamil Nadu, India)  
**Author:** Senior Full-Stack Developer & Software Architect (Internship Candidate)  
**Target Environment:** Local Windows Environment, Python Flask, SQLite, HTML5/CSS3/Bootstrap 5  

---

## 1. Executive Summary & Problem Context

Small and mid-sized food manufacturing enterprises in India typically operate using fragmented tools: physical daybooks for production floor output, disparate WhatsApp messages for salesman order booking, manual spreadsheets for raw material purchases, and standalone accounting software for GST tax invoicing. This disconnect leads to:
1. **Silent stock discrepancies:** Inventory is manually updated or overwritten without an audit trail.
2. **Hidden manufacturing wastage:** Ingredient consumption variances and damaged pouches go unrecorded, masking the true cost per packet.
3. **Over-promising and delivery shortages:** Salesmen book customer orders without visibility into available finished goods, leading to delayed dispatches.
4. **GST compliance and receivables leakage:** Delayed invoicing, manual CGST/SGST/IGST calculation mistakes, and lack of receivables ageing visibility.

**SnackFlow** provides an integrated **Order-to-Audit ERP** engine built around:
- An **immutable stock ledger** ensuring no stock change occurs without a traceable transaction row.
- **Bill of Materials (BOM) & Variance Engine** tracking planned vs actual yields and consumption spikes.
- **Role-Based Access Control (RBAC)** separating duties across 5 distinct organizational roles.
- **Statutory GST Invoicing** adhering to Section 31 of the GST Act 2017 with financial-year based numbering and ReportLab PDF generation.
- **Batch Absorption Costing** allocating direct ingredients, packaging scrap, frying labour, and gas/power utilities.

---

## 2. High-Level Architecture & Layered Pattern

SnackFlow follows an enterprise **Layered Modular Pattern** built on top of Flask Blueprints and SQLAlchemy:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER                                │
│   Jinja2 Templates | Bootstrap 5 SaaS UI | Chart.js | Responsive Sidebar    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP / Session
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                            CONTROLLER LAYER                                 │
│      Route Blueprints (auth, dashboard, master, inventory, purchases,       │
│               production, sales, invoices, dispatch, payments, reports)     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Calls
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                             SERVICE LAYER                                   │
│  ├── inventory_service.py   (Ledger double-entry, dynamic balances)         │
│  ├── production_service.py  (BOM scaling, yield/consumption variance)       │
│  ├── sales_service.py       (Shortage detection, partial approvals)        │
│  ├── invoice_service.py     (FY numbering, Intra-TN vs Inter-State GST)     │
│  ├── dispatch_service.py    (Finished goods ledger deductions)             │
│  ├── payment_service.py     (Receipts, invoice allocation, 90-day ageing)   │
│  ├── pdf_service.py         (ReportLab GST Tax Invoice PDF generation)      │
│  └── audit_service.py       (Central compliance audit trail)                │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ ORM / Transactions
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                           DATA ACCESS LAYER                                 │
│    Flask-SQLAlchemy Models with Exact Decimal Arithmetic (Decimal/Numeric)  │
│      (User, Product, BOM, StockLedger, SalesOrder, Invoice, Payment, etc.)  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ SQL
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                             DATABASE LAYER                                  │
│                          SQLite (snackflow.db)                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Database Schema & Data Models

All monetary values (`selling_price`, `unit_cost`, `taxable_amount`, `cgst_amount`, `sgst_amount`, `igst_amount`, `balance_due`) and material quantities are modeled using **`db.Numeric(12, 2)`** or **`db.Numeric(12, 4)`**, mapping directly to Python's `decimal.Decimal` to eliminate floating-point rounding errors.

### Core Tables Summary:

| Table Name | Primary Purpose | Key Fields |
|---|---|---|
| `users` | Role-based authentication & profiles | `id`, `username`, `password_hash`, `role`, `full_name`, `is_active` |
| `products` | Finished goods catalog | `id`, `name`, `sku`, `selling_price`, `hsn`, `gst_rate`, `unit`, `status` |
| `raw_materials` | Ingredients & packaging items | `id`, `name`, `code`, `unit`, `stock_threshold`, `cost`, `status` |
| `boms` & `bom_items` | Standard recipes scaled to batch output | `id`, `product_id`, `batch_size`, `standard_quantity`, `unit` |
| `customers` | B2B retailers & wholesale distributors | `id`, `name`, `state`, `state_code`, `gstin`, `customer_type`, `address` |
| `suppliers` | Raw material procurement vendors | `id`, `name`, `state`, `gst_details`, `address` |
| `stock_ledger` | Immutable inventory transaction history | `id`, `transaction_date`, `item_type`, `item_id`, `transaction_type`, `quantity_in`, `quantity_out`, `balance_after`, `unit`, `unit_cost`, `reference_type`, `reference_id` |
| `purchase_orders` & `purchase_items` | Inward vendor procurement records | `id`, `po_number`, `supplier_id`, `total_amount`, `quantity`, `unit_cost` |
| `production_runs` & `production_consumptions` | Manufacturing batches, variances, costs | `id`, `batch_number`, `planned_quantity`, `actual_output_good`, `damaged_units`, `cartons_used`, `yield_variance_pct`, `total_production_cost`, `cost_per_packet` |
| `sales_orders` & `sales_order_items` | Customer sales booking & shortage checks | `id`, `order_number`, `customer_id`, `salesman_id`, `status`, `ordered_quantity`, `approved_quantity`, `available_stock_at_review`, `shortage_quantity` |
| `invoices` & `invoice_items` | Statutory GST tax invoices | `id`, `invoice_number`, `order_id`, `customer_id`, `is_interstate`, `taxable_amount`, `cgst_amount`, `sgst_amount`, `igst_amount`, `total_amount`, `paid_amount`, `balance_due` |
| `dispatch_records` & `dispatch_items` | Physical shipment tracking & stock deduction | `id`, `dispatch_number`, `order_id`, `invoice_id`, `carrier_name`, `total_quantity` |
| `payments` | Customer collections & settlements | `id`, `payment_number`, `invoice_id`, `customer_id`, `amount`, `payment_method`, `reference_number` |
| `audit_logs` | Immutable audit compliance trail | `id`, `user_id`, `username`, `action`, `entity_type`, `entity_id`, `description`, `ip_address`, `timestamp` |

---

## 4. Immutable Inventory Ledger Design

### The Core Architectural Rule:
> **Never silently update stock by directly altering a balance column.**

In SnackFlow, inventory balances are **derived dynamically** by summing ledger transactions:
$$\text{Current Balance} = \sum (\text{Quantity In}) - \sum (\text{Quantity Out})$$

### Transaction Types:
1. `OPENING_STOCK`: Initial warehouse setup.
2. `PURCHASE_RECEIPT`: Supplier inward shipment (credits raw materials).
3. `PRODUCTION_ISSUE`: Ingredients drawn into manufacturing batch (debits raw materials).
4. `MATERIAL_WASTAGE`: Packaging scrap / damaged pouches during production (debits raw materials).
5. `FG_PRODUCTION_OUTPUT`: Passed good finished packets (credits finished goods).
6. `DISPATCH`: Physical customer shipment (debits finished goods).
7. `STOCK_ADJUSTMENT`: Cycle count reconciliation with mandatory audit reason.

### Negative Inventory Prevention:
Before creating any outward movement, `inventory_service.py` evaluates:
$$\text{New Balance} = \text{Current Balance} + \text{Qty In} - \text{Qty Out}$$
If $\text{New Balance} < 0$, a `ValueError` is raised, rolling back the database transaction.

---

## 5. Sales Workflow & Shortage Engine

1. **Order Creation (Salesman):**
   Salesman selects customer and enters quantities. The system computes tentative taxable and GST values.
2. **Stock Availability Verification (Admin):**
   The factory admin inspects live warehouse inventory:
   $$\text{Shortage} = \max(0, \text{Ordered Quantity} - \text{Available Stock})$$
3. **Shortage Handling (Benchmark Step 5 & 6):**
   When Distributor B orders 120 packets while available stock is only 88 packets, the UI displays a high-visibility shortage alert:
   - Ordered: 120 packets
   - Available Stock: 88 packets
   - Shortage: 32 packets
   The Admin can:
   - Approve partial fulfillment (88 packets), leaving 32 packets for a future production run.
   - Keep the order on hold until manufacturing replenishes stock.

---

## 6. Statutory GST Invoicing Engine

### GST Rules Enforced:
- **Factory Registration:** Madurai, Tamil Nadu (State Code: `33`, GSTIN: `33AAAAA0000A1Z5`).
- **Intra-State Supply (Customer in Tamil Nadu, e.g. Retailer A):**
  - CGST = $2.5\%$
  - SGST = $2.5\%$
  - IGST = $0.0\%$
- **Inter-State Supply (Customer outside Tamil Nadu, e.g. Distributor B in Karnataka - Code `29`):**
  - IGST = $5.0\%$
  - CGST = $0.0\%$
  - SGST = $0.0\%$
- **HSN Classification:** `19059040` (Murukku, traditional savory snacks) under 5% GST bracket.
- **Sequential FY Numbering:** `INV/YYYY-YY/XXXX` (e.g. `INV/2026-27/0001`). Gap-free and unique.
- **ReportLab PDF Generation:** Generates downloadable, print-ready PDF invoices formatted with standard Indian GST statutory declarations, seller/buyer tables, and bank remittance coordinates.
- **Cancellation / Credit Note Policy:** Posted invoices cannot be deleted. Cancelling an invoice requires a mandatory reason, zeroes the balance due, and logs an event in the audit trail.

---

## 7. Manufacturing Costing & Margin Analysis

### Absorption Batch Costing Method:
SnackFlow calculates unit manufacturing cost using absorption batch costing:
$$\text{Total Batch Cost} = \text{Raw Materials Cost} + \text{Direct Labour} + \text{Energy Overheads (Gas/Power)} + \text{Overheads}$$

$$\text{Unit Cost per Good Packet} = \frac{\text{Total Batch Cost}}{\text{Actual Passed Good Packets}}$$

$$\text{Gross Margin per Packet} = \text{Selling Price} - \text{Unit Cost per Good Packet}$$

### Benchmark Scenario Step 2 Breakdown:
- **Raw Materials Consumed:**
  - Flour: $40\text{ kg} \times ₹45 = ₹1,800.00$
  - Cooking oil: $10.5\text{ L} \times ₹130 = ₹1,365.00$
  - Salt/spice mix: $1.2\text{ kg} \times ₹100 = ₹120.00$
  - Pouches ($188\text{ good} + 6\text{ damaged} = 194\text{ pcs}$): $194 \times ₹1.50 = ₹291.00$
  - Cartons: $9\text{ pcs} \times ₹25 = ₹225.00$
  - **Subtotal Materials Cost:** $₹3,801.00$
- **Direct Manufacturing Overheads:**
  - Direct Labour: $₹1,200.00$
  - Gas & Power: $₹600.00$
- **Total Production Cost:** $₹3,801 + ₹1,200 + ₹600 = ₹5,601.00$
- **Good Marketable Output:** $188\text{ packets}$
- **Actual Cost per Good Packet:**
  $$\frac{₹5,601.00}{188} = ₹29.7925 \approx ₹29.79\text{ per packet}$$
- **Wholesale Selling Price:** $₹50.00\text{ per packet}$
- **Gross Profit Margin:**
  $$₹50.00 - ₹29.79 = ₹20.21\text{ per packet } (40.42\%)$$

---

## 8. Benchmark Scenario Results Reconciliation

| Metric / Checkpoint | Expected Benchmark Value | SnackFlow Computed Result | Verification Status |
|---|---|---|---|
| Flour Opening Stock | 100 kg | 100 kg | PASS |
| Flour Purchase (Step 1) | +60 kg | +60 kg | PASS |
| Flour Consumed (Step 2) | -40 kg | -40 kg | PASS |
| **Flour Closing Stock** | **120 kg** | **120.0000 kg** | **PASS** |
| Oil Opening Stock | 30 L | 30 L | PASS |
| Oil Consumed (Step 2) | -10.5 L | -10.5 L | PASS |
| **Oil Closing Stock** | **19.5 L** | **19.5000 litres** | **PASS** |
| Pouches Opening Stock | 500 pcs | 500 pcs | PASS |
| Pouches Used (188 + 6) | -194 pcs | -194 pcs | PASS |
| **Pouches Closing Stock** | **306 pcs** | **306.0000 pcs** | **PASS** |
| Finished Goods Opening | 50 pkts | 50 pkts | PASS |
| Finished Goods Produced | +188 pkts | +188 pkts | PASS |
| **Finished Goods Post-Prod** | **238 pkts** | **238.0000 pkts** | **PASS** |
| Dispatched to Retailer A | -150 pkts | -150 pkts | PASS |
| **Finished Goods Post-Disp** | **88 pkts** | **88.0000 pkts** | **PASS** |
| **Yield Variance** | **-6.00% (Flagged)** | **-6.00% (Flagged)** | **PASS** |
| **Oil Consumption Variance** | **+5.00% (Flagged)** | **+5.00% (Flagged)** | **PASS** |
| Retailer A Taxable Amount | ₹7,500.00 | ₹7,500.00 | PASS |
| Retailer A CGST (2.5%) | ₹187.50 | ₹187.50 | PASS |
| Retailer A SGST (2.5%) | ₹187.50 | ₹187.50 | PASS |
| **Retailer A Invoice Total** | **₹7,875.00** | **₹7,875.00** | **PASS** |
| Retailer A Payment | ₹4,000.00 | ₹4,000.00 | PASS |
| **Retailer A Balance Due** | **₹3,875.00** | **₹3,875.00** | **PASS** |
| Distributor B Ordered | 120 pkts | 120 pkts | PASS |
| Distributor B Available | 88 pkts | 88 pkts | PASS |
| **Distributor B Shortage** | **32 pkts (Flagged)** | **32.0000 pkts (Flagged)**| **PASS** |
| **Unit Cost per Packet** | **₹29.79** | **₹29.79** | **PASS** |

---

## 9. Security, RBAC & Audit Design

1. **Password Hashing:** Implemented with `werkzeug.security.generate_password_hash` using modern PBKDF2/SHA256 iterations. Passwords are never stored in plaintext.
2. **Role-Based Permissions:** Enforced through `@role_required(*allowed_roles)` route decorators.
   - `SALESMAN`: Limited to customer ordering and viewing own orders.
   - `FACTORY_ADMIN`: Controls order approval, shortage override, invoicing, dispatch, and receiving.
   - `PRODUCTION_SUPERVISOR`: Manages raw materials, BOM, and production runs.
   - `ACCOUNTANT`: Read-only access to all financial registers, GST summaries, and receivables ageing.
   - `OWNER`: Full executive visibility across all departments.
3. **Audit Trail:** Captured automatically via `log_audit()` on all key operations (user login/logout, order creation, approvals, rejections, purchases, production runs, stock movements, invoices, dispatches, and payments) capturing username, user ID, action, entity type, entity ID, description, timestamp, and remote IP address.
