from flask import Blueprint, render_template
from app.models.content import (
    Project, Service, Testimonial, Profile, Skill,
    Experience, Education, Certification, Award,
)

portfolio_bp = Blueprint("portfolio", __name__)

@portfolio_bp.route("/")
def index():
    profile        = Profile.query.first()
    skills         = Skill.query.order_by(Skill.order).all()
    experiences    = Experience.query.order_by(Experience.order).all()
    educations     = Education.query.order_by(Education.order).all()
    certifications = Certification.query.order_by(Certification.order).all()
    awards         = Award.query.all()
    projects       = Project.query.order_by(Project.featured.desc(), Project.order).all()
    services       = Service.query.filter_by(active=True).order_by(Service.order).all()
    testimonials   = Testimonial.query.filter_by(approved=True, featured=True).order_by(Testimonial.order).all()
    return render_template("cms/about.html",
        profile=profile, skills=skills, experiences=experiences,
        educations=educations, certifications=certifications, awards=awards,
        projects=projects, services=services, testimonials=testimonials)
