"""
Batch 3 of UI components — directly addressing what was asked for:
a light-themed hero, a second dark hero variant, a real "Animation"
category (not folded into other categories), a video/media showcase
card, and a responsive iframe embed. Styled the same way the original
seed set is (Tailwind utility classes), not the standalone-CSS style of
batch 2, since these are meant to slot into the site's existing pages.
Run once: `python add_components_batch3.py`
"""
from app import create_app
from app.extensions import db
from app.models.components import UIComponent

HERO_LIGHT_HTML = """<section class="relative min-h-screen flex items-center justify-center overflow-hidden bg-white w-full">
  <div class="absolute inset-0 bg-[linear-gradient(to_right,#00000006_1px,transparent_1px),linear-gradient(to_bottom,#00000006_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_80%_50%_at_50%_50%,black,transparent)]"></div>
  <div class="absolute top-1/4 left-1/4 w-72 h-72 bg-cyan-300/30 rounded-full blur-3xl"></div>
  <div class="absolute bottom-1/4 right-1/4 w-72 h-72 bg-purple-300/30 rounded-full blur-3xl"></div>
  <div class="relative z-10 max-w-5xl mx-auto text-center px-4">
    <span class="inline-block px-4 py-1.5 rounded-full bg-gray-100 border border-gray-200 text-gray-600 text-xs font-semibold mb-6">✨ Now booking new projects</span>
    <h1 class="text-5xl md:text-7xl font-bold text-gray-900 mb-6">Design That Feels <span class="bg-gradient-to-r from-cyan-500 to-purple-600 bg-clip-text text-transparent">Effortless</span></h1>
    <p class="text-xl md:text-2xl text-gray-500 max-w-3xl mx-auto mb-8">Clean, fast, and built to convert — websites and products for teams who care about the details.</p>
    <div class="flex flex-wrap justify-center gap-4">
      <a href="#" class="px-8 py-3.5 rounded-xl bg-gray-900 text-white font-semibold hover:bg-gray-800 transition-colors">Start a Project</a>
      <a href="#" class="px-8 py-3.5 rounded-xl border border-gray-300 text-gray-700 font-semibold hover:bg-gray-50 transition-colors">View Work</a>
    </div>
  </div>
</section>"""

HERO_MESH_HTML = """<section class="relative min-h-screen flex items-center justify-center overflow-hidden bg-[#050507] w-full">
  <div class="absolute inset-0 opacity-60" style="background:radial-gradient(circle at 20% 20%, #00f5ff33, transparent 40%), radial-gradient(circle at 80% 30%, #bf00ff33, transparent 40%), radial-gradient(circle at 50% 80%, #1db95433, transparent 40%)"></div>
  <div class="relative z-10 max-w-5xl mx-auto text-center px-4">
    <div class="flex justify-center gap-2 mb-6">
      <span class="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
      <span class="text-xs uppercase tracking-widest text-gray-400">Available for freelance</span>
    </div>
    <h1 class="text-5xl md:text-7xl font-bold text-white mb-6 leading-tight">Ship Products People <br/><span class="bg-gradient-to-r from-cyan-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">Actually Love</span></h1>
    <p class="text-xl text-gray-400 max-w-2xl mx-auto mb-10">Full-stack builds, real automation, and interfaces that don't feel like templates.</p>
    <div class="flex flex-wrap justify-center gap-4">
      <a href="#" class="px-8 py-3.5 rounded-xl bg-gradient-to-r from-cyan-400 to-purple-500 text-black font-bold hover:opacity-90 transition-opacity">Get Started →</a>
      <a href="#" class="px-8 py-3.5 rounded-xl border border-white/15 text-white font-semibold hover:bg-white/5 transition-colors">See Case Studies</a>
    </div>
  </div>
</section>"""

ANIM_BLOB_HTML = """<div class="relative h-96 w-full overflow-hidden rounded-2xl bg-[#0a0a0f] flex items-center justify-center">
  <div class="blob-anim blob-1"></div>
  <div class="blob-anim blob-2"></div>
  <div class="blob-anim blob-3"></div>
  <p class="relative z-10 text-white text-2xl font-bold">Content sits on top of this</p>
</div>"""

