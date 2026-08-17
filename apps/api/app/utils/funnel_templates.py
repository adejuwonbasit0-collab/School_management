"""Starter template library for Funnel Builder pages.

Each template is a real, fully-populated set of Blocks-mode blocks (see
app/utils/funnel_blocks.py) — not placeholder text — covering the most
common funnel page types. This is NOT the "hundreds of templates across
dozens of industries" the master prompt describes; it's a genuine, honest
starting set built on the real block system, designed so more can be
added later just by appending another dict entry here (same pattern as
BLOCK_SCHEMAS — no code changes needed elsewhere to add more).
"""

FUNNEL_TEMPLATES = {
    "saas_landing": {
        "label": "SaaS Product Landing", "category": "SaaS", "page_type": "landing",
        "description": "Headline, feature highlights, social proof, pricing, FAQ.",
        "blocks": [
            {"id": "t1", "type": "heading", "data": {"text": "The Tool Your Team Actually Wants to Use", "level": "h1", "align": "center"}},
            {"id": "t2", "type": "paragraph", "data": {"text": "Cut busywork, ship faster, and finally see everything in one place.", "align": "center"}},
            {"id": "t3", "type": "button", "data": {"text": "Start Free Trial", "url": "", "nav": "next", "style": "primary", "align": "center"}},
            {"id": "t4", "type": "spacer", "data": {"height": 40}},
            {"id": "t5", "type": "testimonial", "data": {"items": [
                {"quote": "We cut our onboarding time in half.", "name": "Amara Okafor", "role": "Head of Ops, Flux"},
                {"quote": "Finally, a tool the whole team sticks with.", "name": "Daniel Reyes", "role": "Founder, Loop"},
            ]}},
            {"id": "t6", "type": "pricing_table", "data": {"plans": [
                {"name": "Starter", "price": "$19/mo", "features": "Up to 5 users\\nCore features", "cta_text": "Choose Starter", "highlighted": "no"},
                {"name": "Growth", "price": "$49/mo", "features": "Up to 25 users\\nAll features\\nPriority support", "cta_text": "Choose Growth", "highlighted": "yes"},
            ]}},
            {"id": "t7", "type": "faq", "data": {"items": [
                {"q": "Is there a free trial?", "a": "Yes — 14 days, no card required."},
                {"q": "Can I cancel anytime?", "a": "Yes, cancel anytime from your billing settings."},
            ]}},
        ],
    },
    "coaching_sales": {
        "label": "Coaching / Course Sales Page", "category": "Coaching", "page_type": "sales",
        "description": "Big promise headline, story, transformation, testimonials, pricing.",
        "blocks": [
            {"id": "t1", "type": "heading", "data": {"text": "Stop Guessing. Start Growing.", "level": "h1", "align": "center"}},
            {"id": "t2", "type": "paragraph", "data": {"text": "A step-by-step program to help you go from stuck to unstoppable in 8 weeks.", "align": "center"}},
            {"id": "t3", "type": "video", "data": {"url": ""}},
            {"id": "t4", "type": "button", "data": {"text": "Join The Program", "url": "", "nav": "next", "style": "primary", "align": "center"}},
            {"id": "t5", "type": "accordion", "data": {"items": [
                {"title": "Who is this for?", "content": "Anyone ready to commit to real change over the next 8 weeks."},
                {"title": "What's included?", "content": "Weekly live calls, a private community, and lifetime access to the material."},
            ]}},
            {"id": "t6", "type": "testimonial", "data": {"items": [
                {"quote": "Best investment I've made in myself.", "name": "Priya Nair", "role": "Student"},
            ]}},
            {"id": "t7", "type": "countdown", "data": {"end_date": "", "label": "Enrollment closes in:"}},
        ],
    },
    "webinar_registration": {
        "label": "Webinar Registration", "category": "Events", "page_type": "webinar_registration",
        "description": "Date/time hook, what they'll learn, countdown, single CTA.",
        "blocks": [
            {"id": "t1", "type": "heading", "data": {"text": "Free Live Training: The 3 Mistakes Killing Your Growth", "level": "h1", "align": "center"}},
            {"id": "t2", "type": "paragraph", "data": {"text": "Join us live and walk away with a plan you can use the same day.", "align": "center"}},
            {"id": "t3", "type": "countdown", "data": {"end_date": "", "label": "Training starts in:"}},
            {"id": "t4", "type": "button", "data": {"text": "Save My Seat", "url": "", "nav": "next", "style": "primary", "align": "center"}},
            {"id": "t5", "type": "tabs", "data": {"items": [
                {"label": "What You'll Learn", "content": "The exact framework we use with clients."},
                {"label": "Who This Is For", "content": "Founders and operators who want fast, practical wins."},
            ]}},
        ],
    },
    "lead_magnet": {
        "label": "Lead Magnet / Opt-in", "category": "Lead Generation", "page_type": "lead_capture",
        "description": "Simple, high-contrast opt-in page for a free download.",
        "blocks": [
            {"id": "t1", "type": "heading", "data": {"text": "Get The Free Checklist", "level": "h1", "align": "center"}},
            {"id": "t2", "type": "paragraph", "data": {"text": "The exact 12-point checklist we use before every launch.", "align": "center"}},
            {"id": "t3", "type": "image", "data": {"src": "https://picsum.photos/id/60/900/600", "alt": "Checklist preview"}},
            {"id": "t4", "type": "button", "data": {"text": "Send Me The Checklist", "url": "", "nav": "next", "style": "primary", "align": "center"}},
        ],
    },
    "checkout_upsell": {
        "label": "One-Time Offer / Upsell", "category": "Checkout", "page_type": "upsell",
        "description": "Classic upsell page with accept/decline buttons.",
        "blocks": [
            {"id": "t1", "type": "heading", "data": {"text": "Wait! Add This Before You Go", "level": "h1", "align": "center"}},
            {"id": "t2", "type": "paragraph", "data": {"text": "One-time offer, available only on this page — 40% off.", "align": "center"}},
            {"id": "t3", "type": "progress_bar", "data": {"label": "Only a few left at this price", "percent": 85, "color": "#dc2626"}},
            {"id": "t4", "type": "button", "data": {"text": "Yes, Add It To My Order", "url": "", "nav": "accept", "style": "primary", "align": "center"}},
            {"id": "t5", "type": "button", "data": {"text": "No thanks, continue", "url": "", "nav": "decline", "style": "secondary", "align": "center"}},
        ],
    },
    "thank_you": {
        "label": "Thank You Page", "category": "Checkout", "page_type": "thank_you",
        "description": "Confirmation, next steps, and social sharing.",
        "blocks": [
            {"id": "t1", "type": "icon", "data": {"name": "check-circle", "caption": "", "color": "#16a34a"}},
            {"id": "t2", "type": "heading", "data": {"text": "You're All Set!", "level": "h1", "align": "center"}},
            {"id": "t3", "type": "paragraph", "data": {"text": "Check your email for confirmation and next steps.", "align": "center"}},
            {"id": "t4", "type": "divider", "data": {"style": "dots"}},
            {"id": "t5", "type": "heading", "data": {"text": "What happens next", "level": "h3", "align": "center"}},
            {"id": "t6", "type": "tabs", "data": {"items": [
                {"label": "Step 1", "content": "You'll get a confirmation email within a few minutes."},
                {"label": "Step 2", "content": "Our team will reach out with the next steps."},
            ]}},
            {"id": "t7", "type": "social_links", "data": {"items": [
                {"platform": "instagram", "url": ""}, {"platform": "twitter", "url": ""},
            ]}},
        ],
    },
    "booking_page": {
        "label": "Booking / Consultation", "category": "Services", "page_type": "booking",
        "description": "Booking-intent page with a spot for your calendar embed (Calendly/Cal.com).",
        "blocks": [
            {"id": "t1", "type": "heading", "data": {"text": "Book Your Free Consultation", "level": "h1", "align": "center"}},
            {"id": "t2", "type": "paragraph", "data": {"text": "Pick a time that works for you — 15 minutes, no pressure.", "align": "center"}},
            {"id": "t3", "type": "rating", "data": {"score": 5, "caption": "Rated 5/5 by 200+ clients"}},
            {"id": "t4", "type": "accordion", "data": {"items": [
                {"title": "What happens on the call?", "content": "We'll go over your goals and see if we're a fit to work together."},
                {"title": "Do I need to prepare anything?", "content": "Nope — just show up with your questions."},
            ]}},
            {"id": "t5", "type": "custom_html", "data": {"html": "<!-- Paste your Calendly/Cal.com embed code here -->"}},
        ],
    },
    "webinar_replay": {
        "label": "Webinar Replay", "category": "Events", "page_type": "webinar_replay",
        "description": "Replay video page with a CTA below the recording.",
        "blocks": [
            {"id": "t1", "type": "heading", "data": {"text": "Watch The Replay", "level": "h1", "align": "center"}},
            {"id": "t2", "type": "paragraph", "data": {"text": "You missed the live session — here's the full recording.", "align": "center"}},
            {"id": "t3", "type": "video", "data": {"url": ""}},
            {"id": "t4", "type": "progress_bar", "data": {"label": "Offer expires soon", "percent": 60, "color": "#dc2626"}},
            {"id": "t5", "type": "button", "data": {"text": "Claim The Offer", "url": "", "nav": "next", "style": "primary", "align": "center"}},
        ],
    },
    "membership_login": {
        "label": "Membership Login", "category": "Membership", "page_type": "membership_login",
        "description": "Simple, clean login-intent page for a members area.",
        "blocks": [
            {"id": "t1", "type": "icon", "data": {"name": "lock", "caption": "", "color": "#111827"}},
            {"id": "t2", "type": "heading", "data": {"text": "Member Login", "level": "h1", "align": "center"}},
            {"id": "t3", "type": "paragraph", "data": {"text": "Log in to access your course materials and community.", "align": "center"}},
            {"id": "t4", "type": "custom_html", "data": {"html": "<!-- Your login form / membership platform embed goes here -->"}},
        ],
    },
    "survey_quiz": {
        "label": "Survey / Quiz Intro", "category": "Lead Generation", "page_type": "quiz",
        "description": "Quiz/survey intro page that leads into your quiz tool.",
        "blocks": [
            {"id": "t1", "type": "heading", "data": {"text": "What's Your [X] Type?", "level": "h1", "align": "center"}},
            {"id": "t2", "type": "paragraph", "data": {"text": "Answer 5 quick questions and get your personalized result.", "align": "center"}},
            {"id": "t3", "type": "progress_bar", "data": {"label": "Takes less than 2 minutes", "percent": 100, "color": "#000000"}},
            {"id": "t4", "type": "button", "data": {"text": "Start The Quiz", "url": "", "nav": "next", "style": "primary", "align": "center"}},
        ],
    },
    "restaurant_landing": {
        "label": "Restaurant / Hospitality", "category": "Restaurant", "page_type": "landing",
        "description": "Menu highlight, reservation CTA, location.",
        "blocks": [
            {"id": "t1", "type": "image", "data": {"src": "https://picsum.photos/id/292/900/600", "alt": "Restaurant interior"}},
            {"id": "t2", "type": "heading", "data": {"text": "A Table Is Waiting For You", "level": "h1", "align": "center"}},
            {"id": "t3", "type": "paragraph", "data": {"text": "Fresh, seasonal dishes in the heart of the city.", "align": "center"}},
            {"id": "t4", "type": "button", "data": {"text": "Reserve a Table", "url": "", "nav": "next", "style": "primary", "align": "center"}},
            {"id": "t5", "type": "map_embed", "data": {"embed_url": ""}},
        ],
    },
    "real_estate_listing": {
        "label": "Real Estate Listing", "category": "Real Estate", "page_type": "sales",
        "description": "Property showcase with features and an inquiry CTA.",
        "blocks": [
            {"id": "t1", "type": "image", "data": {"src": "https://picsum.photos/id/164/900/600", "alt": "Property"}},
            {"id": "t2", "type": "heading", "data": {"text": "4 Bed, 3 Bath — Move-In Ready", "level": "h1", "align": "center"}},
            {"id": "t3", "type": "paragraph", "data": {"text": "Spacious family home minutes from downtown.", "align": "center"}},
            {"id": "t4", "type": "comparison_table", "data": {"columns": "This Home", "rows": [
                {"feature": "Bedrooms", "values": "4"}, {"feature": "Bathrooms", "values": "3"}, {"feature": "Garage", "values": "2-car"},
            ]}},
            {"id": "t5", "type": "button", "data": {"text": "Schedule a Viewing", "url": "", "nav": "next", "style": "primary", "align": "center"}},
        ],
    },
    "fitness_landing": {
        "label": "Fitness / Gym Landing", "category": "Fitness", "page_type": "landing",
        "description": "Program hook, transformation proof, membership CTA.",
        "blocks": [
            {"id": "t1", "type": "heading", "data": {"text": "Your Transformation Starts Today", "level": "h1", "align": "center"}},
            {"id": "t2", "type": "paragraph", "data": {"text": "8-week program. Real coaches. Real results.", "align": "center"}},
            {"id": "t3", "type": "logo_cloud", "data": {"heading": "As featured in", "items": [{"name": "Fit Weekly"}, {"name": "Muscle Times"}]}},
            {"id": "t4", "type": "testimonial", "data": {"items": [
                {"quote": "Lost 15lbs in 8 weeks and feel amazing.", "name": "Chidi O.", "role": "Member since 2024"},
            ]}},
            {"id": "t5", "type": "button", "data": {"text": "Join Now", "url": "", "nav": "next", "style": "primary", "align": "center"}},
        ],
    },
    "crypto_finance": {
        "label": "Crypto / Finance Landing", "category": "Finance", "page_type": "landing",
        "description": "Trust-focused landing for finance/crypto offers.",
        "blocks": [
            {"id": "t1", "type": "heading", "data": {"text": "Grow Your Portfolio With Confidence", "level": "h1", "align": "center"}},
            {"id": "t2", "type": "paragraph", "data": {"text": "Simple tools for serious investors.", "align": "center"}},
            {"id": "t3", "type": "rating", "data": {"score": 5, "caption": "4.9/5 from 3,000+ users"}},
            {"id": "t4", "type": "comparison_table", "data": {"columns": "Free, Pro", "rows": [
                {"feature": "Portfolio tracking", "values": "✓, ✓"}, {"feature": "Real-time alerts", "values": "✗, ✓"},
            ]}},
            {"id": "t5", "type": "button", "data": {"text": "Get Started Free", "url": "", "nav": "next", "style": "primary", "align": "center"}},
        ],
    },
    "event_registration": {
        "label": "Event Registration", "category": "Events", "page_type": "lead_capture",
        "description": "In-person or virtual event sign-up page.",
        "blocks": [
            {"id": "t1", "type": "heading", "data": {"text": "Join Us — [Event Name] 2026", "level": "h1", "align": "center"}},
            {"id": "t2", "type": "paragraph", "data": {"text": "One day. One place. A room full of people building what's next.", "align": "center"}},
            {"id": "t3", "type": "countdown", "data": {"end_date": "", "label": "Early bird pricing ends in:"}},
            {"id": "t4", "type": "button", "data": {"text": "Get My Ticket", "url": "", "nav": "next", "style": "primary", "align": "center"}},
            {"id": "t5", "type": "map_embed", "data": {"embed_url": ""}},
        ],
    },
    "agency_portfolio": {
        "label": "Agency / Consulting Landing", "category": "Agency", "page_type": "landing",
        "description": "Services overview, results, contact CTA.",
        "blocks": [
            {"id": "t1", "type": "heading", "data": {"text": "We Build Brands That Grow", "level": "h1", "align": "center"}},
            {"id": "t2", "type": "paragraph", "data": {"text": "Strategy, design, and growth marketing for ambitious teams.", "align": "center"}},
            {"id": "t3", "type": "tabs", "data": {"items": [
                {"label": "Strategy", "content": "We help you find the right message and market."},
                {"label": "Design", "content": "We design brands people remember."},
                {"label": "Growth", "content": "We run the campaigns that get you customers."},
            ]}},
            {"id": "t4", "type": "logo_cloud", "data": {"heading": "Trusted by", "items": [{"name": "Client A"}, {"name": "Client B"}, {"name": "Client C"}]}},
            {"id": "t5", "type": "button", "data": {"text": "Book a Free Consult", "url": "", "nav": "next", "style": "primary", "align": "center"}},
        ],
    },
    "ecommerce_product": {
        "label": "E-commerce Product Page", "category": "E-commerce", "page_type": "sales",
        "description": "Product hero, features, reviews, buy button.",
        "blocks": [
            {"id": "t1", "type": "image", "data": {"src": "https://picsum.photos/id/26/900/600", "alt": "Product"}},
            {"id": "t2", "type": "heading", "data": {"text": "The Last Water Bottle You'll Ever Buy", "level": "h1", "align": "center"}},
            {"id": "t3", "type": "paragraph", "data": {"text": "Keeps drinks cold for 24 hours. Lifetime warranty.", "align": "center"}},
            {"id": "t4", "type": "rating", "data": {"score": 5, "caption": "4.9/5 from 1,200 reviews"}},
            {"id": "t5", "type": "button", "data": {"text": "Buy Now — $39", "url": "", "nav": "next", "style": "primary", "align": "center"}},
            {"id": "t6", "type": "testimonial", "data": {"items": [
                {"quote": "Genuinely never buying a different bottle again.", "name": "Kwame A.", "role": "Verified Buyer"},
            ]}},
        ],
    },
    "application_form": {
        "label": "Apply Now / Application", "category": "Coaching", "page_type": "application_form",
        "description": "Qualification-style page before a call booking.",
        "blocks": [
            {"id": "t1", "type": "heading", "data": {"text": "Apply For A Strategy Call", "level": "h1", "align": "center"}},
            {"id": "t2", "type": "paragraph", "data": {"text": "We work with a limited number of clients each month — tell us about you.", "align": "center"}},
            {"id": "t3", "type": "accordion", "data": {"items": [
                {"title": "Who do you work with?", "content": "Founders doing $10k+/mo looking to scale."},
                {"title": "What happens after I apply?", "content": "We'll review and get back to you within 48 hours."},
            ]}},
            {"id": "t4", "type": "button", "data": {"text": "Apply Now", "url": "", "nav": "next", "style": "primary", "align": "center"}},
        ],
    },
    "law_consulting": {
        "label": "Law Firm / Professional Services", "category": "Law Firm", "page_type": "landing",
        "description": "Trust-first landing for legal/professional services.",
        "blocks": [
            {"id": "t1", "type": "heading", "data": {"text": "Experienced Counsel When It Matters Most", "level": "h1", "align": "center"}},
            {"id": "t2", "type": "paragraph", "data": {"text": "Free initial consultation. No obligation.", "align": "center"}},
            {"id": "t3", "type": "comparison_table", "data": {"columns": "Years Experience, Cases Won", "rows": [
                {"feature": "Track Record", "values": "20+, 500+"},
            ]}},
            {"id": "t4", "type": "button", "data": {"text": "Schedule a Consultation", "url": "", "nav": "next", "style": "primary", "align": "center"}},
        ],
    },
    "course_landing": {
        "label": "Online Course Landing", "category": "Course", "page_type": "sales",
        "description": "Curriculum highlight, instructor credibility, enroll CTA.",
        "blocks": [
            {"id": "t1", "type": "heading", "data": {"text": "Master [Skill] In 30 Days", "level": "h1", "align": "center"}},
            {"id": "t2", "type": "paragraph", "data": {"text": "A step-by-step video course with lifetime access.", "align": "center"}},
            {"id": "t3", "type": "tabs", "data": {"items": [
                {"label": "What You'll Learn", "content": "The exact system, from zero to confident."},
                {"label": "Curriculum", "content": "8 modules, 40+ lessons, downloadable resources."},
            ]}},
            {"id": "t4", "type": "pricing_table", "data": {"plans": [
                {"name": "Course Only", "price": "$97", "features": "Full course access\\nLifetime updates", "cta_text": "Enroll", "highlighted": "no"},
                {"name": "Course + Coaching", "price": "$297", "features": "Everything in Course Only\\n4 group coaching calls", "cta_text": "Enroll", "highlighted": "yes"},
            ]}},
        ],
    },
    "full_site_homepage": {
        "label": "Full Site Homepage (Business)", "category": "Business", "page_type": "landing",
        "description": "A complete, long-form homepage — nav-style header, hero, features, social proof, pricing, FAQ, and footer, all in one page.",
        "blocks": [
            {"id": "n1", "type": "heading", "data": {"text": "Your Business Name", "level": "h3", "align": "left"}},
            {"id": "n2", "type": "divider", "data": {"style": "space"}},
            {"id": "h1", "type": "heading", "data": {"text": "Everything Your Business Needs, In One Place", "level": "h1", "align": "center"}},
            {"id": "h2", "type": "paragraph", "data": {"text": "A complete platform to run, grow, and manage your business — built for teams who move fast.", "align": "center"}},
            {"id": "h3", "type": "button", "data": {"text": "Get Started Free", "url": "", "nav": "next", "style": "primary", "align": "center"}},
            {"id": "h4", "type": "image", "data": {"src": "https://picsum.photos/id/180/1000/600", "alt": "Product screenshot"}},
            {"id": "logos", "type": "logo_cloud", "data": {"heading": "Trusted by teams at", "items": [
                {"name": "Northwind"}, {"name": "Vertex"}, {"name": "Alta Labs"}, {"name": "Kiln"},
            ]}},
            {"id": "d1", "type": "divider", "data": {"style": "space"}},
            {"id": "f1", "type": "heading", "data": {"text": "Everything You Need To Move Faster", "level": "h2", "align": "center"}},
            {"id": "f2", "type": "tabs", "data": {"items": [
                {"label": "Plan", "content": "Map out your work with boards, timelines, and docs — all in sync."},
                {"label": "Collaborate", "content": "Comment, assign, and review without leaving the page."},
                {"label": "Ship", "content": "Track progress in real time and celebrate wins as a team."},
            ]}},
            {"id": "d2", "type": "divider", "data": {"style": "space"}},
            {"id": "r1", "type": "rating", "data": {"score": 5, "caption": "4.9/5 average rating from 2,400+ teams"}},
            {"id": "t1", "type": "testimonial", "data": {"items": [
                {"quote": "We replaced four tools with this. Our team has never moved faster.", "name": "Ade Fashola", "role": "COO, Northwind"},
                {"quote": "Setup took ten minutes. We were live the same afternoon.", "name": "Lena Cho", "role": "Founder, Vertex"},
            ]}},
            {"id": "d3", "type": "divider", "data": {"style": "space"}},
            {"id": "p1", "type": "heading", "data": {"text": "Simple, Honest Pricing", "level": "h2", "align": "center"}},
            {"id": "p2", "type": "pricing_table", "data": {"plans": [
                {"name": "Starter", "price": "$0/mo", "features": "Up to 3 projects\\nCore features\\nCommunity support", "cta_text": "Start Free", "highlighted": "no"},
                {"name": "Team", "price": "$29/mo", "features": "Unlimited projects\\nAll features\\nPriority support", "cta_text": "Start Trial", "highlighted": "yes"},
                {"name": "Business", "price": "$79/mo", "features": "Everything in Team\\nAdvanced permissions\\nDedicated support", "cta_text": "Contact Sales", "highlighted": "no"},
            ]}},
            {"id": "d4", "type": "divider", "data": {"style": "space"}},
            {"id": "faq1", "type": "heading", "data": {"text": "Frequently Asked Questions", "level": "h2", "align": "center"}},
            {"id": "faq2", "type": "faq", "data": {"items": [
                {"q": "Can I cancel anytime?", "a": "Yes — cancel anytime from your billing settings, no questions asked."},
                {"q": "Is there a free trial?", "a": "Yes, 14 days on any paid plan, no card required to start."},
                {"q": "Do you offer discounts for nonprofits?", "a": "Yes — reach out to our team and we'll set you up."},
            ]}},
            {"id": "d5", "type": "divider", "data": {"style": "space"}},
            {"id": "cta1", "type": "heading", "data": {"text": "Ready to get started?", "level": "h2", "align": "center"}},
            {"id": "cta2", "type": "button", "data": {"text": "Create Your Free Account", "url": "", "nav": "next", "style": "primary", "align": "center"}},
            {"id": "foot1", "type": "divider", "data": {"style": "line"}},
            {"id": "foot2", "type": "social_links", "data": {"items": [
                {"platform": "twitter", "url": ""}, {"platform": "linkedin", "url": ""}, {"platform": "instagram", "url": ""},
            ]}},
            {"id": "foot3", "type": "paragraph", "data": {"text": "© 2026 Your Business Name. All rights reserved.", "align": "center"}},
        ],
    },
    "animated_thank_you": {
        "label": "Animated Thank You Page", "category": "Checkout", "page_type": "thank_you",
        "description": "A Thank You page with a real animated checkmark and confetti burst — not a static page.",
        "blocks": [
            {"id": "a1", "type": "custom_html", "data": {"html": """
<style>
@keyframes bzn-pop { 0% { transform: scale(0); opacity: 0; } 60% { transform: scale(1.15); opacity: 1; } 100% { transform: scale(1); } }
@keyframes bzn-confetti-fall { 0% { transform: translateY(-20px) rotate(0deg); opacity: 1; } 100% { transform: translateY(220px) rotate(360deg); opacity: 0; } }
.bzn-check-wrap { display:flex; justify-content:center; margin: 20px 0 10px; position: relative; }
.bzn-check-circle { width: 84px; height: 84px; border-radius: 50%; background: #16a34a; display:flex; align-items:center; justify-content:center; animation: bzn-pop 0.6s cubic-bezier(.26,1.36,.5,1) both; }
.bzn-check-circle svg { width: 42px; height: 42px; stroke: white; stroke-width: 3; fill: none; }
.bzn-confetti { position:absolute; top:-10px; left:50%; width:8px; height:14px; border-radius:2px; }
</style>
<div class="bzn-check-wrap">
  <div class="bzn-check-circle"><svg viewBox="0 0 24 24"><polyline points="4 12 10 18 20 6"></polyline></svg></div>
  <span class="bzn-confetti" style="background:#F2C94C;left:30%;animation:bzn-confetti-fall 1.4s ease-out both;"></span>
  <span class="bzn-confetti" style="background:#EB5757;left:45%;animation:bzn-confetti-fall 1.6s ease-out 0.1s both;"></span>
  <span class="bzn-confetti" style="background:#2D9CDB;left:60%;animation:bzn-confetti-fall 1.3s ease-out 0.2s both;"></span>
  <span class="bzn-confetti" style="background:#9B51E0;left:70%;animation:bzn-confetti-fall 1.5s ease-out 0.15s both;"></span>
</div>
"""}},
            {"id": "a2", "type": "heading", "data": {"text": "You're All Set!", "level": "h1", "align": "center"}},
            {"id": "a3", "type": "paragraph", "data": {"text": "Thanks for your order — check your email for confirmation and next steps.", "align": "center"}},
            {"id": "a4", "type": "divider", "data": {"style": "dots"}},
            {"id": "a5", "type": "social_links", "data": {"items": [
                {"platform": "instagram", "url": ""}, {"platform": "twitter", "url": ""},
            ]}},
        ],
    },

    # ── New templates built on the split-hero / feature-grid / checklist /
    # stat-bar / announcement-bar blocks — same real-block pattern as
    # everything above, styled after common premium course/offer layouts. ──

    "course_split_hero": {
        "label": "Course Sales — Split Hero", "category": "Course", "page_type": "sales",
        "description": "Price-bar header, split hero (copy + video/image), 4-icon feature row, testimonial, FAQ.",
        "blocks": [
            {"id": "c1", "type": "announcement_bar", "data": {"text": "Enrollment open now — save $50 for a limited time.",
                "button_text": "Enroll Now", "button_url": "", "bg_color": "#111111", "text_color": "#ffffff"}},
            {"id": "c2", "type": "hero_split", "data": {
                "eyebrow": "", "heading": "Master The Skill With A Proven, Step-By-Step System",
                "text": "An in-depth course taught by a working expert, built to take you from beginner to confident in weeks, not years.",
                "stat_line": "Over 100,000 students enrolled, 4.5/5 average rating.",
                "button_text": "Enroll Now", "button_url": "", "button_nav": "next",
                "media_type": "video", "video_url": "", "image": "https://picsum.photos/id/1005/900/700", "media_side": "right"}},
            {"id": "c3", "type": "feature_grid", "data": {"heading": "", "columns": "4", "items": [
                {"icon": "play-circle", "title": "Video Lessons", "text": "Hours of focused, densely-packed lessons at your own pace."},
                {"icon": "star", "title": "Full Access License", "text": "Unlock every module the moment you enroll."},
                {"icon": "file-text", "title": "Supporting Materials", "text": "Written summaries, references, and full transcripts."},
                {"icon": "message-circle", "title": "Members Community", "text": "An exclusive space to discuss the material with others."},
            ]}},
            {"id": "c4", "type": "testimonial", "data": {"items": [
                {"quote": "This course paid for itself within the first month.", "name": "Tunde A.", "role": "Student"},
                {"quote": "Clear, practical, and genuinely well taught.", "name": "Grace M.", "role": "Student"},
            ]}},
            {"id": "c5", "type": "faq", "data": {"items": [
                {"q": "How long do I have access?", "a": "Lifetime access, including all future updates."},
                {"q": "Is there a refund policy?", "a": "Yes — 30 days, no questions asked."},
            ]}},
            {"id": "c6", "type": "button", "data": {"text": "Enroll Now", "url": "", "nav": "next", "style": "primary", "align": "center"}},
        ],
    },

    "certification_offer": {
        "label": "Certification / Special Offer", "category": "Course", "page_type": "sales",
        "description": "Split hero with discount + countdown, trust stat bar, feature grid.",
        "blocks": [
            {"id": "e1", "type": "hero_split", "data": {
                "eyebrow": "The Industry's Most Comprehensive Certification",
                "heading": "Become A Certified Expert In Your Field",
                "text": "Turn what you know into a credential that proves it — built by practitioners, not theorists.",
                "stat_line": "", "button_text": "Special Offer — Enroll Now", "button_url": "", "button_nav": "next",
                "media_type": "image", "image": "https://picsum.photos/id/1015/800/800", "media_side": "right"}},
            {"id": "e2", "type": "countdown", "data": {"end_date": "", "label": "Special pricing ends in:"}},
            {"id": "e3", "type": "stat_bar", "data": {"caption": "Trusted by teams at", "items": [
                {"number": "126,000+", "label": "Companies"},
                {"number": "4.8/5", "label": "Average Rating"},
                {"number": "76%", "label": "Avg. Savings vs. Alternatives"},
            ]}},
            {"id": "e4", "type": "feature_grid", "data": {"heading": "What's Included", "columns": "3", "items": [
                {"icon": "book-open", "title": "6 Core Modules", "text": "A complete, structured curriculum you can finish at your pace."},
                {"icon": "badge-check", "title": "Certification", "text": "A shareable credential the moment you complete the program."},
                {"icon": "headphones", "title": "Support", "text": "Direct access to instructors when you get stuck."},
            ]}},
            {"id": "e5", "type": "button", "data": {"text": "Claim Your Spot", "url": "", "nav": "next", "style": "primary", "align": "center"}},
        ],
    },

    "webinar_partner_offer": {
        "label": "Partner / Affiliate Offer", "category": "SaaS", "page_type": "sales",
        "description": "Exclusive-partner-offer layout: split hero with discount pricing, 3-card feature row.",
        "blocks": [
            {"id": "w1", "type": "hero_split", "data": {
                "eyebrow": "Exclusive Partner Offer",
                "heading": "An Exclusive Discount, Just For You",
                "text": "We've teamed up to offer a limited discount on the tool you already trust — plus an extra discount when you pay annually.",
                "stat_line": "", "button_text": "Get Started", "button_url": "", "button_nav": "next",
                "media_type": "image", "image": "https://picsum.photos/id/1027/800/900", "media_side": "right"}},
            {"id": "w2", "type": "feature_grid", "data": {"heading": "Here's What You'll Get", "columns": "3", "items": [
                {"icon": "life-buoy", "title": "Stellar Support", "text": "Our team is on hand around the clock to help you get set up."},
                {"icon": "rocket", "title": "Set Up In Minutes", "text": "Guided onboarding gets you live the same day, not the same month."},
                {"icon": "infinity", "title": "No Limits", "text": "Unlimited usage for as long as your plan is active."},
            ]}},
            {"id": "w3", "type": "button", "data": {"text": "Claim The Discount", "url": "", "nav": "next", "style": "primary", "align": "center"}},
        ],
    },

    "longform_sales_letter": {
        "label": "Long-Form Sales Letter", "category": "Fitness", "page_type": "sales",
        "description": "Classic direct-response layout: eyebrow, big promise headline, pain-point checklist, story, offer.",
        "blocks": [
            {"id": "l1", "type": "container", "data": {
                "eyebrow": "Industry Insider Exposes The Truth",
                "heading": "How Anyone Can Get Better Results In Half The Time",
                "text": "The hidden reason most people never see results — and the simple fix that changes everything.",
                "button_text": "", "button_url": "", "content_align": "center", "min_height": 0}},
            {"id": "l2", "type": "checklist", "data": {"heading": "If you've ever tried this before…", "check_color": "#111111", "items": [
                {"text": "Followed a rigid plan that never fit your life…"},
                {"text": "Put in the work but had little to show for it…"},
                {"text": "Spent more energy managing the process than getting results…"},
            ]}},
            {"id": "l3", "type": "paragraph", "data": {"text": "Then keep reading — because what follows is the exact system that changes the outcome, not just the effort.", "align": "center"}},
            {"id": "l4", "type": "image", "data": {"src": "https://picsum.photos/id/1074/900/600", "alt": ""}},
            {"id": "l5", "type": "checklist", "data": {"heading": "Here's what changes once you have the system:", "check_color": "#16a34a", "items": [
                {"text": "A clear, simple plan you can actually stick to."},
                {"text": "Real progress you can see and measure."},
                {"text": "Less time spent, better results delivered."},
            ]}},
            {"id": "l6", "type": "testimonial", "data": {"items": [
                {"quote": "I wish I'd found this two years ago.", "name": "Bayo O.", "role": "Customer"},
            ]}},
            {"id": "l7", "type": "pricing_table", "data": {"plans": [
                {"name": "The System", "price": "$67", "features": "Full step-by-step system\\nLifetime access\\nBonus quick-start guide", "cta_text": "Get Instant Access", "highlighted": "yes"},
            ]}},
            {"id": "l8", "type": "faq", "data": {"items": [
                {"q": "How fast will I see results?", "a": "Most people notice a difference within the first two weeks of following the system."},
                {"q": "Is there a guarantee?", "a": "Yes — 60 days, full refund, no questions asked."},
            ]}},
        ],
    },

    "seasonal_promo_video": {
        "label": "Seasonal Promo (Video Hero)", "category": "Agency", "page_type": "sales",
        "description": "Colored top bar, centered intro heading, video hero section, single CTA.",
        "blocks": [
            {"id": "s1", "type": "announcement_bar", "data": {"text": "Drive revenue — big revenue — with our seasonal sales playbook.",
                "button_text": "Show Me What's Inside", "button_url": "", "bg_color": "#2D9CDB", "text_color": "#ffffff"}},
            {"id": "s2", "type": "heading", "data": {"text": "Introducing: The Seasonal Sales Playbook", "level": "h2", "align": "center"}},
            {"id": "s3", "type": "paragraph", "data": {"text": "Everything you need to plan and write copy for your next big seasonal campaign.", "align": "center"}},
            {"id": "s4", "type": "video_section", "data": {
                "eyebrow": "", "heading": "Watch The 2-Minute Overview",
                "text": "See exactly what's inside before you decide — no fluff, just the plan.",
                "video_url": "", "button_text": "Join Now", "button_url": "", "media_side": "right"}},
            {"id": "s5", "type": "stat_bar", "data": {"caption": "", "items": [
                {"number": "12,000+", "label": "Marketers Trained"},
                {"number": "4.9/5", "label": "Average Rating"},
            ]}},
            {"id": "s6", "type": "button", "data": {"text": "Join Now", "url": "", "nav": "next", "style": "primary", "align": "center"}},
        ],
    },
}


def get_template(template_id):
    return FUNNEL_TEMPLATES.get(template_id)


def list_templates():
    return [
        {"id": tid, "label": t["label"], "category": t["category"],
         "page_type": t["page_type"], "description": t["description"]}
        for tid, t in FUNNEL_TEMPLATES.items()
    ]
