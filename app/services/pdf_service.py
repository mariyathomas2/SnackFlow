import io
from decimal import Decimal
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from flask import current_app

def generate_invoice_pdf(invoice):
    """
    Generates a professional GST Tax Invoice PDF using ReportLab.
    Returns a BytesIO stream suitable for Flask send_file.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F172A'),
        alignment=1 # Center
    )
    
    header_style = ParagraphStyle(
        'CompanyHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#1E293B')
    )

    normal_style = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )

    bold_style = ParagraphStyle(
        'BoldText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0F172A')
    )

    small_style = ParagraphStyle(
        'SmallText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#64748B')
    )

    story = []

    # Title
    story.append(Paragraph("TAX INVOICE", title_style))
    story.append(Paragraph("<font size=8 color='#64748B'>(Issued under Section 31 of the CGST / SGST / IGST Act, 2017)</font>", ParagraphStyle('Sub', parent=title_style, fontSize=8, alignment=1)))
    story.append(Spacer(1, 10))

    # Company & Invoice Header Table
    company_name = current_app.config.get('COMPANY_NAME', 'SnackFlow Foods Pvt. Ltd.')
    factory_name = current_app.config.get('FACTORY_NAME', 'SnackFlow Madurai Plant')
    factory_addr = current_app.config.get('FACTORY_ADDRESS', 'Plot 42, SIDCO Industrial Estate, Kappalur, Madurai, Tamil Nadu - 625008')
    factory_gstin = current_app.config.get('FACTORY_GSTIN', '33AAAAA0000A1Z5')
    factory_state = current_app.config.get('FACTORY_STATE', 'Tamil Nadu (33)')

    seller_info = f"""
    <b>{company_name}</b><br/>
    <font size=8>{factory_name}</font><br/>
    <font size=8>{factory_addr}</font><br/>
    <b>GSTIN:</b> {factory_gstin} | <b>State:</b> {factory_state}
    """

    inv_info = f"""
    <b>Invoice No:</b> {invoice.invoice_number}<br/>
    <b>Date:</b> {invoice.invoice_date.strftime('%d-%b-%Y')}<br/>
    <b>Due Date:</b> {invoice.due_date.strftime('%d-%b-%Y') if invoice.due_date else 'Immediate'}<br/>
    <b>Place of Supply:</b> {invoice.customer_state} ({invoice.customer_state_code})<br/>
    <b>Order Ref:</b> {invoice.order.order_number if invoice.order else 'Direct Sale'}
    """

    header_table_data = [
        [Paragraph(seller_info, normal_style), Paragraph(inv_info, normal_style)]
    ]
    header_table = Table(header_table_data, colWidths=[4.0 * inch, 3.2 * inch])
    header_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))

    # Buyer Details Table
    buyer_info = f"""
    <b>Billed To / Consignee:</b><br/>
    <b>{invoice.customer_name}</b><br/>
    {invoice.customer_address}<br/>
    <b>State:</b> {invoice.customer_state} (Code: {invoice.customer_state_code})<br/>
    <b>GSTIN / UIN:</b> {invoice.customer_gstin or 'Unregistered Consumer / Composite'}
    """
    buyer_table_data = [[Paragraph(buyer_info, normal_style)]]
    buyer_table = Table(buyer_table_data, colWidths=[7.2 * inch])
    buyer_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFFFFF')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(buyer_table)
    story.append(Spacer(1, 10))

    # Items Table Header
    is_interstate = invoice.is_interstate
    if is_interstate:
        table_headers = [
            Paragraph("<b>#</b>", bold_style),
            Paragraph("<b>Item Description</b>", bold_style),
            Paragraph("<b>HSN</b>", bold_style),
            Paragraph("<b>Qty</b>", bold_style),
            Paragraph("<b>Rate</b>", bold_style),
            Paragraph("<b>Taxable</b>", bold_style),
            Paragraph("<b>IGST</b>", bold_style),
            Paragraph("<b>Total</b>", bold_style)
        ]
        col_widths = [0.4 * inch, 2.3 * inch, 0.8 * inch, 0.7 * inch, 0.7 * inch, 0.9 * inch, 0.8 * inch, 0.9 * inch]
    else:
        table_headers = [
            Paragraph("<b>#</b>", bold_style),
            Paragraph("<b>Item Description</b>", bold_style),
            Paragraph("<b>HSN</b>", bold_style),
            Paragraph("<b>Qty</b>", bold_style),
            Paragraph("<b>Rate</b>", bold_style),
            Paragraph("<b>Taxable</b>", bold_style),
            Paragraph("<b>CGST</b>", bold_style),
            Paragraph("<b>SGST</b>", bold_style),
            Paragraph("<b>Total</b>", bold_style)
        ]
        col_widths = [0.3 * inch, 2.0 * inch, 0.7 * inch, 0.6 * inch, 0.7 * inch, 0.8 * inch, 0.7 * inch, 0.7 * inch, 0.9 * inch]

    items_data = [table_headers]

    for idx, item in enumerate(invoice.items, 1):
        if is_interstate:
            row = [
                Paragraph(str(idx), small_style),
                Paragraph(f"<b>{item.product_name}</b>", normal_style),
                Paragraph(item.hsn, small_style),
                Paragraph(f"{item.quantity:.0f} {item.unit}", small_style),
                Paragraph(f"₹{item.unit_price:.2f}", small_style),
                Paragraph(f"₹{item.taxable_amount:.2f}", small_style),
                Paragraph(f"{item.igst_rate:.1f}%<br/>₹{item.igst_amount:.2f}", small_style),
                Paragraph(f"<b>₹{item.total_amount:.2f}</b>", normal_style)
            ]
        else:
            row = [
                Paragraph(str(idx), small_style),
                Paragraph(f"<b>{item.product_name}</b>", normal_style),
                Paragraph(item.hsn, small_style),
                Paragraph(f"{item.quantity:.0f} {item.unit}", small_style),
                Paragraph(f"₹{item.unit_price:.2f}", small_style),
                Paragraph(f"₹{item.taxable_amount:.2f}", small_style),
                Paragraph(f"{item.cgst_rate:.1f}%<br/>₹{item.cgst_amount:.2f}", small_style),
                Paragraph(f"{item.sgst_rate:.1f}%<br/>₹{item.sgst_amount:.2f}", small_style),
                Paragraph(f"<b>₹{item.total_amount:.2f}</b>", normal_style)
            ]
        items_data.append(row)

    # Summary Row
    if is_interstate:
        items_data.append([
            Paragraph("<b>Total:</b>", bold_style),
            "", "", "", "",
            Paragraph(f"<b>₹{invoice.taxable_amount:,.2f}</b>", bold_style),
            Paragraph(f"<b>₹{invoice.igst_amount:,.2f}</b>", bold_style),
            Paragraph(f"<b>₹{invoice.total_amount:,.2f}</b>", bold_style)
        ])
    else:
        items_data.append([
            Paragraph("<b>Total:</b>", bold_style),
            "", "", "", "",
            Paragraph(f"<b>₹{invoice.taxable_amount:,.2f}</b>", bold_style),
            Paragraph(f"<b>₹{invoice.cgst_amount:,.2f}</b>", bold_style),
            Paragraph(f"<b>₹{invoice.sgst_amount:,.2f}</b>", bold_style),
            Paragraph(f"<b>₹{invoice.total_amount:,.2f}</b>", bold_style)
        ])

    items_table = Table(items_data, colWidths=col_widths, repeatRows=1)
    items_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#0F172A')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('SPAN', (0, -1), (4, -1)), # Merge label in totals row
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F8FAFC')),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 10))

    # Payment Summary & Bank Details
    bank_info = f"""
    <b>Bank Details for NEFT / RTGS:</b><br/>
    <b>Bank:</b> {current_app.config.get('FACTORY_BANK_NAME', 'State Bank of India')}<br/>
    <b>Account No:</b> {current_app.config.get('FACTORY_BANK_ACC', '398712345678')}<br/>
    <b>IFSC:</b> {current_app.config.get('FACTORY_BANK_IFSC', 'SBIN0001234')}<br/>
    <b>Branch:</b> Kappalur Industrial Estate, Madurai
    """

    totals_info = f"""
    <b>Total Taxable Value:</b> ₹{invoice.taxable_amount:,.2f}<br/>
    <b>Total GST:</b> ₹{invoice.total_tax_amount:,.2f}<br/>
    <font size=11><b>Grand Total: ₹{invoice.total_amount:,.2f}</b></font><br/>
    <font color='#16A34A'><b>Amount Paid:</b> ₹{invoice.paid_amount:,.2f}</font><br/>
    <font color='#DC2626'><b>Balance Due:</b> ₹{invoice.balance_due:,.2f}</font>
    """

    bottom_data = [
        [Paragraph(bank_info, normal_style), Paragraph(totals_info, normal_style)]
    ]
    bottom_table = Table(bottom_data, colWidths=[4.0 * inch, 3.2 * inch])
    bottom_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(bottom_table)
    story.append(Spacer(1, 15))

    # Signatory Box
    sig_info = f"""
    <b>For {company_name}</b><br/><br/><br/>
    Authorized Signatory
    """
    sig_table = Table([[Paragraph("<b>Declaration:</b> We declare that this invoice shows the actual price of goods described and that all particulars are true and correct.", small_style), Paragraph(sig_info, normal_style)]], colWidths=[4.5 * inch, 2.7 * inch])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(sig_table)

    doc.build(story)
    buffer.seek(0)
    return buffer
