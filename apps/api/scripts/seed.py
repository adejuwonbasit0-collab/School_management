"""
Run with: python -m scripts.seed
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()
from app import create_app
from app.extensions import db
from app.models.user import User, Role
from app.models.core import SiteSetting, EmailTemplate, CmsBlock
from app.models.content import Service, Testimonial, Project
from app.models.commerce import HostingPlan
from app.models.platform import FAQItem

app = create_app("development")

DEFAULT_SETTINGS = [
    ("site_name",           "Bazillin Studio",        "string",  "general"),
    ("site_tagline",        "Build. Ship. Scale.",     "string",  "general"),
    ("contact_email",       "hello@bazillin.studio",  "string",  "general"),
    ("google_analytics_id","",                        "string",  "general"),
    ("dark_mode",           "true",                   "bool",    "general"),
    ("maintenance_mode",    "false",                  "bool",    "features"),
    ("marketplace_enabled", "false",                  "bool",    "features"),
    ("blog_enabled",        "true",                   "bool",    "features"),
    ("freelancer_mode_enabled","false",                "bool",    "features"),
    ("client_mode_enabled", "true",                   "bool",    "features"),
    ("hosting_portal_enabled","false",                 "bool",    "features"),
    ("hosting_base_domain",  "bazillinapps.com",       "string",  "hosting"),
    ("hosting_server_ip",    "203.0.113.10",           "string",  "hosting"),
    ("ai_tools_enabled",    "true",                   "bool",    "features"),
    ("require_email_verify","false",                  "bool",    "features"),
    ("rate_limiting",       "true",                   "bool",    "security"),
    ("bot_protection",      "false",                  "bool",    "security"),
    ("enable_2fa",          "false",                  "bool",    "security"),
    ("active_gateway",      "stripe",                 "string",  "payments"),
    ("platform_fee_pct",    "10",                     "int",     "payments"),
    ("min_payout_amount",   "50",                     "int",     "payments"),
    ("payout_schedule",     "weekly",                 "string",  "payments"),
    ("currency",            "USD",                    "string",  "payments"),
    ("twitter_url",         "",                       "string",  "social"),
    ("github_url",          "",                       "string",  "social"),
    ("linkedin_url",        "",                       "string",  "social"),
    ("instagram_url",       "",                       "string",  "social"),
    ("youtube_url",         "",                       "string",  "social"),
    ("discord_url",         "",                       "string",  "social"),
    ("seo_site_image",      "",                       "string",  "SEO"),
    ("email_header_image",  "",                       "string",  "general"),
]

EMAIL_TEMPLATES = [
    ("welcome", "Welcome to {{site_name}}!",
     """Hi {{name}},

Welcome to {{site_name}}! Your account has been created successfully.

Login at: {{site_url}}/auth/login

Best,
The {{site_name}} Team"""),

    ("purchase", "Purchase Confirmed — {{product_name}}",
     """Hi {{name}},

