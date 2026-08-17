import os
import secrets
from flask import current_app, abort, send_file
from flask_login import current_user
from app.extensions import db
from app.models.commerce import Order, Product, Download

def get_download_url(order_id):
    order = Order.query.get(order_id)
    if not order or order.status != "paid":
        abort(403)
    if order.user_id != current_user.id:
        abort(403)
    product = order.product
    if not product or not product.file_url:
        abort(404)
    dl = Download(user_id=current_user.id, order_id=order_id, file_url=product.file_url)
    db.session.add(dl)
    product.download_count += 1
    db.session.commit()
    return product.file_url
