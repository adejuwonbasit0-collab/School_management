from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db, limiter
from app.models.user import User, Role
from app.utils.audit import log_action

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(_dashboard_url())
    if request.args.get("timeout"):
        flash("You were signed out after 10 minutes of inactivity.", "info")
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if user.is_banned:
                flash("Your account has been suspended.", "danger")
                return redirect(url_for("auth.login"))
            # Stash `next` in the session (not just the URL) before the 2FA
            # detour — verify_2fa is a separate page load with no query
            # string of its own to carry it, so without this the 2FA path
            # always fell back to the dashboard even when the direct-login
            # path above was fixed to honor next correctly.
            pending_next = request.form.get("next") or request.args.get("next")
            if user.totp_enabled:
                # Don't log in yet — stash a pending login and require the
                # 2FA code first. Nothing in `session` here grants access
                # on its own; login_user() is only called after verify.
                session["pending_2fa_user_id"] = user.id
                session["pending_2fa_remember"] = remember
                session["pending_2fa_next"] = pending_next
                return redirect(url_for("auth.verify_2fa"))
            if user.email_2fa_enabled:
                _send_email_otp(user)
                session["pending_2fa_user_id"] = user.id
                session["pending_2fa_remember"] = remember
                session["pending_2fa_next"] = pending_next
                return redirect(url_for("auth.verify_2fa"))
            _complete_login(user, remember)
            # `next` has to be read from the POSTed form field, not just
            # request.args — the login form's action URL doesn't carry the
            # query string forward on submit, so request.args.get("next")
            # was always empty here and every login silently fell back to
            # the dashboard regardless of where the person actually came
            # from. The template now also renders it as a hidden field.
            next_url = request.form.get("next") or request.args.get("next") or _dashboard_url()
            return redirect(next_url)
        # Log the failed attempt (whether the email exists or not) so the
        # Security Center can actually show failed-login activity instead
        # of having nothing to show — previously only successful logins
        # were ever logged.
        log_action(user.id if user else None, "auth.login_failed", f"email={email}")
        flash("Invalid email or password.", "danger")
    return render_template("auth/login.html")


def _complete_login(user, remember):
    """Shared by normal login and the post-2FA login — finalizes the
    session, records the login, and alerts on a new IP address."""
    import datetime
    from app.utils.email import send_email
    from app.utils.settings import get_setting

    ip = request.remote_addr or "unknown"
    known_ips = user.known_ips or []
    is_new_ip = ip not in known_ips and ip != "unknown"

    login_user(user, remember=remember)
    user.last_login_at = datetime.datetime.utcnow()
    user.last_login_ip = ip
    if is_new_ip:
        known_ips.append(ip)
        user.known_ips = known_ips[-20:]  # cap history, oldest dropped first
    db.session.commit()
    log_action(user.id, "auth.login", f"User#{user.id}")

    if is_new_ip and user.is_admin() and known_ips[:-1]:
        # Only alert for logins after the very first one on record — the
        # first login ever isn't "a new IP", it's just... the first login.
        admin_email = get_setting("admin_notification_email") or user.email
        send_email(
            to=admin_email,
            subject="New login to your admin account from an unrecognized device",
            body_html=f"""<p>Your admin account just logged in from a new IP address:</p>
                <p><strong>IP:</strong> {ip}<br>
                <strong>Time:</strong> {user.last_login_at.strftime('%Y-%m-%d %H:%M UTC')}</p>
                <p>If this wasn't you, change your password immediately and enable
                two-factor authentication in Admin → Security if you haven't already.</p>
                <p style="font-size:12px;color:#888">Note: this is an email alert only — SMS
                alerts would require a paid SMS API (like Twilio) that isn't configured.</p>""",
        )


