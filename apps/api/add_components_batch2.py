"""
Adds four new real, functional UI components to the Component Library
(/tools/components), matching the site's existing dark + cyan/purple
premium aesthetic — not stubs, each has working HTML/CSS/JS.
Run once: `python add_components_batch2.py`
"""
from app import create_app
from app.extensions import db
from app.models.components import UIComponent

PRICING_HTML = """<div class="pc-pricing-grid">
  <div class="pc-price-card">
    <div class="pc-price-name">Starter</div>
    <div class="pc-price-amount">$29<span>/mo</span></div>
    <p class="pc-price-desc">For small projects just getting going.</p>
    <ul class="pc-price-features">
      <li>1 project</li><li>Email support</li><li>Basic analytics</li>
    </ul>
    <button class="pc-price-btn">Get Started</button>
  </div>
  <div class="pc-price-card pc-price-featured">
    <div class="pc-price-badge">Most Popular</div>
    <div class="pc-price-name">Pro</div>
    <div class="pc-price-amount">$79<span>/mo</span></div>
    <p class="pc-price-desc">For growing teams that need more room.</p>
    <ul class="pc-price-features">
      <li>10 projects</li><li>Priority support</li><li>Advanced analytics</li><li>Automation Studio</li>
    </ul>
    <button class="pc-price-btn pc-price-btn-primary">Get Started</button>
  </div>
  <div class="pc-price-card">
    <div class="pc-price-name">Enterprise</div>
    <div class="pc-price-amount">Custom</div>
    <p class="pc-price-desc">For organizations with specific needs.</p>
    <ul class="pc-price-features">
      <li>Unlimited projects</li><li>Dedicated support</li><li>Custom integrations</li>
    </ul>
    <button class="pc-price-btn">Contact Sales</button>
  </div>
</div>"""

PRICING_CSS = """.pc-pricing-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:24px; padding:20px; }
.pc-price-card { background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:16px; padding:28px 24px; position:relative; transition:transform .2s ease, border-color .2s ease; }
.pc-price-card:hover { transform:translateY(-4px); border-color:rgba(0,245,255,0.3); }
.pc-price-featured { border-color:#00f5ff; background:linear-gradient(180deg, rgba(0,245,255,0.06), rgba(191,0,255,0.03)); }
.pc-price-badge { position:absolute; top:-12px; left:50%; transform:translateX(-50%); background:linear-gradient(90deg,#00f5ff,#bf00ff); color:#04060d; font-size:11px; font-weight:800; padding:4px 14px; border-radius:999px; text-transform:uppercase; letter-spacing:.05em; }
.pc-price-name { font-size:14px; font-weight:700; color:#8E8E93; text-transform:uppercase; letter-spacing:.05em; margin-bottom:12px; }
.pc-price-amount { font-size:36px; font-weight:800; color:#fff; margin-bottom:8px; }
.pc-price-amount span { font-size:14px; font-weight:500; color:#8E8E93; }
.pc-price-desc { font-size:13px; color:#8E8E93; margin-bottom:20px; line-height:1.5; }
.pc-price-features { list-style:none; padding:0; margin:0 0 24px; }
.pc-price-features li { font-size:13px; color:#c9c9cf; padding:8px 0; border-top:1px solid rgba(255,255,255,0.06); }
.pc-price-features li:before { content:"✓ "; color:#00f5ff; font-weight:700; }
.pc-price-btn { width:100%; padding:11px; border-radius:10px; border:1px solid rgba(255,255,255,0.15); background:transparent; color:#fff; font-weight:600; font-size:13px; cursor:pointer; transition:all .15s ease; }
.pc-price-btn:hover { background:rgba(255,255,255,0.08); }
.pc-price-btn-primary { background:linear-gradient(90deg,#00f5ff,#bf00ff); border:none; color:#04060d; }
.pc-price-btn-primary:hover { opacity:.9; }"""