ANIM_BLOB_CSS = """.blob-anim { position:absolute; border-radius:50%; filter:blur(60px); opacity:0.5; }
.blob-1 { width:280px; height:280px; background:#00f5ff; top:-60px; left:-40px; animation: blobMove1 9s ease-in-out infinite; }
.blob-2 { width:320px; height:320px; background:#bf00ff; bottom:-80px; right:-60px; animation: blobMove2 11s ease-in-out infinite; }
.blob-3 { width:220px; height:220px; background:#1db954; top:40%; left:40%; animation: blobMove3 13s ease-in-out infinite; }
@keyframes blobMove1 { 0%,100% { transform:translate(0,0) scale(1); } 50% { transform:translate(60px,40px) scale(1.15); } }
@keyframes blobMove2 { 0%,100% { transform:translate(0,0) scale(1); } 50% { transform:translate(-50px,-30px) scale(1.1); } }
@keyframes blobMove3 { 0%,100% { transform:translate(0,0) scale(1); } 50% { transform:translate(30px,-50px) scale(0.9); } }"""

ANIM_MARQUEE_HTML = """<div class="py-10 bg-[#0a0a0f] overflow-hidden">
  <div class="flex gap-16 whitespace-nowrap anim-marquee-track">
    <div class="flex gap-16 items-center flex-shrink-0">
      <span class="text-2xl font-bold text-gray-600">ACME</span>
      <span class="text-2xl font-bold text-gray-600">Globex</span>
      <span class="text-2xl font-bold text-gray-600">Initech</span>
      <span class="text-2xl font-bold text-gray-600">Umbrella</span>
      <span class="text-2xl font-bold text-gray-600">Soylent</span>
    </div>
    <div class="flex gap-16 items-center flex-shrink-0">
      <span class="text-2xl font-bold text-gray-600">ACME</span>
      <span class="text-2xl font-bold text-gray-600">Globex</span>
      <span class="text-2xl font-bold text-gray-600">Initech</span>
      <span class="text-2xl font-bold text-gray-600">Umbrella</span>
      <span class="text-2xl font-bold text-gray-600">Soylent</span>
    </div>
  </div>
</div>"""

ANIM_MARQUEE_CSS = """.anim-marquee-track { display:inline-flex; animation: animMarquee 25s linear infinite; }
@keyframes animMarquee { 0% { transform:translateX(0); } 100% { transform:translateX(-50%); } }"""

VIDEO_SHOWCASE_HTML = """<div class="video-showcase-card" onclick="this.classList.add('video-playing')">
  <img src="https://images.unsplash.com/photo-1551650975-87deedd944c3?w=800&q=60" alt="Video thumbnail" class="video-thumb"/>
  <button class="video-play-btn" aria-label="Play video">
    <svg width="28" height="28" viewBox="0 0 24 24" fill="white"><path d="M8 5v14l11-7z"/></svg>
  </button>
  <div class="video-overlay-frame">
    <iframe src="about:blank" data-src="https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=1" allow="autoplay; encrypted-media" allowfullscreen></iframe>
  </div>
</div>"""

VIDEO_SHOWCASE_CSS = """.video-showcase-card { position:relative; border-radius:16px; overflow:hidden; cursor:pointer; aspect-ratio:16/9; background:#000; }
.video-thumb { width:100%; height:100%; object-fit:cover; opacity:0.75; transition:opacity .2s ease; }
.video-showcase-card:hover .video-thumb { opacity:0.55; }
.video-play-btn { position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); width:64px; height:64px; border-radius:50%; background:rgba(0,0,0,0.6); border:2px solid rgba(255,255,255,0.4); display:flex; align-items:center; justify-content:center; backdrop-filter:blur(4px); transition:transform .2s ease; }
.video-showcase-card:hover .video-play-btn { transform:translate(-50%,-50%) scale(1.1); }
.video-overlay-frame { position:absolute; inset:0; display:none; }
.video-showcase-card.video-playing .video-thumb,
.video-showcase-card.video-playing .video-play-btn { display:none; }
.video-showcase-card.video-playing .video-overlay-frame { display:block; }
.video-overlay-frame iframe { width:100%; height:100%; border:none; }"""

