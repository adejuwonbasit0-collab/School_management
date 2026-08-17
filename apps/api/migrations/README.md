# Bazillin Studio v2 — Flask

Full-stack developer ecosystem built with Python/Flask, SQLAlchemy, and Jinja2.

## Features
- 🏠 **Homepage** — Hero, services, projects, testimonials, blog, CTA (all CMS-controlled)
- 📦 **Marketplace** — Browse, search, buy, and download digital products
- 💳 **Payments** — Stripe + Paystack integration
- 📝 **Blog** — Full blog with categories, Markdown rendering, views tracking
- 🤝 **Hire** — Freelancer profiles, job listings, proposals system
- 🖥️ **Hosting** — Hosting plans and subscription management
- 🤖 **AI Tools Hub** — Claude-powered chat, code review, and more
- 🔧 **Dev Tools** — Live code studio, JSON formatter, and more
- 🎛️ **Admin Control Center** — Full-featured admin with 15+ sections

## Admin Control Center Sections
- **Overview** — Live stats, revenue chart, user chart, quick nav, broadcast
- **Users** — Role management, ban/unban, delete, credits
- **Roles** — Create/delete roles with permissions
- **Products** — CRUD, approval, feature toggle, status management
- **Orders** — Full order history with revenue total
- **Blog** — Create/edit/delete posts, publish toggle
- **CMS Blocks** — Control all homepage/site content from admin
- **Portfolio & About** — Projects, services, skills, testimonials, experience, education, certifications
- **Freelancers & Jobs** — Verify/feature freelancers, close jobs
- **Hosting** — Plans management, subscription control
- **Newsletter** — Subscriber list, CSV export
- **Trends** — Pin, hide, approve trend items
- **Analytics** — Signups, revenue, daily charts, top pages
- **Email Templates** — 8 fully editable templates with variable support
- **Settings** — Feature toggles, site identity, payment config, security
- **Media Library** — File upload and management
- **Support Tickets** — View and update support tickets
- **Audit Log** — Full action history
- **System Health** — Live diagnostic checks with health score

## Quick Start

```bash
# 1. Clone / copy project
cd bazillin-studio-flask-v2/bazillin

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL, SECRET_KEY, etc.

# 5. Initialize database
flask --app run:app db init
flask --app run:app db migrate -m "Initial migration"
flask --app run:app db upgrade

# 6. Seed the database (creates admin + sample data)
python -m scripts.seed

# 7. Run development server
python run.py
```

## Default Admin Credentials
- **Email:** admin@bazillin.studio
- **Password:** Admin@12345
- **URL:** http://localhost:5000/admin

## Environment Variables
See `.env.example` for all required variables.

## Project Structure
```
bazillin/
├── app/
│   ├── admin/        # Admin Control Center routes
│   ├── ai_tools/     # AI features (Claude integration)
│   ├── analytics/    # Analytics tracking
│   ├── api/          # REST API endpoints
│   ├── auth/         # Authentication (login, register)
│   ├── cms/          # Main site pages + dashboards
│   ├── comms/        # Messaging
│   ├── extensions/   # Flask extensions init
│   ├── freelance/    # Hire/freelance system
│   ├── hosting/      # Hosting plans & subscriptions
│   ├── marketplace/  # Product marketplace
│   ├── models/       # SQLAlchemy models (30+ models)
│   ├── payments/     # Stripe/Paystack payments
│   ├── portfolio/    # Portfolio routes
│   ├── tools/        # Dev tools
│   └── utils/        # Helpers (settings, email, audit, payments)
├── config/           # App configuration
├── scripts/          # Seed script
├── static/           # CSS, JS, uploads
├── templates/        # Jinja2 templates
│   ├── admin/        # Admin Control Center templates
│   ├── auth/         # Login / register
│   ├── cms/          # Public pages
│   ├── dashboard/    # User/freelancer/client dashboards
│   ├── marketplace/  # Marketplace pages
│   ├── hire/         # Freelance/hire pages
│   ├── hosting/      # Hosting pages
│   ├── ai_tools/     # AI Tools Hub
│   ├── tools/        # Dev tools (code studio etc)
│   └── errors/       # Error pages (403, 404, 500)
├── prisma/           # (legacy schema reference)
├── .env.example
├── requirements.txt
├── run.py
└── wsgi.py
```


git add .
git commit -m "add"
git push origin main