Thank you for your purchase of {{product_name}} (Order #{{order_id}}).

Download your file at: {{download_url}}

Best,
{{site_name}}"""),

    ("password_reset", "Reset Your Password",
     """Hi {{name}},

Click the link below to reset your password:

{{reset_url}}

This link expires in 1 hour.

{{site_name}}"""),

    ("email_verify", "Verify Your Email Address",
     """Hi {{name}},

Please verify your email address:

{{verify_url}}

{{site_name}}"""),

    ("freelancer_approved", "Your Freelancer Profile is Approved!",
     """Hi {{name}},

Congratulations! Your freelancer profile has been verified on {{site_name}}.

You can now apply for jobs and start earning.

{{site_name}}"""),

    ("job_application", "New Proposal on Your Job",
     """Hi {{name}},

A freelancer has submitted a proposal on your job posting.

View it at: {{site_url}}/hire/jobs/{{job_id}}

{{site_name}}"""),

    ("newsletter", "{{site_name}} Newsletter",
     """Hi {{name}},

{{content}}

Unsubscribe: {{unsubscribe_url}}

{{site_name}}"""),

    ("download_ready", "Your Download is Ready",
     """Hi {{name}},

Your download for {{product_name}} is ready:

{{download_url}}

{{site_name}}"""),
]

CMS_BLOCKS = [
    ("hero", "section", {
        "badge": "Open for work",
        "headline": "Building Digital Experiences That Matter",
        "subheadline": "Full-stack developer & designer crafting pixel-perfect products with modern tech.",
        "primary_cta_text": "View My Work",
        "primary_cta_url": "/portfolio",
        "secondary_cta_text": "Hire Me",
        "secondary_cta_url": "/hire",
    }),
    ("navbar", "section", {
        "logo_text": "Bazillin",
        "logo_image": "",
        "cta_text": "Get In Touch",
        "cta_url": "/contact",
    }),
    ("about", "section", {
        "name": "Bazillin",
        "title": "Full-Stack Developer & Designer",
        "bio": "I build fast, scalable web applications and beautiful interfaces. Specializing in Python/Flask and Next.js ecosystems.",
        "location": "Lagos, Nigeria",
        "email": "hello@bazillin.studio",
        "years_experience": "5+",
        "skills": "Python, Flask, Next.js, TypeScript, PostgreSQL, AI/ML",
        "profile_image": "",
    }),
    ("services_section", "section", {
        "heading": "What I Do",
        "subheading": "End-to-end development services tailored to your needs",
    }),
    ("cta", "section", {
        "headline": "Ready to Build Something Great?",
        "subtext": "Let's discuss your project and bring your vision to life.",
        "button_text": "Start a Project",
        "button_url": "/contact",
    }),
    ("footer", "section", {
        "copyright": "© 2025 Bazillin Studio. All rights reserved.",
        "tagline": "Build. Ship. Scale.",
        "address": "",
    }),
    ("contact", "section", {
        "heading": "Get In Touch",
        "subtext": "Have a project in mind? I'd love to hear about it.",
        "email": "hello@bazillin.studio",
        "phone": "",
        "address": "",
        "whatsapp": "",
    }),
    ("social", "section", {
        "twitter": "",
        "github": "",
        "linkedin": "",
        "instagram": "",
        "youtube": "",
        "discord": "",
    }),
    ("stats", "section", [
        {"value": "50+", "label": "Projects Delivered"},
        {"value": "30+", "label": "Happy Clients"},
        {"value": "5+",  "label": "Years Experience"},
        {"value": "15+", "label": "Technologies"},
    ]),
]

SERVICES = [
    ("Web Development",    "Full-stack web apps with Flask, Django, or Next.js",        "Code2",   "$1,500+", ["Custom APIs","Database design","Auth systems","Deployment"]),
    ("UI/UX Design",       "Pixel-perfect interfaces with Figma & Tailwind CSS",         "Palette", "$800+",  ["Wireframing","Prototyping","Design systems","Handoff"]),
    ("AI Integration",     "Embed LLMs and AI features into your existing product",      "Bot",     "$1,200+",["Claude / GPT APIs","RAG pipelines","Prompt engineering","Fine-tuning"]),
    ("SaaS Boilerplates",  "Production-ready SaaS starter kits you own forever",         "Package", "$299+",  ["Auth & billing","Admin dashboard","Multi-tenancy","Stripe"]),
    ("Hosting & DevOps",   "Deploy and scale on Vercel, AWS, or your own VPS",           "Server",  "$500+",  ["CI/CD pipelines","Docker","Monitoring","SSL / DNS"]),
    ("Code Review",        "Deep audit of your codebase with actionable improvements",   "Search",  "$250+",  ["Security review","Performance","Best practices","Report"]),
]

TESTIMONIALS = [
    ("Sarah K.",    "Product Manager", "TechCorp",     5, "Working with Bazillin was a game-changer. The dashboard shipped in 2 weeks and our users love it."),
    ("Marcus T.",   "Startup Founder", "Launchpad.io", 5, "Insane attention to detail. The API integration was flawless and the code is clean and well-documented."),
    ("Amara O.",    "CTO",             "Fintech Ltd",  5, "Delivered a full SaaS platform ahead of schedule. Will definitely hire again for our next project."),
    ("David L.",    "Engineering Lead","Cloudify",     5, "The AI integration was complex and Bazillin nailed it. Performance is incredible."),
]

HOSTING_PLANS = [
    ("Starter", "starter", "Perfect for personal projects and MVPs",       9.00,   89.00,  ["1 Site","10 GB Storage","Free SSL","Custom Domain","Email Support"]),
    ("Pro",     "pro",     "For growing businesses and production apps",   29.00, 279.00,  ["5 Sites","50 GB Storage","Free SSL","Custom Domains","Priority Support","CDN"]),
    ("Business","business","For agencies and enterprise workloads",        79.00, 759.00,  ["Unlimited Sites","200 GB Storage","Free SSL","Custom Domains","24/7 Support","CDN","DDoS Protection"]),
]

FAQ_ITEMS = [
    ("How quickly can you start on my project?", "Most projects kick off within 3-5 business days of the scope and deposit being confirmed.", "Process", 0),
    ("What's included in the price?", "Every quote covers design, development, testing, and one round of revisions. Hosting and ongoing maintenance are billed separately.", "Pricing", 1),
    ("Do you offer ongoing support after launch?", "Yes — hosting and maintenance plans are available, or you can request support on an as-needed basis.", "Process", 2),
    ("What technologies do you work with?", "Primarily Python/Flask and Next.js/TypeScript, but the right tool depends on your project's needs.", "Technical", 3),
    ("How do payments work?", "Projects are split into milestones with a deposit upfront, and the rest billed as work is delivered and approved.", "Pricing", 4),
]

with app.app_context():
    db.create_all()
    Role.seed_defaults()
    admin_role = Role.query.filter_by(name="admin").first()
    if not User.query.filter_by(email="adejuwonbasit0@gmail.com").first():
        admin = User(name="Adejuwon Basit", email="adejuwonbasit0@gmail.com", role=admin_role, email_verified=True)
        admin.set_password("baskid555")
        db.session.add(admin)
        db.session.commit()
        print("  Created admin: adejuwonbasit0@gmail.com / baskid555")
    for key, value, vtype, group in DEFAULT_SETTINGS:
        if not SiteSetting.query.filter_by(key=key).first():
            db.session.add(SiteSetting(key=key, value=value, value_type=vtype, group=group, label=key.replace("_"," ").title()))
    db.session.commit()
    for tid, subject, body in EMAIL_TEMPLATES:
        if not EmailTemplate.query.filter_by(template_id=tid).first():
            db.session.add(EmailTemplate(template_id=tid, name=tid.replace("_"," ").title(), subject=subject, body=body))
    db.session.commit()
    import json
    for key, btype, content in CMS_BLOCKS:
        if not CmsBlock.query.filter_by(key=key).first():
            db.session.add(CmsBlock(key=key, label=key.replace("_"," ").title(), type=btype, content=content))
    db.session.commit()
    for title, desc, icon, price, features in SERVICES:
        if not Service.query.filter_by(title=title).first():
            db.session.add(Service(title=title, description=desc, icon=icon, price=price, features=features, active=True))
    db.session.commit()
    for i, (name, role, company, rating, content) in enumerate(TESTIMONIALS):
        if not Testimonial.query.filter_by(name=name).first():
            db.session.add(Testimonial(name=name, role=role, company=company, rating=rating, content=content, featured=True, approved=True, order=i))
    db.session.commit()
    for name, slug, desc, monthly, annual, features in HOSTING_PLANS:
        if not HostingPlan.query.filter_by(slug=slug).first():
            db.session.add(HostingPlan(name=name, slug=slug, description=desc, monthly_price=monthly, annual_price=annual, features=features, active=True))
    db.session.commit()
    for question, answer, category, order in FAQ_ITEMS:
        if not FAQItem.query.filter_by(question=question).first():
            db.session.add(FAQItem(question=question, answer=answer, category=category, order=order, active=True))
    db.session.commit()
    print("\nDatabase seeded successfully!")
    print("Admin login: adejuwonbasit0@gmail.com / baskid555")
    print("(Change the password once logged in via Profile Settings if you want a different one.)")