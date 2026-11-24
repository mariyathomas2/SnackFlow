import csv
import io
from decimal import Decimal
from datetime import datetime, date
from flask import Blueprint, render_template, request, make_response, Response, redirect, url_for
from flask_login import login_required
from app import db
from app.models.user import Role
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from app.models.purchase import PurchaseOrder, PurchaseItem
from app.models.production import ProductionRun, ProductionConsumption
from app.models.payment import Payment
from app.models.inventory import StockLedger
from app.models.audit import AuditLog
from app.routes.auth import role_required
from app.services.inventory_service import get_raw_materials_summary, get_finished_goods_summary
from app.services.payment_service import get_customer_receivables_summary

reports_bp = Blueprint('reports', __name__)

def generate_csv_response(filename, headers, rows):
    """
    Utility to stream dynamic CSV response.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    return response

@reports_bp.route('/')
@login_required
def index():
    return render_template('reports/index.html')

# 1. SALES REGISTER
@reports_bp.route('/sales-register')
@login_required
def sales_register():
    month = request.args.get('month', '')
    query = Invoice.query.filter(Invoice.status != InvoiceStatus.CANCELLED).order_by(Invoice.invoice_date.desc())
    
    invoices = query.all()
    
    if request.args.get('export') == 'csv':
        headers = ['Invoice No', 'Date', 'Customer Name', 'State', 'GSTIN', 'Taxable Amount (Rs)', 'CGST (Rs)', 'SGST (Rs)', 'IGST (Rs)', 'Total GST (Rs)', 'Total Amount (Rs)', 'Status']
        rows = [
            [
                inv.invoice_number,
                inv.invoice_date.strftime('%Y-%m-%d'),
                inv.customer_name,
                inv.customer_state,
                inv.customer_gstin or 'Unregistered',
                f"{inv.taxable_amount:.2f}",
                f"{inv.cgst_amount:.2f}",
                f"{inv.sgst_amount:.2f}",
                f"{inv.igst_amount:.2f}",
                f"{inv.total_tax_amount:.2f}",
                f"{inv.total_amount:.2f}",
                inv.status
            ]
            for inv in invoices
        ]
        return generate_csv_response('sales_register.csv', headers, rows)

    total_taxable = sum(i.taxable_amount for i in invoices)
    total_cgst = sum(i.cgst_amount for i in invoices)
    total_sgst = sum(i.sgst_amount for i in invoices)
    total_igst = sum(i.igst_amount for i in invoices)
    total_amount = sum(i.total_amount for i in invoices)

    return render_template(
        'reports/sales_register.html',
        invoices=invoices,
        total_taxable=total_taxable,
        total_cgst=total_cgst,
        total_sgst=total_sgst,
        total_igst=total_igst,
        total_amount=total_amount
    )

# 2. GST SUMMARY
@reports_bp.route('/gst-summary')
@login_required
def gst_summary():
    invoices = Invoice.query.filter(Invoice.status != InvoiceStatus.CANCELLED).all()

    intra_state_invoices = [i for i in invoices if not i.is_interstate]
    inter_state_invoices = [i for i in invoices if i.is_interstate]

    intra_taxable = sum(i.taxable_amount for i in intra_state_invoices)
    intra_cgst = sum(i.cgst_amount for i in intra_state_invoices)
    intra_sgst = sum(i.sgst_amount for i in intra_state_invoices)

    inter_taxable = sum(i.taxable_amount for i in inter_state_invoices)
    inter_igst = sum(i.igst_amount for i in inter_state_invoices)

    total_taxable = intra_taxable + inter_taxable
    total_gst = intra_cgst + intra_sgst + inter_igst

    if request.args.get('export') == 'csv':
        headers = ['Category', 'Taxable Turnover (Rs)', 'CGST (Rs)', 'SGST (Rs)', 'IGST (Rs)', 'Total Tax (Rs)']
        rows = [
            ['Intra-State (Tamil Nadu)', f"{intra_taxable:.2f}", f"{intra_cgst:.2f}", f"{intra_sgst:.2f}", "0.00", f"{(intra_cgst + intra_sgst):.2f}"],
            ['Inter-State (Outside TN)', f"{inter_taxable:.2f}", "0.00", "0.00", f"{inter_igst:.2f}", f"{inter_igst:.2f}"],
            ['GRAND TOTAL', f"{total_taxable:.2f}", f"{intra_cgst:.2f}", f"{intra_sgst:.2f}", f"{inter_igst:.2f}", f"{total_gst:.2f}"]
        ]
        return generate_csv_response('gst_summary.csv', headers, rows)

    return render_template(
        'reports/gst_summary.html',
        intra_taxable=intra_taxable,
        intra_cgst=intra_cgst,
        intra_sgst=intra_sgst,
        inter_taxable=inter_taxable,
        inter_igst=inter_igst,
        total_taxable=total_taxable,
        total_gst=total_gst
    )

# 3. PURCHASE REGISTER
@reports_bp.route('/purchase-register')
@login_required
def purchase_register():
    orders = PurchaseOrder.query.order_by(PurchaseOrder.purchase_date.desc()).all()

    if request.args.get('export') == 'csv':
        headers = ['PO Number', 'Date', 'Supplier Name', 'State', 'GSTIN', 'Total Amount (Rs)', 'Status']
        rows = [
            [
                po.po_number,
                po.purchase_date.strftime('%Y-%m-%d'),
                po.supplier.name,
                po.supplier.state,
                po.supplier.gst_details or 'Unregistered',
                f"{po.total_amount:.2f}",
                po.status
            ]
            for po in orders
        ]
        return generate_csv_response('purchase_register.csv', headers, rows)

    total_spend = sum(po.total_amount for po in orders)
    return render_template('reports/purchase_register.html', orders=orders, total_spend=total_spend)

# 4. RAW MATERIAL STOCK SUMMARY
@reports_bp.route('/raw-material-stock')
@login_required
def raw_material_stock():
    summary = get_raw_materials_summary()
    total_val = sum(s['stock_value'] for s in summary)

    if request.args.get('export') == 'csv':
        headers = ['Code', 'Material Name', 'Unit', 'Current Stock', 'Stock Threshold', 'Unit Cost (Rs)', 'Valuation (Rs)', 'Status']
        rows = [
            [
                s['code'],
                s['name'],
                s['unit'],
                f"{s['current_stock']:.4f}",
                f"{s['threshold']:.2f}",
                f"{s['cost']:.2f}",
                f"{s['stock_value']:.2f}",
                s['status']
            ]
            for s in summary
        ]
        return generate_csv_response('raw_material_stock.csv', headers, rows)

    return render_template('reports/raw_material_stock.html', summary=summary, total_val=total_val)

# 5. FINISHED GOODS STOCK SUMMARY
@reports_bp.route('/finished-goods-stock')
@login_required
def finished_goods_stock():
    summary = get_finished_goods_summary()
    total_val = sum(s['stock_value'] for s in summary)

    if request.args.get('export') == 'csv':
        headers = ['SKU', 'Product Name', 'Unit', 'Current Stock', 'Selling Price (Rs)', 'Retail Valuation (Rs)', 'GST Rate %']
        rows = [
            [
                s['sku'],
                s['name'],
                s['unit'],
                f"{s['current_stock']:.2f}",
                f"{s['selling_price']:.2f}",
                f"{s['stock_value']:.2f}",
                f"{s['gst_rate']:.2f}"
            ]
            for s in summary
        ]
        return generate_csv_response('finished_goods_stock.csv', headers, rows)

    return render_template('reports/finished_goods_stock.html', summary=summary, total_val=total_val)

# 5b. FULL STOCK LEDGER EXPORT
@reports_bp.route('/stock-ledger')
@login_required
def stock_ledger():
    entries = StockLedger.query.order_by(StockLedger.id.desc()).all()
    if request.args.get('export') == 'csv':
        headers = ['Tx ID', 'Date', 'Item Name', 'Category', 'Transaction Type', 'Qty In', 'Qty Out', 'Balance After', 'Unit', 'Unit Cost (Rs)', 'Reference Type', 'Reference ID', 'Notes']
        rows = [
            [
                e.id,
                e.transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
                e.item_name,
                e.item_type,
                e.transaction_type,
                f"{e.quantity_in:.4f}",
                f"{e.quantity_out:.4f}",
                f"{e.balance_after:.4f}",
                e.unit,
                f"{e.unit_cost:.2f}",
                e.reference_type or '',
                e.reference_id or '',
                e.notes or ''
            ]
            for e in entries
        ]
        return generate_csv_response('stock_ledger.csv', headers, rows)
    return redirect(url_for('inventory.ledger'))

# 6. PRODUCTION & VARIANCE REPORT
@reports_bp.route('/production-variance')
@login_required
def production_variance():
    runs = ProductionRun.query.order_by(ProductionRun.run_date.desc(), ProductionRun.id.desc()).all()

    if request.args.get('export') == 'csv':
        headers = ['Batch No', 'Date', 'Product', 'Planned Qty', 'Actual Good', 'Damaged', 'Yield Var %', 'Material Cost (Rs)', 'Total Cost (Rs)', 'Cost/Pkt (Rs)']
        rows = [
            [
                r.batch_number,
                r.run_date.strftime('%Y-%m-%d'),
                r.product.name,
                f"{r.planned_quantity:.2f}",
                f"{r.actual_output_good:.2f}",
                f"{r.damaged_units:.2f}",
                f"{r.yield_variance_pct:.2f}%",
                f"{r.total_material_cost:.2f}",
                f"{r.total_production_cost:.2f}",
                f"{r.cost_per_packet:.2f}"
            ]
            for r in runs
        ]
        return generate_csv_response('production_variance.csv', headers, rows)

    return render_template('reports/production_variance.html', runs=runs)

# 7. RECEIVABLES AGEING REPORT
@reports_bp.route('/receivables-ageing')
@login_required
def receivables_ageing():
    summary = get_customer_receivables_summary()
    total_receivables = sum(c['total_outstanding'] for c in summary)

    if request.args.get('export') == 'csv':
        headers = ['Customer Name', 'State', 'GSTIN', 'Total Outstanding (Rs)', '0-30 Days (Rs)', '31-60 Days (Rs)', '61-90 Days (Rs)', '90+ Days (Rs)']
        rows = [
            [
                c['customer_name'],
                c['state'],
                c['gstin'],
                f"{c['total_outstanding']:.2f}",
                f"{c['bucket_0_30']:.2f}",
                f"{c['bucket_31_60']:.2f}",
                f"{c['bucket_61_90']:.2f}",
                f"{c['bucket_90_plus']:.2f}"
            ]
            for c in summary
        ]
        return generate_csv_response('receivables_ageing.csv', headers, rows)

    return render_template('reports/receivables_ageing.html', summary=summary, total_receivables=total_receivables)
