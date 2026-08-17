import base64
import io


def generate_qr_data_uri(data, box_size=8, border=2):
    """Returns a data: URI (base64 PNG) for the given string, or None if
    the qrcode library isn't available for some reason — callers should
    handle that by just not showing the QR image rather than erroring."""
    if not data:
        return None
    try:
        import qrcode
        qr = qrcode.QRCode(border=border, box_size=box_size)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except Exception:
        return None