VIDEO_SHOWCASE_JS = """document.querySelectorAll('.video-showcase-card').forEach(card => {
  card.addEventListener('click', function handler() {
    const iframe = card.querySelector('iframe');
    if (iframe && iframe.dataset.src && iframe.src === 'about:blank') {
      iframe.src = iframe.dataset.src;
    }
    card.removeEventListener('click', handler);
  }, { once: true });
});"""

IFRAME_EMBED_HTML = """<div class="responsive-iframe-wrap">
  <iframe src="https://www.openstreetmap.org/export/embed.html?bbox=-0.1276%2C51.5033%2C-0.1076%2C51.5133&layer=mapnik"
    loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>
</div>"""

IFRAME_EMBED_CSS = """.responsive-iframe-wrap { position:relative; width:100%; aspect-ratio:16/9; border-radius:14px; overflow:hidden; border:1px solid rgba(255,255,255,0.08); }
.responsive-iframe-wrap iframe { position:absolute; inset:0; width:100%; height:100%; border:none; }"""

CTA_LIGHT_HTML = """<section class="bg-white py-20 px-6">
  <div class="max-w-3xl mx-auto text-center border border-gray-200 rounded-3xl p-12 bg-gray-50">
    <h2 class="text-3xl md:text-4xl font-bold text-gray-900 mb-4">Ready to get started?</h2>
    <p class="text-gray-500 text-lg mb-8">Tell us about your project and we'll get back to you within a day.</p>
    <div class="flex flex-wrap justify-center gap-3">
      <a href="#" class="px-7 py-3 rounded-xl bg-gray-900 text-white font-semibold hover:bg-gray-800 transition-colors">Hire Us</a>
      <a href="#" class="px-7 py-3 rounded-xl border border-gray-300 text-gray-700 font-semibold hover:bg-white transition-colors">See Pricing</a>
    </div>
  </div>
</section>"""

PRICING_LIGHT_HTML = """<div class="bg-white py-10 px-6">
  <div class="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
    <div class="border border-gray-200 rounded-2xl p-7 bg-white">
      <div class="text-xs font-bold text-gray-400 uppercase tracking-wide mb-3">Starter</div>
      <div class="text-4xl font-bold text-gray-900 mb-1">$29<span class="text-sm text-gray-400 font-medium">/mo</span></div>
      <p class="text-sm text-gray-500 mb-6">For small projects.</p>
      <ul class="space-y-2 text-sm text-gray-600 mb-6">
        <li>✓ 1 project</li><li>✓ Email support</li>
      </ul>
      <button class="w-full py-2.5 rounded-lg border border-gray-300 font-semibold text-gray-800 hover:bg-gray-50">Choose Plan</button>
    </div>
    <div class="border-2 border-gray-900 rounded-2xl p-7 bg-white relative shadow-lg">
      <div class="absolute -top-3 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-xs font-bold px-3 py-1 rounded-full">Popular</div>
      <div class="text-xs font-bold text-gray-400 uppercase tracking-wide mb-3">Pro</div>
      <div class="text-4xl font-bold text-gray-900 mb-1">$79<span class="text-sm text-gray-400 font-medium">/mo</span></div>
      <p class="text-sm text-gray-500 mb-6">For growing teams.</p>
      <ul class="space-y-2 text-sm text-gray-600 mb-6">
        <li>✓ 10 projects</li><li>✓ Priority support</li><li>✓ Advanced analytics</li>
      </ul>
      <button class="w-full py-2.5 rounded-lg bg-gray-900 text-white font-semibold hover:bg-gray-800">Choose Plan</button>
    </div>
    <div class="border border-gray-200 rounded-2xl p-7 bg-white">
      <div class="text-xs font-bold text-gray-400 uppercase tracking-wide mb-3">Enterprise</div>
      <div class="text-4xl font-bold text-gray-900 mb-1">Custom</div>
      <p class="text-sm text-gray-500 mb-6">For organizations.</p>
      <ul class="space-y-2 text-sm text-gray-600 mb-6">
        <li>✓ Unlimited projects</li><li>✓ Dedicated support</li>
      </ul>
      <button class="w-full py-2.5 rounded-lg border border-gray-300 font-semibold text-gray-800 hover:bg-gray-50">Contact Sales</button>
    </div>
  </div>
</div>"""

