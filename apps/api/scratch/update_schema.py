import sys
sys.path.insert(0, '.')
from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    # 1. Create all missing tables (like premium_modules)
    db.create_all()
    print("Tables created.")
    
    # 2. Add phone, website, address to leads if they don't exist
    conn = db.engine.connect()
    columns = [info[1] for info in conn.execute(text("PRAGMA table_info(leads)")).fetchall()]
    print("Current columns on leads:", columns)
    
    if "phone" not in columns:
        conn.execute(text("ALTER TABLE leads ADD COLUMN phone VARCHAR(64)"))
        print("Added phone column.")
    if "website" not in columns:
        conn.execute(text("ALTER TABLE leads ADD COLUMN website VARCHAR(512)"))
        print("Added website column.")
    if "address" not in columns:
        conn.execute(text("ALTER TABLE leads ADD COLUMN address TEXT"))
        print("Added address column.")
    
    conn.commit()
    conn.close()
    
    # 3. Seed the premium modules
    from app.models.platform import PremiumModule
    from decimal import Decimal
    
    modules = [
        {"slug": "website-builder", "name": "Website Builder", "price": 99.00},
        {"slug": "funnel-builder", "name": "Sales Funnel Builder", "price": 149.00},
        {"slug": "invoice-generator", "name": "Invoice Generator", "price": 29.00},
        {"slug": "payment-link-generator", "name": "Payment Link Generator", "price": 39.00},
        {"slug": "whatsapp-bot", "name": "WhatsApp Business Bot", "price": 79.00},
        {"slug": "ai-chatbot", "name": "AI Chatbot", "price": 89.00},
        {"slug": "automation-studio", "name": "Automation Studio", "price": 119.00},
    ]
    
    for m in modules:
        existing = PremiumModule.query.filter_by(slug=m["slug"]).first()
        if not existing:
            mod = PremiumModule(slug=m["slug"], name=m["name"], price=Decimal(str(m["price"])), active=True)
            db.session.add(mod)
            print(f"Seeded module addon: {m['name']}")
        else:
            print(f"Module addon {m['name']} already exists.")
            
    db.session.commit()
    print("Addon modules seeded.")
