"""
Seed Premium Products into the marketplace.
Run: flask --app run:app shell < scripts/seed_premium_products.py
Or:  python -c "from scripts.seed_premium_products import seed; seed()"

IMPORTANT: only genuinely SELLABLE, buyer-facing dashboard tools belong in
this list. Admin-only studios (Website Builder, Graphics Studio, Content
Studio, Video Studio, Automation Studio, Social Media Bot, Prompt Library)
were wrongly seeded here in an earlier version, making them show up as
purchasable in the public marketplace — fixed once already (batch 60) and
re-fixed here since this list had reverted to including them again.
"""


def seed():
    """Seed all premium tool products into the Product table."""
    from app import create_app
    from app.extensions import db
    from app.models.commerce import Product

    app = create_app()
    with app.app_context():
        products = [
            {
                "title": "Sales Funnel Builder",
                "slug": "funnel-builder",
                "description": "Design high-converting sales funnels with AI-generated pages.",
                "long_description": """## Sales Funnel Builder

Create complete sales funnels that convert visitors into customers. Each step is AI-generated and optimized for conversions.

### Features
- **8 Step Types** — Landing, Sales, Checkout, Thank You, Upsell, Downsell, Webinar, Booking
- **AI Page Generation** — Describe each step and get high-converting copy
- **Visual Flow Editor** — Drag and arrange funnel steps
- **Conversion Tracking** — Monitor views and conversions
- **One-Click Publish** — Each funnel gets its own shareable URL
- **Mobile Optimized** — Responsive pages on every device""",
                "price": 39.99,
                "category": "Builders",
                "tags": "funnel,sales,marketing,conversion,landing-page",
            },
            {
                "title": "Invoice Generator",
                "slug": "invoice-generator",
                "description": "Create professional invoices with PDF export and email delivery.",
                "long_description": """## Professional Invoice Generator

Create, send, and track invoices like a pro. Generate beautiful PDF invoices and email them directly to your clients.

### Features
- **Professional PDF Export** — Download stunning invoice PDFs
- **Email Delivery** — Send invoices directly to clients
- **Auto-Calculations** — Subtotal, tax, discounts auto-calculated
- **Status Tracking** — Draft, Sent, Paid, Overdue statuses
- **Custom Branding** — Add your logo and business info
- **Line Items** — Unlimited items per invoice
- **Multiple Currencies** — Support for all major currencies
- **Invoice History** — Track all your invoices in one place""",
                "price": 19.99,
                "category": "Finance",
                "tags": "invoice,billing,pdf,finance,business",
            },
            {
                "title": "Payment Link Generator",
                "slug": "payment-link-generator",
                "description": "Create shareable payment links and collect payments instantly.",
                "long_description": """## Payment Link Generator

Create beautiful payment pages and share them anywhere. Collect payments without a full e-commerce setup.

### Features
- **Instant Links** — Create payment links in seconds
- **Shareable URLs** — Share via email, social media, or messaging
- **Analytics Dashboard** — Track views, payments, and revenue
- **Custom Branding** — Match your brand style
- **Multiple Currencies** — Accept payments in any currency
- **Active/Inactive Toggle** — Control link availability""",
                "price": 14.99,
                "category": "Finance",
                "tags": "payment,link,collection,billing,online-payment",
            },
            {
                "title": "WhatsApp Business Bot",
                "slug": "whatsapp-bot",
                "description": "Build intelligent chatbots for WhatsApp, Telegram, and web.",
                "long_description": """## WhatsApp Business Bot Builder

Create AI-powered chatbots that handle customer conversations 24/7. No coding required.

### Features
- **Multi-Platform** — WhatsApp, Telegram, Web Widget
- **AI-Powered Replies** — GPT-driven intelligent responses
- **Keyword Rules** — Set up exact match, contains, or regex triggers
- **Custom Flows** — Build conversation flows step by step
- **Greeting Messages** — Auto-greet new visitors
- **Test Chat Panel** — Test your bot before going live
- **Message Analytics** — Track message volume and engagement""",
                "price": 49.99,
                "category": "Bots",
                "tags": "whatsapp,chatbot,bot,automation,messaging,telegram",
            },
            {
                "title": "WhatsApp Chat Widget",
                "slug": "whatsapp-widget",
                "description": "Add a WhatsApp chat button to your website in minutes — no API, no coding.",
                "long_description": """## WhatsApp Chat Widget

A simple, professional WhatsApp click-to-chat button for your website. Visitors click it and go straight into a WhatsApp chat with your number.

### Features
- **No API, No Coding** — Just enter your WhatsApp number
- **Fully Customizable** — Position, color, animation, welcome message
- **Three Install Options** — Embed code, WordPress plugin, or a standalone hosted link
- **Real Analytics** — Views, clicks, and click rate
- **Live Preview** — See changes instantly while configuring""",
                "price": 0,
                "category": "Bots",
                "tags": "whatsapp,widget,chat,website,click-to-chat",
            },
            {
                "title": "AI Voice Studio",
                "slug": "voice-studio",
                "description": "Generate real, downloadable speech, or record your own voice — saved permanently to your account.",
                "long_description": """## AI Voice Studio

Turn text into real, downloadable audio — or record your own voice — right from your dashboard. Every generation is saved permanently to your account, not just this browser tab.

### Features
- **Real Audio Generation** — Genuine MP3 files, not a fake preview
- **Persistent Library** — Every generation is saved to "My Audio" and stays there after you log out
- **Voice Recording** — Record your own voice directly in the browser, no software needed
- **Favorite & Organize** — Star, rename, and manage your generations
- **Premium Voices** — Real named voices with gender/accent (when ElevenLabs is configured)""",
                "price": 4.99,
                "category": "AI Tools",
                "tags": "voice,tts,text-to-speech,audio,recording,ai",
            },
            {
                "title": "AI Chatbot",
                "slug": "ai-chatbot",
                "description": "Deploy an AI-powered chatbot on your website.",
                "long_description": """## AI Chatbot for Your Website

Add a smart AI chatbot to any website. It learns from your content and answers customer questions automatically.

### Features
- **Custom Training** — Train with your own content and FAQs
- **Website Widget** — Embeddable chat widget for any site
- **AI Responses** — Powered by GPT for natural conversations
- **Lead Capture** — Collect visitor info automatically
- **Handoff to Human** — Seamless agent takeover when needed""",
                "price": 29.99,
                "category": "Bots",
                "tags": "chatbot,ai,website,widget,customer-support",
            },
        ]

        created = 0
        updated = 0
        for p_data in products:
            existing = Product.query.filter_by(slug=p_data["slug"]).first()
            tags_list = [t.strip() for t in p_data.get("tags", "").split(",") if t.strip()]
            if existing:
                existing.title = p_data["title"]
                existing.description = p_data["description"]
                existing.long_desc = p_data.get("long_description", "")
                existing.price = p_data["price"]
                existing.category = p_data.get("category", "")
                existing.tags = tags_list
                existing.status = "active"
                existing.type = "premium_tool"
                updated += 1
            else:
                product = Product(
                    title=p_data["title"],
                    slug=p_data["slug"],
                    description=p_data["description"],
                    long_desc=p_data.get("long_description", ""),
                    price=p_data["price"],
                    category=p_data.get("category", ""),
                    tags=tags_list,
                    status="active",
                    type="premium_tool",
                )
                db.session.add(product)
                created += 1

        db.session.commit()
        print(f"[OK] Premium products seeded: {created} created, {updated} updated")
        return created, updated


if __name__ == "__main__":
    seed()
