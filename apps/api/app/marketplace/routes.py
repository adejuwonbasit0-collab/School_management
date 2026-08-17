from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_required, current_user
from app.models.commerce import Product, Order, WishlistItem, Download, ProductReview
from app.extensions import db
from app.utils.feature_flags import require_feature
from datetime import datetime

marketplace_bp = Blueprint("marketplace", __name__)


@marketplace_bp.route("/")
@require_feature("marketplace_enabled")
def index():
    category = request.args.get("category", "")
    q = request.args.get("q", "")
    sort = request.args.get("sort", "newest")
    page = request.args.get("page", 1, type=int)
    query = Product.query.filter_by(status="active")
    if category:
        query = query.filter_by(category=category)
    if q:
        query = query.filter(Product.title.ilike(f"%{q}%"))
    if sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort == "popular":
        query = query.order_by(Product.download_count.desc())
    else:
        query = query.order_by(Product.featured.desc(), Product.created_at.desc())
    products = query.paginate(page=page, per_page=12, error_out=False)
    categories = [c[0] for c in db.session.query(Product.category).distinct().all() if c[0]]
    return render_template("marketplace/index.html",
        products=products, categories=categories,
        current_cat=category, current_sort=sort)


@marketplace_bp.route("/<slug>")
@require_feature("marketplace_enabled")
def product_detail(slug):
    product = Product.query.filter_by(slug=slug, status="active").first_or_404()
    product.view_count = (product.view_count or 0) + 1
    db.session.commit()
    owned = False
    wishlisted = False
    my_review = None
    dashboard_url = None
    if product.type == "premium_tool":
        from app.dashboard.premium import PREMIUM_PRODUCTS
        info = PREMIUM_PRODUCTS.get(product.slug)
        if info and info.get("endpoint"):
            # The dashboard tool's actual route rarely matches the
            # marketplace slug 1:1 (e.g. "payment-link-generator" the
            # product vs "/dashboard/payment-links" the real route) — a
            # hardcoded `/dashboard/<slug>` link in the template used to
            # guess wrong and 404 for 2 of these. Resolving through the
            # real endpoint here means it can never drift out of sync
            # with the actual registered route again.
            dashboard_url = url_for(info["endpoint"])
    if current_user.is_authenticated:
        if product.type == "premium_tool":
            from app.dashboard.premium import has_product_access
            owned = current_user.is_admin() or has_product_access(current_user, product.slug)
        else:
            owned = Order.query.filter_by(
                user_id=current_user.id, product_id=product.id, status="paid"
            ).first() is not None
        wishlisted = WishlistItem.query.filter_by(
            user_id=current_user.id, product_id=product.id
        ).first() is not None
        my_review = ProductReview.query.filter_by(
            user_id=current_user.id, product_id=product.id
        ).first()
    reviews = (ProductReview.query.filter_by(product_id=product.id, approved=True)
               .order_by(ProductReview.created_at.desc()).all())
    related = Product.query.filter_by(category=product.category, status="active")\
        .filter(Product.id != product.id).limit(4).all()
    return render_template("marketplace/product.html",
        product=product, owned=owned, wishlisted=wishlisted, related=related, dashboard_url=dashboard_url,
        reviews=reviews, my_review=my_review,
        page_seo_title=product.seo_title or product.title,
        page_seo_desc=product.seo_desc or product.description,
        page_og_image=(product.images[0] if product.images else None))


@marketplace_bp.route("/<int:product_id>/wishlist", methods=["POST"])
@require_feature("marketplace_enabled")
@login_required
def toggle_wishlist(product_id):
    existing = WishlistItem.query.filter_by(
        user_id=current_user.id, product_id=product_id
    ).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({"wishlisted": False})
    db.session.add(WishlistItem(user_id=current_user.id, product_id=product_id))
    db.session.commit()
    return jsonify({"wishlisted": True})


@marketplace_bp.route("/<int:product_id>/download")
@require_feature("marketplace_enabled")
@login_required
def download(product_id):
    """Server-side ownership/free gate. This is the ONLY sanctioned path to a
    product's file — direct file_url is never exposed unauthenticated."""
    product = Product.query.get_or_404(product_id)
    order = Order.query.filter_by(user_id=current_user.id, product_id=product_id, status="paid").first()
    if not order and product.is_free:
        # auto-grant a $0 order so it shows in purchase history / dashboard
        order = Order(user_id=current_user.id, product_id=product_id,
                      amount=0, currency="USD", status="paid", gateway="free")
        db.session.add(order)
        db.session.commit()
    if not order:
        flash("You need to purchase this product before downloading.", "danger")
        return redirect(url_for("payments.checkout", product_id=product_id))
    if not product.file_url:
        flash("No file is currently attached to this product. Please contact support.", "danger")
        return redirect(url_for("marketplace.product_detail", slug=product.slug))

    dl = Download(user_id=current_user.id, order_id=order.id,
                   file_url=product.file_url, ip_address=request.remote_addr)
    db.session.add(dl)
    product.download_count = (product.download_count or 0) + 1
    db.session.commit()
    return redirect(product.file_url)


@marketplace_bp.route("/<int:product_id>/review", methods=["POST"])
@require_feature("marketplace_enabled")
@login_required
def submit_review(product_id):
    product = Product.query.get_or_404(product_id)
    owned = Order.query.filter_by(user_id=current_user.id, product_id=product_id, status="paid").first()
    if not owned and not product.is_free:
        flash("You can only review products you own.", "danger")
        return redirect(url_for("marketplace.product_detail", slug=product.slug))
    rating = request.form.get("rating", type=int)
    if not rating or rating < 1 or rating > 5:
        flash("Please select a rating between 1 and 5.", "danger")
        return redirect(url_for("marketplace.product_detail", slug=product.slug))
    review = ProductReview.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if review:
        review.rating = rating
        review.title = request.form.get("title", "")
        review.body = request.form.get("body", "")
        review.created_at = datetime.utcnow()
    else:
        review = ProductReview(product_id=product_id, user_id=current_user.id, rating=rating,
                               title=request.form.get("title", ""), body=request.form.get("body", ""))
        db.session.add(review)
    db.session.commit()
    _recalculate_rating(product)
    flash("Review submitted. Thanks for the feedback!", "success")
    return redirect(url_for("marketplace.product_detail", slug=product.slug))


def _recalculate_rating(product: Product):
    reviews = ProductReview.query.filter_by(product_id=product.id, approved=True).all()
    if reviews:
        product.rating = round(sum(r.rating for r in reviews) / len(reviews), 2)
        product.review_count = len(reviews)
    else:
        product.rating = 0.0
        product.review_count = 0
    db.session.commit()