def _send_email_otp(user):
    """Generates a 6-digit one-time code, stores it (hashed reference is
    unnecessary here — it's single-use and expires in 10 minutes, held only
    in the signed server-side session, never in a client-readable cookie
    value) and emails it. Real alternative to an authenticator app for
    people who don't want to install one."""
    import random
    import datetime
    from app.utils.email import send_email
    code = f"{random.randint(0, 999999):06d}"
    session["pending_email_otp_code"] = code
    session["pending_email_otp_expires"] = (datetime.datetime.utcnow() + datetime.timedelta(minutes=10)).isoformat()
    send_email(
        to=user.email,
        subject="Your login verification code",
        body_html=f"""<p>Your one-time login code is:</p>
            <p style="font-size:28px;font-weight:700;letter-spacing:0.1em">{code}</p>
            <p style="font-size:12px;color:#888">Expires in 10 minutes. If you didn't try to log in, you can ignore this.</p>""",
    )


@auth_bp.route("/verify-2fa", methods=["GET", "POST"])
def verify_2fa():
    import datetime
    from app.utils.security import verify_totp_code
    uid = session.get("pending_2fa_user_id")
    if not uid:
        return redirect(url_for("auth.login"))
    user = User.query.get(uid)
    if not user:
        session.pop("pending_2fa_user_id", None)
        return redirect(url_for("auth.login"))

    using_email_otp = bool(user.email_2fa_enabled and not user.totp_enabled)

    if request.method == "POST":
        if using_email_otp and request.form.get("resend"):
            _send_email_otp(user)
            flash("A new code has been sent to your email.", "info")
            return render_template("auth/verify_2fa.html", using_email_otp=using_email_otp)

        code = request.form.get("code", "")
        valid = False
        if using_email_otp:
            expires_raw = session.get("pending_email_otp_expires")
            expired = not expires_raw or datetime.datetime.utcnow() > datetime.datetime.fromisoformat(expires_raw)
            if not expired and code and code == session.get("pending_email_otp_code"):
                valid = True
        else:
            valid = verify_totp_code(user.totp_secret, code)

        if valid:
            remember = session.pop("pending_2fa_remember", False)
            session.pop("pending_2fa_user_id", None)
            session.pop("pending_email_otp_code", None)
            session.pop("pending_email_otp_expires", None)
            next_url = session.pop("pending_2fa_next", None)
            _complete_login(user, remember)
            return redirect(next_url or _dashboard_url())
        flash("Incorrect or expired code. Try again.", "danger")
    return render_template("auth/verify_2fa.html", using_email_otp=using_email_otp)