ACCORDION_HTML = """<div class="pc-accordion">
  <div class="pc-accordion-item">
    <button class="pc-accordion-trigger" onclick="pcToggleAccordion(this)">
      <span>How long does a typical project take?</span>
      <span class="pc-accordion-icon">+</span>
    </button>
    <div class="pc-accordion-panel"><p>Most projects take 2-6 weeks depending on scope — I'll give you a real timeline after our first call, not a generic estimate.</p></div>
  </div>
  <div class="pc-accordion-item">
    <button class="pc-accordion-trigger" onclick="pcToggleAccordion(this)">
      <span>Do you offer ongoing support after launch?</span>
      <span class="pc-accordion-icon">+</span>
    </button>
    <div class="pc-accordion-panel"><p>Yes — monthly maintenance plans are available, or you can reach out ad-hoc whenever something needs attention.</p></div>
  </div>
  <div class="pc-accordion-item">
    <button class="pc-accordion-trigger" onclick="pcToggleAccordion(this)">
      <span>What's your payment structure?</span>
      <span class="pc-accordion-icon">+</span>
    </button>
    <div class="pc-accordion-panel"><p>Full payment upfront, a 50/50 split, or pay-after-delivery — you choose what works when you accept a proposal.</p></div>
  </div>
</div>"""

ACCORDION_CSS = """.pc-accordion { max-width:640px; margin:0 auto; padding:20px; }
.pc-accordion-item { border-bottom:1px solid rgba(255,255,255,0.08); }
.pc-accordion-trigger { width:100%; display:flex; justify-content:space-between; align-items:center; background:none; border:none; padding:18px 4px; color:#fff; font-size:15px; font-weight:600; text-align:left; cursor:pointer; }
.pc-accordion-icon { font-size:20px; color:#00f5ff; transition:transform .2s ease; flex-shrink:0; margin-left:16px; }
.pc-accordion-item.pc-open .pc-accordion-icon { transform:rotate(45deg); }
.pc-accordion-panel { max-height:0; overflow:hidden; transition:max-height .25s ease; }
.pc-accordion-item.pc-open .pc-accordion-panel { max-height:200px; }
.pc-accordion-panel p { padding:0 4px 18px; color:#8E8E93; font-size:13px; line-height:1.6; margin:0; }"""

ACCORDION_JS = """function pcToggleAccordion(btn) {
  const item = btn.closest('.pc-accordion-item');
  const wasOpen = item.classList.contains('pc-open');
  item.parentElement.querySelectorAll('.pc-accordion-item').forEach(i => i.classList.remove('pc-open'));
  if (!wasOpen) item.classList.add('pc-open');
}"""

TOAST_HTML = """<button class="pc-toast-demo-btn" onclick="pcShowToast('Changes saved successfully!', 'success')">Trigger Success Toast</button>
<button class="pc-toast-demo-btn pc-toast-demo-danger" onclick="pcShowToast('Something went wrong.', 'error')">Trigger Error Toast</button>
<div id="pc-toast-root"></div>"""

TOAST_CSS = """.pc-toast-demo-btn { padding:10px 20px; border-radius:10px; border:1px solid rgba(255,255,255,0.15); background:rgba(255,255,255,0.05); color:#fff; font-weight:600; font-size:13px; cursor:pointer; margin-right:10px; }
.pc-toast-demo-danger { border-color:rgba(248,113,113,0.3); }
.pc-toast { position:fixed; bottom:24px; right:24px; background:#111214; border:1px solid rgba(255,255,255,0.1); border-radius:12px; padding:14px 18px; color:#fff; font-size:13px; font-weight:600; box-shadow:0 10px 40px rgba(0,0,0,0.4); display:flex; align-items:center; gap:10px; transform:translateY(20px); opacity:0; transition:all .25s ease; z-index:9999; }
.pc-toast.pc-toast-show { transform:translateY(0); opacity:1; }
.pc-toast-success { border-left:3px solid #1db954; }
.pc-toast-error { border-left:3px solid #f87171; }"""

TOAST_JS = """function pcShowToast(message, type) {
  const root = document.getElementById('pc-toast-root');
  const el = document.createElement('div');
  el.className = 'pc-toast pc-toast-' + type;
  el.textContent = (type === 'success' ? '✓ ' : '✕ ') + message;
  root.appendChild(el);
  requestAnimationFrame(() => el.classList.add('pc-toast-show'));
  setTimeout(() => {
    el.classList.remove('pc-toast-show');
    setTimeout(() => el.remove(), 300);
  }, 3000);
}"""

