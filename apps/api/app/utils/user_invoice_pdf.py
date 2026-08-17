"""
User Invoice PDF Generator.
Generates professional PDF invoices from UserInvoice model data.
Uses pure HTML → PDF conversion approach (no ReportLab dependency needed).
Falls back to a simple text-based PDF if weasyprint/pdfkit aren't available.
"""
from datetime import datetime
import io


def generate_user_invoice_pdf(invoice):
    """Generate a PDF from a UserInvoice model instance.

    Returns bytes of the PDF file.
    """
    # Try weasyprint first (best quality), then pdfkit, then fallback
    try:
        return _generate_with_weasyprint(invoice)
    except ImportError:
        pass

    try:
        return _generate_with_reportlab(invoice)
    except ImportError:
        pass

    # Final fallback: generate a simple HTML file as PDF-like content
    return _generate_html_fallback(invoice)


def _build_invoice_html(invoice):
    """Build the HTML string for the invoice."""
    items_html = ""
    for item in (invoice.items or []):
        desc = item.get("description", "")
        qty = item.get("qty", item.get("quantity", 1))
        rate = item.get("rate", item.get("price", 0))
        amount = item.get("amount", float(qty) * float(rate))
        items_html += f"""
        <tr>
            <td style="padding:10px 12px; border-bottom:1px solid #e5e7eb;">{desc}</td>
            <td style="padding:10px 12px; border-bottom:1px solid #e5e7eb; text-align:center;">{qty}</td>
            <td style="padding:10px 12px; border-bottom:1px solid #e5e7eb; text-align:right;">{float(rate):,.2f}</td>
            <td style="padding:10px 12px; border-bottom:1px solid #e5e7eb; text-align:right;">{float(amount):,.2f}</td>
        </tr>"""

    currency = invoice.currency or "USD"
    logo_html = f'<img src="{invoice.logo_url}" style="max-height:60px; max-width:200px;" />' if invoice.logo_url else ""

    due_date_str = invoice.due_date.strftime("%B %d, %Y") if invoice.due_date else "Upon Receipt"
    created_str = invoice.created_at.strftime("%B %d, %Y") if invoice.created_at else datetime.utcnow().strftime("%B %d, %Y")

    status_color = {
        "draft": "#6B7280",
        "sent": "#3B82F6",
        "paid": "#10B981",
        "overdue": "#EF4444",
        "cancelled": "#9CA3AF",
    }.get(invoice.status, "#6B7280")

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #1f2937; line-height: 1.5; }}
    .invoice-container {{ max-width: 800px; margin: 0 auto; padding: 40px; }}
    .header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 40px; }}
    .header-left {{ flex: 1; }}
    .header-right {{ text-align: right; }}
    .invoice-title {{ font-size: 32px; font-weight: 700; color: #111827; letter-spacing: -0.5px; }}
    .invoice-number {{ font-size: 14px; color: #6B7280; margin-top: 4px; }}
    .status-badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; color: white; background: {status_color}; }}
    .details-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 40px; }}
    .detail-section h3 {{ font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #9CA3AF; margin-bottom: 8px; font-weight: 600; }}
    .detail-section p {{ font-size: 14px; color: #374151; margin-bottom: 2px; }}
    .detail-section .name {{ font-weight: 600; font-size: 16px; color: #111827; }}
    .items-table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
    .items-table th {{ background: #F9FAFB; padding: 12px; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #6B7280; font-weight: 600; border-bottom: 2px solid #E5E7EB; }}
    .items-table th:first-child {{ text-align: left; }}
    .items-table th:last-child, .items-table th:nth-child(3) {{ text-align: right; }}
    .items-table th:nth-child(2) {{ text-align: center; }}
    .totals {{ display: flex; justify-content: flex-end; margin-bottom: 40px; }}
    .totals-table {{ min-width: 280px; }}
    .totals-row {{ display: flex; justify-content: space-between; padding: 6px 0; font-size: 14px; color: #6B7280; }}
    .totals-row.total {{ border-top: 2px solid #111827; margin-top: 8px; padding-top: 12px; font-size: 18px; font-weight: 700; color: #111827; }}
    .notes {{ background: #F9FAFB; border-radius: 8px; padding: 20px; margin-bottom: 20px; }}
    .notes h3 {{ font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #9CA3AF; margin-bottom: 8px; }}
    .notes p {{ font-size: 13px; color: #6B7280; white-space: pre-wrap; }}
    .footer {{ text-align: center; padding-top: 30px; border-top: 1px solid #E5E7EB; font-size: 12px; color: #9CA3AF; }}
</style>
</head>
<body>
<div class="invoice-container">
    <div class="header">
        <div class="header-left">
            {logo_html}
            <div class="invoice-title">INVOICE</div>
            <div class="invoice-number">{invoice.invoice_number}</div>
        </div>
        <div class="header-right">
            <span class="status-badge">{(invoice.status or 'draft').upper()}</span>
            <div style="margin-top:12px; font-size:13px; color:#6B7280;">
                <div>Date: {created_str}</div>
                <div>Due: {due_date_str}</div>
            </div>
        </div>
    </div>

    <div class="details-grid">
        <div class="detail-section">
            <h3>From</h3>
            <p class="name">{invoice.business_name or ''}</p>
            <p>{invoice.business_email or ''}</p>
            <p>{invoice.business_phone or ''}</p>
            <p>{(invoice.business_address or '').replace(chr(10), '<br>')}</p>
        </div>
        <div class="detail-section">
            <h3>Bill To</h3>
            <p class="name">{invoice.client_name or ''}</p>
            <p>{invoice.client_email or ''}</p>
            <p>{invoice.client_phone or ''}</p>
            <p>{(invoice.client_address or '').replace(chr(10), '<br>')}</p>
        </div>
    </div>

    <table class="items-table">
        <thead>
            <tr>
                <th>Description</th>
                <th>Qty</th>
                <th>Rate</th>
                <th style="text-align:right">Amount</th>
            </tr>
        </thead>
        <tbody>
            {items_html}
        </tbody>
    </table>

    <div class="totals">
        <div class="totals-table">
            <div class="totals-row">
                <span>Subtotal</span>
                <span>{currency} {float(invoice.subtotal or 0):,.2f}</span>
            </div>
            <div class="totals-row">
                <span>Tax ({invoice.tax_rate or 0}%)</span>
                <span>{currency} {float(invoice.tax_amount or 0):,.2f}</span>
            </div>
            {"<div class='totals-row'><span>Discount</span><span>-" + currency + " " + f"{float(invoice.discount):,.2f}" + "</span></div>" if invoice.discount else ""}
            <div class="totals-row total">
                <span>Total</span>
                <span>{currency} {float(invoice.total or 0):,.2f}</span>
            </div>
        </div>
    </div>

    {"<div class='notes'><h3>Notes</h3><p>" + (invoice.notes or '') + "</p></div>" if invoice.notes else ""}
    {"<div class='notes'><h3>Terms &amp; Conditions</h3><p>" + (invoice.terms or '') + "</p></div>" if invoice.terms else ""}

    <div class="footer">
        <p>Thank you for your business!</p>
    </div>
</div>
</body>
</html>"""


def _generate_with_weasyprint(invoice):
    """Generate PDF using WeasyPrint (best quality)."""
    from weasyprint import HTML
    html_content = _build_invoice_html(invoice)
    pdf = HTML(string=html_content).write_pdf()
    return pdf


def _generate_with_reportlab(invoice):
    """Generate PDF using ReportLab (simpler but widely available)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch, mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=30*mm, bottomMargin=20*mm,
                           leftMargin=20*mm, rightMargin=20*mm)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle('InvoiceTitle', parent=styles['Heading1'], fontSize=24, spaceAfter=6)
    story.append(Paragraph("INVOICE", title_style))
    story.append(Paragraph(f"<b>{invoice.invoice_number}</b>", styles['Normal']))
    story.append(Spacer(1, 20))

    # From / To
    from_text = f"<b>From:</b> {invoice.business_name or ''}<br/>{invoice.business_email or ''}<br/>{invoice.business_phone or ''}"
    to_text = f"<b>Bill To:</b> {invoice.client_name or ''}<br/>{invoice.client_email or ''}<br/>{invoice.client_phone or ''}"
    info_data = [[Paragraph(from_text, styles['Normal']), Paragraph(to_text, styles['Normal'])]]
    info_table = Table(info_data, colWidths=[doc.width/2]*2)
    story.append(info_table)
    story.append(Spacer(1, 20))

    # Items table
    currency = invoice.currency or "USD"
    table_data = [["Description", "Qty", "Rate", "Amount"]]
    for item in (invoice.items or []):
        desc = item.get("description", "")
        qty = item.get("qty", item.get("quantity", 1))
        rate = item.get("rate", item.get("price", 0))
        amount = item.get("amount", float(qty) * float(rate))
        table_data.append([desc, str(qty), f"{float(rate):,.2f}", f"{float(amount):,.2f}"])

    t = Table(table_data, colWidths=[doc.width*0.45, doc.width*0.15, doc.width*0.2, doc.width*0.2])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))

    # Totals
    totals_data = [
        ["", "", "Subtotal:", f"{currency} {float(invoice.subtotal or 0):,.2f}"],
        ["", "", f"Tax ({invoice.tax_rate or 0}%):", f"{currency} {float(invoice.tax_amount or 0):,.2f}"],
    ]
    if invoice.discount:
        totals_data.append(["", "", "Discount:", f"-{currency} {float(invoice.discount):,.2f}"])
    totals_data.append(["", "", "TOTAL:", f"{currency} {float(invoice.total or 0):,.2f}"])

    tt = Table(totals_data, colWidths=[doc.width*0.25, doc.width*0.25, doc.width*0.25, doc.width*0.25])
    tt.setStyle(TableStyle([
        ('FONTNAME', (-2, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (-2, -1), (-1, -1), 12),
        ('LINEABOVE', (-2, -1), (-1, -1), 1.5, colors.black),
        ('ALIGN', (-2, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(tt)

    # Notes
    if invoice.notes:
        story.append(Spacer(1, 20))
        story.append(Paragraph("<b>Notes:</b>", styles['Normal']))
        story.append(Paragraph(invoice.notes, styles['Normal']))

    if invoice.terms:
        story.append(Spacer(1, 10))
        story.append(Paragraph("<b>Terms:</b>", styles['Normal']))
        story.append(Paragraph(invoice.terms, styles['Normal']))

    story.append(Spacer(1, 30))
    story.append(Paragraph("<i>Thank you for your business!</i>", styles['Normal']))

    doc.build(story)
    return buffer.getvalue()


def _generate_html_fallback(invoice):
    """Fallback: return the invoice as a styled HTML file (pseudo-PDF).
    Most browsers can print this to PDF.
    """
    html = _build_invoice_html(invoice)
    return html.encode("utf-8")
