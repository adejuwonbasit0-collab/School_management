import io
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT


def generate_invoice_pdf(invoice, site_name="Bazillin Studio"):
    """Renders a clean, simple invoice PDF for a project Invoice record.
    Returns a BytesIO ready to be sent as a file response."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch,
                             leftMargin=0.75 * inch, rightMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("InvoiceTitle", parent=styles["Heading1"], fontSize=22, spaceAfter=4)
    label_style = ParagraphStyle("Label", parent=styles["Normal"], textColor=colors.HexColor("#666666"), fontSize=9)
    right_style = ParagraphStyle("Right", parent=styles["Normal"], alignment=TA_RIGHT)

    elements = []
    elements.append(Paragraph(site_name, title_style))
    elements.append(Paragraph(f"Invoice #{invoice.id}", label_style))
    elements.append(Spacer(1, 0.3 * inch))

    status_color = {"paid": "#1DB954", "unpaid": "#F2C94C", "cancelled": "#888888"}.get(invoice.status, "#888888")
    meta_table = Table([
        [Paragraph("Bill To", label_style), Paragraph("Status", label_style)],
        [Paragraph(invoice.project.client.name or invoice.project.client.email, styles["Normal"]),
         Paragraph(f'<font color="{status_color}"><b>{invoice.status.upper()}</b></font>', styles["Normal"])],
        [Paragraph("Project", label_style), Paragraph("Date Issued", label_style)],
        [Paragraph(invoice.project.title, styles["Normal"]),
         Paragraph(invoice.created_at.strftime("%B %d, %Y"), styles["Normal"])],
    ], colWidths=[3.5 * inch, 3.5 * inch])
    meta_table.setStyle(TableStyle([("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    elements.append(meta_table)
    elements.append(Spacer(1, 0.4 * inch))

    from app.utils.currency import format_amount
    amount_str = format_amount(float(invoice.amount), invoice.currency)
    line_items = [["Description", "Amount"], [invoice.title, amount_str]]
    if invoice.description:
        line_items.insert(1, [invoice.description, ""])
    line_items.append(["", f"Total: {amount_str}"])

    items_table = Table(line_items, colWidths=[5.0 * inch, 2.0 * inch])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#111111")),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#111111")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(items_table)

    if invoice.due_date:
        elements.append(Spacer(1, 0.3 * inch))
        elements.append(Paragraph(f"Due date: {invoice.due_date.strftime('%B %d, %Y')}", label_style))
    if invoice.paid_at:
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(f"Paid on {invoice.paid_at.strftime('%B %d, %Y')} via {invoice.gateway or 'unknown method'}", label_style))

    doc.build(elements)
    buf.seek(0)
    return buf