MODAL_HTML = """<button class="pc-modal-open-btn" onclick="document.getElementById('pc-demo-modal').classList.add('pc-modal-show')">Open Modal</button>
<div id="pc-demo-modal" class="pc-modal-overlay" onclick="if(event.target===this) this.classList.remove('pc-modal-show')">
  <div class="pc-modal-box">
    <button class="pc-modal-close" onclick="document.getElementById('pc-demo-modal').classList.remove('pc-modal-show')">×</button>
    <h3 class="pc-modal-title">Confirm Action</h3>
    <p class="pc-modal-body">Are you sure you want to proceed? This can't be undone.</p>
    <div class="pc-modal-actions">
      <button class="pc-modal-btn-ghost" onclick="document.getElementById('pc-demo-modal').classList.remove('pc-modal-show')">Cancel</button>
      <button class="pc-modal-btn-primary" onclick="document.getElementById('pc-demo-modal').classList.remove('pc-modal-show')">Confirm</button>
    </div>
  </div>
</div>"""

MODAL_CSS = """.pc-modal-open-btn { padding:10px 22px; border-radius:10px; border:none; background:linear-gradient(90deg,#00f5ff,#bf00ff); color:#04060d; font-weight:700; font-size:13px; cursor:pointer; }
.pc-modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.65); backdrop-filter:blur(4px); display:none; align-items:center; justify-content:center; z-index:9998; padding:20px; }
.pc-modal-overlay.pc-modal-show { display:flex; }
.pc-modal-box { background:#111214; border:1px solid rgba(255,255,255,0.08); border-radius:16px; padding:28px; max-width:400px; width:100%; position:relative; box-shadow:0 20px 60px rgba(0,0,0,0.5); }
.pc-modal-close { position:absolute; top:14px; right:14px; background:none; border:none; color:#8E8E93; font-size:22px; cursor:pointer; line-height:1; }
.pc-modal-title { color:#fff; font-size:18px; font-weight:800; margin:0 0 10px; }
.pc-modal-body { color:#8E8E93; font-size:13px; line-height:1.6; margin:0 0 22px; }
.pc-modal-actions { display:flex; gap:10px; justify-content:flex-end; }
.pc-modal-btn-ghost { padding:9px 18px; border-radius:8px; border:1px solid rgba(255,255,255,0.15); background:transparent; color:#fff; font-size:13px; font-weight:600; cursor:pointer; }
.pc-modal-btn-primary { padding:9px 18px; border-radius:8px; border:none; background:linear-gradient(90deg,#00f5ff,#bf00ff); color:#04060d; font-size:13px; font-weight:700; cursor:pointer; }"""


def add_component(name, category, description, html_code, css_code="", js_code="", tags=None, featured=False, order=0):
    existing = UIComponent.query.filter_by(name=name).first()
    if existing:
        print(f"⏭️  '{name}' already exists, skipping.")
        return
    db.session.add(UIComponent(
        name=name, category=category, description=description,
        html_code=html_code, css_code=css_code, js_code=js_code,
        tags=tags or [], featured=featured, active=True, order=order,
    ))
    print(f"➕ Added: {name}")


def main():
    app = create_app()
    with app.app_context():
        db.create_all()
        add_component("Pricing Table", "Pricing", "Three-tier pricing grid with a highlighted 'most popular' plan.",
                       PRICING_HTML, PRICING_CSS, tags=["pricing", "cards"], featured=True, order=10)
        add_component("FAQ Accordion", "Accordion", "Expand/collapse FAQ list, one item open at a time.",
                       ACCORDION_HTML, ACCORDION_CSS, ACCORDION_JS, tags=["faq", "accordion"], order=11)
        add_component("Toast Notification", "Feedback", "Auto-dismissing success/error toast, slides in from the corner.",
                       TOAST_HTML, TOAST_CSS, TOAST_JS, tags=["toast", "notification"], order=12)
        add_component("Confirmation Modal", "Modal", "Dialog overlay with confirm/cancel actions, click-outside-to-close.",
                       MODAL_HTML, MODAL_CSS, tags=["modal", "dialog"], order=13)
        db.session.commit()
        print("\n✅ Batch 2 components added. Visit /tools/components or /admin/ui-components to see them.")


if __name__ == "__main__":
    main()
