from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.platform import FreelancerProfile, JobPost, Proposal
from app.utils.feature_flags import require_feature

freelance_bp = Blueprint("freelance", __name__)


@freelance_bp.route("/")
@require_feature("freelancer_mode_enabled")
def index():
    freelancers = FreelancerProfile.query.filter_by(verified=True).order_by(
        FreelancerProfile.featured.desc(), FreelancerProfile.rating.desc()).all()
    jobs = JobPost.query.filter_by(status="open").order_by(JobPost.created_at.desc()).limit(10).all()
    return render_template("hire/index.html", freelancers=freelancers, jobs=jobs)


@freelance_bp.route("/jobs")
@require_feature("freelancer_mode_enabled")
def jobs():
    jobs = JobPost.query.filter_by(status="open").order_by(JobPost.created_at.desc()).all()
    return render_template("hire/jobs.html", jobs=jobs)


@freelance_bp.route("/jobs/<int:job_id>")
@require_feature("freelancer_mode_enabled")
def job_detail(job_id):
    job = JobPost.query.get_or_404(job_id)
    return render_template("hire/job_detail.html", job=job)


@freelance_bp.route("/jobs/post", methods=["GET", "POST"])
@require_feature("freelancer_mode_enabled")
@login_required
def post_job():
    if not (current_user.is_client() or current_user.is_admin()):
        flash("Only clients can post jobs.", "danger")
        return redirect(url_for("freelance.index"))
    if request.method == "POST":
        skills = [s.strip() for s in request.form.get("skills", "").split(",") if s.strip()]
        budget_min = request.form.get("budget_min") or None
        budget_max = request.form.get("budget_max") or None
        job = JobPost(
            client_id=current_user.id,
            title=request.form.get("title", ""),
            description=request.form.get("description", ""),
            category=request.form.get("category", ""),
            skills=skills,
            budget_min=float(budget_min) if budget_min else None,
            budget_max=float(budget_max) if budget_max else None,
            budget_type=request.form.get("budget_type", "fixed"),
            duration=request.form.get("duration", ""),
        )
        db.session.add(job)
        db.session.commit()
        flash("Job posted successfully!", "success")
        return redirect(url_for("freelance.jobs"))
    return render_template("hire/post_job.html")


@freelance_bp.route("/jobs/<int:job_id>/apply", methods=["POST"])
@require_feature("freelancer_mode_enabled")
@login_required
def apply_job(job_id):
    if not current_user.is_freelancer():
        return jsonify({"error": "Only freelancers can apply"}), 403
    job = JobPost.query.get_or_404(job_id)
    existing = Proposal.query.filter_by(job_id=job_id, user_id=current_user.id).first()
    if existing:
        flash("You have already applied to this job.", "warning")
        return redirect(url_for("freelance.job_detail", job_id=job_id))
    bid = request.form.get("bid_amount")
    days = request.form.get("delivery_days")
    proposal = Proposal(
        job_id=job_id,
        user_id=current_user.id,
        cover_letter=request.form.get("cover_letter", ""),
        bid_amount=float(bid) if bid else 0,
        delivery_days=int(days) if days else None,
    )
    db.session.add(proposal)
    db.session.commit()

    from app.utils.automation import trigger as automation_trigger
    automation_trigger("job_application_submitted", {
        "job_title": job.title, "job_id": job.id, "applicant_name": current_user.name,
        "applicant_email": current_user.email, "bid_amount": proposal.bid_amount,
    })

    flash("Proposal submitted successfully!", "success")
    return redirect(url_for("freelance.job_detail", job_id=job_id))


@freelance_bp.route("/profile/setup", methods=["GET", "POST"])
@require_feature("freelancer_mode_enabled")
@login_required
def setup_profile():
    if not (current_user.is_freelancer() or current_user.is_admin()):
        abort(403)
    profile = current_user.freelancer_profile
    if not profile:
        profile = FreelancerProfile(user_id=current_user.id)
        db.session.add(profile)
        db.session.commit()
    if request.method == "POST":
        profile.title = request.form.get("title", "")
        profile.bio = request.form.get("bio", "")
        rate = request.form.get("hourly_rate")
        profile.hourly_rate = float(rate) if rate else None
        profile.availability = request.form.get("availability", "available")
        skills_raw = request.form.get("skills", "")
        profile.skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
        langs_raw = request.form.get("languages", "")
        profile.languages = [l.strip() for l in langs_raw.split(",") if l.strip()]
        profile.location = request.form.get("location", "")
        profile.portfolio_url = request.form.get("portfolio_url", "")
        profile.experience = request.form.get("experience", "intermediate")
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("dashboard.home"))
    return render_template("hire/setup_profile.html", profile=profile)


@freelance_bp.route("/verify", methods=["POST"])
@require_feature("freelancer_mode_enabled")
@login_required
def submit_verification():
    if not current_user.is_freelancer():
        abort(403)
    profile = current_user.freelancer_profile
    if not profile:
        profile = FreelancerProfile(user_id=current_user.id)
        db.session.add(profile)
    profile.verification_submitted = True
    db.session.commit()
    flash("Verification request submitted! Admin will review your profile.", "success")
    return redirect(url_for("dashboard.home"))