@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def register():
    if current_user.is_authenticated:
        return redirect(_dashboard_url())
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")
        role_name = request.form.get("role", "user")

        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("auth/register.html")
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template("auth/register.html")
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html")
        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "danger")
            return render_template("auth/register.html")

        # Check feature flags
        from app.utils.settings import get_setting
        if role_name == "freelancer" and not get_setting("freelancer_mode_enabled", True):
            flash("Freelancer registration is currently disabled.", "danger")
            return render_template("auth/register.html")
        if role_name == "client" and not get_setting("client_mode_enabled", True):
            flash("Client registration is currently disabled.", "danger")
            return render_template("auth/register.html")

        role = Role.query.filter_by(name=role_name).first() or Role.query.filter_by(name="user").first()
        user = User(name=name or email.split("@")[0], email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        from app.utils.analytics import log_event
        log_event("signup", path="/register", metadata={"role": role_name})

        # Create sub-profiles
        if role_name == "freelancer":
            from app.models.platform import FreelancerProfile
            db.session.add(FreelancerProfile(user_id=user.id))
            db.session.commit()
        if role_name == "client":
            from app.models.platform import ClientProfile
            db.session.add(ClientProfile(user_id=user.id))
            db.session.commit()

        log_action(user.id, "auth.register", f"User#{user.id}")

        # Neither of these existed before — register() had zero email logic
        # at all, so a brand-new signup produced no confirmation to the
        # user and no notification to the admin, ever.
        from app.utils.email import send_email
        send_email(
            to=user.email,
            subject=f"Welcome to {get_setting('site_name', 'Bazillin Studio')}!",
            body_html=f"""<p>Hi {user.name or 'there'},</p>
                <p>Your account is ready — you're signed up as a <strong>{role_name}</strong>.</p>
                <p>You can log in anytime and pick up right where you left off.</p>""",
        )
        admin_email = get_setting("admin_notification_email") or get_setting("admin_email") or get_setting("contact_email")
        if admin_email:
            send_email(
                to=admin_email,
                subject=f"👤 New {role_name} signup — {user.name or user.email}",
                body_html=f"<p><strong>{user.name or user.email}</strong> ({user.email}) just registered as a <strong>{role_name}</strong>.</p>",
            )

        login_user(user)
        flash(f"Welcome to Bazillin Studio, {user.name}!", "success")
        return redirect(_dashboard_url())
    return render_template("auth/register.html")


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def forgot_password():
    """Real self-service reset — the login page's 'Forgot password?' link
    used to point at '#' with nothing behind it. Reuses the same signed
    itsdangerous token and /set-password/<token> route already used for
    invite links, so no new "set new password" page was needed — just the
    missing "request a reset link" step in front of it."""
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        # Always show the same success message whether or not the email
        # exists, so this can't be used to find out who has an account.
        generic_msg = "If an account exists for that email, a reset link is on its way."
        if email:
            user = User.query.filter(db.func.lower(User.email) == email).first()
            if user:
                from itsdangerous import URLSafeTimedSerializer
                from flask import current_app
                from app.utils.email import send_email
                serializer = URLSafeTimedSerializer(current_app.secret_key)
                token = serializer.dumps({"user_id": user.id})
                reset_url = url_for("auth.set_password", token=token, _external=True)
                try:
                    send_email(
                        to=user.email,
                        subject="Reset your password",
                        body_html=f"""<p>Someone (hopefully you) requested a password reset.</p>
                            <p><a href="{reset_url}" style="font-weight:700">Click here to set a new password</a></p>
                            <p style="font-size:12px;color:#888">This link expires in 3 days. If you didn't request this, you can ignore this email — your password won't change.</p>""",
                    )
                except Exception:
                    from flask import current_app as _app
                    _app.logger.exception("Failed to send password reset email to %s", user.email)
                log_action(user.id, "auth.forgot_password_requested")
        flash(generic_msg, "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html")


@auth_bp.route("/set-password/<token>", methods=["GET", "POST"])
def set_password(token):
    """Used by the link sent when an account gets auto-created for someone
    submitting Hire Me while logged out — lets them set their own password
    instead of us ever emailing one. Expires after 3 days."""
    from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
    from flask import current_app
    serializer = URLSafeTimedSerializer(current_app.secret_key)
    try:
        data = serializer.loads(token, max_age=60 * 60 * 24 * 3)
    except SignatureExpired:
        flash("That link has expired — use 'Forgot password' on the login page instead.", "warning")
        return redirect(url_for("auth.login"))
    except BadSignature:
        return redirect(url_for("auth.login"))

    user = User.query.get(data.get("user_id"))
    if not user:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return render_template("auth/set_password.html", token=token)
        if password != confirm:
            flash("Passwords don't match.", "danger")
            return render_template("auth/set_password.html", token=token)
        user.set_password(password)
        user.email_verified = True
        db.session.commit()
        login_user(user)
        flash("Password set — you're logged in.", "success")
        return redirect(_dashboard_url())

    return render_template("auth/set_password.html", token=token)


@auth_bp.route("/logout")
@login_required
def logout():
    log_action(current_user.id, "auth.logout")
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("cms.home"))


def _dashboard_url():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return url_for("admin.dashboard")
        if current_user.is_freelancer():
            return url_for("dashboard.home")
        if current_user.is_client():
            return url_for("dashboard.home")
    return url_for("dashboard.home")


@auth_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    from flask import jsonify
    import bcrypt as _bcrypt
    data = request.get_json(silent=True) or {}
    cur = data.get("current_password", "")
    new = data.get("new_password", "")
    if not cur or not new or len(new) < 8:
        return jsonify({"error": "Invalid input — new password must be at least 8 chars"}), 400
    if not current_user.check_password(cur):
        return jsonify({"error": "Current password is incorrect"}), 400
    current_user.set_password(new)
    db.session.commit()
    log_action(current_user.id, "auth.password_change")
    return jsonify({"message": "Password updated successfully"})
