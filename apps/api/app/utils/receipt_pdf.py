import io
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT


def _qr_image(verify_url, size=1.3 * inch):
    """Returns a reportlab Image of a QR code pointing to the verify URL,
    or None if the qrcode library isn't available for some reason — the
    receipt should still render without it rather than fail outright."""
    try:
        import qrcode
        qr = qrcode.QRCode(border=1, box_size=6)
        qr.add_data(verify_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return Image(buf, width=size, height=size)
    except Exception:
        return None


def generate_receipt_pdf(receipt, verify_url, site_name="Bazillin Studio"):
    """Renders a receipt PDF for a paid Invoice's Receipt record. Includes
    a QR code linking to `verify_url` (a public page confirming the
    reference number, amount, and paid date — no other account details)."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch,
                             leftMargin=0.75 * inch, rightMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ReceiptTitle", parent=styles["Heading1"], fontSize=22, spaceAfter=4)
    label_style = ParagraphStyle("Label", parent=styles["Normal"], textColor=colors.HexColor("#666666"), fontSize=9)

    invoice = receipt.invoice
    elements = []
    elements.append(Paragraph(site_name, title_style))
    elements.append(Paragraph(f"Receipt #{receipt.reference}", label_style))
    elements.append(Spacer(1, 0.3 * inch))

    from app.utils.currency import format_amount
    amount_str = format_amount(float(receipt.amount), receipt.currency)

    meta_rows = [
        [Paragraph("Paid By", label_style), Paragraph("Amount Paid", label_style)],
        [Paragraph(invoice.project.client.name or invoice.project.client.email, styles["Normal"]),
         Paragraph(f"<b>{amount_str}</b>", styles["Normal"])],
        [Paragraph("For", label_style), Paragraph("Payment Method", label_style)],
        [Paragraph(invoice.title, styles["Normal"]),
         Paragraph((receipt.payment_method or "unspecified").replace("_", " ").title(), styles["Normal"])],
        [Paragraph("Project", label_style), Paragraph("Date Paid", label_style)],
        [Paragraph(invoice.project.title, styles["Normal"]),
         Paragraph(receipt.paid_at.strftime("%B %d, %Y %H:%M UTC"), styles["Normal"])],
    ]
    meta_table = Table(meta_rows, colWidths=[3.5 * inch, 3.5 * inch])
    meta_table.setStyle(TableStyle([("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    elements.append(meta_table)
    elements.append(Spacer(1, 0.4 * inch))

    qr = _qr_image(verify_url)
    footer_cells = [Paragraph(
        f'This receipt can be verified at:<br/><font color="#0066cc">{verify_url}</font>', label_style
    )]
    if qr:
        footer_table = Table([[footer_cells[0], qr]], colWidths=[5.0 * inch, 1.5 * inch])
        footer_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        elements.append(footer_table)
    else:
        elements.append(footer_cells[0])

    doc.build(elements)
    buf.seek(0)
    return buf