FEATURE_GRID_LIGHT_HTML = """<div class="bg-white py-16 px-6">
  <div class="max-w-5xl mx-auto grid md:grid-cols-2 gap-8">
    <div class="flex gap-4">
      <div class="w-11 h-11 rounded-xl bg-cyan-50 flex items-center justify-center text-xl flex-shrink-0">⚡</div>
      <div><h3 class="font-bold text-gray-900 mb-1">Lightning Fast</h3><p class="text-sm text-gray-500">Optimized builds with modern tooling — nothing feels sluggish.</p></div>
    </div>
    <div class="flex gap-4">
      <div class="w-11 h-11 rounded-xl bg-purple-50 flex items-center justify-center text-xl flex-shrink-0">🔒</div>
      <div><h3 class="font-bold text-gray-900 mb-1">Secure by Default</h3><p class="text-sm text-gray-500">Best practices baked in from day one, not bolted on later.</p></div>
    </div>
    <div class="flex gap-4">
      <div class="w-11 h-11 rounded-xl bg-green-50 flex items-center justify-center text-xl flex-shrink-0">📱</div>
      <div><h3 class="font-bold text-gray-900 mb-1">Fully Responsive</h3><p class="text-sm text-gray-500">Looks right on every screen, not just the one you tested on.</p></div>
    </div>
    <div class="flex gap-4">
      <div class="w-11 h-11 rounded-xl bg-pink-50 flex items-center justify-center text-xl flex-shrink-0">🎨</div>
      <div><h3 class="font-bold text-gray-900 mb-1">Pixel-Perfect Design</h3><p class="text-sm text-gray-500">Details that make it feel premium, not templated.</p></div>
    </div>
  </div>
</div>"""


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
    print(f"➕ Added: {name} ({category})")


def main():
    app = create_app()
    with app.app_context():
        db.create_all()
        add_component("Hero — Light Theme", "Hero", "Clean light-background hero with soft gradient blobs and dark text.",
                       HERO_LIGHT_HTML, tags=["hero", "light"], featured=True, order=2)
        add_component("Hero — Gradient Mesh (Dark)", "Hero", "A second dark hero variant — animated gradient mesh background instead of a grid.",
                       HERO_MESH_HTML, tags=["hero", "dark", "gradient"], featured=True, order=3)
        add_component("Animated Gradient Blobs", "Animation", "Three softly-morphing blurred gradient blobs, pure CSS — a background for any section.",
                       ANIM_BLOB_HTML, ANIM_BLOB_CSS, tags=["animation", "background"], featured=True, order=20)
        add_component("Animated Logo Marquee", "Animation", "Infinite-scrolling logo/text strip — swap the placeholder names for real client logos.",
                       ANIM_MARQUEE_HTML, ANIM_MARQUEE_CSS, tags=["animation", "marquee", "logos"], order=21)
        add_component("Video Showcase Card", "Media", "Thumbnail + play button that swaps to a live embedded video on click (a 'movie holder').",
                       VIDEO_SHOWCASE_HTML, VIDEO_SHOWCASE_CSS, VIDEO_SHOWCASE_JS, tags=["video", "media", "showcase"], featured=True, order=30)
        add_component("Responsive Iframe Embed", "Media", "16:9 responsive container for any iframe — maps, videos, embeds — that never breaks layout.",
                       IFRAME_EMBED_HTML, IFRAME_EMBED_CSS, tags=["iframe", "embed", "media"], order=31)
        add_component("CTA — Light Theme", "CTA", "Light-background call-to-action card with two buttons.",
                       CTA_LIGHT_HTML, tags=["cta", "light"], order=4)
        add_component("Pricing Table — Light Theme", "Pricing", "Same three-tier pricing grid, light background version.",
                       PRICING_LIGHT_HTML, tags=["pricing", "light", "cards"], order=11)
        add_component("Feature Grid — Light Theme", "Features", "2x2 icon feature grid, light background version.",
                       FEATURE_GRID_LIGHT_HTML, tags=["features", "light", "grid"], order=5)
        db.session.commit()
        print("\n✅ Batch 3 components added. Visit /tools/components or /admin/ui-components to see them.")


if __name__ == "__main__":
    main()
