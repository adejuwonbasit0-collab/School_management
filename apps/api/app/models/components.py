from datetime import datetime
from app.extensions import db

class UIComponent(db.Model):
    __tablename__ = "ui_components"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    category = db.Column(db.String(64), nullable=False)
    description = db.Column(db.Text)
    preview_image = db.Column(db.String(512))
    html_code = db.Column(db.Text, nullable=False)
    css_code = db.Column(db.Text)
    js_code = db.Column(db.Text)
    tags = db.Column(db.JSON, default=list)
    featured = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'preview_image': self.preview_image,
            'html_code': self.html_code,
            'css_code': self.css_code or '',
            'js_code': self.js_code or '',
            'tags': self.tags or [],
            'featured': self.featured,
            'active': self.active,
            'order': self.order,
        }