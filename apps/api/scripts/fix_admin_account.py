"""
Recovers YOUR OWN admin account after being locked out (e.g. accidentally
changing your own role to "user"), and/or resets your login email/password.

USAGE — edit the three variables below, then run:
    python -m scripts.fix_admin_account
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

# ── Edit these ──────────────────────────────────────────────
CURRENT_EMAIL = "admin@bazillin.studio"      # the email you log in with right now
NEW_EMAIL     = "adejuwonbasit0@gmail.com"                        # set to "adejuwonbasit0@gmail.com" if you want to change, or None to keep current
NEW_PASSWORD  = "baskid555"                  # your new password (or None to keep current)
# ────────────────────────────────────────────────────────────

from app import create_app
from app.extensions import db
from app.models.user import User, Role

app = create_app("development")

with app.app_context():
    user = User.query.filter_by(email=CURRENT_EMAIL).first()
    if not user:
        print(f"No user found with email '{CURRENT_EMAIL}'. "
              f"Edit CURRENT_EMAIL in this script to match your actual login email, then run again.")
        sys.exit(1)

    admin_role = Role.query.filter_by(name="admin").first()
    if not admin_role:
        admin_role = Role(name="admin", description="Full access", permissions=["all"], is_system=True)
        db.session.add(admin_role)
        db.session.flush()

    user.role_id = admin_role.id

    if NEW_EMAIL:
        existing = User.query.filter_by(email=NEW_EMAIL).first()
        if existing and existing.id != user.id:
            print(f"Another account already uses '{NEW_EMAIL}' — pick a different email or delete that account first.")
            sys.exit(1)
        user.email = NEW_EMAIL

    if NEW_PASSWORD:
        if len(NEW_PASSWORD) < 8:
            print("NEW_PASSWORD is shorter than 8 characters — choose a longer one for real security, then run again.")
            sys.exit(1)
        user.set_password(NEW_PASSWORD)

    db.session.commit()
    print(f"Done. Account '{user.email}' is now role=admin.")
    if NEW_EMAIL or NEW_PASSWORD:
        print("Login email/password updated as requested.")