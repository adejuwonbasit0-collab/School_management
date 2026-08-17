from flask import Blueprint, jsonify, request
from flask_login import current_user
from app.models import Product, BlogPost, Project, Service, Testimonial
from app.models.components import UIComponent   # <-- ADDED UIComponent
from app.extensions import csrf

api_bp = Blueprint("api", __name__)

@api_bp.route("/products")
def products():
    items = Product.query.filter_by(status="active").order_by(Product.created_at.desc()).all()
    return jsonify([{"id": p.id, "title": p.title, "slug": p.slug, "price": float(p.effective_price or 0), "category": p.category, "featured": p.featured} for p in items])

@api_bp.route("/blog")
def blog():
    posts = BlogPost.query.filter_by(published=True).order_by(BlogPost.created_at.desc()).limit(20).all()
    return jsonify([{"id": p.id, "title": p.title, "slug": p.slug, "category": p.category, "excerpt": p.excerpt} for p in posts])

@api_bp.route("/projects")
def projects():
    items = Project.query.order_by(Project.featured.desc(), Project.order).all()
    return jsonify([{"id": p.id, "title": p.title, "description": p.description, "image_url": p.image_url, "live_url": p.live_url, "tags": p.tags or [], "featured": p.featured} for p in items])

@api_bp.route("/services")
def services():
    items = Service.query.filter_by(active=True).order_by(Service.order).all()
    return jsonify([{"id": s.id, "title": s.title, "description": s.description, "icon": s.icon, "price": s.price, "features": s.features or []} for s in items])

@api_bp.route("/testimonials")
def testimonials():
    items = Testimonial.query.filter_by(approved=True, featured=True).order_by(Testimonial.order).all()
    return jsonify([{"id": t.id, "name": t.name, "role": t.role, "company": t.company, "content": t.content, "rating": t.rating, "avatar": t.avatar} for t in items])

@api_bp.route("/health")
def health():
    return jsonify({"status": "ok", "version": "2.0.0"})

# ── UI Component API ──────────────────────────────────────────────────
@api_bp.route('/component/<int:id>', methods=['GET'])
def get_component(id):
    comp = UIComponent.query.get_or_404(id)
    return jsonify(comp.to_dict())

@api_bp.route('/component/<int:id>/code', methods=['GET'])
def get_component_code(id):
    comp = UIComponent.query.get_or_404(id)
    code_type = request.args.get('type', 'html')
    if code_type == 'html':
        code = comp.html_code
    elif code_type == 'css':
        code = comp.css_code or ''
    else:
        code = comp.js_code or ''
    return jsonify({'code': code})


# ── Website Automation: Popups ──────────────────────────────────────────────
@api_bp.route('/popups/active')
def popups_active():
    """Which popups are eligible to show on this path. Frequency (once per
    session/visitor) is enforced client-side via localStorage in
    partials/popup_loader.html — this endpoint just filters by page match,
    the browser decides whether THIS visitor has already seen it."""
    from app.models.core import SitePopup
    path = request.args.get('path', '/')
    popups = SitePopup.query.filter_by(active=True).all()
    matching = [p for p in popups if not p.path_pattern or path.startswith(p.path_pattern)]
    return jsonify([{
        'id': p.id, 'headline': p.headline, 'body_html': p.body_html or '',
        'cta_text': p.cta_text or '', 'cta_url': p.cta_url or '',
        'trigger_type': p.trigger_type, 'trigger_value': p.trigger_value,
        'frequency': p.frequency,
    } for p in matching])


@api_bp.route('/popups/<int:popup_id>/event', methods=['POST'])
@csrf.exempt
def popup_event(popup_id):
    from app.extensions import db
    from app.models.core import SitePopup
    popup = SitePopup.query.get_or_404(popup_id)
    kind = (request.get_json(silent=True) or {}).get('type')
    if kind == 'impression':
        popup.impressions = (popup.impressions or 0) + 1
    elif kind == 'click':
        popup.clicks = (popup.clicks or 0) + 1
    else:
        return jsonify({'error': 'unknown event type'}), 400
    db.session.commit()
    return jsonify({'ok': True})