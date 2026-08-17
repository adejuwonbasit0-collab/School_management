"""
Seeds 21 additional UI components (on top of the 9 from seed_components.py
and add_components.py, for 30 total). Run with: python -m scripts.seed_ui_components

All components use the site's existing dark/neon design language
(cyan #00f5ff / purple #bf00ff gradients, glass surfaces) so anything
copied from the library matches the rest of the site out of the box.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import db
from app.models.components import UIComponent

COMPONENTS = [
    dict(name="Button – Outline Glow", category="Buttons", tags=["button", "outline"],
         description="Ghost button with a neon border that glows on hover.",
         html_code='<button class="btn-outline-glow">Explore</button>',
         css_code='.btn-outline-glow{padding:12px 28px;border-radius:9999px;background:transparent;border:2px solid #00f5ff;color:#00f5ff;font-weight:700;cursor:pointer;transition:.2s}\n.btn-outline-glow:hover{background:#00f5ff;color:#000;box-shadow:0 0 24px rgba(0,245,255,.5)}'),

    dict(name="Button – Icon Loading", category="Buttons", tags=["button", "loading"],
         description="Button that swaps to a spinner on click.",
         html_code='<button class="btn-load" onclick="this.classList.add(\'loading\')"><span class="txt">Submit</span><span class="spin"></span></button>',
         css_code='.btn-load{position:relative;padding:12px 28px;border-radius:10px;background:linear-gradient(135deg,#00f5ff,#bf00ff);border:none;color:#000;font-weight:700;cursor:pointer}\n.btn-load .spin{display:none;width:16px;height:16px;border:2px solid #000;border-top-color:transparent;border-radius:50%;animation:sp .6s linear infinite}\n.btn-load.loading .txt{display:none}\n.btn-load.loading .spin{display:inline-block}\n@keyframes sp{to{transform:rotate(360deg)}}'),

    dict(name="Card – Pricing", category="Cards", tags=["pricing", "card"], featured=True,
         description="Single pricing tier card with feature list.",
         html_code='<div class="price-card"><h3>Pro</h3><div class="p">$29<span>/mo</span></div><ul><li>Unlimited projects</li><li>Priority support</li></ul><button>Choose</button></div>',
         css_code='.price-card{background:#12141c;border:1px solid rgba(255,255,255,.1);border-radius:16px;padding:28px;width:240px;color:#fff;font-family:sans-serif}\n.price-card h3{margin:0 0 8px}\n.price-card .p{font-size:2.2rem;font-weight:700;margin-bottom:14px}\n.price-card .p span{font-size:.9rem;color:#8899b0}\n.price-card ul{list-style:none;padding:0;margin:0 0 20px;color:#8899b0;font-size:13px;display:flex;flex-direction:column;gap:6px}\n.price-card button{width:100%;padding:10px;border-radius:8px;border:none;background:#00f5ff;font-weight:700;cursor:pointer}'),

    dict(name="Card – Profile", category="Cards", tags=["profile", "avatar"],
         description="User profile card with avatar and stats.",
         html_code='<div class="profile-card"><div class="av">JD</div><h4>Jane Doe</h4><p>Product Designer</p><div class="stats"><span>1.2k Followers</span><span>340 Following</span></div></div>',
         css_code='.profile-card{background:#12141c;border:1px solid rgba(255,255,255,.1);border-radius:16px;padding:24px;width:220px;text-align:center;color:#fff;font-family:sans-serif}\n.profile-card .av{width:56px;height:56px;border-radius:50%;background:linear-gradient(135deg,#00f5ff,#bf00ff);display:flex;align-items:center;justify-content:center;font-weight:700;color:#000;margin:0 auto 12px}\n.profile-card p{color:#8899b0;font-size:13px;margin:2px 0 14px}\n.profile-card .stats{display:flex;justify-content:space-around;font-size:11px;color:#6b7a9a;border-top:1px solid rgba(255,255,255,.08);padding-top:12px}'),

    dict(name="Badge – Status", category="Badges", tags=["badge", "status"],
         description="Small colored status pill (success/warning/error).",
         html_code='<span class="badge success">Active</span> <span class="badge warn">Pending</span> <span class="badge err">Failed</span>',
         css_code='.badge{display:inline-block;padding:3px 10px;border-radius:9999px;font-size:11px;font-weight:700;font-family:sans-serif}\n.badge.success{background:rgba(74,222,128,.15);color:#4ade80}\n.badge.warn{background:rgba(250,204,21,.15);color:#facc15}\n.badge.err{background:rgba(248,113,113,.15);color:#f87171}'),

    dict(name="Alert – Banner", category="Alerts", tags=["alert", "banner"],
         description="Dismissible alert banner with icon.",
         html_code='<div class="alert" id="a1"><span>⚠️ Your trial ends in 3 days.</span><button onclick="document.getElementById(\'a1\').remove()">✕</button></div>',
         css_code='.alert{display:flex;justify-content:space-between;align-items:center;background:rgba(250,204,21,.08);border:1px solid rgba(250,204,21,.3);color:#facc15;padding:12px 16px;border-radius:10px;font-family:sans-serif;font-size:13px}\n.alert button{background:none;border:none;color:inherit;cursor:pointer;font-size:14px}'),

    dict(name="Toast – Notification", category="Alerts", tags=["toast", "notification"],
         description="Bottom-corner toast notification with auto style.",
         html_code='<div class="toast"><span class="dot"></span><div><strong>Saved!</strong><p>Your changes have been saved.</p></div></div>',
         css_code='.toast{display:flex;gap:12px;align-items:start;background:#12141c;border:1px solid rgba(255,255,255,.1);border-radius:12px;padding:14px 16px;width:260px;font-family:sans-serif;box-shadow:0 10px 30px rgba(0,0,0,.4)}\n.toast .dot{width:8px;height:8px;border-radius:50%;background:#4ade80;margin-top:5px;flex-shrink:0}\n.toast strong{color:#fff;font-size:13px}\n.toast p{color:#8899b0;font-size:12px;margin:2px 0 0}'),

    dict(name="Navbar – Glass", category="Navigation", tags=["navbar", "glass"], featured=True,
         description="Sticky translucent navbar with blur backdrop.",
         html_code='<nav class="nav-glass"><span class="brand">Brand</span><div class="links"><a href="#">Home</a><a href="#">Docs</a><a href="#">Pricing</a></div></nav>',
         css_code='.nav-glass{display:flex;justify-content:space-between;align-items:center;padding:14px 24px;background:rgba(18,20,28,.6);backdrop-filter:blur(12px);border-bottom:1px solid rgba(255,255,255,.08);font-family:sans-serif}\n.nav-glass .brand{color:#fff;font-weight:800}\n.nav-glass .links{display:flex;gap:20px}\n.nav-glass a{color:#8899b0;text-decoration:none;font-size:14px}\n.nav-glass a:hover{color:#00f5ff}'),

    dict(name="Breadcrumbs", category="Navigation", tags=["breadcrumb"],
         description="Simple breadcrumb trail.",
         html_code='<div class="crumbs"><a href="#">Home</a><span>/</span><a href="#">Projects</a><span>/</span><span class="cur">Settings</span></div>',
         css_code='.crumbs{display:flex;gap:8px;align-items:center;font-family:sans-serif;font-size:13px}\n.crumbs a{color:#8899b0;text-decoration:none}\n.crumbs a:hover{color:#00f5ff}\n.crumbs span{color:#4a5568}\n.crumbs .cur{color:#fff}'),

    dict(name="Pagination", category="Navigation", tags=["pagination"],
         description="Numbered pagination with prev/next.",
         html_code='<div class="pag"><button>‹</button><button class="active">1</button><button>2</button><button>3</button><button>›</button></div>',
         css_code='.pag{display:flex;gap:6px;font-family:sans-serif}\n.pag button{width:32px;height:32px;border-radius:8px;border:1px solid rgba(255,255,255,.1);background:rgba(255,255,255,.03);color:#8899b0;cursor:pointer}\n.pag button.active{background:#00f5ff;color:#000;border-color:#00f5ff;font-weight:700}'),

    dict(name="Tabs – Underline", category="Navigation", tags=["tabs"],
         description="Simple underline-style tab switcher.",
         html_code='<div class="tabs"><button class="tab active" onclick="sw(this,0)">Overview</button><button class="tab" onclick="sw(this,1)">Details</button><button class="tab" onclick="sw(this,2)">Reviews</button></div>',
         css_code='.tabs{display:flex;gap:4px;border-bottom:1px solid rgba(255,255,255,.1);font-family:sans-serif}\n.tab{background:none;border:none;color:#8899b0;padding:10px 16px;cursor:pointer;border-bottom:2px solid transparent;font-size:13px}\n.tab.active{color:#00f5ff;border-color:#00f5ff}',
         js_code='function sw(el){document.querySelectorAll(".tab").forEach(t=>t.classList.remove("active"));el.classList.add("active")}'),

    dict(name="Accordion", category="Navigation", tags=["accordion", "faq"],
         description="Collapsible FAQ-style accordion item.",
         html_code='<div class="acc"><button class="acc-h" onclick="this.parentElement.classList.toggle(\'open\')">What is this? <span>+</span></button><div class="acc-b">A collapsible content panel for FAQs.</div></div>',
         css_code='.acc{background:#12141c;border:1px solid rgba(255,255,255,.1);border-radius:10px;overflow:hidden;width:280px;font-family:sans-serif}\n.acc-h{width:100%;text-align:left;background:none;border:none;color:#fff;padding:14px 16px;cursor:pointer;display:flex;justify-content:space-between;font-size:13px}\n.acc-b{max-height:0;overflow:hidden;padding:0 16px;color:#8899b0;font-size:12px;transition:.25s}\n.acc.open .acc-b{max-height:100px;padding:0 16px 14px}'),

    dict(name="Modal – Glass", category="Overlays", tags=["modal", "dialog"],
         description="Centered modal dialog with backdrop blur.",
         html_code='<button onclick="document.getElementById(\'m1\').style.display=\'flex\'">Open Modal</button><div id="m1" class="modal-bg"><div class="modal-box"><h3>Confirm Action</h3><p>Are you sure you want to continue?</p><div class="row"><button onclick="document.getElementById(\'m1\').style.display=\'none\'">Cancel</button><button class="ok">Confirm</button></div></div></div>',
         css_code='.modal-bg{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);backdrop-filter:blur(4px);align-items:center;justify-content:center;font-family:sans-serif}\n.modal-box{background:#12141c;border:1px solid rgba(255,255,255,.1);border-radius:16px;padding:24px;width:280px;color:#fff}\n.modal-box p{color:#8899b0;font-size:13px}\n.modal-box .row{display:flex;gap:10px;margin-top:16px}\n.modal-box button{flex:1;padding:10px;border-radius:8px;border:1px solid rgba(255,255,255,.1);background:rgba(255,255,255,.05);color:#fff;cursor:pointer}\n.modal-box .ok{background:#00f5ff;color:#000;border:none;font-weight:700}'),

    dict(name="Tooltip", category="Overlays", tags=["tooltip"],
         description="Hover tooltip on any element.",
         html_code='<span class="tip">Hover me<span class="tip-txt">Helpful hint here</span></span>',
         css_code='.tip{position:relative;color:#00f5ff;font-family:sans-serif;font-size:13px;cursor:help;border-bottom:1px dashed #00f5ff}\n.tip .tip-txt{visibility:hidden;position:absolute;bottom:130%;left:50%;transform:translateX(-50%);background:#12141c;border:1px solid rgba(255,255,255,.1);color:#fff;padding:6px 10px;border-radius:6px;font-size:11px;white-space:nowrap}\n.tip:hover .tip-txt{visibility:visible}'),

    dict(name="Dropdown Menu", category="Overlays", tags=["dropdown", "menu"],
         description="Click-triggered dropdown menu.",
         html_code='<div class="dd"><button onclick="this.nextElementSibling.classList.toggle(\'show\')">Options ▾</button><div class="dd-menu"><a href="#">Edit</a><a href="#">Duplicate</a><a href="#">Delete</a></div></div>',
         css_code='.dd{position:relative;display:inline-block;font-family:sans-serif}\n.dd>button{padding:10px 16px;border-radius:8px;border:1px solid rgba(255,255,255,.1);background:rgba(255,255,255,.05);color:#fff;cursor:pointer}\n.dd-menu{display:none;position:absolute;top:110%;left:0;background:#12141c;border:1px solid rgba(255,255,255,.1);border-radius:10px;min-width:140px;overflow:hidden;z-index:10}\n.dd-menu.show{display:block}\n.dd-menu a{display:block;padding:10px 14px;color:#8899b0;text-decoration:none;font-size:13px}\n.dd-menu a:hover{background:rgba(255,255,255,.05);color:#fff}'),

    dict(name="Progress Bar", category="Feedback", tags=["progress"],
         description="Gradient progress bar with percentage label.",
         html_code='<div class="prog-wrap"><div class="prog" style="width:68%"></div></div><span class="prog-label">68%</span>',
         css_code='.prog-wrap{width:220px;height:8px;background:rgba(255,255,255,.08);border-radius:9999px;overflow:hidden}\n.prog{height:100%;background:linear-gradient(90deg,#00f5ff,#bf00ff);border-radius:9999px}\n.prog-label{font-family:sans-serif;font-size:11px;color:#8899b0;margin-left:8px}'),

    dict(name="Spinner – Ring", category="Feedback", tags=["loader", "spinner"],
         description="Simple rotating ring loader.",
         html_code='<div class="ring"></div>',
         css_code='.ring{width:36px;height:36px;border:3px solid rgba(255,255,255,.1);border-top-color:#00f5ff;border-radius:50%;animation:ringspin .8s linear infinite}\n@keyframes ringspin{to{transform:rotate(360deg)}}'),

    dict(name="Skeleton Loader", category="Feedback", tags=["skeleton", "loading"],
         description="Shimmering placeholder for loading content.",
         html_code='<div class="skel-row"><div class="skel-avatar"></div><div class="skel-lines"><div class="skel-line" style="width:60%"></div><div class="skel-line" style="width:40%"></div></div></div>',
         css_code='.skel-row{display:flex;gap:12px;align-items:center}\n.skel-avatar{width:44px;height:44px;border-radius:50%;background:linear-gradient(90deg,#1a1f2e 25%,#242938 37%,#1a1f2e 63%);background-size:400% 100%;animation:shim 1.4s ease infinite}\n.skel-lines{flex:1;display:flex;flex-direction:column;gap:8px}\n.skel-line{height:10px;border-radius:4px;background:linear-gradient(90deg,#1a1f2e 25%,#242938 37%,#1a1f2e 63%);background-size:400% 100%;animation:shim 1.4s ease infinite}\n@keyframes shim{0%{background-position:100% 50%}100%{background-position:0 50%}}'),

    dict(name="Toggle Switch", category="Forms", tags=["toggle", "switch"],
         description="iOS-style animated toggle switch.",
         html_code='<label class="switch"><input type="checkbox"/><span class="slider"></span></label>',
         css_code='.switch{position:relative;display:inline-block;width:44px;height:24px}\n.switch input{opacity:0;width:0;height:0}\n.slider{position:absolute;inset:0;background:rgba(255,255,255,.15);border-radius:9999px;cursor:pointer;transition:.2s}\n.slider:before{content:"";position:absolute;width:18px;height:18px;left:3px;top:3px;background:#fff;border-radius:50%;transition:.2s}\ninput:checked+.slider{background:#00f5ff}\ninput:checked+.slider:before{transform:translateX(20px)}'),

    dict(name="Input – Floating Label", category="Forms", tags=["input", "form"],
         description="Text input with a floating label animation.",
         html_code='<div class="float-field"><input type="text" placeholder=" " id="fl1"/><label for="fl1">Email address</label></div>',
         css_code='.float-field{position:relative;width:220px}\n.float-field input{width:100%;padding:16px 12px 6px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);border-radius:10px;color:#fff;font-family:sans-serif}\n.float-field label{position:absolute;left:12px;top:14px;color:#6b7a9a;font-size:14px;pointer-events:none;transition:.15s}\n.float-field input:focus+label,.float-field input:not(:placeholder-shown)+label{top:6px;font-size:10px;color:#00f5ff}\n.float-field input:focus{outline:none;border-color:#00f5ff}'),

    dict(name="Search Bar", category="Forms", tags=["search", "input"],
         description="Rounded search input with icon.",
         html_code='<div class="search"><span>🔍</span><input type="text" placeholder="Search…"/></div>',
         css_code='.search{display:flex;align-items:center;gap:8px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);border-radius:9999px;padding:10px 16px;width:220px}\n.search input{background:none;border:none;outline:none;color:#fff;font-family:sans-serif;font-size:13px;width:100%}'),

    dict(name="Testimonial Card", category="Cards", tags=["testimonial", "quote"], featured=True,
         description="Quote card with avatar and star rating.",
         html_code='<div class="testi"><div class="stars">★★★★★</div><p>"This platform saved me weeks of work — incredible."</p><div class="who"><div class="av">MK</div><div><strong>Maria K.</strong><span>Founder, Studio Co.</span></div></div></div>',
         css_code='.testi{background:#12141c;border:1px solid rgba(255,255,255,.1);border-radius:16px;padding:24px;width:280px;font-family:sans-serif;color:#fff}\n.testi .stars{color:#facc15;font-size:14px;margin-bottom:10px}\n.testi p{color:#c5cee0;font-size:13px;line-height:1.6;margin-bottom:16px}\n.testi .who{display:flex;align-items:center;gap:10px}\n.testi .av{width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#00f5ff,#bf00ff);display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#000}\n.testi strong{display:block;font-size:13px}\n.testi span{color:#6b7a9a;font-size:11px}'),

    dict(name="Footer – Minimal", category="Layout", tags=["footer"],
         description="Simple two-column footer.",
         html_code='<footer class="ftr"><span>© 2026 Brand Inc.</span><div class="links"><a href="#">Privacy</a><a href="#">Terms</a><a href="#">Contact</a></div></footer>',
         css_code='.ftr{display:flex;justify-content:space-between;align-items:center;padding:20px 24px;border-top:1px solid rgba(255,255,255,.08);font-family:sans-serif;font-size:12px;color:#6b7a9a}\n.ftr .links{display:flex;gap:16px}\n.ftr a{color:#6b7a9a;text-decoration:none}\n.ftr a:hover{color:#00f5ff}'),
]


def run():
    app = create_app("development")
    with app.app_context():
        added, updated = 0, 0
        for i, data in enumerate(COMPONENTS):
            existing = UIComponent.query.filter_by(name=data["name"]).first()
            if existing:
                existing.active = True
                updated += 1
                print(f"~ Already exists: {data['name']}")
                continue
            db.session.add(UIComponent(
                name=data["name"], category=data["category"],
                description=data.get("description", ""),
                html_code=data["html_code"], css_code=data.get("css_code", ""),
                js_code=data.get("js_code", ""), tags=data.get("tags", []),
                featured=data.get("featured", False), active=True, order=i,
            ))
            added += 1
            print(f"+ Added: {data['name']}")
        db.session.commit()
        total = UIComponent.query.count()
        print(f"\nDone — {added} added, {updated} already present. {total} total components in the library.")


if __name__ == "__main__":
    run()
